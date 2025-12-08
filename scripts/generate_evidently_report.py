#!/usr/bin/env python3
"""
Generate Evidently Report
Creates data quality and drift reports comparing early and late windows of data.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging first (before imports that might fail)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import Evidently - try multiple paths
try:
    from evidently import Report
    from evidently.presets import DataDriftPreset, DataSummaryPreset
except ImportError:
    try:
        # Try alternative import path
        from evidently.presets import DataDriftPreset, DataSummaryPreset
        from evidently.report import Report
    except ImportError as e:
        logger.error(f"Could not import Evidently: {e}")
        logger.error("Please check your Evidently installation: pip install evidently")
        raise


def save_report_html(report: Report, output_path: Path) -> None:
    """Save Evidently report to HTML file, handling different API versions."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    saved = False

    # Try different methods based on Evidently version
    # Method 1: save_html() - newer versions (0.7+)
    if hasattr(report, "save_html"):
        try:
            report.save_html(str(output_path))
            saved = True
            logger.debug("Saved using save_html() method")
        except Exception as e:
            logger.debug(f"save_html() failed: {e}")

    # Method 2: get_html() - some versions return HTML as string
    if not saved and hasattr(report, "get_html"):
        try:
            html_content = report.get_html()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            saved = True
            logger.debug("Saved using get_html() method")
        except Exception as e:
            logger.debug(f"get_html() failed: {e}")

    # Method 3: save() - older versions (0.4.x Dashboard API)
    if not saved and hasattr(report, "save"):
        try:
            report.save(str(output_path))
            saved = True
            logger.debug("Saved using save() method")
        except Exception as e:
            logger.debug(f"save() failed: {e}")

    # Method 4: as_html() - some versions have this
    if not saved and hasattr(report, "as_html"):
        try:
            html_content = report.as_html()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            saved = True
            logger.debug("Saved using as_html() method")
        except Exception as e:
            logger.debug(f"as_html() failed: {e}")

    # Method 5: Try to get HTML from internal representation
    if not saved:
        # Check for common internal attributes that might contain HTML
        for attr in ["_html", "html", "_get_html", "to_html"]:
            if hasattr(report, attr):
                try:
                    html_getter = getattr(report, attr)
                    if callable(html_getter):
                        html_content = html_getter()
                    else:
                        html_content = html_getter
                    if html_content and isinstance(html_content, str):
                        with open(output_path, "w", encoding="utf-8") as f:
                            f.write(html_content)
                        saved = True
                        logger.debug(f"Saved using {attr} attribute/method")
                        break
                except Exception as e:
                    logger.debug(f"{attr} failed: {e}")
                    continue

    # Fallback: create basic HTML with info about the report
    if not saved:
        logger.warning(
            f"Could not find standard save method for Report. Available methods: {[m for m in dir(report) if not m.startswith('_')][:10]}"
        )
        logger.warning("Creating basic HTML report. Check JSON output for detailed metrics.")

        # Try to get some info from the report
        report_info = {
            "type": type(report).__name__,
            "module": type(report).__module__,
        }

        # Try to get metadata if available
        if hasattr(report, "metadata"):
            try:
                report_info["metadata"] = str(report.metadata)
            except:
                pass

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Evidently Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .info {{ background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .warning {{ background: #fff3cd; padding: 15px; margin: 10px 0; border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <h1>Evidently Report</h1>
    <div class="info">
        <p><strong>Report generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Report type:</strong> {report_info['type']}</p>
        <p><strong>Module:</strong> {report_info.get('module', 'unknown')}</p>
    </div>
    <div class="warning">
        <p><strong>Note:</strong> Full HTML export not available in this Evidently version.</p>
        <p>Please check the corresponding JSON file for detailed metrics and analysis.</p>
        <p>You may need to upgrade Evidently: <code>pip install --upgrade evidently</code></p>
    </div>
    <p>For detailed metrics, see the corresponding JSON file.</p>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)


def load_features(config_path: str = "config.yaml") -> pd.DataFrame:
    """Load features from Parquet file."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    features_path = Path(config["features"]["data_dir"]) / "features.parquet"

    if not features_path.exists():
        raise FileNotFoundError(f"Features file not found: {features_path}")

    logger.info(f"Loading features from {features_path}")
    df = pd.read_parquet(features_path)
    logger.info(f"Loaded {len(df)} feature rows")

    return df


def split_early_late(df: pd.DataFrame, split_ratio: float = 0.5) -> tuple:
    """Split dataframe into early and late windows."""
    # Sort by timestamp
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)
    else:
        df = df.reset_index(drop=True)

    # Split at the ratio
    split_idx = int(len(df) * split_ratio)

    early_df = df.iloc[:split_idx].copy()
    late_df = df.iloc[split_idx:].copy()

    logger.info(f"Early window: {len(early_df)} rows")
    logger.info(f"Late window: {len(late_df)} rows")

    return early_df, late_df


def load_train_test_sets(config_path: str = "config.yaml") -> tuple:
    """Load training and test sets for comparison."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    features_dir = Path(config["features"]["data_dir"])
    train_path = features_dir / "features.parquet"
    test_path = features_dir / "test_set.parquet"

    if not train_path.exists():
        raise FileNotFoundError(f"Training features not found: {train_path}")
    if not test_path.exists():
        raise FileNotFoundError(f"Test set not found: {test_path}")

    logger.info(f"Loading training set from {train_path}")
    train_df = pd.read_parquet(train_path)

    logger.info(f"Loading test set from {test_path}")
    test_df = pd.read_parquet(test_path)

    # Filter to only samples used for training (exclude test period)
    train_df = train_df.sort_values("timestamp").reset_index(drop=True)
    test_df = test_df.sort_values("timestamp").reset_index(drop=True)

    # Remove test period from training set
    test_start_time = test_df["timestamp"].min()
    train_df = train_df[train_df["timestamp"] < test_start_time].copy()

    logger.info(f"Training set: {len(train_df)} rows")
    logger.info(f"Test set: {len(test_df)} rows")

    return train_df, test_df


def generate_data_quality_report(
    reference_df: pd.DataFrame, current_df: pd.DataFrame, output_path: Path
) -> Report:
    """Generate data quality report."""
    logger.info("Generating data quality report...")

    # Filter numeric features (exclude timestamp and metadata)
    numeric_features = reference_df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_features = [
        col
        for col in numeric_features
        if col not in ["timestamp", "_computed_at", "window_size", "num_returns"]
    ]

    # Select only numeric feature columns
    ref_data = reference_df[numeric_features].copy()
    curr_data = current_df[numeric_features].copy()

    # Create report using Evidently presets
    report = Report(metrics=[DataSummaryPreset()])
    report.run(reference_data=ref_data, current_data=curr_data)

    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract report data for JSON
    report_data = {
        "metadata": report.metadata if hasattr(report, "metadata") else {},
        "metrics": [],
    }

    # Get metric data
    for item in report.items():
        metric_info = {
            "type": type(item).__name__,
        }

        # Get columns if available
        if hasattr(item, "columns"):
            try:
                cols = item.columns
                if cols is not None:
                    metric_info["columns"] = (
                        list(cols)
                        if hasattr(cols, "__iter__") and not isinstance(cols, str)
                        else []
                    )
                else:
                    metric_info["columns"] = numeric_features
            except:
                metric_info["columns"] = numeric_features
        else:
            metric_info["columns"] = numeric_features

        report_data["metrics"].append(metric_info)

    # Save as JSON
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    logger.info(f"Data quality report (JSON) saved to {json_path}")

    # Save as HTML (handles different Evidently versions)
    save_report_html(report, output_path)
    logger.info(f"Data quality report (HTML) saved to {output_path}")

    return report


def generate_drift_report(
    reference_df: pd.DataFrame, current_df: pd.DataFrame, output_path: Path
) -> Report:
    """Generate data drift report."""
    logger.info("Generating data drift report...")

    # Filter numeric features
    numeric_features = reference_df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_features = [
        col
        for col in numeric_features
        if col not in ["timestamp", "_computed_at", "window_size", "num_returns"]
    ]

    # Select only numeric feature columns
    ref_data = reference_df[numeric_features].copy()
    curr_data = current_df[numeric_features].copy()

    # Create report using Evidently presets
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=ref_data, current_data=curr_data)

    # Save report
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Extract report data for JSON
    report_data = {
        "metadata": report.metadata if hasattr(report, "metadata") else {},
        "metrics": [],
    }

    # Get metric data with drift details
    for item in report.items():
        metric_info = {
            "type": type(item).__name__,
        }

        # Get columns if available
        if hasattr(item, "columns"):
            try:
                cols = item.columns
                if cols is not None:
                    metric_info["columns"] = (
                        list(cols)
                        if hasattr(cols, "__iter__") and not isinstance(cols, str)
                        else []
                    )
                else:
                    metric_info["columns"] = numeric_features
            except:
                metric_info["columns"] = numeric_features
        else:
            metric_info["columns"] = numeric_features

        # Extract drift information
        drift_info = {}
        if hasattr(item, "drift_share"):
            drift_info["drift_share"] = item.drift_share
        if hasattr(item, "cat_method"):
            drift_info["categorical_method"] = item.cat_method
        if hasattr(item, "cat_threshold"):
            drift_info["categorical_threshold"] = item.cat_threshold

        if drift_info:
            metric_info["drift_info"] = drift_info

        report_data["metrics"].append(metric_info)

    # Save as JSON
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    logger.info(f"Drift report (JSON) saved to {json_path}")

    # Save as HTML (handles different Evidently versions)
    save_report_html(report, output_path)
    logger.info(f"Drift report (HTML) saved to {output_path}")

    return report


def generate_report(early_df: pd.DataFrame, late_df: pd.DataFrame, output_dir: Path):
    """Generate combined Evidently report comparing early and late windows."""
    logger.info("Generating Evidently reports...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate data quality report
    quality_report_path = output_dir / f"data_quality_report_{timestamp}.html"
    quality_report = generate_data_quality_report(early_df, late_df, quality_report_path)

    # Generate drift report
    drift_report_path = output_dir / f"data_drift_report_{timestamp}.html"
    drift_report = generate_drift_report(early_df, late_df, drift_report_path)

    # Also save as main report files
    main_quality_path = output_dir / "evidently_report_quality.html"
    main_drift_path = output_dir / "evidently_report_drift.html"

    save_report_html(quality_report, main_quality_path)
    save_report_html(drift_report, main_drift_path)

    logger.info(f"Saved quality report to {main_quality_path}")
    logger.info(f"Saved drift report to {main_drift_path}")

    return quality_report, drift_report


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate Evidently report")
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--split-ratio",
        type=float,
        default=0.5,
        help="Ratio to split early/late windows (default: 0.5)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/evidently",
        help="Output directory for reports (default: reports/evidently)",
    )
    parser.add_argument(
        "--compare-train-test",
        action="store_true",
        help="Compare training vs test sets instead of early/late windows",
    )

    args = parser.parse_args()
    config_path = os.getenv("CONFIG_PATH", args.config)

    try:
        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if args.compare_train_test:
            # Compare training vs test sets
            logger.info("Comparing training vs test sets...")
            train_df, test_df = load_train_test_sets(config_path)

            if len(train_df) < 100 or len(test_df) < 100:
                logger.warning(f"Insufficient data. Train: {len(train_df)}, Test: {len(test_df)}")
                return

            # Generate reports
            quality_report, drift_report = generate_report(train_df, test_df, output_dir)
            logger.info("Train vs Test comparison reports generated!")
        else:
            # Split into early and late windows
            df = load_features(config_path)

            if len(df) < 100:
                logger.warning(
                    f"Only {len(df)} rows available. Need at least 100 for meaningful report."
                )
                return

            early_df, late_df = split_early_late(df, args.split_ratio)

            # Generate reports
            quality_report, drift_report = generate_report(early_df, late_df, output_dir)
            logger.info("Early vs Late window comparison reports generated!")

        # Print summary
        print("\n" + "=" * 60)
        print("EVIDENTLY REPORTS GENERATED")
        print("=" * 60)
        print(f"Data Quality Report: {output_dir / 'evidently_report_quality.html'}")
        print(f"Data Drift Report: {output_dir / 'evidently_report_drift.html'}")
        print("=" * 60)

        logger.info("Report generation complete!")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
