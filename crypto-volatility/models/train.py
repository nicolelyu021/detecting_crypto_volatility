#!/usr/bin/env python3
"""
Model Training Script
Trains baseline (z-score) and ML models for volatility spike detection.
Logs everything to MLflow.
"""

import json
import logging
import os
import pickle
import sys
from pathlib import Path
from typing import Dict, Tuple

import mlflow
import mlflow.sklearn
from mlflow.exceptions import MlflowException
import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BaselineModel:
    """Baseline model using z-score threshold."""

    def __init__(self, threshold_std: float = 2.0):
        self.threshold_std = threshold_std
        self.mean_ = None
        self.std_ = None

    def fit(self, X, y):
        """Fit the baseline model."""
        # Compute mean and std of volatility feature
        volatility_col = "volatility" if "volatility" in X.columns else X.columns[0]
        self.mean_ = X[volatility_col].mean()
        self.std_ = X[volatility_col].std()
        logger.info(f"Baseline model: mean={self.mean_:.6f}, std={self.std_:.6f}")
        return self

    def predict(self, X):
        """Predict using z-score threshold."""
        volatility_col = "volatility" if "volatility" in X.columns else X.columns[0]
        z_scores = (X[volatility_col] - self.mean_) / self.std_
        return (z_scores >= self.threshold_std).astype(int)

    def predict_proba(self, X):
        """Predict probabilities (distance from threshold)."""
        volatility_col = "volatility" if "volatility" in X.columns else X.columns[0]
        z_scores = (X[volatility_col] - self.mean_) / self.std_
        # Convert z-score to probability-like score
        prob = 1 / (1 + np.exp(-(z_scores - self.threshold_std)))
        return np.column_stack([1 - prob, prob])


