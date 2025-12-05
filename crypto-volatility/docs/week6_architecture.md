# Week 6 Monitoring Architecture

## System Architecture with Metrics

```
┌─────────────────────────────────────────────────────────────────┐
│                     MONITORING LAYER (Week 6)                   │
│                                                                 │
│  ┌─────────────────┐         ┌──────────────────┐             │
│  │   Prometheus    │◄────────│   Grafana        │             │
│  │   :9090         │         │   :3000          │             │
│  │                 │         │   (Dashboards)   │             │
│  └────────┬────────┘         └──────────────────┘             │
│           │                                                     │
│           │ scrapes metrics every 15s                          │
│           │                                                     │
│  ┌────────▼────────────────────────────────────────┐          │
│  │                                                   │          │
│  │  /metrics endpoints                             │          │
│  │                                                   │          │
└──┴───────────────────────────────────────────────────┴──────────┘
           │                                    │
           │                                    │
  ┌────────▼─────────┐              ┌──────────▼──────────┐
  │   FastAPI        │              │   Consumer          │
  │   :8000          │              │   :8001             │
  │                  │              │                     │
  │  Metrics:        │              │  Metrics:           │
  │  - Latency       │              │  - Consumer lag     │
  │  - Requests      │              │  - Processing rate  │
  │  - Errors        │              │  - Messages count   │
  │  - Health        │              │  - Errors           │
  └──────────────────┘              └─────────────────────┘
```

---

## Metrics Flow

### 1. **API Metrics (Port 8000)**

```
User Request → FastAPI
                 │
                 ├─> Record request counter
                 ├─> Start timer
                 ├─> Make prediction
                 ├─> Stop timer (record latency)
                 ├─> Record probability
                 ├─> Record prediction (0 or 1)
                 └─> Return response
                 
Every 15 seconds → Prometheus scrapes /metrics
```

**Metrics collected:**
- `volatility_api_requests_total{method, endpoint, status}`
- `volatility_api_errors_total{endpoint, error_type}`
- `volatility_prediction_latency_seconds` (histogram)
- `volatility_predictions_total{prediction}`
- `volatility_api_health_status` (1 or 0)

---

### 2. **Consumer Metrics (Port 8001)**

```
Kafka Message → Consumer
                  │
                  ├─> Record message received
                  ├─> Calculate lag (msg time - now)
                  ├─> Start timer
                  ├─> Process features
                  ├─> Make prediction
                  ├─> Stop timer (record processing time)
                  ├─> Publish to Kafka
                  └─> Update processing rate
                  
Every 15 seconds → Prometheus scrapes /metrics
```

**Metrics collected:**
- `volatility_consumer_messages_processed_total`
- `volatility_consumer_predictions_made_total`
- `volatility_consumer_lag_seconds` (gauge)
- `volatility_consumer_processing_seconds` (histogram)
- `volatility_consumer_processing_rate` (gauge)
- `volatility_consumer_errors_total{error_type}`

---

## Data Flow

```
┌──────────────┐
│   Kafka      │
│   :9092      │
└──────┬───────┘
       │
       │ ticks.features
       │
       ▼
┌──────────────────────┐
│  Consumer            │
│  (prediction_        │
│   consumer.py)       │
│                      │
│  Metrics: :8001      │ ◄──── Prometheus scrapes
└──────┬───────────────┘
       │
       │ predictions
       │
       ▼
┌──────────────────────┐
│  Kafka               │
│  ticks.predictions   │
└──────────────────────┘

                    ┌──────────────────────┐
User Request ──────►│  FastAPI             │
                    │  (app.py)            │
                    │                      │
                    │  Metrics: :8000      │ ◄──── Prometheus scrapes
                    └──────┬───────────────┘
                           │
                           ▼
                    [ Prediction Result ]
```

---

## Prometheus Queries for Week 6

### For Grafana Dashboards

#### Panel 1: P95 Latency (should be ≤ 800ms)
```promql
histogram_quantile(0.95, 
  rate(volatility_prediction_latency_seconds_bucket[5m])
) * 1000
```
Unit: milliseconds  
Threshold line: 800ms (red)

---

#### Panel 2: P50 Latency (median)
```promql
histogram_quantile(0.50, 
  rate(volatility_prediction_latency_seconds_bucket[5m])
) * 1000
```
Unit: milliseconds

---

#### Panel 3: Request Rate (requests per second)
```promql
sum(rate(volatility_api_requests_total[1m]))
```
Unit: req/s

---

#### Panel 4: Error Rate (errors per second)
```promql
sum(rate(volatility_api_errors_total[5m]))
```
Unit: errors/s

---

#### Panel 5: Error Percentage
```promql
(sum(rate(volatility_api_errors_total[5m])) / 
 sum(rate(volatility_api_requests_total[5m]))) * 100
```
Unit: %  
Threshold: < 1%

---

#### Panel 6: Consumer Lag (freshness)
```promql
volatility_consumer_lag_seconds
```
Unit: seconds  
Threshold: < 60s (yellow), < 30s (green)

