#!/usr/bin/env python3
"""
Kafka Consumer Validation Script
Consumes messages from Kafka topic to validate the stream.
"""

import json
import logging
import os
import signal
import sys

import yaml
from confluent_kafka import Consumer
from confluent_kafka.error import KafkaError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KafkaStreamValidator:
    """Validates Kafka stream by consuming and analyzing messages."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the validator with configuration."""
        self.config = self._load_config(config_path)
        self.consumer: Consumer | None = None
        self.running = False
        self.message_count = 0
        self.product_counts: dict[str, int] = {}

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file."""
        config_file = os.path.abspath(config_path)
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file) as f:
            return yaml.safe_load(f)

    def _create_kafka_consumer(self) -> Consumer:
        """Create and return a Kafka consumer."""
        bootstrap_servers = self.config["kafka"]["bootstrap_servers"]
        topic = self.config["kafka"]["topic_raw"]
        group_id = self.config["kafka"]["consumer_group"]

        logger.info(f"Connecting to Kafka at {bootstrap_servers}")
        logger.info(f"Subscribing to topic: {topic}")

        # Confluent Kafka uses a config dictionary
        consumer_config = {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",  # Start from beginning for validation
            "enable.auto.commit": True,
            "session.timeout.ms": 10000,
        }

        consumer = Consumer(consumer_config)
        consumer.subscribe([topic])

        return consumer

    def validate_message(self, message: dict) -> bool:
        """Validate message structure and content."""
        # Check for either 'timestamp' or 'ingestion_timestamp'
        required_fields = ["product_id", "price"]

        for field in required_fields:
            if field not in message:
                logger.warning(f"Missing required field: {field}")
                return False

        # Check for at least one timestamp field
        if "timestamp" not in message and "ingestion_timestamp" not in message:
            logger.warning("Missing timestamp field (timestamp or ingestion_timestamp)")
            return False

        # Validate price is numeric
        try:
            float(message["price"])
        except (ValueError, TypeError):
            logger.warning(f"Invalid price value: {message['price']}")
            return False

        return True

    def start(self, duration_seconds: int = 60):
        """Start consuming and validating messages."""
        logger.info("Starting Kafka stream validation")

        # Create Kafka consumer
        self.consumer = self._create_kafka_consumer()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.running = True
        start_time = os.times().elapsed

        try:
            logger.info(f"Consuming messages for {duration_seconds} seconds...")
            logger.info("Press Ctrl+C to stop early")

            while self.running:
                elapsed = os.times().elapsed - start_time
                if elapsed >= duration_seconds:
                    logger.info(f"Validation duration ({duration_seconds}s) reached")
                    break

                # Poll for messages (timeout in seconds)
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    # Timeout - no message available, continue polling
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition event - not an error, continue
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        break

                try:
                    # Deserialize message manually
                    value = json.loads(msg.value().decode("utf-8"))
                    msg.key().decode("utf-8") if msg.key() else None

                    # Validate message
                    if self.validate_message(value):
                        self.message_count += 1
                        product_id = value.get("product_id", "unknown")
                        self.product_counts[product_id] = self.product_counts.get(product_id, 0) + 1

                        # Log every 10 messages
                        if self.message_count % 10 == 0:
                            logger.info(
                                f"Consumed {self.message_count} messages | "
                                f"Latest: {product_id} @ {value.get('price', 'N/A')} | "
                                f"Partition: {msg.partition()}, Offset: {msg.offset()}"
                            )
                    else:
                        logger.warning(f"Invalid message: {value}")

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
        finally:
            self.shutdown()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def shutdown(self):
        """Gracefully shutdown the validator."""
        logger.info("Shutting down validator...")

        if self.consumer:
            self.consumer.close()

        # Print summary
        logger.info("=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total messages consumed: {self.message_count}")
        logger.info("Messages per product:")
        for product_id, count in sorted(self.product_counts.items()):
            logger.info(f"  {product_id}: {count} messages")
        logger.info("=" * 60)

        if self.message_count > 0:
            logger.info("✓ Stream validation successful!")
        else:
            logger.warning("⚠ No messages consumed. Check Kafka connection and topic.")

        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Kafka stream")
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration to consume messages in seconds (default: 60)",
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
        validator = KafkaStreamValidator(config_path)
        validator.start(duration_seconds=args.duration)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
