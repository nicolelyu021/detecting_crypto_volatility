"""
Kafka consumer that computes windowed features from raw ticker data.

Features computed:
- midprice returns (rolling)
- bid-ask spread
- trade intensity (trades per second)
- optionally: order-book imbalance
"""

import time
import json
import orjson
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
import numpy as np


class FeatureWindow:
    """Sliding window to compute rolling features."""
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.ticks = deque()  # Store (timestamp, midprice, spread, has_trade)
        self.last_midprice = None
        
    def add_tick(self, ts: float, midprice: float, spread: float, has_trade: bool = True):
        """Add a new tick to the window."""
        self.ticks.append((ts, midprice, spread, has_trade))
        self.last_midprice = midprice
        
        # Remove ticks outside the window
        cutoff = ts - self.window_seconds
        while self.ticks and self.ticks[0][0] < cutoff:
            self.ticks.popleft()
    
    def compute_features(self, current_ts: float) -> Dict:
        """Compute features for the current window."""
        if len(self.ticks) < 2:
            return None
        
        window_ticks = list(self.ticks)
        if not window_ticks:
            return None
        
        # Extract data from window
        timestamps = [t[0] for t in window_ticks]
        midprices = [t[1] for t in window_ticks]
        spreads = [t[2] for t in window_ticks]
        trades = [t[3] for t in window_ticks]
        
        # Midprice returns (log returns)
        if len(midprices) >= 2:
            returns = np.diff(np.log(midprices))
            midprice_return_mean = float(np.mean(returns)) if len(returns) > 0 else 0.0
            midprice_return_std = float(np.std(returns)) if len(returns) > 0 else 0.0
        else:
            midprice_return_mean = 0.0
            midprice_return_std = 0.0
        
        # Bid-ask spread (average in window)
        avg_spread = float(np.mean(spreads)) if spreads else 0.0
        
        # Trade intensity (trades per second in window)
        window_duration = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 1.0
        trade_count = sum(trades)
        trade_intensity = trade_count / window_duration if window_duration > 0 else 0.0
        
        # Order-book imbalance (simplified: using spread as proxy)
        # If spread is large relative to midprice, imbalance exists
        current_midprice = midprices[-1] if midprices else 1.0
        order_book_imbalance = avg_spread / current_midprice if current_midprice > 0 else 0.0
        
        return {
            "ts": current_ts,
            "midprice_return_mean": midprice_return_mean,
            "midprice_return_std": midprice_return_std,
            "bid_ask_spread": avg_spread,
            "trade_intensity": trade_intensity,
            "order_book_imbalance": order_book_imbalance,
            "window_size": len(window_ticks),
            "window_duration": window_duration
        }


def parse_ticker_message(raw_str: str) -> Optional[Dict]:
    """Parse Coinbase ticker message from raw string."""
    try:
        tick = orjson.loads(raw_str)
        
        # Coinbase ticker format typically has:
        # - price: last trade price
        # - best_bid: best bid price
        # - best_ask: best ask price
        # - volume_24h: 24h volume
        # - time: timestamp
        
        # Handle different possible field names
        price = tick.get("price") or tick.get("last_price")
        best_bid = tick.get("best_bid") or tick.get("bid")
        best_ask = tick.get("best_ask") or tick.get("ask")
        
        # If we have price but no bid/ask, use price for both (simplified)
        if price and not (best_bid and best_ask):
            best_bid = float(price) * 0.9999  # Approximate
            best_ask = float(price) * 1.0001
        
        if not (best_bid and best_ask):
            return None
        
        best_bid = float(best_bid)
        best_ask = float(best_ask)
        midprice = (best_bid + best_ask) / 2.0
        spread = best_ask - best_bid
        
        return {
            "price": float(price) if price else midprice,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "midprice": midprice,
            "spread": spread,
            "volume_24h": tick.get("volume_24h", 0.0),
            "time": tick.get("time") or tick.get("timestamp")
        }
    except Exception as e:
        print(f"Error parsing ticker message: {e}")
        return None