---

#### Panel 7: Processing Rate
```promql
volatility_consumer_processing_rate
```
Unit: messages/second

---

#### Panel 8: Predictions Distribution
```promql
# Spike predictions
sum(volatility_predictions_total{prediction="1"})

# Normal predictions
sum(volatility_predictions_total{prediction="0"})
```
Chart type: Pie chart

---

#### Panel 9: API Health
```promql
volatility_api_health_status
```
Value: 1 (healthy) or 0 (unhealthy)  
Alert if < 1

---

## SLO Definitions (for docs/slo.md)

### 1. Latency SLO
- **Objective:** 95% of predictions complete in ≤ 800ms
- **Metric:** `histogram_quantile(0.95, volatility_prediction_latency_seconds_bucket) <= 0.8`
- **Measurement:** Measured over 5-minute rolling windows
- **Alert:** If p95 > 800ms for 5 consecutive minutes

### 2. Error Rate SLO
- **Objective:** Error rate < 1%
- **Metric:** `rate(volatility_api_errors_total[5m]) / rate(volatility_api_requests_total[5m]) < 0.01`
- **Measurement:** Measured over 5-minute rolling windows
- **Alert:** If error rate > 1% for 5 consecutive minutes

### 3. Availability SLO
- **Objective:** API uptime > 99.9%
- **Metric:** `avg_over_time(volatility_api_health_status[24h]) > 0.999`
- **Measurement:** Measured over 24-hour rolling windows
- **Alert:** If health drops to 0

### 4. Freshness SLO (Consumer Lag)
- **Objective:** Consumer lag < 30 seconds
- **Metric:** `volatility_consumer_lag_seconds < 30`
- **Measurement:** Current value
- **Alert:** If lag > 60 seconds

---

## Alerting Rules (Future Enhancement)

```yaml
# Example alert for high latency
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m])) > 0.8
  for: 5m
  annotations:
    summary: "P95 latency exceeds 800ms"
    
- alert: HighErrorRate
  expr: rate(volatility_api_errors_total[5m]) / rate(volatility_api_requests_total[5m]) > 0.01
  for: 5m
  annotations:
    summary: "Error rate exceeds 1%"
    
- alert: ConsumerLagging
  expr: volatility_consumer_lag_seconds > 60
  for: 2m
  annotations:
    summary: "Consumer is lagging behind by more than 60 seconds"
```

---

## Week 6 Monitoring Checklist

### ✅ Infrastructure
- [x] Prometheus running (:9090)
- [x] Grafana running (:3000)
- [x] API exposing metrics (:8000/metrics)
- [x] Consumer exposing metrics (:8001/metrics)
- [x] Prometheus scraping both services

### ⬜ Dashboards (TODO)
- [ ] Create Grafana dashboard with 9 panels
- [ ] Add threshold lines (800ms, 1% error rate)
- [ ] Export dashboard JSON
- [ ] Take screenshot for submission

### ⬜ Documentation (TODO)
- [ ] Write docs/slo.md with 4 SLOs
- [ ] Write docs/runbook.md with procedures
- [ ] Generate Evidently drift report
- [ ] Write docs/drift_summary.md

### ⬜ Features (TODO)
- [ ] Add MODEL_VARIANT rollback toggle
- [ ] Test switching between ML and baseline models
- [ ] Verify metrics during rollback

---

## Testing Procedure

### 1. Verify Metrics Collection
```bash
# Check API metrics
curl http://localhost:8000/metrics | grep volatility

# Check consumer metrics
curl http://localhost:8001/metrics | grep volatility
```

### 2. Generate Load
```bash
# Run load test to populate metrics
cd crypto-volatility
python scripts/load_test.py
```

### 3. Verify Prometheus
```bash
# Open Prometheus and check targets are UP
open http://localhost:9090/targets

# Run test queries
open http://localhost:9090/graph
```

### 4. Create Grafana Dashboard
```bash
# Open Grafana
open http://localhost:3000

# Login: admin/admin
# Add data source: http://prometheus:9090
# Create dashboard with panels
```

---

## Success Criteria

✅ **Week 6 is complete when:**

1. Prometheus successfully scrapes metrics from both API and Consumer
2. Grafana dashboard displays:
   - P50 and P95 latency graphs
   - Error rate graph
   - Request volume graph
   - Consumer lag graph
3. SLO document defines clear objectives with metrics
4. Runbook documents startup, troubleshooting, and recovery
5. Evidently drift report generated with summary
6. Model rollback feature works (can switch via env var)

---

## Port Reference

| Port | Service | Purpose |
|------|---------|---------|
| 8000 | FastAPI | API + metrics endpoint |
| 8001 | Consumer | Consumer metrics endpoint |
| 9090 | Prometheus | Metrics database & query UI |
| 3000 | Grafana | Dashboard UI |
| 5001 | MLflow | Model registry |
| 9092 | Kafka | Message queue |

All services accessible via `localhost` when running Docker Compose.

