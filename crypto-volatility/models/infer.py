#!/usr/bin/env python3
"""
Inference Script
Real-time inference for volatility spike detection.
"""

import json
import logging
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VolatilityPredictor:
    """Predictor for volatility spikes."""
    
    def __init__(self, model_path: str, scaler_path: Optional[str] = None, model_type: str = "ml"):
        """Initialize predictor with saved model."""
        self.model_type = model_type
        
        # Load model
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        # Load scaler if provided
        self.scaler = None
        if scaler_path and os.path.exists(scaler_path):
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
        
        logger.info(f"Loaded {model_type} model from {model_path}")
    
    def predict(self, features: pd.DataFrame) -> np.ndarray:
        """Predict volatility spikes."""
        # First, check what features the model expects
        model_expected_features = None
        if hasattr(self.model, 'feature_names_in_'):
            model_expected_features = list(self.model.feature_names_in_)
        elif hasattr(self.model, 'get_booster'):
            # For XGBoost, check booster
            booster = self.model.get_booster()
            if hasattr(booster, 'feature_names') and booster.feature_names:
                model_expected_features = list(booster.feature_names)
        
        # If we have model's expected features, use them exactly
        if model_expected_features:
            # Create a DataFrame with the exact features the model expects, in the exact order
            X_dict = {}
            for feat_name in model_expected_features:
                if feat_name in features.columns:
                    X_dict[feat_name] = features[feat_name].values
                else:
                    # Fill missing features with 0
                    logger.warning(f"Feature {feat_name} not found in input, using 0")
                    X_dict[feat_name] = np.zeros(len(features))
            
            # Create DataFrame with exact column names and order
            X = pd.DataFrame(X_dict, columns=model_expected_features)
        else:
            # Fallback: use scaler's feature names if available
            if self.scaler is not None and hasattr(self.scaler, 'feature_names_in_'):
                scaler_features = list(self.scaler.feature_names_in_)
                X_dict = {}
                for feat_name in scaler_features:
                    if feat_name in features.columns:
                        X_dict[feat_name] = features[feat_name].values
                    else:
                        X_dict[feat_name] = np.zeros(len(features))
                X = pd.DataFrame(X_dict, columns=scaler_features)
            else:
                # Last resort: use standard feature list
                feature_cols = [
                    'price', 'midprice', 'return_1s', 'return_5s', 'return_30s', 'return_60s',
                    'volatility', 'trade_intensity', 'spread_abs', 'spread_rel', 'order_book_imbalance'
                ]
                feature_cols = [col for col in feature_cols if col in features.columns]
                X = features[feature_cols].copy()
        
        # Handle NaN values
        X = X.fillna(0)
        
        # Scale if scaler available
        if self.scaler is not None:
            # Check how many features the scaler expects
            expected_n_features = getattr(self.scaler, 'n_features_in_', None)
            if expected_n_features is not None and X.shape[1] != expected_n_features:
                # If scaler expects different number of features, try to match
                if hasattr(self.scaler, 'feature_names_in_'):
                    # Use only the features the scaler was trained on
                    scaler_features = list(self.scaler.feature_names_in_)
                    available_scaler_features = [f for f in scaler_features if f in X.columns]
                    if len(available_scaler_features) == expected_n_features:
                        X = X[available_scaler_features]
                    else:
                        # Use scaler's expected features in order
                        X = X[scaler_features] if all(f in X.columns for f in scaler_features) else X.iloc[:, :expected_n_features]
                        logger.warning(f"Using scaler's feature order: {list(X.columns)}")
                else:
                    # Fallback: use first N features that scaler expects
                    logger.warning(f"Scaler expects {expected_n_features} features but got {X.shape[1]}. Using first {expected_n_features} features.")
                    X = X.iloc[:, :expected_n_features]
            
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X.values
        
        # Ensure X_scaled has the right shape for the model
        if hasattr(self.model, 'n_features_in_'):
            model_n_features = self.model.n_features_in_
            if X_scaled.shape[1] != model_n_features:
                logger.warning(f"Model expects {model_n_features} features but got {X_scaled.shape[1]}. Adjusting.")
                if X_scaled.shape[1] > model_n_features:
                    X_scaled = X_scaled[:, :model_n_features]
                else:
                    # Pad with zeros (not ideal but better than failing)
                    padding = np.zeros((X_scaled.shape[0], model_n_features - X_scaled.shape[1]))
                    X_scaled = np.hstack([X_scaled, padding])
        
        # Predict
        predictions = self.model.predict(X_scaled)
        
        return predictions
    
    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        """Predict probabilities of volatility spikes."""
        # First, check what features the model expects
        model_expected_features = None
        if hasattr(self.model, 'feature_names_in_'):
            model_expected_features = list(self.model.feature_names_in_)
        elif hasattr(self.model, 'get_booster'):
            # For XGBoost, check booster
            booster = self.model.get_booster()
            if hasattr(booster, 'feature_names') and booster.feature_names:
                model_expected_features = list(booster.feature_names)
        
        # If we have model's expected features, use them exactly
        if model_expected_features:
            # Create a DataFrame with the exact features the model expects, in the exact order
            X_dict = {}
            for feat_name in model_expected_features:
                if feat_name in features.columns:
                    X_dict[feat_name] = features[feat_name].values
                else:
                    # Fill missing features with 0
                    logger.warning(f"Feature {feat_name} not found in input, using 0")
                    X_dict[feat_name] = np.zeros(len(features))
            
            # Create DataFrame with exact column names and order
            X = pd.DataFrame(X_dict, columns=model_expected_features)
        else:
            # Fallback: use scaler's feature names if available
            if self.scaler is not None and hasattr(self.scaler, 'feature_names_in_'):
                scaler_features = list(self.scaler.feature_names_in_)
                X_dict = {}
                for feat_name in scaler_features:
                    if feat_name in features.columns:
                        X_dict[feat_name] = features[feat_name].values
                    else:
                        X_dict[feat_name] = np.zeros(len(features))
                X = pd.DataFrame(X_dict, columns=scaler_features)
            else:
                # Last resort: use standard feature list
                feature_cols = [
                    'price', 'midprice', 'return_1s', 'return_5s', 'return_30s', 'return_60s',
                    'volatility', 'trade_intensity', 'spread_abs', 'spread_rel', 'order_book_imbalance'
                ]
                feature_cols = [col for col in feature_cols if col in features.columns]
                X = features[feature_cols].copy()
        
        # Scale if scaler available
        # IMPORTANT: Scaler may expect different features than the model
        scaler_features = None
        if self.scaler is not None and hasattr(self.scaler, 'feature_names_in_'):
            scaler_features = list(self.scaler.feature_names_in_)
        
        if self.scaler is not None and scaler_features:
            # Create DataFrame with scaler's expected features (all 11)
            X_for_scaler_dict = {}
            for feat_name in scaler_features:
                if feat_name in features.columns:
                    val = features[feat_name].values
                    # Handle NaN
                    val = np.nan_to_num(val, nan=0.0)
                    X_for_scaler_dict[feat_name] = val
                else:
                    # Fill missing with 0
                    X_for_scaler_dict[feat_name] = np.zeros(len(features))
            
            X_for_scaler = pd.DataFrame(X_for_scaler_dict, columns=scaler_features)
            X_scaled = self.scaler.transform(X_for_scaler)
            
            # Now select only the features the model expects from the scaled result
            if model_expected_features:
                # Convert scaled array back to DataFrame for easier selection
                X_scaled_df = pd.DataFrame(X_scaled, columns=scaler_features)
                # Check which model features exist in scaled features
                available_model_features = [f for f in model_expected_features if f in X_scaled_df.columns]
                
                if len(available_model_features) == len(model_expected_features):
                    # All model features available - select them in the exact order model expects
                    X_scaled = X_scaled_df[model_expected_features].values
                    logger.debug(f"Selected {len(model_expected_features)} model features: {model_expected_features}")
                else:
                    # Some model features missing - log what we have vs what we need
                    missing_features = [f for f in model_expected_features if f not in X_scaled_df.columns]
                    logger.warning(f"Model expects {len(model_expected_features)} features: {model_expected_features}")
                    logger.warning(f"Available in scaled features: {list(X_scaled_df.columns)}")
                    logger.warning(f"Missing features: {missing_features}")
                    logger.warning(f"Found {len(available_model_features)}/{len(model_expected_features)} model features")
                    
                    # If we have some features, use them and pad with zeros for missing ones
                    if available_model_features:
                        # Get the values for available features in model's order
                        result = np.zeros((X_scaled_df.shape[0], len(model_expected_features)))
                        for i, feat_name in enumerate(model_expected_features):
                            if feat_name in X_scaled_df.columns:
                                result[:, i] = X_scaled_df[feat_name].values
                            else:
                                logger.warning(f"Using 0 for missing feature: {feat_name}")
                                result[:, i] = 0.0
                        X_scaled = result
                    else:
                        # No matching features - this is a serious problem
                        logger.error(f"None of the model's expected features found in scaled features!")
                        logger.error(f"Model expects: {model_expected_features}")
                        logger.error(f"Scaler provides: {list(X_scaled_df.columns)}")
                        # Fallback: use first N features (likely wrong but better than crashing)
                        X_scaled = X_scaled[:, :len(model_expected_features)]
            else:
                # No model feature names - use all scaled features
                X_scaled = X_scaled
        else:
            # No scaler - use X directly
            X = X.fillna(0)
            X_scaled = X.values
        
        # Predict probabilities
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X_scaled)
        else:
            # For baseline model, use predict_proba if available
            probabilities = self.model.predict_proba(X_scaled)
        
        return probabilities


