"""
Inference script for making predictions with trained models.

Supports both baseline and ML models.
Can load models from artifacts and make predictions on new data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
import mlflow
import mlflow.sklearn
from typing import Optional, Union
import sys
import time

sys.path.insert(0, str(Path(__file__).parent))
from baseline import ZScoreBaseline


class ModelInferencer:
    """Wrapper for making predictions with trained models."""
    
    def __init__(self, model_path: str, model_type: str = "auto"):
        """
        Initialize inferencer.
        
        Args:
            model_path: Path to saved model file (.pkl) or MLflow run ID
            model_type: Type of model ('baseline', 'logistic_regression', or 'auto')
        """
        self.model_path = model_path
        self.model_type = model_type
        self.model = None
        self.feature_cols = [
            'midprice_return_mean',
            'midprice_return_std',
            'bid_ask_spread',
            'trade_intensity',
            'order_book_imbalance'
        ]
        
        self.load_model()
    
    def load_model(self):
        """Load model from file or MLflow."""
        model_path = Path(self.model_path)
        
        if model_path.exists() and model_path.suffix == '.pkl':
            # Load from pickle file
            self.model = joblib.load(model_path)
            print(f"Loaded model from: {model_path}")
            
            # Auto-detect model type
            if self.model_type == "auto":
                if isinstance(self.model, ZScoreBaseline):
                    self.model_type = "baseline"
                else:
                    self.model_type = "logistic_regression"
            
        else:
            # Try to load from MLflow
            try:
                self.model = mlflow.sklearn.load_model(self.model_path)
                print(f"Loaded model from MLflow: {self.model_path}")
                self.model_type = "logistic_regression"
            except Exception as e:
                raise ValueError(f"Could not load model from {self.model_path}: {e}")
        
        print(f"Model type: {self.model_type}")
    
    def predict(self, X: Union[pd.DataFrame, np.ndarray], return_proba: bool = False):
        """
        Make predictions.
        
        Args:
            X: Input features (DataFrame or array)
            return_proba: If True, return probabilities instead of binary predictions
            
        Returns:
            Array of predictions or probabilities
        """
        if self.model is None:
            raise ValueError("Model not loaded")
        
        # Ensure X has required features
        if isinstance(X, pd.DataFrame):
            # Check if all features are present
            missing_features = set(self.feature_cols) - set(X.columns)
            if missing_features:
                raise ValueError(f"Missing features: {missing_features}")
            X_input = X[self.feature_cols]
        else:
            X_input = X
        
        if return_proba:
            # Return probabilities
            if hasattr(self.model, 'predict_proba'):
                probs = self.model.predict_proba(X_input)
                return probs[:, 1]  # Return probability of spike (class 1)
            else:
                raise ValueError("Model does not support probability predictions")
        else:
            # Return binary predictions
            return self.model.predict(X_input)
    
    def predict_batch(self, data_path: str, output_path: Optional[str] = None):
        """
        Make predictions on a batch of data from file.
        
        Args:
            data_path: Path to input data (Parquet)
            output_path: Path to save predictions (optional)
            
        Returns:
            DataFrame with predictions
        """
        start_time = time.time()
        
        print(f"\nMaking batch predictions...")
        print(f"  Input: {data_path}")
        
        # Load data
        df = pd.read_parquet(data_path)
        print(f"  Loaded {len(df)} samples")
        
        # Make predictions
        predictions = self.predict(df, return_proba=False)
        probabilities = self.predict(df, return_proba=True)
        
        # Calculate latency
        inference_time = time.time() - start_time
        window_size = 60  # seconds (feature window size)
        max_allowed = 2 * window_size  # 120 seconds (2x real-time requirement)
        
        # Add predictions to DataFrame
        df['predicted_label'] = predictions
        df['spike_probability'] = probabilities
        
        # Count spikes
        spike_count = predictions.sum()
        spike_pct = (spike_count / len(predictions)) * 100
        print(f"  Predicted spikes: {spike_count} ({spike_pct:.2f}%)")
        
        # Print latency metrics (required for Milestone 3)
        print(f"\n{'='*60}")
        print(f"Inference Latency Check")
        print(f"{'='*60}")
        print(f"  Inference time: {inference_time:.3f} seconds")
        print(f"  Window size: {window_size} seconds")
        print(f"  Max allowed: {max_allowed} seconds (2x window size)")
        if inference_time < max_allowed:
            print(f"  Status: ✓ PASS (< 2x real-time)")
        else:
            print(f"  Status: ✗ FAIL (exceeds 2x real-time)")
        print(f"{'='*60}")
        
        # Save if output path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(output_file, index=False)
            print(f"  Saved predictions to: {output_path}")
        
        return df


def main():
    """Example usage of inference script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Make predictions with trained models")
    parser.add_argument("--model-path", required=True, help="Path to model file or MLflow run ID")
    parser.add_argument("--data-path", required=True, help="Path to input data (Parquet)")
    parser.add_argument("--output-path", default=None, help="Path to save predictions (optional)")
    parser.add_argument("--model-type", default="auto", 
                       choices=['auto', 'baseline', 'logistic_regression'],
                       help="Type of model")
    
    args = parser.parse_args()
    
    # Create inferencer
    inferencer = ModelInferencer(
        model_path=args.model_path,
        model_type=args.model_type
    )
    
    # Make predictions
    results = inferencer.predict_batch(
        data_path=args.data_path,
        output_path=args.output_path
    )
    
    print("\nInference complete!")
    print(f"Results shape: {results.shape}")
    print(f"\nFirst few predictions:")
    print(results[['predicted_label', 'spike_probability']].head(10))


if __name__ == "__main__":
    main()

