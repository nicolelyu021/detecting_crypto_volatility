#!/usr/bin/env python3
"""
Feature Engineering Pipeline
Kafka consumer that computes windowed features from raw tick data.
"""

import json
import logging
import os
import signal
import sys
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml
from confluent_kafka import Consumer, Producer
from confluent_kafka.error import KafkaError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Computes windowed features from tick data."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the feature engineer."""
        self.config = self._load_config(config_path)
        self.consumer: Optional[Consumer] = None
        self.producer: Optional[Producer] = None
        self.running = False

        # Data buffers per product
        self.buffers: Dict[str, deque] = {}

        # Feature storage
        self.feature_buffer: List[Dict] = []
        self.feature_count = 0

        # Create output directories
        self.features_dir = Path(self.config["features"]["data_dir"])
        self.features_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, "r") as f:
            return yaml.safe_load(f)

    def _create_kafka_consumer(self) -> Consumer:
        """Create Kafka consumer for raw ticks."""
        bootstrap_servers = self.config["kafka"]["bootstrap_servers"]
        topic = self.config["kafka"]["topic_raw"]
        group_id = self.config["kafka"]["features_consumer_group"]

        logger.info(f"Connecting to Kafka at {bootstrap_servers}")
        logger.info(f"Subscribing to topic: {topic}")

        consumer_config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "latest",  # Start from latest for live processing
            "enable.auto.commit": True,
            "session.timeout.ms": 10000,
        }

        consumer = Consumer(consumer_config)
        consumer.subscribe([topic])

        return consumer

    def _create_kafka_producer(self) -> Producer:
        """Create Kafka producer for features."""
        bootstrap_servers = self.config["kafka"]["bootstrap_servers"]

        producer_config = {
            "bootstrap.servers": bootstrap_servers,
            "acks": "all",
            "retries": 3,
            "compression.type": "snappy",
        }

        return Producer(producer_config)

    def _compute_midprice(self, best_bid: str, best_ask: str) -> Optional[float]:
        """Compute midprice from bid and ask."""
        try:
            bid = float(best_bid) if best_bid else None
            ask = float(best_ask) if best_ask else None

            if bid is not None and ask is not None and bid > 0 and ask > 0:
                return (bid + ask) / 2.0
            return None
        except (ValueError, TypeError):
            return None

    def _compute_returns(self, prices: List[float], intervals: List[int]) -> Dict[str, float]:
        """Compute returns over different intervals."""
        if len(prices) < 2:
            return {}

        returns = {}
        for interval in intervals:
            if len(prices) > interval:
                # Compute return: (price_t - price_{t-interval}) / price_{t-interval}
                current_price = prices[-1]
                past_price = prices[-interval - 1] if len(prices) > interval else prices[0]

                if past_price > 0:
                    ret = (current_price - past_price) / past_price
                    returns[f"return_{interval}s"] = ret
                else:
                    returns[f"return_{interval}s"] = 0.0
            else:
                returns[f"return_{interval}s"] = 0.0

        return returns

    def _compute_bid_ask_spread(self, best_bid: str, best_ask: str) -> Optional[float]:
        """Compute bid-ask spread (absolute and relative)."""
        try:
            bid = float(best_bid) if best_bid else None
            ask = float(best_ask) if best_ask else None

            if bid is not None and ask is not None and bid > 0 and ask > 0:
                spread_abs = ask - bid
                spread_rel = spread_abs / ((bid + ask) / 2.0)  # Relative spread
                return {"spread_abs": spread_abs, "spread_rel": spread_rel}
            return None
        except (ValueError, TypeError):
            return None

    def _compute_trade_intensity(self, timestamps: List[float], window_seconds: int = 60) -> float:
        """Compute number of trades per second in the window."""
        if len(timestamps) < 2:
            return 0.0

        # Count trades in the last window_seconds
        current_time = timestamps[-1]
        window_start = current_time - window_seconds

        trades_in_window = sum(1 for ts in timestamps if ts >= window_start)
        return trades_in_window / window_seconds

    def _compute_volatility(self, returns: List[float], window_size: int = 60) -> float:
        """Compute rolling standard deviation of returns."""
        if len(returns) < 2:
            return 0.0

        # Use last window_size returns
        recent_returns = returns[-window_size:] if len(returns) > window_size else returns

        if len(recent_returns) > 1:
            return np.std(recent_returns)
        return 0.0

    def _compute_order_book_imbalance(self, best_bid: str, best_ask: str) -> Optional[float]:
        """Compute order book imbalance: (ask - bid) / (ask + bid)."""
        try:
            bid = float(best_bid) if best_bid else None
            ask = float(best_ask) if best_ask else None

            if bid is not None and ask is not None and bid > 0 and ask > 0:
                return (ask - bid) / (ask + bid)
            return None
        except (ValueError, TypeError):
            return None

    def _process_tick(self, tick_data: Dict) -> Optional[Dict]:
        """Process a single tick and compute features if window is ready."""
        product_id = tick_data.get("product_id", "")
        if not product_id:
            return None

        # Initialize buffer for this product if needed
        if product_id not in self.buffers:
            self.buffers[product_id] = {
                "timestamps": deque(maxlen=10000),
                "prices": deque(maxlen=10000),
                "midprices": deque(maxlen=10000),
                "returns": deque(maxlen=10000),
                "best_bids": deque(maxlen=10000),
                "best_asks": deque(maxlen=10000),
                "raw_ticks": deque(maxlen=10000),
            }

        buffer = self.buffers[product_id]

        # Extract data
        ingestion_ts = tick_data.get("ingestion_timestamp", time.time())
        price_str = tick_data.get("price", "")
        best_bid = tick_data.get("best_bid", "")
        best_ask = tick_data.get("best_ask", "")

        # Parse price
        try:
            price = float(price_str) if price_str else None
        except (ValueError, TypeError):
            price = None

        if price is None or price <= 0:
            return None

        # Compute midprice
        midprice = self._compute_midprice(best_bid, best_ask)
        if midprice is None:
            midprice = price  # Fallback to price if midprice unavailable

        # Add to buffers
        buffer["timestamps"].append(ingestion_ts)
        buffer["prices"].append(price)
        buffer["midprices"].append(midprice)
        buffer["best_bids"].append(best_bid)
        buffer["best_asks"].append(best_ask)
        buffer["raw_ticks"].append(tick_data)

        # Check if we have enough data for feature computation
        window_size = self.config["features"]["window_size"]
        min_points = self.config["features"]["min_window_points"]

        if len(buffer["timestamps"]) < min_points:
            return None

        # Check if we're at the window boundary (every N seconds or every N ticks)
        # For simplicity, compute features every tick (can be optimized)
        current_time = buffer["timestamps"][-1]
        window_start_time = current_time - window_size

        # Filter data within window
        window_indices = [i for i, ts in enumerate(buffer["timestamps"]) if ts >= window_start_time]

        if len(window_indices) < min_points:
            return None

        # Extract window data
        window_midprices = [buffer["midprices"][i] for i in window_indices]
        window_timestamps = [buffer["timestamps"][i] for i in window_indices]
        window_returns = []

        # Compute returns for the window
        for i in range(1, len(window_midprices)):
            if window_midprices[i - 1] > 0:
                ret = (window_midprices[i] - window_midprices[i - 1]) / window_midprices[i - 1]
                window_returns.append(ret)

        # Compute features
        compute_intervals = self.config["features"]["compute_intervals"]
        returns_dict = self._compute_returns(window_midprices, compute_intervals)

        # Bid-ask spread
        spread_info = self._compute_bid_ask_spread(best_bid, best_ask)

        # Trade intensity
        trade_intensity = self._compute_trade_intensity(list(window_timestamps), window_seconds=60)

        # Volatility (rolling std of returns)
        volatility = self._compute_volatility(
            window_returns, window_size=min(60, len(window_returns))
        )

        # Order book imbalance
        imbalance = self._compute_order_book_imbalance(best_bid, best_ask)

        # Build feature vector
        features = {
            "timestamp": current_time,
            "product_id": product_id,
            "price": price,
            "midprice": midprice,
            **returns_dict,
            "volatility": volatility,
            "trade_intensity": trade_intensity,
            "spread_abs": spread_info["spread_abs"] if spread_info else None,
            "spread_rel": spread_info["spread_rel"] if spread_info else None,
            "order_book_imbalance": imbalance,
            "window_size": len(window_indices),
            "num_returns": len(window_returns),
        }

        return features

    def _save_to_parquet(self, force: bool = False):
        """Save buffered features to Parquet file."""
        batch_size = self.config["features"]["parquet_batch_size"]

        if len(self.feature_buffer) >= batch_size or (force and len(self.feature_buffer) > 0):
            df = pd.DataFrame(self.feature_buffer)

            # Create filename with timestamp
            timestamp = int(time.time())
            parquet_path = self.features_dir / f"features_{timestamp}.parquet"

            df.to_parquet(parquet_path, index=False, engine="pyarrow")
            logger.info(f"Saved {len(self.feature_buffer)} features to {parquet_path}")

            # Also append to main features file
            main_features_path = self.features_dir / "features.parquet"
            if main_features_path.exists():
                existing_df = pd.read_parquet(main_features_path)
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df.to_parquet(main_features_path, index=False, engine="pyarrow")
            else:
                df.to_parquet(main_features_path, index=False, engine="pyarrow")

            self.feature_buffer.clear()

    def _publish_to_kafka(self, features: Dict):
        """Publish features to Kafka."""
        topic = self.config["kafka"]["topic_features"]
        product_id = features.get("product_id", "")

        value = json.dumps(features).encode("utf-8")
        key = product_id.encode("utf-8") if product_id else None

        def delivery_callback(err, msg):
            if err:
                logger.error(f"Failed to deliver feature message: {err}")

        try:
            self.producer.produce(topic, value=value, key=key, callback=delivery_callback)
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Error publishing features to Kafka: {e}")

    def start(self):
        """Start the feature engineering pipeline."""
        logger.info("Starting feature engineering pipeline")

        # Create Kafka consumer and producer
        self.consumer = self._create_kafka_consumer()
        self.producer = self._create_kafka_producer()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.running = True
        last_save_time = time.time()

        try:
            logger.info("Consuming ticks and computing features...")

            while self.running:
                # Poll for messages
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    # Check if we need to save buffered features
                    if time.time() - last_save_time > 60:  # Save every minute
                        self._save_to_parquet()
                        last_save_time = time.time()
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break

                try:
                    # Deserialize message
                    tick_data = json.loads(msg.value().decode("utf-8"))

                    # Process tick and compute features
                    features = self._process_tick(tick_data)

                    if features:
                        # Publish to Kafka
                        self._publish_to_kafka(features)

                        # Add to buffer for Parquet
                        self.feature_buffer.append(features)
                        self.feature_count += 1

                        if self.feature_count % 100 == 0:
                            logger.info(f"Computed {self.feature_count} feature vectors")

                        # Save to Parquet periodically
                        if (
                            len(self.feature_buffer)
                            >= self.config["features"]["parquet_batch_size"]
                        ):
                            self._save_to_parquet()
                            last_save_time = time.time()

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.shutdown()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def shutdown(self):
        """Gracefully shutdown the feature engineer."""
        logger.info("Shutting down feature engineering pipeline...")

        # Save remaining features
        self._save_to_parquet(force=True)

        if self.consumer:
            self.consumer.close()

        if self.producer:
            self.producer.flush(timeout=10)

        logger.info(f"Total features computed: {self.feature_count}")
        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    config_path = os.getenv("CONFIG_PATH", "config.yaml")

    try:
        engineer = FeatureEngineer(config_path)
        engineer.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
