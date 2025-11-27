#!/usr/bin/env python3
"""
FastAPI Application for Crypto Volatility Detection
Provides /health, /predict, /version, and /metrics endpoints.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml
import mlflow
import mlflow.sklearn
import mlflow.xgboost
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Import predictor from models
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.infer import VolatilityPredictor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Crypto Volatility Detection API",
    description="API for real-time volatility spike detection",
    version="1.0.0"
)

# Prometheus metrics
PREDICTION_COUNTER = Counter(
    'volatility_predictions_total',
    'Total number of predictions made',
    ['prediction']
)

PREDICTION_LATENCY = Histogram(
    'volatility_prediction_latency_seconds',
    'Prediction latency in seconds',
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

PREDICTION_PROBABILITY = Histogram(
    'volatility_prediction_probability',
    'Prediction probability distribution',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

MODEL_LOAD_TIME = Gauge(
    'model_load_time_seconds',
    'Time taken to load the model'
)

# Global predictor instance
predictor: Optional[VolatilityPredictor] = None
model_version: str = "unknown"
model_loaded_at: Optional[float] = None


class FeatureRequest(BaseModel):
    """Request model for prediction endpoint."""
    price: float = Field(..., description="Current price")
    midprice: Optional[float] = Field(None, description="Midprice (bid+ask)/2")
    return_1s: Optional[float] = Field(0.0, description="1-second return")
    return_5s: Optional[float] = Field(0.0, description="5-second return")
    return_30s: Optional[float] = Field(0.0, description="30-second return")
    return_60s: Optional[float] = Field(0.0, description="60-second return")
    volatility: Optional[float] = Field(0.0, description="Rolling volatility")
    trade_intensity: Optional[float] = Field(0.0, description="Trade intensity")
    spread_abs: Optional[float] = Field(None, description="Absolute bid-ask spread")
    spread_rel: Optional[float] = Field(None, description="Relative bid-ask spread")
    order_book_imbalance: Optional[float] = Field(None, description="Order book imbalance")


class PredictionResponse(BaseModel):
    """Response model for prediction endpoint."""
    prediction: int = Field(..., description="Binary prediction (0=normal, 1=spike)")
    probability: float = Field(..., description="Probability of volatility spike")
    model_version: str = Field(..., description="Model version used")
    timestamp: float = Field(..., description="Prediction timestamp")


def load_model(config_path: str = "config.yaml"):
    """
    Load model from MLflow Model Registry or MLflow runs.
    
    Priority order:
    1. MODEL_VARIANT env var (e.g., "models:/xgb_model/Production" or "models:/xgb_model/1")
    2. Latest MLflow run with run_name matching model type
    3. Local pickle file (fallback for backward compatibility)
    
    Supports:
    - MODEL_VARIANT: MLflow model registry path (e.g., "models:/xgb_model/Production")
    - MODEL_RUN_NAME: Specific MLflow run name (e.g., "ml_xgboost")
    - MODEL_RUN_ID: Specific MLflow run ID
    """
    global predictor, model_version, model_loaded_at
    
    start_time = time.time()
    
    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Setup MLflow tracking URI
    tracking_uri = config['mlflow']['tracking_uri']
    mlflow.set_tracking_uri(tracking_uri)
    experiment_name = config['mlflow']['experiment_name']
    
    model_variant = os.getenv('MODEL_VARIANT', None)
    model_run_name = os.getenv('MODEL_RUN_NAME', 'ml_xgboost')  # Default to xgboost
    model_run_id = os.getenv('MODEL_RUN_ID', None)
    
    loaded_from = None
    mlflow_model = None
    scaler = None
    
    try:
        # Priority 1: Load from MLflow Model Registry (if MODEL_VARIANT is set)
        if model_variant and model_variant.startswith('models:/'):
            logger.info(f"Loading model from MLflow Model Registry: {model_variant}")
            try:
                mlflow_model = mlflow.pyfunc.load_model(model_variant)
                model_version = model_variant
                loaded_from = "mlflow_registry"
                logger.info(f"✅ Loaded model from Model Registry: {model_variant}")
            except Exception as e:
                logger.warning(f"Failed to load from Model Registry {model_variant}: {e}")
                logger.info("Falling back to MLflow runs...")
        
        # Priority 2: Load from specific MLflow run ID
        if mlflow_model is None and model_run_id:
            logger.info(f"Loading model from MLflow run ID: {model_run_id}")
            try:
                run = mlflow.get_run(model_run_id)
                model_uri = f"runs:/{model_run_id}/model"
                mlflow_model = mlflow.sklearn.load_model(model_uri)
                model_version = f"run-{model_run_id}"
                loaded_from = "mlflow_run_id"
                logger.info(f"✅ Loaded model from run ID: {model_run_id}")
            except Exception as e:
                logger.warning(f"Failed to load from run ID {model_run_id}: {e}")
        
        # Priority 3: Load from latest MLflow run by run_name
        if mlflow_model is None:
            logger.info(f"Searching for latest MLflow run with name: {model_run_name}")
            try:
                mlflow.set_experiment(experiment_name)
                experiment = mlflow.get_experiment_by_name(experiment_name)
                
                if experiment is None:
                    raise ValueError(f"Experiment '{experiment_name}' not found in MLflow")
                
                # Search for runs with matching run_name
                runs = mlflow.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    filter_string=f"tags.mlflow.runName = '{model_run_name}'",
                    order_by=["start_time DESC"],
                    max_results=1
                )
                
                if len(runs) > 0:
                    run_id = runs.iloc[0]['run_id']
                    run = mlflow.get_run(run_id)
                    model_uri = f"runs:/{run_id}/model"
                    
                    # Try to load as sklearn model (works for XGBoost wrapped in sklearn)
                    try:
                        mlflow_model = mlflow.sklearn.load_model(model_uri)
                    except:
                        # Fallback to pyfunc
                        mlflow_model = mlflow.pyfunc.load_model(model_uri)
                    
                    model_version = f"run-{run_id}"
                    loaded_from = "mlflow_run"
                    logger.info(f"✅ Loaded model from MLflow run: {run_id} (name: {model_run_name})")
                else:
                    logger.warning(f"No runs found with name '{model_run_name}' in experiment '{experiment_name}'")
            except Exception as e:
                logger.warning(f"Failed to load from MLflow runs: {e}")
                logger.info("Falling back to local pickle file...")
        
        # Priority 4: Fallback to local pickle file (backward compatibility)
        if mlflow_model is None:
            logger.info("Loading model from local pickle file (fallback)")
            models_dir = Path(config['modeling']['models_dir'])
            model_path = models_dir / "xgb_model.pkl"
            
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Model not found. Tried:\n"
                    f"  1. MLflow Model Registry: {model_variant or 'not set'}\n"
                    f"  2. MLflow Run: {model_run_name}\n"
                    f"  3. Local file: {model_path}\n"
                    f"Please ensure MODEL_VARIANT is set or train a model first."
                )
            
            # Load from local pickle
            predictor = VolatilityPredictor(
                str(model_path),
                scaler_path=None,  # xgb_model.pkl was trained without a scaler
                model_type="ml"
            )
            model_version = f"local-{int(model_path.stat().st_mtime)}"
            loaded_from = "local_pickle"
            logger.info(f"✅ Loaded model from local file: {model_path}")
        
        else:
            # Create a wrapper for MLflow-loaded models
            # MLflow models loaded via sklearn/pyfunc can be used directly
            logger.info("Creating MLflow model wrapper")
            
            class MLflowVolatilityPredictor:
                """Wrapper to make MLflow models compatible with VolatilityPredictor interface."""
                def __init__(self, mlflow_model, model_version_str):
                    self.model = mlflow_model
                    self.model_version = model_version_str
                    self.scaler = None  # MLflow models may have scaler baked in
                    self.model_type = 'ml'
                
                def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
                    """Predict probabilities using MLflow model."""
                    # MLflow models expect DataFrame input
                    try:
                        if hasattr(self.model, 'predict_proba'):
                            # sklearn-style model (XGBoost wrapped in sklearn)
                            proba = self.model.predict_proba(X)
                            # Ensure 2D array with 2 columns
                            if proba.shape[1] == 1:
                                # If only one column, assume it's probability of class 1
                                proba = np.column_stack([1 - proba[:, 0], proba[:, 0]])
                            return proba
                        elif hasattr(self.model, 'predict'):
                            # pyfunc model - try to get probabilities
                            predictions = self.model.predict(X)
                            # If predictions are probabilities (2D array), return as-is
                            if isinstance(predictions, np.ndarray) and len(predictions.shape) == 2:
                                return predictions
                            # Otherwise convert binary predictions to probabilities
                            proba = np.zeros((len(predictions), 2))
                            proba[:, 1] = predictions
                            proba[:, 0] = 1 - predictions
                            return proba
                        else:
                            raise ValueError("MLflow model doesn't have predict or predict_proba method")
                    except Exception as e:
                        logger.error(f"Error in MLflow model prediction: {e}")
                        raise
            
            # Create wrapper
            predictor = MLflowVolatilityPredictor(mlflow_model, model_version)
            logger.info(f"✅ Created MLflow model wrapper (loaded from: {loaded_from})")
    
    except Exception as e:
        logger.error(f"Failed to load model: {e}", exc_info=True)
        raise
    
    model_loaded_at = time.time()
    load_time = model_loaded_at - start_time
    MODEL_LOAD_TIME.set(load_time)
    
    logger.info(f"✅ Model loaded successfully from {loaded_from} (version: {model_version}) in {load_time:.3f}s")
    
    return predictor


@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    try:
        config_path = os.getenv('CONFIG_PATH', 'config.yaml')
        load_model(config_path)
        logger.info("API startup complete")
    except Exception as e:
        logger.error(f"Failed to load model on startup: {e}", exc_info=True)
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy" if predictor is not None else "unhealthy",
        "model_loaded": predictor is not None,
        "model_version": model_version,
        "timestamp": time.time()
    }
    
    if predictor is None:
        return JSONResponse(
            status_code=503,
            content=health_status
        )
    
    return health_status


@app.get("/version")
async def get_version():
    """Get API and model version information."""
    return {
        "api_version": "1.0.0",
        "model_version": model_version,
        "model_loaded_at": model_loaded_at,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(features: FeatureRequest):
    """
    Predict volatility spike from features.
    
    Returns:
    - prediction: 0 (normal) or 1 (volatility spike)
    - probability: Probability of volatility spike (0-1)
    - model_version: Version of model used
    - timestamp: Prediction timestamp
    """
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    
    try:
        # Convert request to DataFrame
        feature_dict = features.dict()
        
        # Ensure midprice is set (use price if not provided)
        if feature_dict.get('midprice') is None:
            feature_dict['midprice'] = feature_dict['price']
        
        # xgb_model.pkl expects exactly these 5 features (from training code):
        # 1. midprice_return_mean
        # 2. midprice_return_std
        # 3. bid_ask_spread
        # 4. trade_intensity
        # 5. order_book_imbalance
        
        # Compute midprice_return_mean and midprice_return_std from the return features
        return_1s = feature_dict.get('return_1s', 0.0) or 0.0
        return_5s = feature_dict.get('return_5s', 0.0) or 0.0
        return_30s = feature_dict.get('return_30s', 0.0) or 0.0
        return_60s = feature_dict.get('return_60s', 0.0) or 0.0
        
        # Collect all non-zero returns for computing mean and std
        returns = [r for r in [return_1s, return_5s, return_30s, return_60s] 
                  if r is not None and not np.isnan(r) and r != 0.0]
        
        if len(returns) > 0:
            midprice_return_mean = float(np.mean(returns))
            midprice_return_std = float(np.std(returns)) if len(returns) > 1 else 0.0
        else:
            # If no returns provided, use 0.0 (or could use volatility if available)
            midprice_return_mean = 0.0
            midprice_return_std = feature_dict.get('volatility', 0.0) or 0.0
        
        # bid_ask_spread is the absolute spread
        bid_ask_spread = feature_dict.get('spread_abs', 0.0) or 0.0
        
        # trade_intensity and order_book_imbalance come directly from the request
        trade_intensity = feature_dict.get('trade_intensity', 0.0) or 0.0
        order_book_imbalance = feature_dict.get('order_book_imbalance', 0.0) or 0.0
        
        # Create feature vector with EXACTLY the 5 features the model expects
        feature_vector = {
            'midprice_return_mean': midprice_return_mean,
            'midprice_return_std': midprice_return_std,
            'bid_ask_spread': bid_ask_spread,
            'trade_intensity': trade_intensity,
            'order_book_imbalance': order_book_imbalance
        }
        
        # Create DataFrame with exactly these 5 features in the correct order
        df = pd.DataFrame([feature_vector], columns=[
            'midprice_return_mean',
            'midprice_return_std',
            'bid_ask_spread',
            'trade_intensity',
            'order_book_imbalance'
        ])
        
        logger.debug(f"Created feature vector for xgb_model.pkl: {feature_vector}")
        
        # Get prediction probability
        probabilities = predictor.predict_proba(df)
        prob_value = probabilities[0, 1] if probabilities.shape[1] > 1 else probabilities[0, 0]
        
        # Use threshold (default 0.5, can be optimized)
        threshold = 0.5
        prediction = 1 if prob_value >= threshold else 0
        
        # Record metrics
        latency = time.time() - start_time
        PREDICTION_LATENCY.observe(latency)
        PREDICTION_PROBABILITY.observe(prob_value)
        PREDICTION_COUNTER.labels(prediction=str(prediction)).inc()
        
        return PredictionResponse(
            prediction=prediction,
            probability=float(prob_value),
            model_version=model_version,
            timestamp=time.time()
        )
    
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

