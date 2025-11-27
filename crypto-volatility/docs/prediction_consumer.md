# Prediction Consumer

## Overview

The prediction consumer completes the real-time streaming pipeline by:
1. Consuming feature messages from the `ticks.features` Kafka topic
2. Making volatility predictions using the trained model
3. Publishing prediction results to the `ticks.predictions` Kafka topic

## Architecture

```
ticks.raw → [Feature Engine] → ticks.features → [Prediction Consumer] → ticks.predictions
```

## Usage

### Local Development

```bash
# Make sure Kafka and MLflow are running
docker-compose -f docker/compose.yaml up -d kafka mlflow

# Run the consumer
python scripts/prediction_consumer.py --config config.yaml
```

### Docker

The consumer is automatically started when you run:

```bash
docker-compose -f docker/compose.yaml up -d
```

The consumer service is named `prediction-consumer` and will:
- Connect to Kafka at `kafka:29092` (internal Docker network)
- Connect to MLflow at `http://mlflow:5000`
- Read from `ticks.features` topic
- Write to `ticks.predictions` topic

## Configuration

### Environment Variables

- `CONFIG_PATH`: Path to config file (default: `config.yaml`)
- `KAFKA_BOOTSTRAP_SERVERS`: Override Kafka bootstrap servers (default: from config)
- `MLFLOW_TRACKING_URI`: Override MLflow tracking URI (default: from config)
- `MODEL_VARIANT`: MLflow model variant (e.g., `models:/xgb_model/Production`)
- `MODEL_RUN_ID`: MLflow run ID to load model from
- `MODEL_RUN_NAME`: MLflow run name to load model from

### Config File Settings

In `config.yaml`:

```yaml
kafka:
  bootstrap_servers: "localhost:9092"
  topic_features: "ticks.features"
  topic_predictions: "ticks.predictions"
  prediction_consumer_group: "volatility-predictor"
```

## Model Loading

The consumer attempts to load the model in this order:

1. **MLflow Model Registry** (if `MODEL_VARIANT` is set)
   - Example: `models:/xgb_model/Production`

2. **MLflow Run** (if `MODEL_RUN_ID` or `MODEL_RUN_NAME` is set)
   - Loads from a specific MLflow run

3. **Local Pickle File** (fallback)
   - Loads from `models/artifacts/xgb_model.pkl`

## Prediction Format

### Input (from `ticks.features`)

```json
{
  "timestamp": 1234567890.0,
  "product_id": "BTC-USD",
  "price": 50000.0,
  "midprice": 50000.5,
  "return_1s": 0.0001,
  "return_5s": 0.0005,
  "return_30s": 0.002,
  "return_60s": 0.004,
  "volatility": 0.001,
  "trade_intensity": 2.5,
  "spread_abs": 1.0,
  "spread_rel": 0.00002,
  "order_book_imbalance": 0.1
}
```

### Output (to `ticks.predictions`)

```json
{
  "timestamp": 1234567890.5,
  "product_id": "BTC-USD",
  "price": 50000.0,
  "midprice": 50000.5,
  "prediction": 0,
  "probability": 0.23,
  "threshold": 0.5,
  "features": {
    "midprice_return_mean": 0.00165,
    "midprice_return_std": 0.0015,
    "bid_ask_spread": 1.0,
    "trade_intensity": 2.5,
    "order_book_imbalance": 0.1
  },
  "model_version": "local-1234567890"
}
```

## Monitoring

The consumer logs:
- Messages processed
- Predictions made
- Errors encountered
- Processing rate (messages/sec, predictions/sec)

View logs:

```bash
# Docker
docker logs -f volatility-prediction-consumer

# Local
# Logs are printed to stdout
```

## Testing the Pipeline

1. **Start all services:**
   ```bash
   docker-compose -f docker/compose.yaml up -d
   ```

2. **Replay data to Kafka:**
   ```bash
   python scripts/replay_to_kafka.py --duration 10
   ```

3. **Check consumer logs:**
   ```bash
   docker logs -f volatility-prediction-consumer
   ```

4. **Verify predictions topic:**
   ```bash
   # Use kafka-console-consumer to see predictions
   docker exec -it kafka kafka-console-consumer \
     --bootstrap-server localhost:9092 \
     --topic ticks.predictions \
     --from-beginning
   ```

## Troubleshooting

### Consumer not receiving messages

- Check that the feature engine is running and publishing to `ticks.features`
- Verify Kafka connectivity: `docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092`
- Check consumer group: `docker exec -it kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group volatility-predictor`

### Model loading errors

- Ensure model file exists: `ls models/artifacts/xgb_model.pkl`
- Check MLflow connection: `curl http://localhost:5000/health`
- Verify model version in logs

### No predictions published

- Check consumer logs for errors
- Verify producer can connect to Kafka
- Check that `ticks.predictions` topic exists (auto-created if `KAFKA_AUTO_CREATE_TOPICS_ENABLE=true`)

