#!/usr/bin/env python3
"""
Coinbase Advanced Trade WebSocket Ingestor
Connects to Coinbase WebSocket API, collects ticker data, and streams to Kafka.
"""

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import websocket
import yaml
from dotenv import load_dotenv
from confluent_kafka import Producer
from confluent_kafka.error import KafkaError


# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CoinbaseWSIngestor:
    """WebSocket ingestor for Coinbase Advanced Trade API."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the ingestor with configuration."""
        self.config = self._load_config(config_path)
        self.producer: Optional[Producer] = None
        self.ws: Optional[websocket.WebSocketApp] = None
        self.running = False
        self.reconnect_attempts = 0
        self.last_heartbeat = time.time()
        self.message_count = 0
        self.subscription_error_count = 0
        self.last_error = None
        
        # Create data directory if it doesn't exist
        self.data_dir = Path(self.config['ingestion']['data_dir'])
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file or environment variable."""
        # Allow override from environment variable
        config_path = os.getenv('CONFIG_PATH', config_path)
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _create_kafka_producer(self) -> Producer:
        """Create and return a Kafka producer with retry and reconnect logic."""
        # Allow override from environment variable
        bootstrap_servers = os.getenv(
            'KAFKA_BOOTSTRAP_SERVERS',
            self.config['kafka']['bootstrap_servers']
        )
        logger.info(f"Connecting to Kafka at {bootstrap_servers}")
        
        # Confluent Kafka uses a config dictionary
        producer_config = {
            'bootstrap.servers': bootstrap_servers,
            'acks': 'all',
            'retries': 10,  # Increased retries for resilience
            'retry.backoff.ms': 1000,  # 1 second backoff between retries
            'max.in.flight.requests.per.connection': 1,
            'enable.idempotence': True,
            'compression.type': 'snappy',
            'socket.keepalive.enable': True,  # Keep connections alive
            'reconnect.backoff.ms': 100,  # Initial reconnect backoff
            'reconnect.backoff.max.ms': 10000,  # Max reconnect backoff
            'message.send.max.retries': 10,  # Max retries per message
            'request.timeout.ms': 30000,  # Request timeout
            'delivery.timeout.ms': 120000,  # Total delivery timeout
        }
        
        return Producer(producer_config)
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            # Handle different message types
            # Coinbase Advanced Trade API can send messages in different formats
            if 'channel' in data:
                if data['channel'] == 'ticker':
                    # Handle ticker channel messages
                    if 'events' in data:
                        # New format with events array
                        for event in data.get('events', []):
                            if event.get('type') == 'snapshot' or event.get('type') == 'update':
                                for ticker in event.get('tickers', []):
                                    self._handle_ticker_message(ticker, data.get('timestamp'))
                    else:
                        # Direct ticker message
                        self._handle_ticker_message(data, data.get('timestamp'))
                elif data['channel'] == 'heartbeat':
                    self.last_heartbeat = time.time()
                    logger.debug("Received heartbeat")
            elif 'type' in data:
                if data['type'] == 'subscriptions':
                    logger.info(f"Subscribed to channels: {data}")
                    self.subscription_error_count = 0  # Reset on successful subscription
                elif data['type'] == 'error':
                    error_msg = data.get('message', str(data))
                    logger.error(f"WebSocket error: {error_msg}")
                    self.last_error = error_msg
                    self.subscription_error_count += 1
                    
                    # If we get repeated subscription errors, don't reconnect (it won't help)
                    if 'channel' in error_msg.lower() or 'unmarshal' in error_msg.lower():
                        logger.error("Subscription format error detected. This won't be fixed by reconnecting.")
                        if self.subscription_error_count >= 3:
                            logger.error("Too many subscription errors. Exiting to prevent infinite loop.")
                            self.running = False
                            if self.ws:
                                self.ws.close()
                elif data['type'] == 'heartbeat':
                    self.last_heartbeat = time.time()
                    logger.debug("Received heartbeat")
            else:
                # Try to handle as ticker if it has product_id and price
                if 'product_id' in data and 'price' in data:
                    self._handle_ticker_message(data, data.get('timestamp'))
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}, message: {message}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    def _handle_ticker_message(self, data: Dict, message_timestamp: str = None):
        """Process ticker messages and send to Kafka."""
        try:
            # Extract relevant ticker data
            ticker_data = {
                'ingestion_timestamp': time.time(),
                'message_timestamp': message_timestamp or data.get('timestamp', ''),
                'product_id': data.get('product_id', ''),
                'price': data.get('price', ''),
                'time': data.get('time', ''),
                'volume_24h': data.get('volume_24h', ''),
                'volume_30d': data.get('volume_30d', ''),
                'best_bid': data.get('best_bid', ''),
                'best_ask': data.get('best_ask', ''),
                'side': data.get('side', ''),
                'trade_id': data.get('trade_id', ''),
                'last_size': data.get('last_size', ''),
                'high_24h': data.get('high_24h', ''),
                'low_24h': data.get('low_24h', ''),
                'open_24h': data.get('open_24h', ''),
            }
            
            # Send to Kafka
            topic = self.config['kafka']['topic_raw']
            product_id = ticker_data['product_id']
            
            # Serialize message manually
            value = json.dumps(ticker_data).encode('utf-8')
            key = product_id.encode('utf-8') if product_id else None
            
            # Delivery callback for error handling
            def delivery_callback(err, msg):
                if err:
                    logger.error(f"Failed to deliver message: {err}")
                else:
                    logger.debug(f"Message delivered to {topic}[{msg.partition()}]:{msg.offset()}")
            
            # Produce message (non-blocking)
            try:
                self.producer.produce(
                    topic,
                    value=value,
                    key=key,
                    callback=delivery_callback
                )
                # Poll to handle delivery callbacks (non-blocking)
                self.producer.poll(0)
            except BufferError:
                # Producer buffer is full, flush and retry
                logger.warning("Producer buffer full, flushing...")
                self.producer.poll(1)
                # Retry once
                try:
                    self.producer.produce(
                        topic,
                        value=value,
                        key=key,
                        callback=delivery_callback
                    )
                except Exception as e:
                    logger.error(f"Failed to send message after flush: {e}")
            except KafkaError as e:
                logger.error(f"Failed to send message to Kafka: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending message: {e}")
            
            # Optionally write to local file
            self._write_to_file(ticker_data)
            
            self.message_count += 1
            if self.message_count % 100 == 0:
                logger.info(f"Processed {self.message_count} messages")
                
        except Exception as e:
            logger.error(f"Error handling ticker message: {e}", exc_info=True)
    
    def _write_to_file(self, data: Dict):
        """Write data to local file (NDJSON format)."""
        if self.config['ingestion']['file_format'] == 'ndjson':
            product_id = data.get('product_id', 'unknown')
            file_path = self.data_dir / f"{product_id}.ndjson"
            
            with open(file_path, 'a') as f:
                f.write(json.dumps(data) + '\n')
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close events with reconnect logic."""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        
        # Don't reconnect if we had subscription errors (reconnecting won't help)
        if self.subscription_error_count >= 3:
            logger.error("Too many subscription errors. Not reconnecting.")
            self.running = False
            return
        
        # Don't reconnect if shutdown was requested
        if not self.running:
            logger.info("Shutdown requested, not reconnecting.")
            return
        
        # Attempt to reconnect with exponential backoff
        max_attempts = self.config['ingestion']['max_reconnect_attempts']
        if self.reconnect_attempts < max_attempts:
            delay = self.config['ingestion']['reconnect_delay']
            # Exponential backoff: delay * 2^attempts, capped at 60 seconds
            actual_delay = min(delay * (2 ** min(self.reconnect_attempts, 5)), 60)
            logger.info(
                f"Reconnecting in {actual_delay:.1f} seconds... "
                f"(attempt {self.reconnect_attempts + 1}/{max_attempts})"
            )
            time.sleep(actual_delay)
            self.reconnect_attempts += 1
            
            # Only reconnect if still running
            if self.running:
                try:
                    self.connect()
                except Exception as e:
                    logger.error(f"Reconnection attempt failed: {e}")
                    if self.reconnect_attempts >= max_attempts:
                        logger.error("Max reconnect attempts reached. Exiting.")
                        self.running = False
        else:
            logger.error("Max reconnect attempts reached. Exiting.")
            self.running = False
    
    def _on_open(self, ws):
        """Handle WebSocket open events."""
        logger.info("WebSocket connection opened")
        self.running = True
        self.reconnect_attempts = 0
        self.subscription_error_count = 0  # Reset subscription errors on new connection
        self.last_heartbeat = time.time()
        
        # Small delay before subscribing (some APIs need a moment after connection)
        time.sleep(0.5)
        
        # Subscribe to ticker channels
        self._subscribe_to_channels()
    
    def _subscribe_to_channels(self):
        """Subscribe to ticker channels for configured products."""
        products = self.config['coinbase']['products']
        channels = self.config['coinbase']['channels']
        
        # Coinbase API expects 'channel' (singular) as a string, not an array
        # If multiple channels are specified, subscribe to each one separately
        for channel in channels:
            subscribe_message = {
                "type": "subscribe",
                "product_ids": products,
                "channel": channel  # Singular, string value
            }
            
            logger.info(f"Subscribing to channel '{channel}' for products: {products}")
            try:
                self.ws.send(json.dumps(subscribe_message))
            except Exception as e:
                logger.error(f"Failed to send subscription for channel {channel}: {e}")
    
    def _check_heartbeat(self):
        """Check if heartbeat is still active."""
        heartbeat_interval = self.config['coinbase']['heartbeat_interval']
        time_since_heartbeat = time.time() - self.last_heartbeat
        
        if time_since_heartbeat > heartbeat_interval * 2:
            logger.warning(f"No heartbeat received for {time_since_heartbeat:.1f} seconds. Reconnecting...")
            self.ws.close()
    
    def connect(self):
        """Establish WebSocket connection."""
        ws_url = self.config['coinbase']['ws_url']
        logger.info(f"Connecting to {ws_url}")
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        # Run WebSocket in a separate thread
        self.ws.run_forever()
    
    def start(self):
        """Start the ingestor."""
        logger.info("Starting Coinbase WebSocket Ingestor")
        
        # Create Kafka producer
        self.producer = self._create_kafka_producer()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Connect to WebSocket
        try:
            self.connect()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.ws:
            self.ws.close()
    
    def shutdown(self):
        """Gracefully shutdown the ingestor."""
        logger.info("Shutting down ingestor...")
        self.running = False
        
        # Close WebSocket connection
        if self.ws:
            try:
                self.ws.close()
                # Give it a moment to close gracefully
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        # Flush Kafka producer with retries
        if self.producer:
            try:
                logger.info("Flushing remaining Kafka messages...")
                # Poll to handle any pending delivery callbacks
                remaining = self.producer.poll(1)
                # Flush with timeout
                unflushed = self.producer.flush(timeout=10)
                if unflushed > 0:
                    logger.warning(f"{unflushed} messages could not be flushed")
                else:
                    logger.info("All messages flushed successfully")
            except Exception as e:
                logger.error(f"Error flushing producer: {e}")
        
        logger.info(f"Total messages processed: {self.message_count}")
        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')
    
    try:
        ingestor = CoinbaseWSIngestor(config_path)
        ingestor.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

