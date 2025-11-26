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


def load_model(config_path: str = "config.yaml") -> VolatilityPredictor:
    """Load the best model (xgb_model.pkl)."""
    global predictor, model_version, model_loaded_at
    
    start_time = time.time()
    
    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Use ONLY xgb_model.pkl - no fallback
    # Note: Based on training code, xgb_model.pkl was trained WITHOUT a scaler
    models_dir = Path(config['modeling']['models_dir'])
    model_path = models_dir / "xgb_model.pkl"
    
    if not model_path.exists():
        raise FileNotFoundError(f"xgb_model.pkl not found at {model_path}. This is the required model.")
    
    # Load model WITHOUT scaler (training code shows no scaler was used)
    predictor = VolatilityPredictor(
        str(model_path),
        scaler_path=None,  # xgb_model.pkl was trained without a scaler
        model_type="ml"
    )
    
    # Set model version from file modification time
    model_version = f"xgb-{int(model_path.stat().st_mtime)}"
    model_loaded_at = time.time()
    load_time = model_loaded_at - start_time
    MODEL_LOAD_TIME.set(load_time)
    
    logger.info(f"Loaded model from {model_path} (version: {model_version}) in {load_time:.3f}s")
    
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

