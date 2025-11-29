#!/usr/bin/env python3
"""
Replay Script for Kafka
Replays raw data through Kafka topics to test the pipeline end-to-end.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import yaml
from confluent_kafka import Producer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KafkaReplay:
    """Replay raw data through Kafka."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize Kafka replay."""
        self.config = self._load_config(config_path)
        self.producer = self._create_producer()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file) as f:
            return yaml.safe_load(f)

    def _create_producer(self) -> Producer:
        """Create Kafka producer."""
        bootstrap_servers = self.config["kafka"]["bootstrap_servers"]

        producer_config = {
            "bootstrap.servers": bootstrap_servers,
            "acks": "all",
            "retries": 3,
            "compression.type": "snappy",
        }

        producer = Producer(producer_config)
        logger.info(f"Created Kafka producer for {bootstrap_servers}")
        return producer

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

    def _extract_10_minutes(self, ticks: list[dict], start_time: float = None) -> list[dict]:
        """Extract 10 minutes (600 seconds) of data."""
        if not ticks:
            return []

        # Sort by timestamp
        ticks_sorted = sorted(ticks, key=lambda x: x.get("ingestion_timestamp", 0))

        if start_time is None:
            # Use the first timestamp as start
            start_time = ticks_sorted[0].get("ingestion_timestamp", 0)

        end_time = start_time + 600  # 10 minutes = 600 seconds

        # Filter ticks within the 10-minute window
        filtered_ticks = [
            tick
            for tick in ticks_sorted
            if start_time <= tick.get("ingestion_timestamp", 0) <= end_time
        ]

        logger.info(
            f"Extracted {len(filtered_ticks)} ticks from 10-minute window "
            f"({start_time} to {end_time})"
        )

        return filtered_ticks

    def _publish_tick(self, tick: dict, topic: str):
        """Publish a single tick to Kafka."""
        value = json.dumps(tick).encode("utf-8")
        product_id = tick.get("product_id", "").encode("utf-8") if tick.get("product_id") else None

        def delivery_callback(err, msg):
            if err:
                logger.error(f"Failed to deliver message: {err}")

        try:
            self.producer.produce(topic, value=value, key=product_id, callback=delivery_callback)
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Error publishing to Kafka: {e}")

    def replay(self, data_file: str = None, duration_minutes: int = 10, speedup: float = 1.0):
        """
        Replay raw data through Kafka.

        Args:
            data_file: Path to raw data file (default: most recent in data/raw/)
            duration_minutes: Duration to replay in minutes (default: 10)
            speedup: Speedup factor (1.0 = real-time, 2.0 = 2x speed)
        """
        # Determine data file
        if data_file:
            file_path = Path(data_file)
        else:
            raw_data_dir = Path(self.config["ingestion"]["data_dir"])
            data_files = list(raw_data_dir.glob("*.ndjson"))

            if not data_files:
                raise FileNotFoundError(f"No raw data files found in {raw_data_dir}")

            file_path = max(data_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Using most recent file: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        # Load raw data
        ticks = self._load_raw_data(file_path)

        if not ticks:
            logger.warning("No ticks to replay")
            return

        # Extract duration_minutes of data
        duration_seconds = duration_minutes * 60
        ticks_sorted = sorted(ticks, key=lambda x: x.get("ingestion_timestamp", 0))

        if not ticks_sorted:
            logger.warning("No valid ticks found")
            return

        start_time = ticks_sorted[0].get("ingestion_timestamp", 0)
        end_time = start_time + duration_seconds

        filtered_ticks = [
            tick
            for tick in ticks_sorted
            if start_time <= tick.get("ingestion_timestamp", 0) <= end_time
        ]

        if not filtered_ticks:
            logger.warning(f"No ticks found in {duration_minutes}-minute window")
            return

        logger.info(
            f"Replaying {len(filtered_ticks)} ticks over {duration_minutes} minutes "
            f"(speedup: {speedup}x)"
        )

        # Get topic
        topic = self.config["kafka"]["topic_raw"]

        # Replay ticks with timing
        replay_start = time.time()

        for i, tick in enumerate(filtered_ticks):
            tick_time = tick.get("ingestion_timestamp", 0)

            # Calculate delay based on original timing and speedup
            if i == 0:
                delay = 0
            else:
                prev_tick_time = filtered_ticks[i - 1].get("ingestion_timestamp", 0)
                original_delay = tick_time - prev_tick_time
                delay = max(0, original_delay / speedup)

            if delay > 0:
                time.sleep(delay)

            # Publish to Kafka
            self._publish_tick(tick, topic)

            if (i + 1) % 100 == 0:
                elapsed = time.time() - replay_start
                logger.info(
                    f"Published {i+1}/{len(filtered_ticks)} ticks " f"({elapsed:.1f}s elapsed)"
                )

        # Flush remaining messages
        self.producer.flush(timeout=10)

        total_time = time.time() - replay_start
        logger.info(f"Replay complete! Published {len(filtered_ticks)} ticks in {total_time:.1f}s")
        logger.info(f"Average rate: {len(filtered_ticks)/total_time:.1f} ticks/second")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Replay raw data through Kafka")
    parser.add_argument(
        "--data-file",
        type=str,
        default=None,
        help="Path to raw data NDJSON file (default: most recent file in data/raw/)",
    )
    parser.add_argument(
        "--duration", type=int, default=10, help="Duration to replay in minutes (default: 10)"
    )
    parser.add_argument(
        "--speedup",
        type=float,
        default=1.0,
        help="Speedup factor (1.0 = real-time, 2.0 = 2x speed) (default: 1.0)",
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
        replay = KafkaReplay(config_path)
        replay.replay(
            data_file=args.data_file, duration_minutes=args.duration, speedup=args.speedup
        )
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
