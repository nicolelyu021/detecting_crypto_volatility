#!/usr/bin/env python3
"""
Kafka Consumer for Real-time Volatility Predictions
Consumes feature messages from Kafka, makes predictions, and publishes results.
"""

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import yaml
from confluent_kafka import Consumer, Producer, KafkaError
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.infer import VolatilityPredictor

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PredictionConsumer:
    """Kafka consumer that makes real-time volatility predictions."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the prediction consumer."""
        self.config = self._load_config(config_path)
        self.consumer: Optional[Consumer] = None
        self.producer: Optional[Producer] = None
        self.predictor: Optional[VolatilityPredictor] = None
        self.running = False
        
        # Statistics
        self.messages_processed = 0
        self.predictions_made = 0
        self.errors = 0
        self.start_time = None
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_model(self):
        """Load the volatility prediction model."""
        logger.info("Loading prediction model...")
        
        # Try to load from MLflow first (same logic as API)
        model_variant = os.getenv('MODEL_VARIANT')
        model_run_id = os.getenv('MODEL_RUN_ID')
        model_run_name = os.getenv('MODEL_RUN_NAME')
        
        mlflow_model = None
        model_version = "unknown"
        loaded_from = "unknown"
        
        try:
            import mlflow
            import mlflow.sklearn
            import mlflow.xgboost
            
            # Allow override from environment variable (useful for Docker)
            mlflow_tracking_uri = os.getenv('MLFLOW_TRACKING_URI', self.config['mlflow']['tracking_uri'])
            mlflow.set_tracking_uri(mlflow_tracking_uri)
            
            if model_variant:
                # Load from Model Registry (e.g., "models:/xgb_model/Production")
                logger.info(f"Loading model from MLflow Model Registry: {model_variant}")
                mlflow_model = mlflow.pyfunc.load_model(model_variant)
                model_version = model_variant
                loaded_from = "mlflow_registry"
            elif model_run_id:
                # Load from specific run ID
                logger.info(f"Loading model from MLflow run: {model_run_id}")
                mlflow_model = mlflow.pyfunc.load_model(f"runs:/{model_run_id}/model")
                model_version = f"run-{model_run_id[:8]}"
                loaded_from = "mlflow_run_id"
            elif model_run_name:
                # Find run by name
                experiment = mlflow.get_experiment_by_name(self.config['mlflow']['experiment_name'])
                if experiment:
                    runs = mlflow.search_runs(
                        experiment_ids=[experiment.experiment_id],
                        filter_string=f"tags.mlflow.runName = '{model_run_name}'",
                        order_by=["start_time DESC"],
                        max_results=1
                    )
                    if not runs.empty:
                        run_id = runs.iloc[0]['run_id']
                        mlflow_model = mlflow.pyfunc.load_model(f"runs:/{run_id}/model")
                        model_version = f"run-{run_id[:8]}"
                        loaded_from = "mlflow_run_name"
        except Exception as e:
            logger.warning(f"Could not load model from MLflow: {e}")
        
        # Fallback to local pickle file
        if mlflow_model is None:
            logger.info("Loading model from local pickle file (fallback)")
            models_dir = Path(self.config['modeling']['models_dir'])
            model_path = models_dir / "xgb_model.pkl"
            
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Model not found. Tried:\n"
                    f"  1. MLflow Model Registry: {model_variant or 'not set'}\n"
                    f"  2. MLflow Run: {model_run_name or model_run_id or 'not set'}\n"
                    f"  3. Local file: {model_path}\n"
                    f"Please ensure MODEL_VARIANT is set or train a model first."
                )
            
            # Load from local pickle
            self.predictor = VolatilityPredictor(
                str(model_path),
                scaler_path=None,  # xgb_model.pkl was trained without a scaler
                model_type="ml"
            )
            model_version = f"local-{int(model_path.stat().st_mtime)}"
            loaded_from = "local_pickle"
            logger.info(f"✅ Loaded model from local file: {model_path}")
        else:
            # Create a wrapper for MLflow-loaded models
            logger.info("Creating MLflow model wrapper")
            
            class MLflowVolatilityPredictor:
                """Wrapper to make MLflow models compatible with VolatilityPredictor interface."""
                def __init__(self, mlflow_model, model_version_str):
                    self.model = mlflow_model
                    self.model_version = model_version_str
                    self.scaler = None
                    self.model_type = 'ml'
                
                def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
                    """Predict probabilities using MLflow model."""
                    try:
                        if hasattr(self.model, 'predict_proba'):
                            proba = self.model.predict_proba(X)
                            if proba.shape[1] == 1:
                                proba = np.column_stack([1 - proba[:, 0], proba[:, 0]])
                            return proba
                        elif hasattr(self.model, 'predict'):
                            predictions = self.model.predict(X)
                            if isinstance(predictions, np.ndarray) and len(predictions.shape) == 2:
                                return predictions
                            proba = np.zeros((len(predictions), 2))
                            proba[:, 1] = predictions
                            proba[:, 0] = 1 - predictions
                            return proba
                        else:
                            raise ValueError("MLflow model doesn't have predict or predict_proba method")
                    except Exception as e:
                        logger.error(f"Error in MLflow model prediction: {e}")
                        raise
            
            # Create wrapper
            self.predictor = MLflowVolatilityPredictor(mlflow_model, model_version)
            logger.info(f"✅ Created MLflow model wrapper (loaded from: {loaded_from})")
        
        logger.info(f"✅ Model loaded successfully (version: {model_version}, source: {loaded_from})")
    
    def _create_kafka_consumer(self) -> Consumer:
        """Create Kafka consumer for feature messages."""
        # Allow override from environment variable (useful for Docker)
        bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', self.config['kafka']['bootstrap_servers'])
        topic = self.config['kafka']['topic_features']
        consumer_group = self.config['kafka'].get('prediction_consumer_group', 'volatility-predictor')
        
        consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': consumer_group,
            'auto.offset.reset': 'latest',  # Start from latest messages
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'session.timeout.ms': 30000,
            'max.poll.interval.ms': 300000
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe([topic])
        
        logger.info(f"Created Kafka consumer for topic '{topic}' (group: {consumer_group})")
        return consumer
    
    def _create_kafka_producer(self) -> Producer:
        """Create Kafka producer for prediction results."""
        # Allow override from environment variable (useful for Docker)
        bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', self.config['kafka']['bootstrap_servers'])
        
        producer_config = {
            'bootstrap.servers': bootstrap_servers,
            'acks': 'all',
            'retries': 3,
            'compression.type': 'snappy'
        }
        
        producer = Producer(producer_config)
        logger.info(f"Created Kafka producer for {bootstrap_servers}")
        return producer
    
    def _process_feature_message(self, message_value: bytes) -> Optional[Dict]:
        """Process a feature message and make a prediction."""
        try:
            # Parse JSON message
            feature_data = json.loads(message_value.decode('utf-8'))
            
            # Extract features (same logic as /predict endpoint)
            price = feature_data.get('price', 0.0)
            midprice = feature_data.get('midprice', price)
            
            # Get return features
            return_1s = feature_data.get('return_1s', 0.0) or 0.0
            return_5s = feature_data.get('return_5s', 0.0) or 0.0
            return_30s = feature_data.get('return_30s', 0.0) or 0.0
            return_60s = feature_data.get('return_60s', 0.0) or 0.0
            
            # Compute derived features (same as /predict endpoint)
            returns = [r for r in [return_1s, return_5s, return_30s, return_60s] 
                      if r is not None and not np.isnan(r) and r != 0.0]
            
            if len(returns) > 0:
                midprice_return_mean = float(np.mean(returns))
                midprice_return_std = float(np.std(returns)) if len(returns) > 1 else 0.0
            else:
                midprice_return_mean = 0.0
                midprice_return_std = feature_data.get('volatility', 0.0) or 0.0
            
            bid_ask_spread = feature_data.get('spread_abs', 0.0) or 0.0
            trade_intensity = feature_data.get('trade_intensity', 0.0) or 0.0
            order_book_imbalance = feature_data.get('order_book_imbalance', 0.0) or 0.0
            
            # Create feature vector (exactly what model expects)
            feature_vector = {
                'midprice_return_mean': midprice_return_mean,
                'midprice_return_std': midprice_return_std,
                'bid_ask_spread': bid_ask_spread,
                'trade_intensity': trade_intensity,
                'order_book_imbalance': order_book_imbalance
            }
            
            # Create DataFrame
            df = pd.DataFrame([feature_vector], columns=[
                'midprice_return_mean',
                'midprice_return_std',
                'bid_ask_spread',
                'trade_intensity',
                'order_book_imbalance'
            ])
            
            # Make prediction
            probabilities = self.predictor.predict_proba(df)
            prob_value = probabilities[0, 1] if probabilities.shape[1] > 1 else probabilities[0, 0]
            
            # Binary prediction (threshold = 0.5)
            threshold = 0.5
            prediction = 1 if prob_value >= threshold else 0
            
            # Create prediction result
            prediction_result = {
                'timestamp': time.time(),
                'product_id': feature_data.get('product_id', 'unknown'),
                'price': price,
                'midprice': midprice,
                'prediction': prediction,
                'probability': float(prob_value),
                'threshold': threshold,
                'features': feature_vector,
                'model_version': getattr(self.predictor, 'model_version', 'unknown')
            }
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Error processing feature message: {e}", exc_info=True)
            return None
    
    def _publish_prediction(self, prediction: Dict):
        """Publish prediction result to Kafka."""
        topic = self.config['kafka'].get('topic_predictions', 'ticks.predictions')
        product_id = prediction.get('product_id', '').encode('utf-8') if prediction.get('product_id') else None
        
        value = json.dumps(prediction).encode('utf-8')
        
        def delivery_callback(err, msg):
            if err:
                logger.error(f"Failed to deliver prediction message: {err}")
        
        try:
            self.producer.produce(
                topic,
                value=value,
                key=product_id,
                callback=delivery_callback
            )
            self.producer.poll(0)
        except Exception as e:
            logger.error(f"Error publishing prediction to Kafka: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def start(self):
        """Start the prediction consumer."""
        logger.info("Starting prediction consumer...")
        
        # Load model
        self._load_model()
        
        # Create Kafka consumer and producer
        self.consumer = self._create_kafka_consumer()
        self.producer = self._create_kafka_producer()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.running = True
        self.start_time = time.time()
        
        logger.info("✅ Prediction consumer started. Waiting for messages...")
        
        try:
            while self.running:
                # Poll for messages (timeout = 1 second)
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition - continue polling
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        self.errors += 1
                        continue
                
                # Process message
                self.messages_processed += 1
                prediction = self._process_feature_message(msg.value())
                
                if prediction:
                    self.predictions_made += 1
                    self._publish_prediction(prediction)
                    
                    # Log periodically
                    if self.predictions_made % 100 == 0:
                        elapsed = time.time() - self.start_time
                        rate = self.predictions_made / elapsed if elapsed > 0 else 0
                        logger.info(
                            f"Processed {self.messages_processed} messages, "
                            f"made {self.predictions_made} predictions "
                            f"({rate:.1f} predictions/sec)"
                        )
                else:
                    self.errors += 1
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in consumer loop: {e}", exc_info=True)
        finally:
            self._shutdown()
    
    def _shutdown(self):
        """Shutdown the consumer gracefully."""
        logger.info("Shutting down prediction consumer...")
        
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
        
        if self.producer:
            self.producer.flush(timeout=10)
            logger.info("Kafka producer flushed")
        
        # Print statistics
        if self.start_time:
            elapsed = time.time() - self.start_time
            logger.info(f"\n{'='*60}")
            logger.info("PREDICTION CONSUMER STATISTICS")
            logger.info(f"{'='*60}")
            logger.info(f"Messages processed: {self.messages_processed}")
            logger.info(f"Predictions made: {self.predictions_made}")
            logger.info(f"Errors: {self.errors}")
            logger.info(f"Uptime: {elapsed:.1f} seconds")
            if elapsed > 0:
                logger.info(f"Processing rate: {self.messages_processed/elapsed:.1f} messages/sec")
                logger.info(f"Prediction rate: {self.predictions_made/elapsed:.1f} predictions/sec")
            logger.info(f"{'='*60}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Kafka consumer for real-time volatility predictions')
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )
    
    args = parser.parse_args()
    config_path = os.getenv('CONFIG_PATH', args.config)
    
    try:
        consumer = PredictionConsumer(config_path)
        consumer.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

