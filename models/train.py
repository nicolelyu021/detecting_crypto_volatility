"""
Model training script for crypto volatility spike detection.

Trains:
1. Baseline z-score model
2. Logistic Regression model
3. XGBoost model

Logs all experiments to MLflow with metrics, parameters, and artifacts.

Note: Labels are FORWARD-LOOKING - predicting if the NEXT 60-second window
will have high volatility (not the current window).
"""

import pandas as pd
import numpy as np
from pathlib import Path
import mlflow
import mlflow.sklearn
import mlflow.xgboost
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_recall_curve,
    auc,
    f1_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score
)
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import json
from datetime import datetime
import xgboost as xgb

# Import baseline model
import sys
sys.path.insert(0, str(Path(__file__).parent))
from baseline import ZScoreBaseline


def load_and_prepare_data(
    features_path: str = "data/processed/features.parquet",
    threshold_tau: float = 0.000015,
    feature_cols: list = None,
    drop_cols: list = None
):
    """
    Load features and create labels.
    
    Args:
        features_path: Path to features parquet file
        threshold_tau: Threshold for labeling spikes
        feature_cols: List of features to use (if None, use defaults)
        drop_cols: List of columns to drop
        
    Returns:
        DataFrame with features and labels
    """
    print(f"\n{'='*60}")
    print("Loading and preparing data...")
    print(f"{'='*60}")
    
    # Load features
    df = pd.read_parquet(features_path)
    print(f"Loaded {len(df)} samples from {features_path}")
    print(f"Columns: {list(df.columns)}")
    
    # Create labels based on FUTURE volatility (predict next 60 seconds)
    # Shift -1 means: use next row's volatility as the label for current row
    df['label'] = (df['midprice_return_std'].shift(-1) >= threshold_tau).astype(int)
    
    # Drop the last row (has NaN label since there's no "next" window)
    df = df.dropna(subset=['label'])
    df['label'] = df['label'].astype(int)
    
    spike_count = df['label'].sum()
    spike_pct = (spike_count / len(df)) * 100
    print(f"\nLabels created (FORWARD-LOOKING):")
    print(f"  Threshold τ: {threshold_tau}")
    print(f"  Spikes (label=1): {spike_count} ({spike_pct:.2f}%)")
    print(f"  Normal (label=0): {len(df) - spike_count} ({100-spike_pct:.2f}%)")
    print(f"  Note: Predicting if NEXT 60-second window will have high volatility")
    
    # Define feature columns
    if feature_cols is None:
        feature_cols = [
            'midprice_return_mean',
            'midprice_return_std',
            'bid_ask_spread',
            'trade_intensity',
            'order_book_imbalance'
        ]
    
    # Define columns to drop
    if drop_cols is None:
        drop_cols = ['ts', 'pair', 'raw_price', 'window_size', 'window_duration']
    
    # Remove dropped columns if they exist
    for col in drop_cols:
        if col in df.columns:
            df = df.drop(columns=[col])
    
    print(f"\nFeature columns: {feature_cols}")
    print(f"Dropped columns: {drop_cols}")
    
    # Check for missing values
    missing = df[feature_cols + ['label']].isnull().sum()
    if missing.sum() > 0:
        print(f"\nWarning: Missing values detected:")
        print(missing[missing > 0])
        df = df.dropna(subset=feature_cols + ['label'])
        print(f"Dropped rows with missing values. New size: {len(df)}")
    
    return df, feature_cols


def split_data_chronologically(df, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    """
    Split data chronologically (time-based split).
    
    Args:
        df: DataFrame with data
        train_ratio: Fraction for training
        val_ratio: Fraction for validation
        test_ratio: Fraction for testing
        
    Returns:
        train_df, val_df, test_df
    """
    print(f"\n{'='*60}")
    print("Splitting data chronologically...")
    print(f"{'='*60}")
    
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)
    
    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()
    
    print(f"Train set: {len(train_df)} samples ({train_ratio*100:.0f}%)")
    print(f"  Spikes: {train_df['label'].sum()} ({train_df['label'].mean()*100:.2f}%)")
    print(f"\nValidation set: {len(val_df)} samples ({val_ratio*100:.0f}%)")
    print(f"  Spikes: {val_df['label'].sum()} ({val_df['label'].mean()*100:.2f}%)")
    print(f"\nTest set: {len(test_df)} samples ({test_ratio*100:.0f}%)")
    print(f"  Spikes: {test_df['label'].sum()} ({test_df['label'].mean()*100:.2f}%)")
    
    return train_df, val_df, test_df


