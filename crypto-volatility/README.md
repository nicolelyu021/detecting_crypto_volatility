# Crypto Volatility Detection Pipeline

A real-time data pipeline for detecting short-term volatility spikes in cryptocurrency markets using Coinbase Advanced Trade WebSocket API, Kafka, MLflow, and Evidently.

## 🎯 Week 4: System Setup & API Thin Slice

This repository now includes the Week 4 deliverables with a complete FastAPI application, Docker Compose setup, and monitoring infrastructure.

### Quick Start (Week 4)

1. **Start Infrastructure:**
   ```bash
   docker-compose -f docker/compose.yaml up -d
   ```

2. **Test API:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/docs  # Interactive API docs
   ```

3. **Replay 10-Minute Dataset:**
   ```bash
   python scripts/replay_to_kafka.py --duration 10
   ```

4. **Make a Prediction:**
   ```bash
   curl -X POST http://localhost:8000/predict \
     -H "Content-Type: application/json" \
     -d '{
       "price": 50000.0,
       "midprice": 50000.0,
       "return_1s": 0.001,
       "return_5s": 0.002,
       "return_30s": 0.005,
       "return_60s": 0.01,
       "volatility": 0.02,
       "trade_intensity": 10.0,
       "spread_abs": 1.0,
       "spread_rel": 0.00002,
       "order_book_imbalance": 0.001
     }'
   ```

### Week 4 Services

- **API**: http://localhost:8000 (FastAPI with /health, /predict, /version, /metrics)
- **MLflow**: http://localhost:5000 (Model registry)
- **Prometheus**: http://localhost:9090 (Metrics database)
- **Grafana**: http://localhost:3000 (Visualization - admin/admin)

See [WEEK4_DELIVERABLES.md](WEEK4_DELIVERABLES.md) for complete Week 4 documentation.

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

## Quick Start

### 1. Start Infrastructure Services

Start Kafka (KRaft mode) and MLflow:

```bash
cd docker
docker compose up -d
```

Verify services are running:

```bash
docker compose ps
```

You should see:
- `kafka` (port 9092)
- `mlflow` (port 5000)

Access MLflow UI at: http://localhost:5000

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example environment file (optional, defaults are in config.yaml):

```bash
cp .env.example .env
```

Edit `.env` if you need to override any defaults.

### 4. Run WebSocket Ingestor

Start ingesting data from Coinbase:

```bash
python scripts/ws_ingest.py
```

The script will:
- Connect to Coinbase Advanced Trade WebSocket API
- Subscribe to ticker channels for BTC-USD and ETH-USD
- Publish messages to Kafka topic `ticks.raw`
- Optionally save raw data to `data/raw/` directory

Let it run for at least 15 minutes to collect data.

### 5. Validate Kafka Stream

In a separate terminal, run the validation consumer:

```bash
python scripts/kafka_consume_check.py --duration 60
```

This will consume messages from Kafka and display validation statistics.

### 6. Run Ingestor in Docker

Build and run the ingestor container:

```bash
# From project root directory
# Build the image
docker build -f docker/Dockerfile.ingestor -t crypto-ingestor .

# Run the container (connect to Kafka network)
docker run --rm \
  --network docker_kafka-network \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml \
  crypto-ingestor
```

Note: The network name may vary. Check with `docker network ls` and look for a network containing "kafka-network".

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

