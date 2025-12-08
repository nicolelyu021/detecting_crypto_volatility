#!/usr/bin/env python3
"""
Replay Script
Regenerates features from saved raw data identically to the live consumer.
"""

import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# Add parent directory to path to import featurizer
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.featurizer import FeatureEngineer

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ReplayEngineer(FeatureEngineer):
    """Feature engineer that processes saved raw data instead of Kafka."""

    def __init__(self, config_path: str = "config.yaml", data_file: str = None):
        """Initialize replay engineer."""
        super().__init__(config_path)
        self.data_file = data_file
        self.producer = None  # Don't publish to Kafka during replay

    def _load_raw_data(self, file_path: Path) -> list[dict]:
        """Load raw data from NDJSON file."""
        logger.info(f"Loading raw data from {file_path}")

        ticks = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        tick = json.loads(line)
                        ticks.append(tick)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse line: {e}")

        logger.info(f"Loaded {len(ticks)} ticks from {file_path}")
        return ticks

    def _publish_to_kafka(self, features: dict):
        """Override to skip Kafka publishing during replay."""
        pass  # Don't publish during replay

    def replay(self, data_file: str = None):
        """Replay raw data and regenerate features."""
        if data_file:
            file_path = Path(data_file)
        elif self.data_file:
            file_path = Path(self.data_file)
        else:
            # Default: use the most recent raw data file
            raw_data_dir = Path(self.config["ingestion"]["data_dir"])
            data_files = list(raw_data_dir.glob("*.ndjson"))

            if not data_files:
                raise FileNotFoundError(f"No raw data files found in {raw_data_dir}")

            # Use the file with most recent modification time
            file_path = max(data_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Using most recent file: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        # Load raw data
        ticks = self._load_raw_data(file_path)

        if not ticks:
            logger.warning("No ticks to process")
            return

        # Sort by timestamp to ensure chronological order
        ticks.sort(key=lambda x: x.get("ingestion_timestamp", 0))

        logger.info(f"Processing {len(ticks)} ticks to generate features...")

        # Process each tick
        features_list = []
        for i, tick in enumerate(ticks):
            features = self._process_tick(tick)

            if features:
                features_list.append(features)
                self.feature_count += 1

                if self.feature_count % 100 == 0:
                    logger.info(
                        f"Processed {i+1}/{len(ticks)} ticks, generated {self.feature_count} features"
                    )

        # Save all features to Parquet
        if features_list:
            df = pd.DataFrame(features_list)

            # Save to replay-specific file
            replay_output = self.features_dir / "features_replay.parquet"
            df.to_parquet(replay_output, index=False, engine="pyarrow")
            logger.info(f"Saved {len(features_list)} features to {replay_output}")

            # Also append to main features file
            main_features_path = self.features_dir / "features.parquet"
            if main_features_path.exists():
                existing_df = pd.read_parquet(main_features_path)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_parquet(main_features_path, index=False, engine="pyarrow")
                logger.info(f"Appended to main features file: {main_features_path}")
            else:
                df.to_parquet(main_features_path, index=False, engine="pyarrow")
                logger.info(f"Created main features file: {main_features_path}")

        logger.info(
            f"Replay complete. Generated {self.feature_count} features from {len(ticks)} ticks."
        )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Replay raw data to regenerate features")
    parser.add_argument(
        "--data-file",
        type=str,
        default=None,
        help="Path to raw data NDJSON file (default: most recent file in data/raw/)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    args = parser.parse_args()
    config_path = os.getenv("CONFIG_PATH", args.config)

    try:
        engineer = ReplayEngineer(config_path, args.data_file)
        engineer.replay()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