def compute_metrics(y_true, y_pred, y_proba=None):
    """
    Compute evaluation metrics.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        y_proba: Predicted probabilities for positive class (optional)
        
    Returns:
        Dictionary of metrics
    """
    metrics = {}
    
    # Basic classification metrics
    metrics['accuracy'] = (y_true == y_pred).mean()
    metrics['f1_score'] = f1_score(y_true, y_pred, zero_division=0)
    
    # Precision and recall
    from sklearn.metrics import precision_score, recall_score
    metrics['precision'] = precision_score(y_true, y_pred, zero_division=0)
    metrics['recall'] = recall_score(y_true, y_pred, zero_division=0)
    
    # If probabilities available, compute PR-AUC and ROC-AUC
    if y_proba is not None:
        try:
            # PR-AUC (Precision-Recall AUC) - PRIMARY METRIC
            metrics['pr_auc'] = average_precision_score(y_true, y_proba)
            
            # ROC-AUC
            if len(np.unique(y_true)) > 1:  # Need both classes
                metrics['roc_auc'] = roc_auc_score(y_true, y_proba)
            else:
                metrics['roc_auc'] = 0.0
        except Exception as e:
            print(f"Warning: Could not compute AUC metrics: {e}")
            metrics['pr_auc'] = 0.0
            metrics['roc_auc'] = 0.0
    
    # Confusion matrix elements
    cm = confusion_matrix(y_true, y_pred)
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        metrics['true_negatives'] = int(tn)
        metrics['false_positives'] = int(fp)
        metrics['false_negatives'] = int(fn)
        metrics['true_positives'] = int(tp)
    
    return metrics


def plot_pr_curve(y_true, y_proba, title="Precision-Recall Curve", save_path=None):
    """Plot Precision-Recall curve."""
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    pr_auc = auc(recall, precision)
    
    plt.figure(figsize=(10, 6))
    plt.plot(recall, precision, linewidth=2, label=f'PR-AUC = {pr_auc:.3f}')
    plt.xlabel('Recall', fontsize=12)
    plt.ylabel('Precision', fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved PR curve to {save_path}")
    
    return precision, recall, thresholds


def plot_confusion_matrix(y_true, y_pred, title="Confusion Matrix", save_path=None):
    """Plot confusion matrix."""
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['Normal', 'Spike'], 
                yticklabels=['Normal', 'Spike'])
    plt.xlabel('Predicted', fontsize=12)
    plt.ylabel('True', fontsize=12)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Saved confusion matrix to {save_path}")


