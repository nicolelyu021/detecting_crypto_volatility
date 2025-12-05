# Week 6 - Prometheus Metrics Setup ✅

## What Was Done

This document summarizes the **Prometheus metrics implementation** for Week 6.

---

## ✅ Completed Tasks

### 1. Added API Metrics (app.py)

**New metrics added to FastAPI:**

- ✅ `volatility_api_requests_total` - Tracks all API requests (by method, endpoint, status)
- ✅ `volatility_api_errors_total` - Tracks errors (by endpoint and error type)
- ✅ `volatility_api_health_status` - Tracks API health (1=healthy, 0=unhealthy)
- ✅ Updated `/health` endpoint to track requests and update health gauge
- ✅ Updated `/predict` endpoint to track requests and errors
- ✅ Updated `/version` endpoint to track requests

**Existing metrics (already working):**
- ✅ `volatility_predictions_total` - Total predictions made
- ✅ `volatility_prediction_latency_seconds` - Prediction latency histogram
- ✅ `volatility_prediction_probability` - Prediction probability distribution
- ✅ `model_load_time_seconds` - Model loading time

---

### 2. Added Consumer Metrics (prediction_consumer.py)

**New metrics added to Kafka Consumer:**

- ✅ `volatility_consumer_messages_processed_total` - Messages processed counter
- ✅ `volatility_consumer_predictions_made_total` - Predictions made counter
- ✅ `volatility_consumer_errors_total` - Consumer errors counter (by error type)
- ✅ `volatility_consumer_processing_seconds` - Processing time histogram
- ✅ `volatility_consumer_lag_seconds` - **Consumer lag gauge** (time behind real-time)
- ✅ `volatility_consumer_processing_rate` - Current processing rate (msg/sec)

**Changes made:**
- ✅ Started Prometheus HTTP server on port 8001
- ✅ Updated message processing to track metrics
- ✅ Calculate consumer lag from message timestamp

---

### 3. Updated Configuration Files

**prometheus.yml:**
- ✅ Added consumer scrape target: `prediction-consumer:8001`
- ✅ API scrape target already configured: `api:8000`
- ✅ Scrape interval: 15 seconds

**docker/compose.yaml:**
- ✅ Exposed consumer metrics port: `8001:8001`
- ✅ Added `METRICS_PORT` environment variable
- ✅ Prometheus and Grafana already configured (from Week 5)

**requirements-consumer.txt:**
- ✅ Added `prometheus-client>=0.19.0`

---

### 4. Documentation Created

- ✅ `docs/prometheus_metrics_guide.md` - Comprehensive metrics guide
- ✅ `scripts/test_prometheus_metrics.sh` - Testing script
- ✅ This summary document

---

## 🚀 How to Test

### Step 1: Start Services

```bash
cd crypto-volatility/docker
docker compose up -d
```

Wait 30 seconds for all services to start.

---

### Step 2: Run Test Script

```bash
cd crypto-volatility
./scripts/test_prometheus_metrics.sh
```

This will:
- Check if services are running
- Test API metrics endpoint
- Make a test prediction
- Verify metrics are updating
- Check Prometheus targets

---

### Step 3: View Metrics

**Raw Metrics:**
```bash
# API metrics
curl http://localhost:8000/metrics

# Consumer metrics
curl http://localhost:8001/metrics
```

**Prometheus UI:**
- Open: http://localhost:9090
- Go to Status → Targets (should show both API and consumer as "UP")
- Try queries:
  ```promql
  rate(volatility_api_requests_total[1m])
  histogram_quantile(0.95, volatility_prediction_latency_seconds_bucket)
  volatility_consumer_lag_seconds
  ```

**Grafana:**
- Open: http://localhost:3000
- Login: `admin` / `admin`
- Add Prometheus data source: `http://prometheus:9090`
- Create dashboards (next step!)

---

## 📊 Key Metrics for Week 6 Requirements

### 1. **Latency (p50/p95)**
```promql
# p50 latency
histogram_quantile(0.50, rate(volatility_prediction_latency_seconds_bucket[5m]))

# p95 latency (should be ≤ 800ms)
histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m]))
```

### 2. **Error Rate**
```promql
# Error rate (errors per second)
rate(volatility_api_errors_total[5m])

# Error percentage
rate(volatility_api_errors_total[5m]) / rate(volatility_api_requests_total[5m]) * 100
```

### 3. **Request Count**
```promql
# Requests per second
rate(volatility_api_requests_total[1m])

# Total requests
sum(volatility_api_requests_total)
```

