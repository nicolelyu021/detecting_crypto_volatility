"""
Generate Evidently AI report comparing early and late windows of data.

This script:
1. Loads features from Parquet
2. Splits data into early (reference) and late (current) windows
3. Generates Evidently reports for drift detection and data quality
4. Saves HTML and JSON reports to reports/evidently/
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


def generate_evidently_report(
    features_path: str = "data/processed/features.parquet",
    output_dir: str = "reports/evidently",
    split_ratio: float = 0.5
):
    """
    Generate Evidently reports comparing early vs late data windows.
    
    Args:
        features_path: Path to features Parquet file
        output_dir: Directory to save reports
        split_ratio: Ratio to split data (0.5 = 50% early, 50% late)
    """
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load features
    features_file = Path(features_path)
    
    if not features_file.exists():
        print(f"ERROR: Features file not found: {features_path}")
        print("Please run featurizer.py or replay.py first to generate features.")
        return
    
    print(f"Loading features from: {features_file}")
    df = pd.read_parquet(features_file)
    print(f"Loaded {len(df)} feature records")
    
    # Sort by timestamp if available
    if 'ts' in df.columns:
        df = df.sort_values('ts').reset_index(drop=True)
        print("Data sorted by timestamp")
    else:
        print("Warning: No timestamp column found, using row order")
    
    # Split into early (reference) and late (current) windows
    split_idx = int(len(df) * split_ratio)
    reference_data = df.iloc[:split_idx].copy()
    current_data = df.iloc[split_idx:].copy()
    
    print(f"\nData split:")
    print(f"  Reference (early) window: {len(reference_data)} records")
    print(f"  Current (late) window: {len(current_data)} records")
    
    # Select feature columns for analysis
    feature_cols = [
        'midprice_return_mean',
        'midprice_return_std',
        'bid_ask_spread',
        'trade_intensity',
        'order_book_imbalance'
    ]
    
    # Filter to columns that exist
    available_cols = [col for col in feature_cols if col in df.columns]
    if not available_cols:
        print("ERROR: No feature columns found in data")
        print(f"Available columns: {list(df.columns)}")
        return
    
    print(f"\nAnalyzing features: {available_cols}")
    
    reference_features = reference_data[available_cols]
    current_features = current_data[available_cols]
    
    # Generate Data Drift Report
    print("\n" + "="*60)
    print("Generating Data Drift Report...")
    print("="*60)
    
    drift_report = Report(metrics=[DataDriftPreset()])
    drift_report.run(
        reference_data=reference_features,
        current_data=current_features
    )
    
    # Save drift report
    drift_html_path = output_path / "data_drift_report.html"
    drift_json_path = output_path / "data_drift_report.json"
    
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
        reference_data=reference_features,
        current_data=current_features
    )
    
    # Save quality report
    quality_html_path = output_path / "data_quality_report.html"
    quality_json_path = output_path / "data_quality_report.json"
    
    quality_report.save_html(str(quality_html_path))
    print(f"✓ Saved HTML report: {quality_html_path}")
    
    quality_report.save_json(str(quality_json_path))
    print(f"✓ Saved JSON report: {quality_json_path}")
    
    # Generate Combined Report (both drift and quality)
    print("\n" + "="*60)
    print("Generating Combined Report (Drift + Quality)...")
    print("="*60)
    
    combined_report = Report(metrics=[DataDriftPreset(), DataQualityPreset()])
    combined_report.run(
        reference_data=reference_features,
        current_data=current_features
    )
    
    combined_html_path = output_path / "combined_report.html"
    combined_json_path = output_path / "combined_report.json"
    
    combined_report.save_html(str(combined_html_path))
    print(f"✓ Saved HTML report: {combined_html_path}")
    
    combined_report.save_json(str(combined_json_path))
    print(f"✓ Saved JSON report: {combined_json_path}")
    
    # Print summary statistics
    print("\n" + "="*60)
    print("Summary Statistics")
    print("="*60)
    print("\nReference (Early) Window:")
    print(reference_features.describe())
    print("\nCurrent (Late) Window:")
    print(current_features.describe())
    
    # Extract key metrics from JSON report (if available)
    try:
        with open(combined_json_path, 'r') as f:
            report_data = json.load(f)
            print("\n" + "="*60)
            print("Key Metrics from Report:")
            print("="*60)
            # Evidently JSON structure may vary, but we can try to extract useful info
            print("(Open the HTML report for detailed visualizations)")
    except Exception as e:
        print(f"Could not parse JSON report: {e}")
    
    print("\n" + "="*60)
    print("Reports generated successfully!")
    print("="*60)
    print(f"\nOpen the HTML reports in your browser:")
    print(f"  - {combined_html_path}")
    print(f"  - {drift_html_path}")
    print(f"  - {quality_html_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Evidently AI reports")
    parser.add_argument("--features", default="data/processed/features.parquet", 
                       help="Path to features Parquet file")
    parser.add_argument("--output-dir", default="reports/evidently", 
                       help="Output directory for reports")
    parser.add_argument("--split-ratio", type=float, default=0.5,
                       help="Ratio to split data (0.5 = 50% early, 50% late)")
    
    args = parser.parse_args()
    
    generate_evidently_report(
        features_path=args.features,
        output_dir=args.output_dir,
        split_ratio=args.split_ratio
    )