def train_baseline_model(X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, artifacts_dir):
    """Train and log baseline z-score model."""
    print(f"\n{'='*60}")
    print("Training Baseline Model (Z-Score)")
    print(f"{'='*60}")
    
    # Start MLflow run
    with mlflow.start_run(run_name="baseline_zscore") as run:
        # Train baseline
        baseline = ZScoreBaseline(threshold=2.0, feature_name='midprice_return_std')
        baseline.fit(X_train)
        
        print(f"Model fitted:")
        print(f"  Mean: {baseline.mean_:.6f}")
        print(f"  Std: {baseline.std_:.6f}")
        print(f"  Threshold: {baseline.mean_ + baseline.threshold * baseline.std_:.6f}")
        
        # Log parameters
        params = baseline.get_params()
        mlflow.log_params(params)
        
        # Predictions on all splits
        train_pred = baseline.predict(X_train)
        train_proba = baseline.predict_proba(X_train)[:, 1]
        
        val_pred = baseline.predict(X_val)
        val_proba = baseline.predict_proba(X_val)[:, 1]
        
        test_pred = baseline.predict(X_test)
        test_proba = baseline.predict_proba(X_test)[:, 1]
        
        # Compute metrics
        train_metrics = compute_metrics(y_train, train_pred, train_proba)
        val_metrics = compute_metrics(y_val, val_pred, val_proba)
        test_metrics = compute_metrics(y_test, test_pred, test_proba)
        
        # Log metrics to MLflow
        for name, value in train_metrics.items():
            mlflow.log_metric(f"train_{name}", value)
        for name, value in val_metrics.items():
            mlflow.log_metric(f"val_{name}", value)
        for name, value in test_metrics.items():
            mlflow.log_metric(f"test_{name}", value)
        
        # Print metrics
        print(f"\nTrain Metrics:")
        print(f"  PR-AUC: {train_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {train_metrics['f1_score']:.4f}")
        print(f"  Precision: {train_metrics['precision']:.4f}")
        print(f"  Recall: {train_metrics['recall']:.4f}")
        
        print(f"\nValidation Metrics:")
        print(f"  PR-AUC: {val_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {val_metrics['f1_score']:.4f}")
        
        print(f"\nTest Metrics:")
        print(f"  PR-AUC: {test_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {test_metrics['f1_score']:.4f}")
        print(f"  Precision: {test_metrics['precision']:.4f}")
        print(f"  Recall: {test_metrics['recall']:.4f}")
        
        # Create plots
        artifacts_path = Path(artifacts_dir) / "baseline"
        artifacts_path.mkdir(parents=True, exist_ok=True)
        
        # PR curve
        plot_pr_curve(y_test, test_proba, 
                     title="Baseline Model - Precision-Recall Curve",
                     save_path=artifacts_path / "pr_curve.png")
        mlflow.log_artifact(artifacts_path / "pr_curve.png")
        plt.close()
        
        # Confusion matrix
        plot_confusion_matrix(y_test, test_pred,
                            title="Baseline Model - Confusion Matrix",
                            save_path=artifacts_path / "confusion_matrix.png")
        mlflow.log_artifact(artifacts_path / "confusion_matrix.png")
        plt.close()
        
        # Save model
        model_path = artifacts_path / "baseline_model.pkl"
        baseline.save(model_path)
        mlflow.log_artifact(model_path)
        
        # Save metrics to JSON
        all_metrics = {
            "train": train_metrics,
            "validation": val_metrics,
            "test": test_metrics
        }
        metrics_path = artifacts_path / "metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(all_metrics, f, indent=2)
        mlflow.log_artifact(metrics_path)
        
        print(f"\nBaseline model saved to: {model_path}")
        print(f"MLflow run ID: {run.info.run_id}")
        
        return baseline, test_metrics


