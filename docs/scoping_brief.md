# Crypto Volatility Detection Pipeline
## Scoping Brief - Milestone 1

**Date:** 2024  
**Project:** Real-time Cryptocurrency Volatility Spike Detection  
**Milestone:** 1 - Streaming Setup & Scoping

---

## 1. Use Case

### Problem Statement
Cryptocurrency markets exhibit high volatility with rapid price movements that can occur within seconds. Traders, risk managers, and algorithmic trading systems need early warning signals to detect short-term volatility spikes before they fully materialize. Current solutions often rely on batch processing or delayed indicators, missing critical windows for decision-making.

### Solution Overview
We are building a real-time data pipeline that:
- Ingests live market data from Coinbase Advanced Trade WebSocket API
- Streams ticker data to Kafka for distributed processing
- Processes data into volatility features in real-time
- Trains and deploys ML models to predict volatility spikes 60 seconds ahead
- Monitors data quality and model drift using Evidently

### Target Users
- Algorithmic traders seeking volatility-based trading signals
- Risk management systems requiring early volatility warnings
- Quantitative researchers studying market microstructure
- Portfolio managers monitoring exposure to volatile assets

---

## 2. Prediction Goal

### Objective
**Predict short-term volatility spikes 60 seconds in advance**

### Definition of Volatility Spike
A volatility spike is defined as:
- A price movement exceeding **2 standard deviations** from the rolling 60-second mean
- OR a price change rate (returns) exceeding **3% within 60 seconds**

### Prediction Window
- **Lookback window:** 5 minutes of historical tick data
- **Prediction horizon:** 60 seconds ahead
- **Update frequency:** Real-time (every new tick, ~1-5 seconds per product)

### Input Features (Planned)
- Price returns (1s, 5s, 30s, 60s windows)
- Volume metrics (volume_24h, recent volume)
- Bid-ask spread
- Trade frequency
- Rolling volatility (standard deviation of returns)
- Technical indicators (RSI, moving averages)

---

## 3. Success Metrics

### Primary Metrics
1. **Precision:** ≥ 70% of predicted spikes should actually occur
2. **Recall:** ≥ 60% of actual spikes should be detected
3. **Latency:** End-to-end prediction latency < 2 seconds from tick arrival
4. **Coverage:** System handles at least 2 trading pairs (BTC-USD, ETH-USD) simultaneously

### Secondary Metrics
1. **False Positive Rate:** < 30% (to avoid alert fatigue)
2. **Data Quality:** < 1% message loss, < 0.5% invalid messages
3. **System Uptime:** ≥ 99% during trading hours
4. **Model Drift Detection:** Evidently reports generated within 5 minutes of deployment

### Evaluation Approach
- **Training:** Use historical data from past 30 days
- **Validation:** Hold-out set from past 7 days
- **Testing:** Real-time evaluation on live stream
- **Baseline:** Simple moving average + threshold approach

---

## 4. Risk Assumptions

### Technical Risks

1. **WebSocket Connection Stability**
   - **Risk:** Coinbase API may disconnect or throttle connections
   - **Mitigation:** Implement robust reconnection logic with exponential backoff, heartbeat monitoring
   - **Assumption:** API maintains > 99% uptime, reconnection succeeds within 30 seconds

2. **Kafka Performance**
   - **Risk:** Kafka may become a bottleneck under high message volume
   - **Mitigation:** Proper partitioning, batch processing, consumer groups
   - **Assumption:** Single Kafka broker handles 1000+ messages/second per product

3. **Data Quality Issues**
   - **Risk:** Missing ticks, duplicate messages, malformed data
   - **Mitigation:** Validation at ingestion, deduplication, data quality monitoring with Evidently
   - **Assumption:** Coinbase API provides > 99% valid messages

4. **Model Performance in Production**
   - **Risk:** Model may degrade due to concept drift (market regime changes)
   - **Mitigation:** Continuous monitoring with Evidently, periodic retraining
   - **Assumption:** Model retraining required monthly or when drift detected

### Business/Operational Risks

1. **Market Regime Changes**
   - **Risk:** Model trained in one market condition may fail in another (bull vs bear market)
   - **Mitigation:** Include regime indicators, ensemble models, adaptive thresholds
   - **Assumption:** Model generalizes across normal market conditions

2. **Latency Requirements**
   - **Risk:** Pipeline latency may exceed 2-second target
   - **Mitigation:** Optimize feature computation, use async processing, monitor latency
   - **Assumption:** Network and processing infrastructure can meet latency targets

3. **Scalability**
   - **Risk:** System may not scale beyond 2-3 trading pairs
   - **Mitigation:** Horizontal scaling of Kafka consumers, distributed feature computation
   - **Assumption:** Initial scope limited to 2 products (BTC-USD, ETH-USD)

### Data Risks

1. **API Rate Limits**
   - **Risk:** Coinbase may rate limit or restrict access
   - **Mitigation:** Use public WebSocket (no auth required), monitor for throttling
   - **Assumption:** Public WebSocket API has sufficient capacity

2. **Data Completeness**
   - **Risk:** Missing data during reconnections or outages
   - **Mitigation:** Buffer recent data, gap detection, backfill strategies
   - **Assumption:** Brief gaps (< 1 minute) are acceptable for 60-second predictions

---

## 5. Architecture Overview

### Components (Milestone 1)
1. **WebSocket Ingestor:** Connects to Coinbase, publishes to Kafka
2. **Kafka Broker:** Message queue for tick data
3. **Kafka Consumer (Validation):** Validates stream integrity
4. **MLflow:** Experiment tracking and model registry
5. **Data Storage:** NDJSON files for raw data backup

### Future Components (Milestones 2-3)
- Feature engineering pipeline
- Model training and serving
- Evidently monitoring dashboard
- Alerting system

---

## 6. Timeline & Milestones

- **Milestone 1 (Week 1):** Streaming setup, data ingestion, scoping ✓
- **Milestone 2 (Week 2):** Feature engineering, model training, MLflow integration
- **Milestone 3 (Week 3):** Evidently monitoring, production deployment, documentation

---

## 7. Constraints & Limitations

- **Data:** Public market data only (no authenticated endpoints)
- **Trading:** No actual trades will be placed (research/analysis only)
- **Scope:** Initial focus on BTC-USD and ETH-USD
- **Infrastructure:** Local development with Docker Compose (not production-grade)
- **Secrets:** All secrets managed via environment variables, never committed

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Status:** Draft - Milestone 1