### 4. **Consumer Lag**
```promql
# Current lag (should be < 30-60 seconds)
volatility_consumer_lag_seconds

# Processing rate
volatility_consumer_processing_rate
```

### 5. **Freshness**
```promql
# Time since last prediction (should be recent)
time() - timestamp(volatility_predictions_total)
```

---

## 📝 Next Steps for Week 6

✅ **Done:** Prometheus metrics collecting data  

⬜ **TODO:** Create Grafana dashboards showing:
   - p50/p95 latency graphs
   - Error rate over time
   - Request volume
   - Consumer lag

⬜ **TODO:** Define SLOs in `docs/slo.md`:
   - p95 latency ≤ 800ms
   - Error rate < 1%
   - Uptime > 99%
   - Consumer lag < 60s

⬜ **TODO:** Create runbook in `docs/runbook.md`:
   - How to start/stop services
   - Troubleshooting common issues
   - Recovery procedures

⬜ **TODO:** Evidently drift detection:
   - Schedule drift reports
   - Write `docs/drift_summary.md`

⬜ **TODO:** Model rollback feature:
   - Add `MODEL_VARIANT=baseline` option
   - Test switching between models

---

## 🔍 Troubleshooting

### Metrics endpoint returns 404
- Check service is running: `docker ps`
- Check logs: `docker logs volatility-api`

### Prometheus not scraping targets
1. Open http://localhost:9090/targets
2. Check if targets are "UP"
3. If "DOWN", check:
   - Services are running
   - Ports are exposed in docker-compose.yaml
   - prometheus.yml has correct target names

### Consumer metrics not showing
1. Check consumer is running: `docker ps | grep consumer`
2. Check port 8001 is exposed: `docker compose ps`
3. Try: `curl http://localhost:8001/metrics`
4. Check consumer logs: `docker logs volatility-prediction-consumer`

---

## 📚 Files Modified

### Modified Files:
- `crypto-volatility/api/app.py` - Added new metrics
- `crypto-volatility/scripts/prediction_consumer.py` - Added consumer metrics
- `crypto-volatility/docker/prometheus.yml` - Added consumer target
- `crypto-volatility/docker/compose.yaml` - Exposed consumer port
- `crypto-volatility/requirements-consumer.txt` - Added prometheus-client

### New Files:
- `crypto-volatility/docs/prometheus_metrics_guide.md` - Metrics documentation
- `crypto-volatility/scripts/test_prometheus_metrics.sh` - Test script
- `crypto-volatility/WEEK6_PROMETHEUS_SUMMARY.md` - This summary

---

## 🎯 Week 6 Grading Alignment

**Monitoring & Drift (30 points):**

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Prometheus metrics integrated | ✅ Done | All metrics implemented and exposed |
| Metrics: latency, request count, errors, consumer lag | ✅ Done | All required metrics present |
| Grafana dashboards (p50/p95 latency, error rate, freshness) | ⬜ TODO | Next step - create visual dashboards |
| SLOs defined (p95 ≤ 800ms) | ⬜ TODO | Next step - write docs/slo.md |
| Evidently drift detection | ⬜ TODO | Next step - run drift reports |
| Runbook | ⬜ TODO | Next step - write docs/runbook.md |
| Rollback toggle (MODEL_VARIANT) | ⬜ TODO | Next step - add baseline switch |

---

## 💡 Tips

1. **Test metrics regularly:** Run the test script after any changes
2. **Monitor Prometheus targets:** Keep http://localhost:9090/targets open
3. **Check logs:** Use `docker logs <container>` to debug issues
4. **Grafana templates:** Look for Prometheus dashboard templates to import
5. **SLO alignment:** Base your SLOs on the actual metrics you're collecting

---

## ✅ Summary

**What you have now:**
- ✅ Comprehensive Prometheus metrics for API and Consumer
- ✅ Latency tracking (histograms with percentiles)
- ✅ Error tracking (counters with labels)
- ✅ Consumer lag tracking (gauges)
- ✅ Request counting (all endpoints)
- ✅ Health monitoring (API status)
- ✅ Prometheus scraping both services
- ✅ Test script to verify everything works
- ✅ Documentation guide

**You're 40% done with Week 6!** 🎉

The hardest part (setting up metrics collection) is complete. Next steps are about:
- **Visualization** (Grafana dashboards)
- **Documentation** (SLOs, runbook)
- **Quality** (drift detection, rollback)