def load_features(config_path: str = "config.yaml") -> pd.DataFrame:
    """Load features from Parquet file."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    features_path = Path(config["features"]["data_dir"]) / "features.parquet"

    if not features_path.exists():
        raise FileNotFoundError(f"Features file not found: {features_path}")

    logger.info(f"Loading features from {features_path}")
    df = pd.read_parquet(features_path)
    logger.info(f"Loaded {len(df)} feature rows")

    return df


def compute_future_volatility_and_labels(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """Compute future volatility and create labels."""
    logger.info("Computing future volatility and labels...")

    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)

    prediction_horizon = config["features"]["prediction_horizon"]  # 60 seconds
    threshold_percentile = config["modeling"]["threshold_percentile"]

    # Compute future volatility for each row
    future_volatility = []
    for idx in range(len(df)):
        current_time = df.loc[idx, "timestamp"]
        future_time = current_time + prediction_horizon

        # Find rows within the future window
        future_mask = (df["timestamp"] > current_time) & (df["timestamp"] <= future_time)
        future_returns = df.loc[future_mask, "return_1s"].dropna()

        if len(future_returns) > 1:
            vol = future_returns.std()
        else:
            vol = np.nan

        future_volatility.append(vol)

    df["future_volatility"] = future_volatility

    # Compute threshold
    vol_data = df["future_volatility"].dropna()
    threshold = np.percentile(vol_data, threshold_percentile)

    # Create binary labels
    df["label"] = (df["future_volatility"] >= threshold).astype(int)

    logger.info(f"Threshold ({threshold_percentile}th percentile): {threshold:.8f}")
    logger.info(f"Label distribution: {df['label'].value_counts().to_dict()}")
    logger.info(f"Spike rate: {df['label'].mean()*100:.2f}%")

    return df, threshold


def time_based_split(
    df: pd.DataFrame, config: Dict
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split data into train, validation, and test sets based on time.
    Ensures positive samples (label=1) are proportionally distributed across splits
    according to the configured ratios, while maintaining temporal order.
    """
    logger.info("Performing stratified time-based split with proportional positive distribution...")

    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)

    train_ratio = config["modeling"]["train_ratio"]
    val_ratio = config["modeling"]["val_ratio"]
    test_ratio = config["modeling"]["test_ratio"]

    # Validate ratios sum to 1
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "Ratios must sum to 1"

    n = len(df)

    # Check label distribution and find optimal split points
    if "label" in df.columns:
        total_positives = df["label"].sum()
        overall_positive_rate = df["label"].mean()

        if total_positives == 0:
            logger.error("No positive samples in entire dataset! Cannot train model.")
            raise ValueError("No positive samples in dataset")

        logger.info(
            f"Overall dataset: {total_positives} positives ({overall_positive_rate*100:.2f}%)"
        )

        # Target number of positives per split (proportional to ratios)
        target_train_positives = int(total_positives * train_ratio)
        target_val_positives = int(total_positives * val_ratio)
        target_test_positives = (
            total_positives - target_train_positives - target_val_positives
        )  # Remaining

        logger.info(
            f"Target positives (proportional) - Train: {target_train_positives}, Val: {target_val_positives}, Test: {target_test_positives}"
        )

        # Get positive sample indices (sorted by position)
        positive_indices = sorted(df[df["label"] == 1].index.tolist())

        # Find optimal split points to achieve proportional distribution
        # Strategy: Find split points where cumulative positives match targets

        # Find train_end: point where we have approximately target_train_positives
        train_end = int(n * train_ratio)  # Start with ratio-based estimate
        train_pos_count = sum(1 for idx in positive_indices if idx < train_end)

        # Adjust train_end to get closer to target
        if train_pos_count < target_train_positives:
            # Need more positives - extend forward
            for idx in positive_indices:
                if idx >= train_end:
                    train_pos_count += 1
                    train_end = idx + 1
                    if train_pos_count >= target_train_positives:
                        break
        elif train_pos_count > target_train_positives:
            # Too many positives - try to reduce (but maintain minimum size)
            min_train_size = int(n * 0.4)
            for idx in reversed(positive_indices):
                if (
                    idx < train_end
                    and train_pos_count > target_train_positives
                    and train_end > min_train_size
                ):
                    train_pos_count -= 1
                    train_end = idx
                    if train_pos_count <= target_train_positives:
                        break

        # Find val_end: point where validation has approximately target_val_positives
        val_end = int(n * (train_ratio + val_ratio))  # Start with ratio-based estimate
        val_pos_count = sum(1 for idx in positive_indices if train_end <= idx < val_end)

        # Adjust val_end to get closer to target
        if val_pos_count < target_val_positives:
            # Need more positives - extend forward
            for idx in positive_indices:
                if idx >= val_end:
                    val_pos_count += 1
                    val_end = idx + 1
                    if val_pos_count >= target_val_positives:
                        break
        elif val_pos_count > target_val_positives:
            # Too many positives - try to reduce (but maintain minimum size)
            min_val_size = int(n * 0.1)
            min_test_size = int(n * 0.1)
            for idx in reversed(positive_indices):
                if train_end <= idx < val_end and val_pos_count > target_val_positives:
                    if val_end - train_end > min_val_size:  # Maintain minimum val size
                        val_pos_count -= 1
                        val_end = idx
                        if val_pos_count <= target_val_positives:
                            break

        # Ensure minimum sizes are maintained
        min_train_size = int(n * 0.4)
        min_val_size = int(n * 0.1)
        min_test_size = int(n * 0.1)

        train_end = max(min_train_size, min(train_end, n - min_val_size - min_test_size))
        val_end = max(train_end + min_val_size, min(val_end, n - min_test_size))

        # Final split
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()

        # Calculate actual positive counts
        train_pos = train_df["label"].sum()
        val_pos = val_df["label"].sum()
        test_pos = test_df["label"].sum()

        logger.info(f"Actual positives - Train: {train_pos}, Val: {val_pos}, Test: {test_pos}")
        logger.info(
            f"Target vs Actual - Train: {target_train_positives} vs {train_pos} (diff: {train_pos - target_train_positives})"
        )
        logger.info(
            f"Target vs Actual - Val: {target_val_positives} vs {val_pos} (diff: {val_pos - target_val_positives})"
        )
        logger.info(
            f"Target vs Actual - Test: {target_test_positives} vs {test_pos} (diff: {test_pos - target_test_positives})"
        )

    else:
        # No labels, use simple time-based split
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()

    # Log final split statistics
    logger.info(f"\nFinal split sizes:")
    logger.info(f"  Train: {len(train_df)} samples ({len(train_df)/n*100:.1f}%)")
    logger.info(f"  Validation: {len(val_df)} samples ({len(val_df)/n*100:.1f}%)")
    logger.info(f"  Test: {len(test_df)} samples ({len(test_df)/n*100:.1f}%)")

    if "label" in df.columns:
        train_pos = train_df["label"].sum()
        val_pos = val_df["label"].sum()
        test_pos = test_df["label"].sum()

        logger.info(f"\nFinal label distribution:")
        logger.info(
            f"  Train - Spikes: {train_pos}, Normal: {(train_df['label']==0).sum()}, Rate: {train_df['label'].mean()*100:.2f}%"
        )
        logger.info(
            f"  Validation - Spikes: {val_pos}, Normal: {(val_df['label']==0).sum()}, Rate: {val_df['label'].mean()*100:.2f}%"
        )
        logger.info(
            f"  Test - Spikes: {test_pos}, Normal: {(test_df['label']==0).sum()}, Rate: {test_df['label'].mean()*100:.2f}%"
        )

        # Calculate proportional distribution
        total_pos = train_pos + val_pos + test_pos
        if total_pos > 0:
            train_pct = (train_pos / total_pos) * 100
            val_pct = (val_pos / total_pos) * 100
            test_pct = (test_pos / total_pos) * 100
            logger.info(f"\nProportional distribution of positives:")
            logger.info(f"  Train: {train_pct:.1f}% (target: {train_ratio*100:.1f}%)")
            logger.info(f"  Validation: {val_pct:.1f}% (target: {val_ratio*100:.1f}%)")
            logger.info(f"  Test: {test_pct:.1f}% (target: {test_ratio*100:.1f}%)")

        # Verify all splits have positives
        if train_pos == 0 or val_pos == 0 or test_pos == 0:
            logger.warning("⚠️  One or more splits still have zero positive samples!")
            logger.warning(
                "   This may affect model training. Consider adjusting threshold_percentile in config."
            )

    return train_df, val_df, test_df


