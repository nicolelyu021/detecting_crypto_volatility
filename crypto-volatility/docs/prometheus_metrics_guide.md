# Prometheus Metrics Guide (Week 6)

This guide explains all the Prometheus metrics we collect for monitoring our AI service.

## 📊 What Are Metrics?

**Metrics** are numbers that tell you how your system is performing. Think of it like your car's dashboard - it shows speed, fuel, temperature, etc.

---

## 🎯 API Metrics (Port 8000)

These metrics track your FastAPI service (the main API that serves predictions).

### Request Tracking

**Metric:** `volatility_api_requests_total`  
**What it measures:** Total number of requests to each endpoint  
**Labels:**
- `method`: GET or POST
- `endpoint`: /health, /predict, /version
- `status`: HTTP status code (200, 500, 503)

**Example use:** Count how many prediction requests you're getting per minute

---

**Metric:** `volatility_api_errors_total`  
**What it measures:** Total number of errors  
**Labels:**
- `endpoint`: Which endpoint failed
- `error_type`: Type of error (model_not_loaded, prediction_error)

**Example use:** Track your error rate (should be < 1%)

---

### Prediction Quality

**Metric:** `volatility_predictions_total`  
**What it measures:** Total predictions made  
**Labels:**
- `prediction`: 0 (normal) or 1 (spike)

**Example use:** See how many spikes vs normal predictions

---

**Metric:** `volatility_prediction_latency_seconds`  
**What it measures:** How long each prediction takes  
**Type:** Histogram (gives you p50, p95, p99)

**Example use:** Check if 95% of predictions are under 800ms (p95 < 0.8)

---

**Metric:** `volatility_prediction_probability`  
**What it measures:** Distribution of prediction probabilities  
**Type:** Histogram

**Example use:** See if model is confident (probabilities near 0 or 1)

---

### System Health

**Metric:** `volatility_api_health_status`  
**What it measures:** Is the API healthy?  
**Values:**
- `1` = Healthy (model loaded)
- `0` = Unhealthy (model not loaded)

**Example use:** Alert if this drops to 0

---

**Metric:** `model_load_time_seconds`  
**What it measures:** How long it took to load the model at startup  
**Type:** Gauge

**Example use:** Track if model loading is getting slower

---

## 🔄 Consumer Metrics (Port 8001)

These metrics track your Kafka consumer (the service that processes streaming data).

### Processing Stats

**Metric:** `volatility_consumer_messages_processed_total`  
**What it measures:** Total messages consumed from Kafka  
**Type:** Counter

**Example use:** Calculate messages per second

---

**Metric:** `volatility_consumer_predictions_made_total`  
**What it measures:** Total predictions made by consumer  
**Type:** Counter

**Example use:** Should match messages_processed (if not, something's wrong)

---

**Metric:** `volatility_consumer_processing_seconds`  
**What it measures:** Time to process each message  
**Type:** Histogram (gives you p50, p95, p99)

**Example use:** Check processing latency

---

### Consumer Health

**Metric:** `volatility_consumer_lag_seconds`  
**What it measures:** **Consumer lag** - how far behind is the consumer?  
**Type:** Gauge

**What is lag?**
- Message arrives at time T
- Consumer processes it at time T+5
- Lag = 5 seconds

**Example use:** Alert if lag > 60 seconds (consumer is falling behind)

---

**Metric:** `volatility_consumer_processing_rate`  
**What it measures:** Current processing speed (messages/second)  
**Type:** Gauge

**Example use:** Track throughput over time

---

**Metric:** `volatility_consumer_errors_total`  
**What it measures:** Total errors in consumer  
**Labels:**
- `error_type`: processing_error, kafka_error

**Example use:** Alert if error rate spikes

---

## 🚀 How to Access Metrics

### 1. Raw Metrics (Text Format)

```bash
# API metrics
curl http://localhost:8000/metrics

# Consumer metrics
curl http://localhost:8001/metrics
```

### 2. Prometheus UI

Open http://localhost:9090

Try these queries:
```promql
# Request rate (requests per second)
rate(volatility_api_requests_total[1m])

# P95 latency (95th percentile)
histogram_quantile(0.95, volatility_prediction_latency_seconds_bucket)

# Error rate
rate(volatility_api_errors_total[5m])

# Consumer lag
volatility_consumer_lag_seconds
```

### 3. Grafana Dashboards (Week 6 Task)

You'll create visual dashboards in Grafana (next step!) showing:
- Latency graphs (p50, p95)
- Error rate over time
- Consumer lag
- Request volume

---

## 📝 Week 6 SLO Examples

Using these metrics, you can define **SLOs (Service Level Objectives)**:

1. **Latency SLO:** "95% of predictions complete in ≤ 800ms"
   - Metric: `histogram_quantile(0.95, volatility_prediction_latency_seconds_bucket) <= 0.8`

2. **Error Rate SLO:** "Error rate < 1%"
   - Metric: `rate(volatility_api_errors_total[5m]) / rate(volatility_api_requests_total[5m]) < 0.01`

3. **Availability SLO:** "API health is 99.9% up"
   - Metric: `volatility_api_health_status == 1`

4. **Freshness SLO:** "Consumer lag < 30 seconds"
   - Metric: `volatility_consumer_lag_seconds < 30`

---

## 🔍 Testing Your Metrics

After starting your services, verify metrics are being collected:

```bash
# Start services
cd crypto-volatility/docker
docker compose up -d

# Wait 30 seconds, then check metrics
curl http://localhost:8000/metrics | grep volatility

# Make a prediction to generate metrics
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"price": 50000.0}'

# Check again - counters should increase
curl http://localhost:8000/metrics | grep volatility_predictions_total
```

---

## 📚 Next Steps for Week 6

✅ **Done:** Prometheus metrics are now collecting data  
⬜ **Next:** Create Grafana dashboards to visualize these metrics  
⬜ **Next:** Write SLO document based on these metrics  
⬜ **Next:** Add Evidently for drift detection

---

## ❓ Common Questions

**Q: What's the difference between Counter and Gauge?**
- **Counter:** Only goes up (like odometer). Example: total_requests
- **Gauge:** Goes up and down (like speedometer). Example: current_lag

**Q: What's a Histogram?**
- Records distribution of values. Lets you calculate percentiles (p50, p95, p99)

**Q: What's consumer lag and why does it matter?**
- Lag = how far behind your consumer is from real-time
- High lag = predictions are stale/outdated
- Should be < 30-60 seconds ideally

**Q: How often does Prometheus scrape metrics?**
- Every 15 seconds (configured in prometheus.yml)