def benchmark_inference(predictor: VolatilityPredictor, test_features: pd.DataFrame, n_iterations: int = 100):
    """Benchmark inference speed."""
    logger.info(f"Benchmarking inference on {len(test_features)} samples...")
    
    # Warmup
    _ = predictor.predict(test_features.head(10))
    
    # Benchmark
    start_time = time.time()
    for _ in range(n_iterations):
        _ = predictor.predict(test_features)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = total_time / n_iterations
    time_per_sample = avg_time / len(test_features)
    
    logger.info(f"Benchmark results:")
    logger.info(f"  Total time: {total_time:.4f}s for {n_iterations} iterations")
    logger.info(f"  Average time per batch: {avg_time:.4f}s")
    logger.info(f"  Time per sample: {time_per_sample*1000:.4f}ms")
    logger.info(f"  Throughput: {len(test_features) / avg_time:.2f} samples/second")
    
    # Check if meets requirement (< 2x real-time)
    window_size = 300  # 5 minutes = 300 seconds
    real_time_per_sample = window_size / len(test_features)  # seconds per sample
    speedup = real_time_per_sample / time_per_sample
    
    logger.info(f"  Real-time window: {real_time_per_sample:.4f}s per sample")
    logger.info(f"  Speedup: {speedup:.2f}x")
    
    if speedup >= 2.0:
        logger.info("✓ Inference meets requirement (< 2x real-time)")
    else:
        logger.warning(f"⚠ Inference is {speedup:.2f}x slower than required (need < 2x)")
    
    return {
        'avg_time_per_batch': avg_time,
        'time_per_sample': time_per_sample,
        'throughput': len(test_features) / avg_time,
        'speedup': speedup
    }


