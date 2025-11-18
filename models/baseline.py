"""
Baseline z-score model for volatility spike detection.

This model uses a simple rule-based approach:
- Compute mean and std of midprice_return_std over training data
- Predict spike = 1 if midprice_return_std > mean + 2*std
"""

import numpy as np
from typing import Optional
import joblib


class ZScoreBaseline:
    """
    Z-score baseline model for anomaly detection.
    
    Uses the rule: spike = 1 if feature > mean + threshold * std
    """
    
    def __init__(self, threshold: float = 2.0, feature_name: str = "midprice_return_std"):
        """
        Args:
            threshold: Number of standard deviations above mean for anomaly
            feature_name: Name of the feature to use for z-score calculation
        """
        self.threshold = threshold
        self.feature_name = feature_name
        self.mean_ = None
        self.std_ = None
        self.is_fitted = False
    
    def fit(self, X, y=None):
        """
        Fit the baseline model by computing mean and std.
        
        Args:
            X: DataFrame or array with features
            y: Not used (for sklearn compatibility)
        """
        if hasattr(X, 'columns'):
            # DataFrame
            if self.feature_name not in X.columns:
                raise ValueError(f"Feature '{self.feature_name}' not found in X")
            feature_values = X[self.feature_name].values
        else:
            # Assume array and feature is first column (or specified index)
            feature_values = X if X.ndim == 1 else X[:, 0]
        
        self.mean_ = np.mean(feature_values)
        self.std_ = np.std(feature_values)
        self.is_fitted = True
        
        return self
    
    def predict(self, X):
        """
        Predict spike labels using z-score rule.
        
        Args:
            X: DataFrame or array with features
            
        Returns:
            Array of binary predictions (0 or 1)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before calling predict")
        
        if hasattr(X, 'columns'):
            # DataFrame
            feature_values = X[self.feature_name].values
        else:
            # Array
            feature_values = X if X.ndim == 1 else X[:, 0]
        
        # Z-score rule: anomaly if value > mean + threshold * std
        threshold_value = self.mean_ + self.threshold * self.std_
        predictions = (feature_values > threshold_value).astype(int)
        
        return predictions
    
    def predict_proba(self, X):
        """
        Predict probabilities using z-score distance.
        
        Returns:
            Array of shape (n_samples, 2) with probabilities [P(class=0), P(class=1)]
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before calling predict_proba")
        
        if hasattr(X, 'columns'):
            feature_values = X[self.feature_name].values
        else:
            feature_values = X if X.ndim == 1 else X[:, 0]
        
        # Convert z-scores to pseudo-probabilities using sigmoid
        # z = (value - mean) / std
        z_scores = (feature_values - self.mean_) / (self.std_ + 1e-10)
        
        # Sigmoid: maps z-scores to [0, 1]
        # Adjust so threshold corresponds to 0.5 probability
        adjusted_z = z_scores - self.threshold
        prob_spike = 1 / (1 + np.exp(-adjusted_z))
        prob_normal = 1 - prob_spike
        
        return np.column_stack([prob_normal, prob_spike])
    
    def decision_function(self, X):
        """
        Return decision function (distance from threshold).
        
        Returns:
            Array of decision function values (higher = more likely spike)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before calling decision_function")
        
        if hasattr(X, 'columns'):
            feature_values = X[self.feature_name].values
        else:
            feature_values = X if X.ndim == 1 else X[:, 0]
        
        # Z-score relative to threshold
        z_scores = (feature_values - self.mean_) / (self.std_ + 1e-10)
        return z_scores - self.threshold
    
    def save(self, filepath: str):
        """Save model to disk."""
        joblib.dump(self, filepath)
        print(f"Baseline model saved to {filepath}")
    
    @staticmethod
    def load(filepath: str):
        """Load model from disk."""
        model = joblib.load(filepath)
        print(f"Baseline model loaded from {filepath}")
        return model
    
    def get_params(self):
        """Get model parameters (for MLflow logging)."""
        return {
            "model_type": "z-score_baseline",
            "threshold": self.threshold,
            "feature_name": self.feature_name,
            "mean": self.mean_ if self.is_fitted else None,
            "std": self.std_ if self.is_fitted else None
        }


if __name__ == "__main__":
    # Quick test
    import pandas as pd
    
    # Generate synthetic data
    np.random.seed(42)
    n_samples = 1000
    
    # Normal data with occasional spikes
    normal_vol = np.random.exponential(0.0001, n_samples)
    spike_indices = np.random.choice(n_samples, size=50, replace=False)
    normal_vol[spike_indices] *= 10  # Create spikes
    
    X = pd.DataFrame({
        'midprice_return_std': normal_vol,
        'other_feature': np.random.randn(n_samples)
    })
    
    # Fit model
    model = ZScoreBaseline(threshold=2.0)
    model.fit(X)
    
    print("Model fitted:")
    print(f"  Mean: {model.mean_:.6f}")
    print(f"  Std: {model.std_:.6f}")
    print(f"  Threshold value: {model.mean_ + model.threshold * model.std_:.6f}")
    
    # Make predictions
    preds = model.predict(X)
    print(f"\nPredictions: {preds.sum()} spikes detected out of {len(preds)} samples")
    
    # Probabilities
    probs = model.predict_proba(X)
    print(f"Probability range: [{probs[:, 1].min():.4f}, {probs[:, 1].max():.4f}]")

