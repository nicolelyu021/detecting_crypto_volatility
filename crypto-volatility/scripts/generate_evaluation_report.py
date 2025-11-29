#!/usr/bin/env python3
"""
Generate Model Evaluation Report
Creates a comprehensive evaluation report comparing baseline and ML models.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import mlflow
import pandas as pd
import yaml
from dotenv import load_dotenv
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    precision_recall_curve,
    recall_score,
    roc_auc_score,
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_test_set(config_path: str = "config.yaml") -> pd.DataFrame:
    """Load test set."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    test_path = Path(config["features"]["data_dir"]) / "test_set.parquet"

    if not test_path.exists():
        raise FileNotFoundError(f"Test set not found: {test_path}")

    logger.info(f"Loading test set from {test_path}")
    df = pd.read_parquet(test_path)
    logger.info(f"Loaded {len(df)} test samples")

    return df


def load_mlflow_runs(config: Dict) -> Dict:
    """Load MLflow runs for baseline and ML models."""
    mlflow.set_tracking_uri(config["mlflow"]["tracking_uri"])
    mlflow.set_experiment(config["mlflow"]["experiment_name"])

    # Get experiment
    experiment = mlflow.get_experiment_by_name(config["mlflow"]["experiment_name"])
    if experiment is None:
        raise ValueError(f"Experiment not found: {config['mlflow']['experiment_name']}")

    # Get runs
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])

    baseline_run = runs[runs["tags.mlflow.runName"] == "baseline_zscore"]
    ml_run = runs[runs["tags.mlflow.runName"].str.contains("ml_", na=False)]

    results = {}

    if not baseline_run.empty:
        results["baseline"] = {
            "run_id": baseline_run.iloc[0]["run_id"],
            "metrics": {
                "pr_auc": baseline_run.iloc[0].get("metrics.val_pr_auc", 0),
                "f1": baseline_run.iloc[0].get("metrics.val_f1", 0),
                "precision": baseline_run.iloc[0].get("metrics.val_precision", 0),
                "recall": baseline_run.iloc[0].get("metrics.val_recall", 0),
            },
        }

    if not ml_run.empty:
        best_ml_run = ml_run.loc[ml_run["metrics.val_pr_auc"].idxmax()]
        results["ml_model"] = {
            "run_id": best_ml_run["run_id"],
            "metrics": {
                "pr_auc": best_ml_run.get("metrics.val_pr_auc", 0),
                "f1": best_ml_run.get("metrics.val_f1", 0),
                "precision": best_ml_run.get("metrics.val_precision", 0),
                "recall": best_ml_run.get("metrics.val_recall", 0),
            },
        }

    return results


def generate_report(test_df: pd.DataFrame, mlflow_results: Dict, output_dir: Path):
    """Generate evaluation report."""
    logger.info("Generating evaluation report...")

    report = {
        "summary": {
            "test_samples": len(test_df),
            "spike_rate": float(test_df["label"].mean()) if "label" in test_df.columns else None,
        },
        "model_comparison": mlflow_results,
        "test_metrics": {},
    }

    # If predictions exist, compute test metrics
    if "prediction" in test_df.columns and "label" in test_df.columns:
        y_true = test_df["label"]
        y_pred = test_df["prediction"]
        y_proba = test_df.get("probability", None)

        report["test_metrics"] = {
            "accuracy": float((y_pred == y_true).mean()),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        }

        if y_proba is not None:
            report["test_metrics"]["pr_auc"] = float(average_precision_score(y_true, y_proba))
            report["test_metrics"]["roc_auc"] = float(roc_auc_score(y_true, y_proba))

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        report["confusion_matrix"] = {
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1]),
        }

        # Classification report
        report["classification_report"] = classification_report(y_true, y_pred, output_dict=True)

    # Save report
    json_path = output_dir / "model_eval.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Saved evaluation report to {json_path}")

    # Print summary
    print("\n" + "=" * 60)
    print("MODEL EVALUATION REPORT")
    print("=" * 60)
    print(f"\nTest Set: {report['summary']['test_samples']} samples")
    if report["summary"]["spike_rate"]:
        print(f"Spike Rate: {report['summary']['spike_rate']*100:.2f}%")

    print("\nModel Comparison (Validation Metrics):")
    if "baseline" in mlflow_results:
        print(
            f"  Baseline - PR-AUC: {mlflow_results['baseline']['metrics']['pr_auc']:.4f}, F1: {mlflow_results['baseline']['metrics']['f1']:.4f}"
        )
    if "ml_model" in mlflow_results:
        print(
            f"  ML Model - PR-AUC: {mlflow_results['ml_model']['metrics']['pr_auc']:.4f}, F1: {mlflow_results['ml_model']['metrics']['f1']:.4f}"
        )

    if report["test_metrics"]:
        print("\nTest Set Metrics:")
        for metric, value in report["test_metrics"].items():
            print(f"  {metric}: {value:.4f}")

    print("=" * 60)

    return report


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate model evaluation report")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")
    parser.add_argument(
        "--output-dir", type=str, default="reports", help="Output directory for reports"
    )

    args = parser.parse_args()
    config_path = os.getenv("CONFIG_PATH", args.config)

    try:
        # Load config
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Load test set
        test_df = load_test_set(config_path)

        # Load MLflow results
        mlflow_results = load_mlflow_runs(config)

        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate report
        report = generate_report(test_df, mlflow_results, output_dir)

        logger.info("Evaluation report generation complete!")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
