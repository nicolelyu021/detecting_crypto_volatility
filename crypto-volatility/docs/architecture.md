# System Architecture

## Overview

The Crypto Volatility Detection system is a real-time pipeline that ingests market data, computes features, and predicts volatility spikes using machine learning.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Data Ingestion Layer                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   Coinbase WebSocket          │
                    │   (ws_ingest.py)              │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   Kafka Topic: ticks.raw      │
                    │   (Raw tick data)             │
                    └───────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Feature Engineering Layer                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   Feature Engineer             │
                    │   (featurizer.py)              │
                    │   - Windowed features          │
                    │   - Returns, volatility        │
                    │   - Spreads, intensity         │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   Kafka Topic: ticks.features  │
                    │   (Computed features)         │
                    └───────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API & Prediction Layer                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
    ┌───────────────────────────┐    ┌───────────────────────────┐
    │   FastAPI Service         │    │   Feature Consumer        │
    │   (api/app.py)             │    │   (Kafka consumer)        │
    │   - /health                │    │   - Consumes features    │
    │   - /predict               │    │   - Calls API           │
    │   - /version               │    │                          │
    │   - /metrics               │    └──────────────────────────┘
    └───────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────┐
    │   XGBoost Model           │
    │   (xgb_model.pkl)         │
    │   - Loaded on startup     │
    │   - Real-time predictions │
    └───────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────┐
    │   Predictions             │
    │   - Binary (0/1)          │
    │   - Probability           │
    └───────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         Infrastructure Layer                             │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
    │   Kafka (KRaft)  │      │   MLflow         │      │   Monitoring     │
    │   - Topic: raw   │      │   - Model reg.   │      │   - Prometheus    │
    │   - Topic:       │      │   - Tracking     │      │   - Metrics      │
    │     features     │      │   - Artifacts    │      │                  │
    └──────────────────┘      └──────────────────┘      └──────────────────┘
```

## Component Details

### 1. Data Ingestion
- **Component**: `scripts/ws_ingest.py`
- **Source**: Coinbase WebSocket API
- **Output**: Raw tick data to Kafka topic `ticks.raw`
- **Format**: NDJSON (one JSON object per line)

### 2. Feature Engineering
- **Component**: `features/featurizer.py`
- **Input**: Raw ticks from Kafka
- **Output**: Computed features to Kafka topic `ticks.features`
- **Features**:
  - Returns (1s, 5s, 30s, 60s)
  - Rolling volatility
  - Trade intensity
  - Bid-ask spreads
  - Order book imbalance

### 3. API Service
- **Component**: `api/app.py`
- **Framework**: FastAPI
- **Endpoints**:
  - `GET /health`: Health check
  - `POST /predict`: Make predictions
  - `GET /version`: API and model version
  - `GET /metrics`: Prometheus metrics
- **Model**: XGBoost (xgb_model.pkl)

### 4. Infrastructure
- **Kafka**: Message broker (KRaft mode, no Zookeeper)
- **MLflow**: Model registry and tracking
- **Monitoring**: Prometheus metrics exposed via `/metrics`

## Data Flow

1. **Ingestion**: WebSocket → Kafka (raw)
2. **Feature Engineering**: Kafka (raw) → Features → Kafka (features)
3. **Prediction**: Kafka (features) → API → Model → Predictions
4. **Storage**: Features saved to Parquet, models to MLflow

## Replay Mode

For testing, the system supports replay mode:
- `scripts/replay_to_kafka.py`: Replays saved data through Kafka
- Maintains original timing (with optional speedup)
- Tests end-to-end pipeline without live data

## Deployment

All services run via Docker Compose:
- Kafka (KRaft mode)
- MLflow
- FastAPI service

See `docker/compose.yaml` for configuration.