def main():
    """Main inference function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run inference for volatility spike detection')
    parser.add_argument(
        '--model-path',
        type=str,
        default='models/artifacts/xgboost_model.pkl',
        help='Path to model file'
    )
    parser.add_argument(
        '--scaler-path',
        type=str,
        default='models/artifacts/xgboost_scaler.pkl',
        help='Path to scaler file (optional)'
    )
    parser.add_argument(
        '--model-type',
        type=str,
        default='ml',
        choices=['ml', 'baseline'],
        help='Model type'
    )
    parser.add_argument(
        '--features-file',
        type=str,
        default=None,
        help='Path to features file for inference (default: test set)'
    )
    parser.add_argument(
        '--benchmark',
        action='store_true',
        help='Run inference benchmark'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file'
    )
    
    args = parser.parse_args()
    config_path = os.getenv('CONFIG_PATH', args.config)
    
    try:
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Load features
        if args.features_file:
            features_path = Path(args.features_file)
        else:
            # Use test set
            features_path = Path(config['features']['data_dir']) / "test_set.parquet"
        
        if not features_path.exists():
            logger.error(f"Features file not found: {features_path}")
            sys.exit(1)
        
        logger.info(f"Loading features from {features_path}")
        df = pd.read_parquet(features_path)
        logger.info(f"Loaded {len(df)} samples")
        
        # Initialize predictor
        model_path = Path(args.model_path)
        scaler_path = Path(args.scaler_path) if args.scaler_path else None
        
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            sys.exit(1)
        
        # Determine model name from path
        model_name = model_path.stem.replace('_model', '').upper()
        logger.info(f"Using {model_name} model for inference")
        
        predictor = VolatilityPredictor(
            str(model_path),
            str(scaler_path) if scaler_path and scaler_path.exists() else None,
            args.model_type
        )
        
        # Prepare features
        feature_cols = [
            'price', 'midprice', 'return_1s', 'return_5s', 'return_30s', 'return_60s',
            'volatility', 'trade_intensity', 'spread_abs', 'spread_rel', 'order_book_imbalance'
        ]
        feature_cols = [col for col in feature_cols if col in df.columns]
        features = df[feature_cols].copy()
        
        # Run inference
        logger.info("Running inference...")
        probabilities = predictor.predict_proba(features)
        prob_values = probabilities[:, 1] if probabilities.shape[1] > 1 else probabilities.flatten()
        
        # Try to load optimal threshold from MLflow, otherwise use percentile-based threshold
        optimal_threshold = None
        try:
            import mlflow
            mlflow.set_tracking_uri(config['mlflow']['tracking_uri'])
            experiment = mlflow.get_experiment_by_name(config['mlflow']['experiment_name'])
            if experiment:
                # Get the latest run for this model type
                runs = mlflow.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    filter_string=f"tags.mlflow.runName = '{model_name.lower()}_model'",
                    order_by=["start_time DESC"],
                    max_results=1
                )
                if not runs.empty:
                    run_id = runs.iloc[0]['run_id']
                    run = mlflow.get_run(run_id)
                    if 'val_best_threshold' in run.data.metrics:
                        optimal_threshold = run.data.metrics['val_best_threshold']
                        logger.info(f"Loaded optimal threshold from MLflow: {optimal_threshold:.4f}")
        except Exception as e:
            logger.debug(f"Could not load threshold from MLflow: {e}")
        
        # Use optimal threshold if available, otherwise use 95th percentile
        if optimal_threshold is not None:
            threshold = optimal_threshold
            threshold_method = "optimal (from MLflow)"
        else:
            # Calculate 95th percentile threshold as fallback
            threshold = np.percentile(prob_values, 95)
            threshold_method = "95th percentile"
            logger.warning(f"Using {threshold_method} threshold: {threshold:.4f} (consider training with threshold tuning)")
        
        logger.info(f"Using {threshold_method} threshold: {threshold:.4f}")
        logger.info(f"Probability statistics: min={prob_values.min():.4f}, max={prob_values.max():.4f}, "
                   f"mean={prob_values.mean():.4f}, median={np.median(prob_values):.4f}")
        
        # Use threshold to make binary predictions
        predictions = (prob_values >= threshold).astype(int)
        
        # Add predictions to dataframe
        df['prediction'] = predictions
        df['probability'] = prob_values
        df['threshold'] = threshold
        df['threshold_method'] = threshold_method
        
        # Save results
        output_path = Path(config['features']['data_dir']) / "predictions.parquet"
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved predictions to {output_path}")
        
        # Print summary
        spike_count = predictions.sum()
        logger.info(f"Predicted {spike_count} volatility spikes ({spike_count/len(predictions)*100:.2f}%)")
        
        # Calculate metrics if labels are available
        if 'label' in df.columns:
            from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, classification_report
            
            y_true = df['label']
            y_pred = df['prediction']
            
            accuracy = (y_pred == y_true).mean()
            precision = precision_score(y_true, y_pred, zero_division=0)
            recall = recall_score(y_true, y_pred, zero_division=0)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            
            cm = confusion_matrix(y_true, y_pred)
            
            logger.info("\n" + "="*60)
            logger.info(f"PERFORMANCE METRICS ({threshold_method} threshold)")
            logger.info("="*60)
            logger.info(f"Accuracy:  {accuracy:.4f}")
            logger.info(f"Precision: {precision:.4f}")
            logger.info(f"Recall:    {recall:.4f}")
            logger.info(f"F1 Score:  {f1:.4f}")
            logger.info(f"\nConfusion Matrix:")
            logger.info(f"  True Negatives:  {cm[0,0]}")
            logger.info(f"  False Positives: {cm[0,1]}")
            logger.info(f"  False Negatives: {cm[1,0]}")
            logger.info(f"  True Positives:  {cm[1,1]}")
            logger.info(f"\nActual spike rate: {y_true.mean()*100:.2f}%")
            logger.info(f"Predicted spike rate: {y_pred.mean()*100:.2f}%")
            logger.info("="*60)
        
        # Benchmark if requested
        if args.benchmark:
            benchmark_inference(predictor, features)
        
        logger.info("Inference complete!")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

