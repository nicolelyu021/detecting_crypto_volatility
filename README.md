# Crypto Volatility Detection in Real-Time

A real-time AI system that predicts **60-second volatility spikes** for BTC-USD cryptocurrency trading data, enabling traders and risk systems to react faster to market swings.

## 🎯 Overview

This project implements a complete MLOps pipeline for detecting short-term crypto volatility spikes:
- **Data Ingestion**: Real-time streaming from Coinbase WebSocket via Kafka
- **Feature Engineering**: Windowed features computed over 60-second sliding windows
- **Model Training**: Baseline (Z-score) and ML models (Logistic Regression, XGBoost)
- **Monitoring**: Evidently AI for drift detection and data quality
- **Experiment Tracking**: MLflow for model versioning and metrics

## 📊 Model Performance

| Model | PR-AUC | F1-Score | Precision | Recall |
|-------|--------|----------|-----------|--------|
| **XGBoost** | **0.9997** | **0.9882** | **0.9779** | **0.9987** |
| Baseline (Z-score) | 0.9997 | 0.9595 | 0.9995 | 0.9226 |
| Logistic Regression | 0.7398 | 0.3309 | 0.7157 | 0.2152 |

**Recommendation**: Use XGBoost model for best performance.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nicolelyu021/detecting_crypto_volatility.git
   cd detecting_crypto_volatility
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start infrastructure**
   ```bash
   cd docker
   docker-compose up -d
   ```

   This starts:
   - Kafka (port 9092)
   - Zookeeper (port 2181)
   - MLflow (port 5001)

5. **Verify services are running**
   ```bash
   docker ps
   ```

## 📖 Usage

### 1. Data Ingestion

Collect live BTC-USD data from Coinbase:

```bash
python scripts/ws_ingest.py
```

This will:
- Connect to Coinbase WebSocket
- Stream data to Kafka topic `ticks.raw`
- Save raw data to `data/raw/slice.ndjson`

### 2. Feature Engineering

Generate features from raw data:

```bash
# From saved data (replay)
python scripts/replay.py

# Or from live Kafka stream
python features/featurizer.py --max-messages 100
```

Features are saved to `data/processed/features.parquet`

### 3. Model Training

Train all models (baseline, Logistic Regression, XGBoost):

```bash
python models/train.py
```

Models are logged to MLflow. View results:
```bash
mlflow ui --backend-store-uri file:./mlruns
```

### 4. Make Predictions

Use trained models for inference:

```bash
python models/infer.py \
  --model-path models/artifacts/xgboost/xgb_model.pkl \
  --data-path data/processed/test_data.parquet \
  --output-path predictions.parquet
```

### 5. Generate Reports

**Evidently Drift Report** (compare early vs late data):
```bash
python scripts/generate_evidently_report.py
```

**Train vs Test Drift Report**:
```bash
python scripts/generate_train_test_drift_report.py
```

**Model Evaluation Report**:
```bash
python scripts/generate_model_eval_report.py
```

## 📁 Project Structure

```
.
├── docker/              # Docker configurations
│   ├── compose.yaml     # Kafka, Zookeeper, MLflow services
│   └── Dockerfile.ingestor
├── scripts/             # Data ingestion and processing
│   ├── ws_ingest.py    # WebSocket data ingestion
│   ├── replay.py       # Feature generation from saved data
│   └── generate_*.py   # Report generation scripts
├── features/            # Feature engineering
│   └── featurizer.py   # Kafka consumer for feature computation
├── models/              # Model training and inference
│   ├── train.py        # Training pipeline with MLflow
│   ├── infer.py        # Inference script
│   ├── baseline.py      # Z-score baseline model
│   └── artifacts/      # Trained models and metrics
├── notebooks/           # Jupyter notebooks
│   └── eda.ipynb       # Exploratory data analysis
├── docs/                # Documentation
│   ├── feature_spec.md # Feature specifications
│   ├── model_card_v1.md # Model documentation
│   └── milestone*_log.md # Milestone logs
├── reports/             # Evaluation reports
│   ├── model_eval.pdf  # Model evaluation report
│   └── evidently/      # Drift and quality reports
└── handoff/             # Team handoff package
    ├── HANDOFF_NOTE.md  # Handoff instructions
    └── [all deliverables]
```

## 🔧 Configuration

### Key Parameters

- **Window Size**: 60 seconds
- **Threshold (τ)**: 0.000028 (95th percentile)
- **Features**: 5 windowed features
  - Midprice return mean/std
  - Bid-ask spread
  - Trade intensity
  - Order-book imbalance

### Environment Variables

See `.env.example` for configuration options:
- `KAFKA_SERVERS`: Kafka broker address
- `PAIR`: Trading pair (default: BTC-USD)
- `THRESHOLD_TAU`: Volatility threshold

## 📚 Documentation

- **Feature Specification**: `docs/feature_spec.md`
- **Model Card**: `docs/model_card_v1.md`
- **Milestone Logs**: `docs/milestone*_log.md`
- **Reviews**: `docs/MILESTONE*_REVIEW.md`

## 🧪 Testing

**Verify data pipeline**:
```bash
python scripts/kafka_consume_check.py --min 10
```

**Test inference latency** (should be < 120 seconds):
```bash
python models/infer.py \
  --model-path models/artifacts/baseline/baseline_model.pkl \
  --data-path data/processed/test_data.parquet
```

## 📦 Handoff Package

The `handoff/` folder contains a complete package for team integration:
- All models and artifacts
- 10-minute data slice with features
- Documentation and reports
- Setup instructions

See `handoff/HANDOFF_NOTE.md` for integration steps.

## 🎓 Course Information

**Course**: CMU 94-879 - Fundamentals of Operationalizing AI  
**Instructor**: Prof. A.S. Rao  
**Project**: Individual Programming Assignment - Detecting Crypto Volatility in Real-time

## 📝 License

This project is for educational purposes as part of the CMU course.

## 🙏 Acknowledgments

- Coinbase WebSocket API for real-time market data
- Evidently AI for drift detection
- MLflow for experiment tracking

---

**Status**: ✅ Complete - All milestones finished, ready for team handoff