def run_featurizer(
    input_topic: str = "ticks.raw",
    output_topic: str = "ticks.features",
    kafka_servers: str = "localhost:9092",
    window_seconds: int = 60,
    parquet_path: str = "data/processed/features.parquet",
    max_messages: Optional[int] = None
):
    """Main featurizer function."""
    
    # Create output directory
    parquet_file = Path(parquet_path)
    parquet_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize Kafka consumer
    consumer = KafkaConsumer(
        input_topic,
        bootstrap_servers=kafka_servers,
        auto_offset_reset="earliest",
        group_id="featurizer-group",
        value_deserializer=lambda m: orjson.loads(m)
    )
    
    # Initialize Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=kafka_servers,
        value_serializer=lambda v: orjson.dumps(v)
    )
    
    # Initialize feature window
    window = FeatureWindow(window_seconds=window_seconds)
    
    # Store features for Parquet output
    features_list = []
    
    print(f"Featurizer started. Consuming from '{input_topic}', outputting to '{output_topic}'")
    print(f"Window size: {window_seconds} seconds")
    
    message_count = 0
    
    try:
        for message in consumer:
            message_count += 1
            
            # Parse message
            rec = message.value
            ts = rec.get("ts", time.time())
            raw_str = rec.get("raw", "")
            
            # Parse ticker data
            tick_data = parse_ticker_message(raw_str)
            if not tick_data:
                continue
            
            # Add to window
            window.add_tick(
                ts=ts,
                midprice=tick_data["midprice"],
                spread=tick_data["spread"],
                has_trade=True  # Assume each tick is a trade
            )
            
            # Compute features
            features = window.compute_features(ts)
            if features is None:
                continue
            
            # Add metadata
            features["pair"] = rec.get("pair", "BTC-USD")
            features["raw_price"] = tick_data["price"]
            
            # Send to Kafka
            producer.send(output_topic, value=features)
            
            # Store for Parquet
            features_list.append(features)
            
            # Periodically save to Parquet
            if len(features_list) >= 100:
                df = pd.DataFrame(features_list)
                if parquet_file.exists():
                    # Append to existing file
                    existing_df = pd.read_parquet(parquet_file)
                    df = pd.concat([existing_df, df], ignore_index=True)
                df.to_parquet(parquet_file, engine="pyarrow", index=False)
                print(f"Saved {len(df)} features to {parquet_file}")
                features_list = []
            
            if max_messages and message_count >= max_messages:
                print(f"Reached max messages ({max_messages}), stopping...")
                break
                
    except KeyboardInterrupt:
        print("\nFeaturizer stopped by user")
    finally:
        # Save remaining features
        if features_list:
            df = pd.DataFrame(features_list)
            if parquet_file.exists():
                existing_df = pd.read_parquet(parquet_file)
                df = pd.concat([existing_df, df], ignore_index=True)
            df.to_parquet(parquet_file, engine="pyarrow", index=False)
            print(f"Final save: {len(df)} features to {parquet_file}")
        
        consumer.close()
        producer.close()
        print("Featurizer closed")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Kafka consumer for feature engineering")
    parser.add_argument("--input-topic", default="ticks.raw", help="Input Kafka topic")
    parser.add_argument("--output-topic", default="ticks.features", help="Output Kafka topic")
    parser.add_argument("--servers", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--window-seconds", type=int, default=60, help="Feature window size in seconds")
    parser.add_argument("--parquet-path", default="data/processed/features.parquet", help="Path to save Parquet file")
    parser.add_argument("--max-messages", type=int, default=None, help="Maximum messages to process (for testing)")
    
    args = parser.parse_args()
    
    run_featurizer(
        input_topic=args.input_topic,
        output_topic=args.output_topic,
        kafka_servers=args.servers,
        window_seconds=args.window_seconds,
        parquet_path=args.parquet_path,
        max_messages=args.max_messages
    )

