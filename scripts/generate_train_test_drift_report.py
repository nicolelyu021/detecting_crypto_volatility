"""
Generate Evidently drift report comparing train vs test data.

This report is required for Milestone 3 to check for distribution drift
between training and test datasets.
"""

import pandas as pd
from pathlib import Path
import json
from datetime import datetime

try:
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, DataQualityPreset
    from evidently.metrics import DatasetSummaryMetric
except ImportError:
    print("ERROR: Evidently not installed. Run: pip install evidently")
    exit(1)


def generate_train_test_drift_report(
    train_path: str = "data/processed/train_data.parquet",
    test_path: str = "data/processed/test_data.parquet",
    output_dir: str = "reports/evidently",
    feature_cols: list = None
):
    """
    Generate Evidently reports comparing train vs test data.
    
    Args:
        train_path: Path to training data Parquet file
        test_path: Path to test data Parquet file
        output_dir: Directory to save reports
        feature_cols: List of feature columns to analyze
    """
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print(f"Loading training data from: {train_path}")
    train_df = pd.read_parquet(train_path)
    print(f"  Loaded {len(train_df)} training samples")
    
    print(f"\nLoading test data from: {test_path}")
    test_df = pd.read_parquet(test_path)
    print(f"  Loaded {len(test_df)} test samples")
    
    # Define feature columns
    if feature_cols is None:
        feature_cols = [
            'midprice_return_mean',
            'midprice_return_std',
            'bid_ask_spread',
            'trade_intensity',
            'order_book_imbalance'
        ]
    
    # Filter to available columns
    available_cols = [col for col in feature_cols if col in train_df.columns and col in test_df.columns]
    if not available_cols:
        print("ERROR: No feature columns found in data")
        print(f"Train columns: {list(train_df.columns)}")
        print(f"Test columns: {list(test_df.columns)}")
        return
    
    # Include label if available
    if 'label' in train_df.columns and 'label' in test_df.columns:
        available_cols.append('label')
    
    print(f"\nAnalyzing features: {available_cols}")
    
    reference_data = train_df[available_cols]
    current_data = test_df[available_cols]
    
    # Generate Data Drift Report
    print("\n" + "="*60)
    print("Generating Train vs Test Data Drift Report...")
    print("="*60)
    
    drift_report = Report(metrics=[DataDriftPreset()])
    drift_report.run(
        reference_data=reference_data,
        current_data=current_data
    )
    
    # Save drift report
    drift_html_path = output_path / "train_test_drift_report.html"
    drift_json_path = output_path / "train_test_drift_report.json"
    
    drift_report.save_html(str(drift_html_path))
    print(f"✓ Saved HTML report: {drift_html_path}")
    
    drift_report.save_json(str(drift_json_path))
    print(f"✓ Saved JSON report: {drift_json_path}")
    
    # Generate Data Quality Report
    print("\n" + "="*60)
    print("Generating Data Quality Report...")
    print("="*60)
    
    quality_report = Report(metrics=[DataQualityPreset()])
    quality_report.run(
        reference_data=reference_data,
        current_data=current_data
    )
    
    # Save quality report
    quality_html_path = output_path / "train_test_quality_report.html"
    quality_json_path = output_path / "train_test_quality_report.json"
    
    quality_report.save_html(str(quality_html_path))
    print(f"✓ Saved HTML report: {quality_html_path}")
    
    quality_report.save_json(str(quality_json_path))
    print(f"✓ Saved JSON report: {quality_json_path}")
    
    # Generate Combined Report
    print("\n" + "="*60)
    print("Generating Combined Report...")
    print("="*60)
    
    combined_report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
    combined_report.run(
        reference_data=reference_data,
        current_data=current_data
    )
    
    combined_html_path = output_path / "train_test_combined_report.html"
    combined_json_path = output_path / "train_test_combined_report.json"
    
    combined_report.save_html(str(combined_html_path))
    print(f"✓ Saved HTML report: {combined_html_path}")
    
    combined_report.save_json(str(combined_json_path))
    print(f"✓ Saved JSON report: {combined_json_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"\nTraining data:")
    print(reference_data.describe())
    print(f"\nTest data:")
    print(current_data.describe())
    
    print("\n" + "="*60)
    print("Reports generated successfully!")
    print("="*60)
    print(f"\nOpen the HTML reports in your browser:")
    print(f"  Main report: {combined_html_path}")
    print(f"  Drift report: {drift_html_path}")
    print(f"  Quality report: {quality_html_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Evidently train vs test drift report")
    parser.add_argument("--train", default="data/processed/train_data.parquet",
                       help="Path to training data")
    parser.add_argument("--test", default="data/processed/test_data.parquet",
                       help="Path to test data")
    parser.add_argument("--output-dir", default="reports/evidently",
                       help="Output directory for reports")
    
    args = parser.parse_args()
    
    generate_train_test_drift_report(
        train_path=args.train,
        test_path=args.test,
        output_dir=args.output_dir
    )

