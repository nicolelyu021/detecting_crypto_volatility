# Crypto Volatility Detection Pipeline

A real-time data pipeline for detecting short-term volatility spikes in cryptocurrency markets using Coinbase Advanced Trade WebSocket API, Kafka, MLflow, and FastAPI.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for running scripts locally)

### 1. Start All Services

```bash
docker-compose -f docker/compose.yaml up -d
```

This starts:
- **Kafka** (port 9092) - Message streaming
- **MLflow** (port 5000) - Model registry and tracking
- **FastAPI** (port 8000) - Prediction API
- **Prediction Consumer** - Real-time Kafka consumer
- **Prometheus** (port 9090) - Metrics
- **Grafana** (port 3000) - Dashboards

Verify services:
```bash
docker-compose -f docker/compose.yaml ps
```

### 2. Access Services

- **FastAPI Docs**: http://localhost:8000/docs (Interactive API documentation)
- **MLflow UI**: http://localhost:5000 (Model experiments and registry)
- **Prometheus**: http://localhost:9090 (Metrics)
- **Grafana**: http://localhost:3000 (Login: admin/admin)

### 3. Replay Data to Test Pipeline

Replay raw data through Kafka to test the full pipeline:

```bash
python scripts/replay_to_kafka.py --duration 10
```

Options:
- `--duration 10` - Replay 10 minutes of data (default)
- `--speedup 2.0` - Replay at 2x speed
- `--data-file path/to/file.ndjson` - Use specific file (default: most recent in `data/raw/`)

### 4. Test API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "local-1234567890",
  "timestamp": 1234567890.0
}
```

#### Get Version
```bash
curl http://localhost:8000/version
```

Response:
```json
{
  "api_version": "1.0.0",
  "model_version": "local-1234567890",
  "model_loaded_at": 1234567890.0,
  "python_version": "3.11.0"
}
```

#### Make a Prediction
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

Response:
```json
{
  "prediction": 0,
  "probability": 0.23,
  "model_version": "local-1234567890",
  "timestamp": 1234567890.5
}
```

#### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

### 5. Check Real-Time Predictions (Kafka)

View predictions from the streaming consumer:

```bash
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ticks.predictions \
  --from-beginning
```

### 6. View Consumer Logs

```bash
docker logs -f volatility-prediction-consumer
```

## 📋 API Endpoints Summary

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/health` | GET | Health check and model status | `curl http://localhost:8000/health` |
| `/version` | GET | API and model version info | `curl http://localhost:8000/version` |
| `/predict` | POST | Make volatility prediction | See example above |
| `/metrics` | GET | Prometheus metrics | `curl http://localhost:8000/metrics` |
| `/docs` | GET | Interactive API docs (Swagger UI) | Open in browser |

## 🔄 Complete Pipeline Flow

```
Raw Data → Kafka (ticks.raw) 
  → Feature Engine → Kafka (ticks.features) 
  → Prediction Consumer → Kafka (ticks.predictions)
```

**To run the full pipeline:**

1. Start services: `docker-compose -f docker/compose.yaml up -d`
2. Run feature engine: `python features/featurizer.py` (in separate terminal)
3. Replay data: `python scripts/replay_to_kafka.py --duration 10`
4. Check predictions: View `ticks.predictions` topic or consumer logs

## 📚 Additional Documentation

- [Week 4 Deliverables](WEEK4_DELIVERABLES.md) - Complete Week 4 documentation
- [Prediction Consumer Guide](docs/prediction_consumer.md) - Kafka consumer details
- [How to Check Predictions](docs/check_predictions.md) - Verification guide
- [MLflow Integration](docs/mlflow_integration.md) - Model versioning and rollback

## Project Structure

```
crypto-volatility/
├── docker/
│   ├── compose.yaml          # Docker Compose for Kafka (KRaft) and MLflow
│   └── Dockerfile.ingestor    # Dockerfile for WebSocket ingestor
├── scripts/
│   ├── ws_ingest.py          # WebSocket ingestor script
│   └── kafka_consume_check.py # Kafka consumer validation script
├── docs/
│   └── scoping_brief.md      # Project scoping document
├── config.yaml               # Configuration file
├── requirements.txt          # Python dependencies
├── .env.example             # Example environment variables
└── README.md                # This file
```

## Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Git

## 📖 Detailed Setup (For Development)

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

For API only (avoids Pydantic conflicts):
```bash
pip install -r requirements-api.txt
```

### Run WebSocket Ingestor (Live Data)

Start ingesting data from Coinbase:

```bash
python scripts/ws_ingest.py
```

The script will:
- Connect to Coinbase Advanced Trade WebSocket API
- Subscribe to ticker channels for BTC-USD
- Publish messages to Kafka topic `ticks.raw`
- Save raw data to `data/raw/` directory

