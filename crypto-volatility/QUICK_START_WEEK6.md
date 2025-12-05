# Week 6 Quick Start Guide

## 🚀 One-Command Startup

```bash
cd crypto-volatility/docker
docker compose up -d
```

Wait 30 seconds, then access:

---

## 🌐 Service URLs

| Service | URL | What It Does |
|---------|-----|--------------|
| **API** | http://localhost:8000 | Main prediction API |
| **API Metrics** | http://localhost:8000/metrics | API Prometheus metrics |
| **Consumer Metrics** | http://localhost:8001/metrics | Consumer Prometheus metrics |
| **Prometheus** | http://localhost:9090 | Metrics database & query UI |
| **Grafana** | http://localhost:3000 | Dashboards (admin/admin) |
| **MLflow** | http://localhost:5001 | Model tracking |
| **Kafka** | localhost:9092 | Message queue |

---

## 🧪 Quick Test

```bash
# Test the API
curl http://localhost:8000/health

# Make a prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"price": 50000.0}'

# View metrics
curl http://localhost:8000/metrics | grep volatility

# Run full test suite
cd crypto-volatility
./scripts/test_prometheus_metrics.sh
```

---

## 📊 Week 6 Checklist

### Task 1: Prometheus Metrics ✅ DONE
- ✅ Latency tracking
- ✅ Request counting
- ✅ Error tracking
- ✅ Consumer lag monitoring

**How to verify:**
```bash
# Check Prometheus targets are UP
open http://localhost:9090/targets

# Query latency
# In Prometheus UI, run:
histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m]))
```

---

### Task 2: Grafana Dashboards ⬜ TODO
Create dashboards showing:
- p50/p95 latency
- Error rate
- Request volume
- Consumer lag

**Steps:**
1. Open http://localhost:3000 (admin/admin)
2. Add Prometheus data source: `http://prometheus:9090`
3. Create → Dashboard → Add Panel
4. Use queries from `docs/prometheus_metrics_guide.md`

---

### Task 3: SLOs Document ⬜ TODO
Create `docs/slo.md` with:
- p95 latency ≤ 800ms (aspirational)
- Error rate < 1%
- Uptime > 99%
- Consumer lag < 60 seconds

**Template:**
```markdown
# Service Level Objectives (SLOs)

## Latency SLO
- **Target:** 95th percentile latency ≤ 800ms
- **Metric:** histogram_quantile(0.95, volatility_prediction_latency_seconds_bucket)
- **Current:** [Check Grafana]
```

---

### Task 4: Evidently Drift Report ⬜ TODO
Generate drift report and write summary.

**Commands:**
```bash
cd crypto-volatility
python scripts/generate_evidently_report.py
```

Create `docs/drift_summary.md` summarizing findings.

---

### Task 5: Runbook ⬜ TODO
Create `docs/runbook.md` with:
- Startup procedure
- Shutdown procedure
- Common issues & fixes
- Recovery procedures

---

### Task 6: Model Rollback ⬜ TODO
Add ability to switch models via environment variable.

**Test:**
```bash
# Use ML model (default)
docker compose up -d

# Use baseline model
MODEL_VARIANT=baseline docker compose up -d
```

---

## 📈 Key Prometheus Queries

Copy these into Prometheus (http://localhost:9090) or Grafana:

### Latency
```promql
# p50 latency
histogram_quantile(0.50, rate(volatility_prediction_latency_seconds_bucket[5m]))

# p95 latency
histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m]))

# p99 latency
histogram_quantile(0.99, rate(volatility_prediction_latency_seconds_bucket[5m]))
```

### Request Rate
```promql
# Requests per second
rate(volatility_api_requests_total[1m])

# Requests by endpoint
sum by (endpoint) (rate(volatility_api_requests_total[5m]))
```

### Error Rate
```promql
# Errors per second
rate(volatility_api_errors_total[5m])

# Error percentage
rate(volatility_api_errors_total[5m]) / rate(volatility_api_requests_total[5m]) * 100
```

### Consumer Health
```promql
# Consumer lag (seconds)
volatility_consumer_lag_seconds

# Processing rate (messages/sec)
volatility_consumer_processing_rate

# Messages processed
rate(volatility_consumer_messages_processed_total[1m])
```

---

## 🛠️ Troubleshooting

### Services won't start
```bash
# Check logs
docker compose logs api
docker compose logs prometheus
docker compose logs prediction-consumer

# Restart everything
docker compose down
docker compose up -d
```

### Metrics not showing up
```bash
# Check if endpoints are accessible
curl http://localhost:8000/metrics
curl http://localhost:8001/metrics

# Check Prometheus targets
open http://localhost:9090/targets
# Both should show "UP"
```

### Grafana can't connect to Prometheus
- In Grafana data source settings, use: `http://prometheus:9090` (not localhost)
- Use "Server" access mode (not "Browser")

---

## 📚 Documentation

- **Full Metrics Guide:** `docs/prometheus_metrics_guide.md`
- **Setup Summary:** `WEEK6_PROMETHEUS_SUMMARY.md`
- **Test Script:** `scripts/test_prometheus_metrics.sh`
- **Monitoring Guide:** `docs/monitoring_guide.md`

---

## 🎯 Week 6 Deliverables

| Deliverable | File/Location | Status |
|-------------|--------------|--------|
| Prometheus metrics | Implemented in code | ✅ Done |
| Grafana dashboard | JSON + screenshot | ⬜ TODO |
| Evidently report | HTML + summary | ⬜ TODO |
| SLO document | `docs/slo.md` | ⬜ TODO |
| Runbook | `docs/runbook.md` | ⬜ TODO |
| Model rollback | Environment variable | ⬜ TODO |

---

## 💡 Pro Tips

1. **Keep Prometheus UI open** while testing to see metrics update in real-time
2. **Use Grafana templates** - search for "FastAPI Prometheus" dashboard templates to import
3. **Test with load** - Use `scripts/load_test.py` to generate traffic and see metrics populate
4. **Document everything** - Take screenshots of your dashboards for the submission
5. **Check consumer metrics** - Make sure Kafka consumer is actually processing messages

---

## ⏱️ Estimated Time Remaining

- Grafana dashboards: 2-3 hours
- SLO document: 30 minutes
- Evidently drift report: 1 hour
- Runbook: 1 hour
- Model rollback: 1 hour
- **Total: ~6 hours**

You've already completed the hardest part (Prometheus setup)! 🎉

