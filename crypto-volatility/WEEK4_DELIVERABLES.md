# Week 4 Deliverables: System Setup & API Thin Slice

## Overview

This document summarizes the Week 4 deliverables for the Crypto Volatility Detection project, focusing on building the first working system prototype in replay mode.

## Deliverables Checklist

### ✅ 1. Base/Composite Model Selection
- **Model Selected**: XGBoost (`xgb_model.pkl`)
- **Location**: `models/artifacts/xgb_model.pkl`
- **Rationale**: Documented in `docs/selection_rationale.md`

### ✅ 2. System Architecture Diagram
- **File**: `docs/architecture.md`
- **Format**: ASCII/text diagram showing:
  - Data ingestion layer (WebSocket → Kafka)
  - Feature engineering layer (Kafka → Features)
  - API & prediction layer (FastAPI + Model)
  - Infrastructure layer (Kafka, MLflow, Monitoring)

### ✅ 3. FastAPI Endpoints
- **File**: `api/app.py`
- **Endpoints Implemented**:
  - `GET /health`: Health check with model status
  - `POST /predict`: Make volatility predictions
  - `GET /version`: API and model version information
  - `GET /metrics`: Prometheus metrics endpoint

### ✅ 4. Docker Compose Configuration
- **File**: `docker/compose.yaml`
- **Services**:
  - Kafka (KRaft mode, no Zookeeper)
  - MLflow (model registry)
  - FastAPI API service
- **File**: `docker/Dockerfile.api` (API service Dockerfile)

### ✅ 5. Replay Script for 10-Minute Dataset
- **File**: `scripts/replay_to_kafka.py`
- **Features**:
  - Replays saved raw data through Kafka
  - Configurable duration (default: 10 minutes)
  - Speedup factor for faster testing
  - Maintains original timing relationships

### ✅ 6. Documentation
- **Team Charter**: `docs/team_charter.md`
  - Team roles and responsibilities
  - Working agreements
  - Success criteria
- **Selection Rationale**: `docs/selection_rationale.md`
  - Model comparison
  - Selection criteria
  - Deployment considerations

## Quick Start Guide

### 1. Start Infrastructure Services

```bash
cd crypto-volatility
docker-compose -f docker/compose.yaml up -d
```

This starts:
- Kafka on port 9092
- MLflow on port 5000
- FastAPI on port 8000

### 2. Verify Services

```bash
# Check Kafka
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Check MLflow
curl http://localhost:5000/health

# Check API
curl http://localhost:8000/health
```

### 3. Replay 10-Minute Dataset

```bash
# Replay 10 minutes of data through Kafka
python scripts/replay_to_kafka.py --duration 10

# Or with speedup (2x faster)
python scripts/replay_to_kafka.py --duration 10 --speedup 2.0
```

### 4. Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Version info
curl http://localhost:8000/version

# Make a prediction
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

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Sample curl Command for /predict

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

**Expected Response:**
```json
{
  "prediction": 0,
  "probability": 0.234,
  "model_version": "xgb-1234567890",
  "timestamp": 1234567890.123
}
```

## Architecture Overview

```
Ingestor → Kafka (raw) → Feature Engineer → Kafka (features) → API → Model → Predictions
```

See `docs/architecture.md` for detailed diagram.

## File Structure

```
crypto-volatility/
├── api/
│   ├── __init__.py
│   └── app.py                    # FastAPI application
├── docker/
│   ├── compose.yaml              # Docker Compose config
│   └── Dockerfile.api            # API Dockerfile
├── docs/
│   ├── architecture.md           # System architecture diagram
│   ├── team_charter.md           # Team roles and charter
│   └── selection_rationale.md    # Model selection rationale
├── scripts/
│   └── replay_to_kafka.py        # Kafka replay script
└── requirements.txt              # Updated with FastAPI deps
```

## Testing the Pipeline

### End-to-End Test

1. **Start services**: `docker-compose -f docker/compose.yaml up -d`
2. **Replay data**: `python scripts/replay_to_kafka.py --duration 10`
3. **Run feature engineer**: `python features/featurizer.py` (in another terminal)
4. **Test API**: Use curl commands above
5. **Check metrics**: `curl http://localhost:8000/metrics`

### Verification Checklist

- [ ] Kafka is running and accessible
- [ ] MLflow UI accessible at http://localhost:5000
- [ ] API health check returns "healthy"
- [ ] `/predict` endpoint returns valid predictions
- [ ] `/metrics` endpoint returns Prometheus metrics
- [ ] Replay script successfully publishes to Kafka
- [ ] 10-minute replay completes without errors

## Next Steps

- Week 5: Live data integration
- Week 6: Advanced monitoring and alerting
- Week 7: Performance optimization
- Week 8: Production deployment

## Notes

- The API loads the model (`xgb_model.pkl`) on startup
- Model version is derived from file modification time
- All predictions are logged to Prometheus metrics
- The system is designed for replay mode first, then live mode

---

**Status**: ✅ All Week 4 deliverables complete
**Date**: Week 4, 2024