Let it run for at least 15 minutes to collect data.

### Run Feature Engine

Process raw data and generate features:

```bash
python features/featurizer.py
```

This will:
- Consume from `ticks.raw`
- Compute features (returns, volatility, spreads, etc.)
- Publish to `ticks.features`
- Save to `data/processed/features.parquet`

## Configuration

Edit `config.yaml` to customize:

- **Kafka settings:** Bootstrap servers, topic names
- **Coinbase products:** Trading pairs to monitor (default: BTC-USD, ETH-USD)
- **Ingestion settings:** Data directory, file format, reconnect behavior
- **MLflow settings:** Tracking URI, experiment name

## Testing Milestone 1 Requirements

### ✅ Verify Services Running

```bash
docker compose ps
```

All services should show "Up" status.

### ✅ Verify Data Ingestion

1. Run `ws_ingest.py` for 15 minutes
2. Check Kafka topic has messages:
   ```bash
   docker exec -it kafka kafka-console-consumer \
     --bootstrap-server localhost:9092 \
     --topic ticks.raw \
     --from-beginning \
     --max-messages 10
   ```

3. Check local data files:
   ```bash
   ls -lh data/raw/*.ndjson
   ```

### ✅ Verify Container Build

```bash
docker build -f docker/Dockerfile.ingestor -t crypto-ingestor .
docker run --rm crypto-ingestor --help
```

## Troubleshooting

### Kafka Connection Issues

- Ensure Kafka is running: `docker compose ps`
- Check Kafka logs: `docker logs kafka`
- Verify network connectivity: `docker network ls`

### WebSocket Connection Issues

- Check internet connectivity
- Verify Coinbase API is accessible
- Review logs for reconnection attempts

### No Messages in Kafka

- Verify ingestor is running and connected
- Check Kafka topic exists: `docker exec kafka kafka-topics --list --bootstrap-server localhost:9092`
- Review ingestor logs for errors

## Milestone 2: Feature Engineering & EDA

### Feature Engineering Pipeline

Run the feature engineering consumer to compute windowed features from raw ticks:

```bash
python features/featurizer.py
```

This will:
- Consume from Kafka topic `ticks.raw`
- Compute features (returns, volatility, spreads, trade intensity)
- Publish to Kafka topic `ticks.features`
- Save features to `data/processed/features.parquet`

### Replay Features from Raw Data

Regenerate features from saved raw data (useful for testing):

```bash
python scripts/replay.py --data-file data/raw/BTC-USD.ndjson
```

Or use the most recent file:
```bash
python scripts/replay.py
```

### Exploratory Data Analysis

Run the EDA notebook to:
- Analyze feature distributions
- Compute future volatility (target variable)
- Generate percentile plots
- Select volatility spike threshold

```bash
jupyter notebook notebooks/eda.ipynb
```

### Generate Evidently Report

Create data quality and drift report:

```bash
python scripts/generate_evidently_report.py
```

This generates:
- `reports/evidently/evidently_report.html` - HTML report
- `reports/evidently/evidently_report.json` - JSON report

## Milestone 3: Modeling, Tracking & Evaluation

### Train Models

Train baseline and ML models:

```bash
# Train with default Logistic Regression
python models/train.py

# Train with XGBoost
python models/train.py --model-type xgboost
```

This will:
- Compute future volatility and create labels
- Perform time-based train/validation/test splits
- Train baseline (z-score) and ML models
- Log everything to MLflow
- Save models to `models/artifacts/`

### Run Inference

Test model inference performance:

```bash
# Run inference on test set
python models/infer.py --benchmark

# Use specific model
python models/infer.py --model-path models/artifacts/xgboost_model.pkl --scaler-path models/artifacts/xgboost_scaler.pkl
```

### Generate Evaluation Report

Create comprehensive evaluation report:

```bash
python scripts/generate_evaluation_report.py
```

This generates `reports/model_eval.json` with:
- Model comparison (baseline vs ML)
- Test set metrics (PR-AUC, F1, precision, recall)
- Confusion matrix
- Classification report

### Generate Train vs Test Evidently Report

Compare training and test distributions:

```bash
python scripts/generate_evidently_report.py --compare-train-test
```

This generates drift and data quality reports comparing training vs test sets.

### View Results

- **MLflow UI:** http://localhost:5000 (view experiments, metrics, models)
- **Evaluation Report:** `reports/model_eval.json`
- **Evidently Report:** `reports/evidently/evidently_report.html`
- **Model Card:** `docs/model_card_v1.md`

## Next Steps

- Production deployment
- Real-time serving API
- Continuous monitoring and retraining

## License

This project is for educational/research purposes only. No actual trades are placed.

