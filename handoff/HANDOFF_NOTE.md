# Handoff Note: Selected-Base

## Decision: **Selected-Base**

This handoff package contains a complete, production-ready implementation that can be used as the base for the team project.

---

## What's Included

### Infrastructure
- `docker/compose.yaml` - Complete Docker Compose setup with Kafka, Zookeeper, MLflow, and ingestor
- `docker/Dockerfile.ingestor` - Containerized data ingestion service
- `.env.example` - Environment variable template

### Documentation
- `docs/feature_spec.md` - Complete feature engineering specification
- `docs/model_card_v1.md` - Model documentation with performance metrics

### Models & Artifacts
- `models/artifacts/` - All trained models:
  - Baseline (Z-score rule)
  - Logistic Regression
  - XGBoost (best performing: PR-AUC = 0.9997)
- Model files (.pkl), metrics (JSON), visualizations (PNG)

### Data
- `data/raw/slice_10min.ndjson` - 10-minute raw data slice (6,000 records)
- `data/processed/features_10min.parquet` - Features generated from 10-minute slice

### Reports
- `reports/model_eval.pdf` - Comprehensive model evaluation report
- `reports/evidently/train_test_combined_report.html` - Data drift analysis

### Predictions
- `predictions_10min.parquet` - Sample predictions on 10-minute data

### Dependencies
- `requirements.txt` - All Python packages needed

---

## Exact Steps to Use This as Base

### Step 1: Setup Environment
```bash
# Copy environment file
cp .env.example .env
# Edit .env with your configuration if needed

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Start Infrastructure
```bash
cd docker
docker-compose up -d
# Wait for services to start (check with: docker ps)
```

### Step 3: Verify Data Pipeline
```bash
# Test data ingestion (collects 1 minute of data)
python scripts/ws_ingest.py

# Verify Kafka is receiving data
python scripts/kafka_consume_check.py --min 10

# Generate features from saved data
python scripts/replay.py
```

### Step 4: Load and Use Models
```bash
# Make predictions with baseline model
python models/infer.py \
  --model-path models/artifacts/baseline/baseline_model.pkl \
  --data-path data/processed/features_10min.parquet \
  --output-path predictions.parquet

# Or use XGBoost (best model)
python models/infer.py \
  --model-path models/artifacts/xgboost/xgb_model.pkl \
  --data-path data/processed/features_10min.parquet \
  --output-path predictions.parquet
```

### Step 5: Retrain Models (Optional)
```bash
# Retrain all models with new data
python models/train.py

# Models will be logged to MLflow
# View results: mlflow ui --backend-store-uri file:./mlruns
```

---

## Model Performance Summary

| Model | PR-AUC | F1-Score | Precision | Recall |
|-------|--------|----------|-----------|--------|
| **XGBoost** | **0.9997** | **0.9882** | **0.9779** | **0.9987** |
| Baseline (Z-score) | 0.9997 | 0.9595 | 0.9995 | 0.9226 |
| Logistic Regression | 0.7398 | 0.3309 | 0.7157 | 0.2152 |

**Recommendation**: Use **XGBoost** model for best performance.

---

## Key Configuration Values

- **Window Size**: 60 seconds
- **Threshold (τ)**: 0.000028 (95th percentile)
- **Features**: 5 windowed features (midprice returns, spread, trade intensity, order-book imbalance)
- **Prediction Task**: Forward-looking (predicts NEXT 60-second window volatility)

---

## Integration Points for Team

1. **Feature Engineering**: All features computed in `features/featurizer.py`
2. **Model Training**: Training pipeline in `models/train.py` with MLflow integration
3. **Inference**: Use `models/infer.py` for predictions
4. **Data Pipeline**: Kafka-based streaming with replay capability

---

## Notes for Team

- All code is production-ready and tested
- Models are trained on 33,881 samples with forward-looking labels
- Threshold was selected via EDA (95th percentile for good class balance)
- MLflow tracking is configured for experiment management
- Evidently reports show minimal drift between train/test splits

---

## Questions or Issues?

Refer to:
- `docs/feature_spec.md` for feature definitions
- `docs/model_card_v1.md` for model details
- `docs/milestone3_log.md` for implementation journey

---

**Status**: Ready for team integration ✅

