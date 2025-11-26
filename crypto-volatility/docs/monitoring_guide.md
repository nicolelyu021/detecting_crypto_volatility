# Monitoring Guide: Prometheus Metrics

This guide explains how to monitor the Crypto Volatility Detection API using Prometheus and Grafana.

## Available Metrics

The API exposes the following Prometheus metrics at `http://localhost:8000/metrics`:

### Custom Metrics

1. **`volatility_predictions_total`** (Counter)
   - Total number of predictions made
   - Labels: `prediction` (0 or 1)
   - Example: `volatility_predictions_total{prediction="0"} 150`

2. **`volatility_prediction_latency_seconds`** (Histogram)
   - Prediction latency in seconds
   - Buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
   - Provides: `_count`, `_sum`, `_bucket` metrics

3. **`volatility_prediction_probability`** (Histogram)
   - Distribution of prediction probabilities
   - Buckets: [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

4. **`model_load_time_seconds`** (Gauge)
   - Time taken to load the model on startup

### Standard Python Metrics

- `python_gc_*` - Garbage collection metrics
- `process_*` - Process memory and CPU metrics

## Monitoring Setup

### Option 1: View Raw Metrics (Quick Check)

View metrics directly from the API:

```bash
# View all metrics
curl http://localhost:8000/metrics

# View only custom metrics
curl http://localhost:8000/metrics | grep volatility_

# View specific metric
curl http://localhost:8000/metrics | grep volatility_predictions_total
```

### Option 2: Prometheus + Grafana (Full Monitoring)

#### 1. Start Services

```bash
cd crypto-volatility
docker-compose -f docker/compose.yaml up -d
```

This starts:
- **Prometheus** on `http://localhost:9090`
- **Grafana** on `http://localhost:3000`
- **API** on `http://localhost:8000`

#### 2. Access Prometheus UI

1. Open `http://localhost:9090` in your browser
2. Go to **Status → Targets** to verify the API is being scraped
3. Go to **Graph** to query metrics

**Example Queries:**
```
# Total predictions
volatility_predictions_total

# Predictions by class
volatility_predictions_total{prediction="1"}  # Spikes predicted
volatility_predictions_total{prediction="0"}  # Normal predicted

# Prediction rate (per second)
rate(volatility_predictions_total[5m])

# Average latency
rate(volatility_prediction_latency_seconds_sum[5m]) / rate(volatility_prediction_latency_seconds_count[5m])

# P95 latency
histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m]))

# Average prediction probability
rate(volatility_prediction_probability_sum[5m]) / rate(volatility_prediction_probability_count[5m])
```

#### 3. Access Grafana UI

1. Open `http://localhost:3000` in your browser
2. Login with:
   - Username: `admin`
   - Password: `admin`
3. Add Prometheus as a data source:
   - Go to **Configuration → Data Sources**
   - Click **Add data source**
   - Select **Prometheus**
   - URL: `http://prometheus:9090`
   - Click **Save & Test**

#### 4. Create Dashboards

**Quick Dashboard Setup:**

1. Go to **Dashboards → New Dashboard**
2. Add panels for:
   - **Prediction Rate**: `rate(volatility_predictions_total[5m])`
   - **Spike Predictions**: `volatility_predictions_total{prediction="1"}`
   - **Average Latency**: `rate(volatility_prediction_latency_seconds_sum[5m]) / rate(volatility_prediction_latency_seconds_count[5m])`
   - **P95 Latency**: `histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m]))`
   - **Probability Distribution**: `rate(volatility_prediction_probability_bucket[5m])`

**Example Grafana Queries:**

```promql
# Prediction throughput (predictions per second)
sum(rate(volatility_predictions_total[1m]))

# Spike prediction rate
sum(rate(volatility_predictions_total{prediction="1"}[1m]))

# Average prediction latency
sum(rate(volatility_prediction_latency_seconds_sum[1m])) / sum(rate(volatility_prediction_latency_seconds_count[1m]))

# 95th percentile latency
histogram_quantile(0.95, sum(rate(volatility_prediction_latency_seconds_bucket[1m])) by (le))

# Probability distribution
histogram_quantile(0.5, sum(rate(volatility_prediction_probability_bucket[1m])) by (le))
```

## Monitoring Best Practices

### Key Metrics to Watch

1. **Prediction Rate**: Monitor request throughput
2. **Latency (P95)**: Ensure predictions are fast (< 100ms)
3. **Spike Detection Rate**: Track how often spikes are predicted
4. **Probability Distribution**: Monitor if probabilities are reasonable

### Alerts (Optional)

You can set up alerts in Grafana for:
- High latency (> 200ms)
- Low prediction rate (API might be down)
- High spike prediction rate (unusual activity)

## Troubleshooting

### Prometheus not scraping

1. Check Prometheus targets: `http://localhost:9090/targets`
2. Verify API is running: `curl http://localhost:8000/health`
3. Check Prometheus logs: `docker logs prometheus`

### Grafana can't connect to Prometheus

1. Verify Prometheus is running: `docker ps | grep prometheus`
2. Check network: Both should be on `kafka-network`
3. Use internal hostname: `http://prometheus:9090` (not `localhost`)

### No metrics appearing

1. Make some predictions: `curl -X POST http://localhost:8000/predict ...`
2. Wait 15 seconds (scrape interval)
3. Refresh Prometheus/Grafana

## Quick Reference

| Service | URL | Purpose |
|---------|-----|---------|
| API Metrics | `http://localhost:8000/metrics` | Raw Prometheus metrics |
| Prometheus | `http://localhost:9090` | Metrics database & query UI |
| Grafana | `http://localhost:3000` | Visualization & dashboards |
| API Health | `http://localhost:8000/health` | Health check |

---

**Default Credentials:**
- Grafana: `admin` / `admin` (change on first login)

