"""
Baseline model for volatility spike detection using z-score threshold.
"""

import numpy as np
import pandas as pd
import pickle
from pathlib import Path


class ZScoreBaseline:
    """
    Baseline model using z-score threshold on a specific feature.
    
    Predicts volatility spikes when the feature value exceeds:
    mean + threshold * std
    """
    
    def __init__(self, threshold: float = 2.0, feature_name: str = 'midprice_return_std'):
        """
        Initialize baseline model.
        
        Args:
            threshold: Number of standard deviations above mean to trigger spike
            feature_name: Name of the feature column to use for z-score calculation
        """
        self.threshold = threshold
        self.feature_name = feature_name
        self.mean_ = None
        self.std_ = None
    
    def fit(self, X: pd.DataFrame):
        """
        Fit the baseline model by computing mean and std of the feature.
        
        Args:
            X: Training DataFrame with features
        """
        if self.feature_name not in X.columns:
            raise ValueError(f"Feature '{self.feature_name}' not found in data. Available: {list(X.columns)}")
        
        self.mean_ = X[self.feature_name].mean()
        self.std_ = X[self.feature_name].std()
        
        if self.std_ == 0:
            raise ValueError(f"Standard deviation of '{self.feature_name}' is 0. Cannot compute z-scores.")
        
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict binary labels (0 = normal, 1 = spike).
        
        Args:
            X: DataFrame with features
            
        Returns:
            Binary predictions (0 or 1)
        """
        if self.mean_ is None or self.std_ is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if self.feature_name not in X.columns:
            raise ValueError(f"Feature '{self.feature_name}' not found in data.")
        
        # Compute z-scores
        z_scores = (X[self.feature_name] - self.mean_) / self.std_
        
        # Predict spike if z-score >= threshold
        predictions = (z_scores >= self.threshold).astype(int)
        
        return predictions
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict probabilities for each class.
        
        Args:
            X: DataFrame with features
            
        Returns:
            Probability array of shape (n_samples, 2) where:
            - Column 0: Probability of class 0 (normal)
            - Column 1: Probability of class 1 (spike)
        """
        if self.mean_ is None or self.std_ is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if self.feature_name not in X.columns:
            raise ValueError(f"Feature '{self.feature_name}' not found in data.")
        
        # Compute z-scores
        z_scores = (X[self.feature_name] - self.mean_) / self.std_
        
        # Convert z-score to probability using sigmoid
        # Higher z-score -> higher probability of spike
        # Adjust by threshold so that z_score == threshold gives ~0.5 probability
        adjusted_z = z_scores - self.threshold
        prob_spike = 1 / (1 + np.exp(-adjusted_z))
        
        # Return probabilities for both classes
        proba = np.column_stack([1 - prob_spike, prob_spike])
        
        return proba
    
    def get_params(self) -> dict:
        """
        Get model parameters for logging.
        
        Returns:
            Dictionary of model parameters
        """
        return {
            'model_type': 'zscore_baseline',
            'threshold': self.threshold,
            'feature_name': self.feature_name,
            'mean': float(self.mean_) if self.mean_ is not None else None,
            'std': float(self.std_) if self.std_ is not None else None
        }
    
    def save(self, path: Path):
        """
        Save model to pickle file.
        
        Args:
            path: Path to save the model
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            pickle.dump(self, f)