def train_ml_model(X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, artifacts_dir):
    """Train and log Logistic Regression model."""
    print(f"\n{'='*60}")
    print("Training ML Model (Logistic Regression)")
    print(f"{'='*60}")
    
    # Start MLflow run
    with mlflow.start_run(run_name="logistic_regression") as run:
        # Train Logistic Regression
        # Use class_weight='balanced' to handle class imbalance
        lr_model = LogisticRegression(
            class_weight='balanced',
            max_iter=1000,
            random_state=42,
            solver='lbfgs'
        )
        lr_model.fit(X_train[feature_cols], y_train)
        
        print("Model fitted successfully")
        
        # Log parameters
        params = {
            "model_type": "logistic_regression",
            "class_weight": "balanced",
            "max_iter": 1000,
            "solver": "lbfgs",
            "random_state": 42,
            "n_features": len(feature_cols),
            "features": ",".join(feature_cols)
        }
        mlflow.log_params(params)
        
        # Predictions on all splits
        train_pred = lr_model.predict(X_train[feature_cols])
        train_proba = lr_model.predict_proba(X_train[feature_cols])[:, 1]
        
        val_pred = lr_model.predict(X_val[feature_cols])
        val_proba = lr_model.predict_proba(X_val[feature_cols])[:, 1]
        
        test_pred = lr_model.predict(X_test[feature_cols])
        test_proba = lr_model.predict_proba(X_test[feature_cols])[:, 1]
        
        # Compute metrics
        train_metrics = compute_metrics(y_train, train_pred, train_proba)
        val_metrics = compute_metrics(y_val, val_pred, val_proba)
        test_metrics = compute_metrics(y_test, test_pred, test_proba)
        
        # Log metrics to MLflow
        for name, value in train_metrics.items():
            mlflow.log_metric(f"train_{name}", value)
        for name, value in val_metrics.items():
            mlflow.log_metric(f"val_{name}", value)
        for name, value in test_metrics.items():
            mlflow.log_metric(f"test_{name}", value)
        
        # Print metrics
        print(f"\nTrain Metrics:")
        print(f"  PR-AUC: {train_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {train_metrics['f1_score']:.4f}")
        print(f"  Precision: {train_metrics['precision']:.4f}")
        print(f"  Recall: {train_metrics['recall']:.4f}")
        
        print(f"\nValidation Metrics:")
        print(f"  PR-AUC: {val_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {val_metrics['f1_score']:.4f}")
        
        print(f"\nTest Metrics:")
        print(f"  PR-AUC: {test_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {test_metrics['f1_score']:.4f}")
        print(f"  Precision: {test_metrics['precision']:.4f}")
        print(f"  Recall: {test_metrics['recall']:.4f}")
        
        # Feature importance (coefficients)
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'coefficient': lr_model.coef_[0]
        }).sort_values('coefficient', key=abs, ascending=False)
        
        print(f"\nFeature Importance (by coefficient magnitude):")
        print(feature_importance.to_string(index=False))
        
        # Create plots
        artifacts_path = Path(artifacts_dir) / "logistic_regression"
        artifacts_path.mkdir(parents=True, exist_ok=True)
        
        # PR curve
        plot_pr_curve(y_test, test_proba,
                     title="Logistic Regression - Precision-Recall Curve",
                     save_path=artifacts_path / "pr_curve.png")
        mlflow.log_artifact(artifacts_path / "pr_curve.png")
        plt.close()
        
        # Confusion matrix
        plot_confusion_matrix(y_test, test_pred,
                            title="Logistic Regression - Confusion Matrix",
                            save_path=artifacts_path / "confusion_matrix.png")
        mlflow.log_artifact(artifacts_path / "confusion_matrix.png")
        plt.close()
        
        # Feature importance plot
        plt.figure(figsize=(10, 6))
        plt.barh(feature_importance['feature'], feature_importance['coefficient'])
        plt.xlabel('Coefficient', fontsize=12)
        plt.title('Logistic Regression - Feature Importance', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(artifacts_path / "feature_importance.png", dpi=150, bbox_inches='tight')
        mlflow.log_artifact(artifacts_path / "feature_importance.png")
        plt.close()
        
        # Save model
        model_path = artifacts_path / "lr_model.pkl"
        joblib.dump(lr_model, model_path)
        mlflow.sklearn.log_model(lr_model, "model")
        mlflow.log_artifact(model_path)
        
        # Save feature importance
        feature_importance.to_csv(artifacts_path / "feature_importance.csv", index=False)
        mlflow.log_artifact(artifacts_path / "feature_importance.csv")
        
        # Save metrics to JSON
        all_metrics = {
            "train": train_metrics,
            "validation": val_metrics,
            "test": test_metrics
        }
        metrics_path = artifacts_path / "metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(all_metrics, f, indent=2)
        mlflow.log_artifact(metrics_path)
        
        print(f"\nLogistic Regression model saved to: {model_path}")
        print(f"MLflow run ID: {run.info.run_id}")
        
        return lr_model, test_metrics


def train_xgboost_model(X_train, y_train, X_val, y_val, X_test, y_test, feature_cols, artifacts_dir):
    """Train and log XGBoost model."""
    print(f"\n{'='*60}")
    print("Training XGBoost Model")
    print(f"{'='*60}")
    
    # Start MLflow run
    with mlflow.start_run(run_name="xgboost") as run:
        # Calculate scale_pos_weight for class imbalance
        scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
        
        # Train XGBoost
        xgb_model = xgb.XGBClassifier(
            scale_pos_weight=scale_pos_weight,
            max_depth=5,
            learning_rate=0.1,
            n_estimators=100,
            random_state=42,
            eval_metric='logloss',
            use_label_encoder=False
        )
        xgb_model.fit(X_train[feature_cols], y_train)
        
        print("Model fitted successfully")
        
        # Log parameters
        params = {
            "model_type": "xgboost",
            "scale_pos_weight": float(scale_pos_weight),
            "max_depth": 5,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "random_state": 42,
            "n_features": len(feature_cols),
            "features": ",".join(feature_cols)
        }
        mlflow.log_params(params)
        
        # Predictions on all splits
        train_pred = xgb_model.predict(X_train[feature_cols])
        train_proba = xgb_model.predict_proba(X_train[feature_cols])[:, 1]
        
        val_pred = xgb_model.predict(X_val[feature_cols])
        val_proba = xgb_model.predict_proba(X_val[feature_cols])[:, 1]
        
        test_pred = xgb_model.predict(X_test[feature_cols])
        test_proba = xgb_model.predict_proba(X_test[feature_cols])[:, 1]
        
        # Compute metrics
        train_metrics = compute_metrics(y_train, train_pred, train_proba)
        val_metrics = compute_metrics(y_val, val_pred, val_proba)
        test_metrics = compute_metrics(y_test, test_pred, test_proba)
        
        # Log metrics to MLflow
        for name, value in train_metrics.items():
            mlflow.log_metric(f"train_{name}", value)
        for name, value in val_metrics.items():
            mlflow.log_metric(f"val_{name}", value)
        for name, value in test_metrics.items():
            mlflow.log_metric(f"test_{name}", value)
        
        # Print metrics
        print(f"\nTrain Metrics:")
        print(f"  PR-AUC: {train_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {train_metrics['f1_score']:.4f}")
        print(f"  Precision: {train_metrics['precision']:.4f}")
        print(f"  Recall: {train_metrics['recall']:.4f}")
        
        print(f"\nValidation Metrics:")
        print(f"  PR-AUC: {val_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {val_metrics['f1_score']:.4f}")
        
        print(f"\nTest Metrics:")
        print(f"  PR-AUC: {test_metrics['pr_auc']:.4f}")
        print(f"  F1-Score: {test_metrics['f1_score']:.4f}")
        print(f"  Precision: {test_metrics['precision']:.4f}")
        print(f"  Recall: {test_metrics['recall']:.4f}")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': xgb_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"\nFeature Importance (by XGBoost gain):")
        print(feature_importance.to_string(index=False))
        
        # Create plots
        artifacts_path = Path(artifacts_dir) / "xgboost"
        artifacts_path.mkdir(parents=True, exist_ok=True)
        
        # PR curve
        plot_pr_curve(y_test, test_proba,
                     title="XGBoost - Precision-Recall Curve",
                     save_path=artifacts_path / "pr_curve.png")
        mlflow.log_artifact(artifacts_path / "pr_curve.png")
        plt.close()
        
        # Confusion matrix
        plot_confusion_matrix(y_test, test_pred,
                            title="XGBoost - Confusion Matrix",
                            save_path=artifacts_path / "confusion_matrix.png")
        mlflow.log_artifact(artifacts_path / "confusion_matrix.png")
        plt.close()
        
        # Feature importance plot
        plt.figure(figsize=(10, 6))
        plt.barh(feature_importance['feature'], feature_importance['importance'])
        plt.xlabel('Importance (Gain)', fontsize=12)
        plt.title('XGBoost - Feature Importance', fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(artifacts_path / "feature_importance.png", dpi=150, bbox_inches='tight')
        mlflow.log_artifact(artifacts_path / "feature_importance.png")
        plt.close()
        
        # Save model
        model_path = artifacts_path / "xgb_model.pkl"
        joblib.dump(xgb_model, model_path)
        mlflow.xgboost.log_model(xgb_model, "model")
        mlflow.log_artifact(model_path)
        
        # Save feature importance
        feature_importance.to_csv(artifacts_path / "feature_importance.csv", index=False)
        mlflow.log_artifact(artifacts_path / "feature_importance.csv")
        
        # Save metrics to JSON
        all_metrics = {
            "train": train_metrics,
            "validation": val_metrics,
            "test": test_metrics
        }
        metrics_path = artifacts_path / "metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(all_metrics, f, indent=2)
        mlflow.log_artifact(metrics_path)
        
        print(f"\nXGBoost model saved to: {model_path}")
        print(f"MLflow run ID: {run.info.run_id}")
        
        return xgb_model, test_metrics


def compare_models(baseline_metrics, ml_metrics, xgb_metrics=None, save_path="reports/model_comparison.png"):
    """Compare baseline vs ML model metrics."""
    print(f"\n{'='*60}")
    print("Model Comparison")
    print(f"{'='*60}")
    
    models_dict = {
        'Baseline (Z-Score)': baseline_metrics,
        'Logistic Regression': ml_metrics
    }
    
    if xgb_metrics is not None:
        models_dict['XGBoost'] = xgb_metrics
    
    comparison_df = pd.DataFrame(models_dict).T
    
    print(comparison_df[['pr_auc', 'f1_score', 'precision', 'recall']])
    
    # Plot comparison
    metrics_to_plot = ['pr_auc', 'f1_score', 'precision', 'recall']
    comparison_subset = comparison_df[metrics_to_plot]
    
    fig, ax = plt.subplots(figsize=(14, 6))
    comparison_subset.T.plot(kind='bar', ax=ax, width=0.7)
    plt.xlabel('Metric', fontsize=12)
    plt.ylabel('Score', fontsize=12)
    
    title = 'Model Comparison: Baseline vs Logistic Regression'
    if xgb_metrics is not None:
        title += ' vs XGBoost'
    plt.title(title, fontsize=14, fontweight='bold')
    
    plt.legend(title='Model', loc='best')
    plt.xticks(rotation=0)
    plt.ylim(0, 1.0)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Saved comparison plot to {save_path}")
    plt.close()


def main():
    """Main training pipeline."""
    print("\n" + "="*60)
    print("MILESTONE 3: MODEL TRAINING PIPELINE")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration
    FEATURES_PATH = "data/processed/features.parquet"
    THRESHOLD_TAU = 0.000028  # 95th percentile from EDA (11,130 samples) - adjusted for better class balance
    ARTIFACTS_DIR = "models/artifacts"
    MLFLOW_TRACKING_URI = "file:./mlruns"  # Use local file-based tracking
    
    # Set MLflow tracking URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("crypto_volatility_detection")
    
    print(f"\nMLflow tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"MLflow experiment: crypto_volatility_detection")
    
    # Load and prepare data
    df, feature_cols = load_and_prepare_data(
        features_path=FEATURES_PATH,
        threshold_tau=THRESHOLD_TAU
    )
    
    # Split data chronologically
    train_df, val_df, test_df = split_data_chronologically(df, 
                                                            train_ratio=0.7, 
                                                            val_ratio=0.15, 
                                                            test_ratio=0.15)
    
    # Prepare X and y
    X_train = train_df[feature_cols + ['label']].copy()
    y_train = X_train.pop('label')
    
    X_val = val_df[feature_cols + ['label']].copy()
    y_val = X_val.pop('label')
    
    X_test = test_df[feature_cols + ['label']].copy()
    y_test = X_test.pop('label')
    
    # Train Baseline Model
    baseline_model, baseline_test_metrics = train_baseline_model(
        X_train, y_train, X_val, y_val, X_test, y_test, 
        feature_cols, ARTIFACTS_DIR
    )
    
    # Train ML Model (Logistic Regression)
    ml_model, ml_test_metrics = train_ml_model(
        X_train, y_train, X_val, y_val, X_test, y_test,
        feature_cols, ARTIFACTS_DIR
    )
    
    # Train XGBoost Model
    xgb_model, xgb_test_metrics = train_xgboost_model(
        X_train, y_train, X_val, y_val, X_test, y_test,
        feature_cols, ARTIFACTS_DIR
    )
    
    # Compare all models
    compare_models(baseline_test_metrics, ml_test_metrics, xgb_test_metrics,
                  save_path="reports/model_comparison.png")
    
    # Save train/test splits for Evidently report
    train_df.to_parquet("data/processed/train_data.parquet", index=False)
    test_df.to_parquet("data/processed/test_data.parquet", index=False)
    print(f"\nSaved train and test data for Evidently reporting")
    
    print(f"\n{'='*60}")
    print("TRAINING COMPLETE - ALL 3 MODELS")
    print(f"{'='*60}")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nModels trained:")
    print(f"  1. Baseline (Z-Score) - Test PR-AUC: {baseline_test_metrics['pr_auc']:.4f}")
    print(f"  2. Logistic Regression - Test PR-AUC: {ml_test_metrics['pr_auc']:.4f}")
    print(f"  3. XGBoost - Test PR-AUC: {xgb_test_metrics['pr_auc']:.4f}")
    print(f"\nNext steps:")
    print(f"  1. View results in MLflow UI: {MLFLOW_TRACKING_URI}")
    print(f"  2. Generate Evidently drift report (train vs test)")
    print(f"  3. Update model card with final metrics")
    print(f"  4. Generate model evaluation PDF")


if __name__ == "__main__":
    main()

