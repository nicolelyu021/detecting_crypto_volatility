"""
Replay script: regenerate features from saved raw data.

This script reads the saved raw data from data/raw/slice.ndjson
and regenerates features identically to how featurizer.py does it.
This ensures reproducibility and allows testing without live data.
"""

import orjson
import pandas as pd
from pathlib import Path
import numpy as np
from collections import deque
from typing import Dict, Optional
import sys

# Import the feature computation logic from featurizer
sys.path.insert(0, str(Path(__file__).parent.parent))
from features.featurizer import FeatureWindow, parse_ticker_message


def replay_features(
    input_path: str = "data/raw/slice.ndjson",
    output_path: str = "data/processed/features.parquet",
    window_seconds: int = 60
):
    """
    Replay features from saved raw data.
    
    Args:
        input_path: Path to saved raw NDJSON file
        output_path: Path to save regenerated features
        window_seconds: Feature window size in seconds
    """
    
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return
    
    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading raw data from: {input_file}")
    print(f"Window size: {window_seconds} seconds")
    
    # Initialize feature window (same as featurizer)
    window = FeatureWindow(window_seconds=window_seconds)
    
    features_list = []
    line_count = 0
    processed_count = 0
    
    # Read and process each line
    with open(input_file, "rb") as f:
        for line in f:
            line_count += 1
            
            try:
                # Parse the saved record
                rec = orjson.loads(line)
                ts = rec.get("ts")
                raw_str = rec.get("raw", "")
                
                if not raw_str:
                    continue
                
                # Parse ticker data (same logic as featurizer)
                tick_data = parse_ticker_message(raw_str)
                if not tick_data:
                    continue
                
                # Add to window (same as featurizer)
                window.add_tick(
                    ts=ts,
                    midprice=tick_data["midprice"],
                    spread=tick_data["spread"],
                    has_trade=True
                )
                
                # Compute features (same as featurizer)
                features = window.compute_features(ts)
                if features is None:
                    continue
                
                # Add metadata
                features["pair"] = rec.get("pair", "BTC-USD")
                features["raw_price"] = tick_data["price"]
                
                features_list.append(features)
                processed_count += 1
                
                if processed_count % 100 == 0:
                    print(f"Processed {processed_count} ticks...")
                    
            except Exception as e:
                print(f"Error processing line {line_count}: {e}")
                continue
    
    print(f"\nTotal lines read: {line_count}")
    print(f"Ticks processed: {processed_count}")
    print(f"Features generated: {len(features_list)}")
    
    if not features_list:
        print("No features generated. Check your input data.")
        return
    
    # Convert to DataFrame and save
    df = pd.DataFrame(features_list)
    df.to_parquet(output_file, engine="pyarrow", index=False)
    
    print(f"\nSaved {len(df)} features to: {output_file}")
    print(f"\nFeature columns: {list(df.columns)}")
    print(f"\nFirst few rows:")
    print(df.head())
    
    # Verify feature statistics
    print(f"\nFeature statistics:")
    print(df.describe())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Replay features from saved raw data")
    parser.add_argument("--input", default="data/raw/slice.ndjson", help="Input raw data file (NDJSON)")
    parser.add_argument("--output", default="data/processed/features.parquet", help="Output Parquet file")
    parser.add_argument("--window-seconds", type=int, default=60, help="Feature window size in seconds")
    
    args = parser.parse_args()
    
    replay_features(
        input_path=args.input,
        output_path=args.output,
        window_seconds=args.window_seconds
    )