def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare features and labels for training."""
    # Select numeric features (exclude metadata)
    feature_cols = [
        "price",
        "midprice",
        "return_1s",
        "return_5s",
        "return_30s",
        "return_60s",
        "volatility",
        "trade_intensity",
        "spread_abs",
        "spread_rel",
        "order_book_imbalance",
    ]

    # Filter to only columns that exist
    feature_cols = [col for col in feature_cols if col in df.columns]

    X = df[feature_cols].copy()
    y = df["label"].copy()

    # Remove rows with NaN values
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]

    logger.info(f"Prepared {len(X)} samples with {len(feature_cols)} features")

    return X, y


def compute_metrics(y_true, y_pred, y_proba=None) -> Dict:
    """Compute evaluation metrics."""
    metrics = {}

    # Basic metrics
    metrics["accuracy"] = (y_pred == y_true).mean()
    metrics["precision"] = precision_score(y_true, y_pred, zero_division=0)
    metrics["recall"] = recall_score(y_true, y_pred, zero_division=0)
    metrics["f1"] = f1_score(y_true, y_pred, zero_division=0)

    # PR-AUC (required)
    if y_proba is not None:
        metrics["pr_auc"] = average_precision_score(y_true, y_proba)
        metrics["roc_auc"] = roc_auc_score(y_true, y_proba)

    # F1@threshold (optional)
    if y_proba is not None:
        precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
        f1_scores = 2 * (precision * recall) / (precision + recall + 1e-10)
        best_idx = np.argmax(f1_scores)
        metrics["f1_at_threshold"] = f1_scores[best_idx]
        metrics["best_threshold"] = thresholds[best_idx] if best_idx < len(thresholds) else 0.5

    return metrics


def train_baseline_model(X_train, y_train, X_val, y_val, config: Dict, run_name: str = "baseline"):
    """Train baseline model and log to MLflow."""
    logger.info("Training baseline model...")

    mlflow.set_experiment(config["mlflow"]["experiment_name"])

    with mlflow.start_run(run_name=run_name):
        # Train baseline model
        baseline = BaselineModel(threshold_std=config["modeling"]["baseline_threshold_std"])
        baseline.fit(X_train, y_train)

        # Predictions
        y_pred_train = baseline.predict(X_train)
        y_pred_val = baseline.predict(X_val)
        y_proba_train = baseline.predict_proba(X_train)[:, 1]
        y_proba_val = baseline.predict_proba(X_val)[:, 1]

        # Compute metrics
        train_metrics = compute_metrics(y_train, y_pred_train, y_proba_train)
        val_metrics = compute_metrics(y_val, y_pred_val, y_proba_val)

        # Log parameters
        mlflow.log_params(
            {
                "model_type": "baseline_zscore",
                "threshold_std": config["modeling"]["baseline_threshold_std"],
                "mean": float(baseline.mean_),
                "std": float(baseline.std_),
            }
        )

        # Log metrics
        for metric_name, metric_value in val_metrics.items():
            mlflow.log_metric(f"val_{metric_name}", metric_value)
        for metric_name, metric_value in train_metrics.items():
            mlflow.log_metric(f"train_{metric_name}", metric_value)

        # Save model
        models_dir = Path(config["modeling"]["models_dir"])
        models_dir.mkdir(parents=True, exist_ok=True)
        model_path = models_dir / "baseline_model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(baseline, f)

        # Log artifact (use absolute path to avoid filesystem issues)
        try:
            mlflow.log_artifact(str(model_path.absolute()), "model")
        except OSError as e:
            logger.warning(f"Could not log artifact to MLflow: {e}. Model saved to {model_path}")
            # Log model path as parameter instead
            mlflow.log_param("model_path", str(model_path.absolute()))

        logger.info(
            f"Baseline model - Val PR-AUC: {val_metrics.get('pr_auc', 0):.4f}, Val F1: {val_metrics.get('f1', 0):.4f}"
        )

        return baseline, val_metrics


def train_ml_model(
    X_train,
    y_train,
    X_val,
    y_val,
    config: Dict,
    model_type: str = "logistic",
    run_name: str = "ml_model",
):
    """Train ML model and log to MLflow."""
    logger.info(f"Training {model_type} model...")

    mlflow.set_experiment(config["mlflow"]["experiment_name"])

    with mlflow.start_run(run_name=run_name):
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)

        # Train model
        if model_type == "logistic":
            # Optimize for precision and PR-AUC with hyperparameter tuning
            # Use stronger regularization (lower C) to reduce overfitting and improve precision
            # Try multiple C values and select best based on PR-AUC
            best_model = None
            best_pr_auc = 0
            best_c = 1.0
            best_scaler = None

            # Hyperparameter search for C (regularization strength)
            c_values = [0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
            logger.info(f"Tuning logistic regression hyperparameters (C values: {c_values})...")

            for c_val in c_values:
                # Try different solvers for better convergence
                for solver in ["lbfgs", "liblinear"]:
                    try:
                        temp_model = LogisticRegression(
                            C=c_val,
                            random_state=42,
                            max_iter=2000,
                            class_weight="balanced",
                            solver=solver,
                            penalty="l2",  # L2 regularization for better generalization
                        )
                        temp_model.fit(X_train_scaled, y_train)

                        # Evaluate on validation set
                        y_proba_temp = temp_model.predict_proba(X_val_scaled)[:, 1]

                        # Check if validation set has positive samples for PR-AUC
                        if y_val.sum() > 0:
                            pr_auc_temp = average_precision_score(y_val, y_proba_temp)
                        else:
                            # If no positives in validation, use training set for evaluation
                            logger.debug(
                                f"  C={c_val}, solver={solver}: No positives in validation, using training set"
                            )
                            y_proba_train_temp = temp_model.predict_proba(X_train_scaled)[:, 1]
                            pr_auc_temp = (
                                average_precision_score(y_train, y_proba_train_temp)
                                if y_train.sum() > 0
                                else 0.0
                            )

                        if pr_auc_temp > best_pr_auc:
                            best_pr_auc = pr_auc_temp
                            best_model = temp_model
                            best_c = c_val
                            best_scaler = scaler
                            logger.info(
                                f"  C={c_val}, solver={solver}: PR-AUC={pr_auc_temp:.4f} (new best)"
                            )
                    except Exception as e:
                        logger.debug(f"  C={c_val}, solver={solver}: Failed ({e})")
                        continue

            if best_model is None:
                # Fallback to default if all combinations fail
                logger.warning("Hyperparameter tuning failed, using default parameters")
                best_model = LogisticRegression(
                    random_state=42, max_iter=2000, class_weight="balanced", solver="lbfgs", C=1.0
                )
                best_model.fit(X_train_scaled, y_train)
                best_c = 1.0
                best_scaler = scaler

            model = best_model
            scaler = best_scaler
            logger.info(f"Selected C={best_c} with PR-AUC={best_pr_auc:.4f}")
        elif model_type == "xgboost":
            model = xgb.XGBClassifier(
                random_state=42,
                eval_metric="logloss",
                use_label_encoder=False,
                scale_pos_weight=(
                    (y_train == 0).sum() / (y_train == 1).sum() if (y_train == 1).sum() > 0 else 1
                ),
            )
            model.fit(X_train_scaled, y_train)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Get probabilities first
        y_proba_train = model.predict_proba(X_train_scaled)[:, 1]
        y_proba_val = model.predict_proba(X_val_scaled)[:, 1]

        # Check if validation set has positive samples
        if y_val.sum() == 0:
            logger.warning(
                "Validation set has no positive samples! Using training set for threshold optimization."
            )
            # Use training set for threshold optimization if validation has no positives
            precision_vals, recall_vals, thresholds = precision_recall_curve(y_train, y_proba_train)
            threshold_source = "training"
        else:
            # Find optimal threshold for precision (using validation set)
            precision_vals, recall_vals, thresholds = precision_recall_curve(y_val, y_proba_val)
            threshold_source = "validation"

        # Strategy 1: Threshold that maximizes F1
        f1_scores = 2 * (precision_vals * recall_vals) / (precision_vals + recall_vals + 1e-10)
        best_f1_idx = np.argmax(f1_scores)
        threshold_f1 = thresholds[best_f1_idx] if best_f1_idx < len(thresholds) else 0.5

        # Strategy 2: Threshold that maximizes precision (with minimum recall constraint)
        # Find threshold with precision >= 0.5 and highest recall
        min_precision = 0.5
        precision_mask = precision_vals >= min_precision
        if precision_mask.any():
            valid_indices = np.where(precision_mask)[0]
            best_precision_idx = valid_indices[np.argmax(recall_vals[valid_indices])]
            threshold_precision = (
                thresholds[best_precision_idx] if best_precision_idx < len(thresholds) else 0.5
            )
        else:
            # If no threshold gives precision >= 0.5, use the one with highest precision
            best_precision_idx = np.argmax(precision_vals)
            threshold_precision = (
                thresholds[best_precision_idx] if best_precision_idx < len(thresholds) else 0.5
            )

        # Strategy 3: Threshold that maximizes PR-AUC (use F1 threshold as proxy)
        threshold_optimal = threshold_f1

        # Use optimal threshold for predictions
        y_pred_train = (y_proba_train >= threshold_optimal).astype(int)
        y_pred_val = (y_proba_val >= threshold_optimal).astype(int)

        # Compute metrics with optimal threshold
        train_metrics = compute_metrics(y_train, y_pred_train, y_proba_train)
        val_metrics = compute_metrics(y_val, y_pred_val, y_proba_val)

        # Also compute metrics at precision-focused threshold (for all models)
        y_pred_val_precision = (y_proba_val >= threshold_precision).astype(int)
        val_metrics_precision = compute_metrics(y_val, y_pred_val_precision, y_proba_val)

        logger.info(f"Optimal threshold (F1): {threshold_optimal:.4f}")
        logger.info(f"Precision-focused threshold: {threshold_precision:.4f}")
        logger.info(f"  Precision at optimal: {val_metrics['precision']:.4f}")
        logger.info(f"  Precision at precision-threshold: {val_metrics_precision['precision']:.4f}")
        logger.info(f"  PR-AUC: {val_metrics['pr_auc']:.4f}")

        # Log parameters
        log_params = {
            "model_type": model_type,
            "n_features": X_train.shape[1],
            "n_train_samples": len(X_train),
            "n_val_samples": len(X_val),
        }

        # Add logistic regression specific parameters
        if model_type == "logistic":
            log_params["C"] = best_c
            log_params["solver"] = model.solver if hasattr(model, "solver") else None
            log_params["penalty"] = model.penalty if hasattr(model, "penalty") else None
            log_params["optimal_threshold"] = threshold_optimal
            log_params["precision_threshold"] = threshold_precision

        mlflow.log_params(log_params)

        # Log precision-focused metrics as additional metrics
        if model_type == "logistic":
            mlflow.log_metric(
                "val_precision_at_precision_threshold", val_metrics_precision["precision"]
            )
            mlflow.log_metric("val_recall_at_precision_threshold", val_metrics_precision["recall"])
            mlflow.log_metric("val_f1_at_precision_threshold", val_metrics_precision["f1"])

        # Log metrics
        for metric_name, metric_value in val_metrics.items():
            mlflow.log_metric(f"val_{metric_name}", metric_value)
        for metric_name, metric_value in train_metrics.items():
            mlflow.log_metric(f"train_{metric_name}", metric_value)

        # Save model and scaler
        models_dir = Path(config["modeling"]["models_dir"])
        models_dir.mkdir(parents=True, exist_ok=True)

        model_path = models_dir / f"{model_type}_model.pkl"
        scaler_path = models_dir / f"{model_type}_scaler.pkl"

        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)

        # Log model using sklearn flavor (handles artifact storage better)
        # Note: mlflow.sklearn.log_model may fail with older MLflow server versions
        try:
            mlflow.sklearn.log_model(model, "model")
            mlflow.log_artifact(str(scaler_path.absolute()), "scaler")
        except (OSError, mlflow.exceptions.MlflowException) as e:
            logger.warning(
                f"Could not log model artifact to MLflow: {e}. Model saved to {model_path}"
            )
            # Log model paths as parameters instead
            mlflow.log_param("model_path", str(model_path.absolute()))
            mlflow.log_param("scaler_path", str(scaler_path.absolute()))
        except Exception as e:
            # Catch any other MLflow-related errors
            logger.warning(f"MLflow model logging failed: {e}. Model saved to {model_path}")
            mlflow.log_param("model_path", str(model_path.absolute()))
            mlflow.log_param("scaler_path", str(scaler_path.absolute()))

        logger.info(
            f"{model_type} model - Val PR-AUC: {val_metrics.get('pr_auc', 0):.4f}, Val F1: {val_metrics.get('f1', 0):.4f}"
        )

        return model, scaler, val_metrics


def main():
    """Main training function."""
    import argparse

    parser = argparse.ArgumentParser(description="Train volatility spike detection models")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")
    parser.add_argument(
        "--model-type",
        type=str,
        default="logistic",
        choices=["logistic", "xgboost"],
        help="ML model type to train",
    )

    args = parser.parse_args()
    config_path = os.getenv("CONFIG_PATH", args.config)

    try:
        # Load config
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Setup MLflow
        tracking_uri = config["mlflow"]["tracking_uri"]
        mlflow.set_tracking_uri(tracking_uri)

        # If using local file URI, ensure directory exists
        if tracking_uri.startswith("file://"):
            artifact_path = Path(tracking_uri.replace("file://", ""))
            artifact_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using local MLflow tracking: {artifact_path.absolute()}")
        else:
            # For remote tracking, artifacts are stored on server
            # But we'll save models locally and log paths if artifact upload fails
            logger.info(f"Using remote MLflow tracking: {tracking_uri}")

        # Load features
        df = load_features(config_path)

        # Compute future volatility and labels
        df, threshold = compute_future_volatility_and_labels(df, config)

        # Time-based split
        train_df, val_df, test_df = time_based_split(df, config)

        # Prepare features
        X_train, y_train = prepare_features(train_df)
        X_val, y_val = prepare_features(val_df)
        X_test, y_test = prepare_features(test_df)

        # Save test set for evaluation
        test_path = Path(config["features"]["data_dir"]) / "test_set.parquet"
        test_df.to_parquet(test_path, index=False)
        logger.info(f"Saved test set to {test_path}")

        # Train baseline model
        baseline_model, baseline_metrics = train_baseline_model(
            X_train, y_train, X_val, y_val, config, run_name="baseline_zscore"
        )

        # Train ML model
        ml_model, scaler, ml_metrics = train_ml_model(
            X_train,
            y_train,
            X_val,
            y_val,
            config,
            model_type=args.model_type,
            run_name=f"ml_{args.model_type}",
        )

        # Compare models
        logger.info("=" * 60)
        logger.info("Model Comparison:")
        logger.info("=" * 60)
        logger.info(
            f"Baseline - Val PR-AUC: {baseline_metrics.get('pr_auc', 0):.4f}, Val F1: {baseline_metrics.get('f1', 0):.4f}"
        )
        logger.info(
            f"ML Model - Val PR-AUC: {ml_metrics.get('pr_auc', 0):.4f}, Val F1: {ml_metrics.get('f1', 0):.4f}"
        )
        logger.info("=" * 60)

        logger.info("Training complete! Check MLflow UI for detailed metrics.")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
