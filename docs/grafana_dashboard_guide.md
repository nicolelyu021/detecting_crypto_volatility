# Grafana Dashboard Setup Guide

## Step-by-Step Instructions

### 1. Access Grafana
```bash
open http://localhost:3000
```
- Username: `admin`
- Password: `admin`

---

### 2. Add Prometheus Data Source

**Navigation:** ☰ Menu → Connections → Data Sources → Add data source → Prometheus

**Settings:**
- **Name:** Prometheus
- **URL:** `http://prometheus:9090` ⚠️ (Use `prometheus`, NOT `localhost`)
- **Access:** Server (not Browser)

Click **"Save & Test"** - should see ✅ "Data source is working"

---

### 3. Create Dashboard

**Navigation:** ☰ Menu → Dashboards → New → New Dashboard → Add visualization → Prometheus

---

## Dashboard Panels Configuration

### Panel 1: P95 Latency ⭐ (Most Important for SLO)

**Query:**
```promql
histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m])) * 1000
```

**Settings:**
- **Title:** P95 Latency (should be ≤ 800ms)
- **Description:** 95th percentile response time - 95% of requests faster than this
- **Unit:** milliseconds (ms)
- **Visualization:** Time series (line graph)
- **Thresholds:**
  - Base: Green
  - 500: Yellow
  - 800: Red
- **Min:** 0

**Why it matters:** Week 6 SLO requires p95 ≤ 800ms

---

### Panel 2: P50 Latency (Median)

**Query:**
```promql
histogram_quantile(0.50, rate(volatility_prediction_latency_seconds_bucket[5m])) * 1000
```

**Settings:**
- **Title:** P50 Latency (Median)
- **Description:** Median response time
- **Unit:** milliseconds (ms)
- **Visualization:** Time series

---

### Panel 3: Request Rate

**Query:**
```promql
sum(rate(volatility_api_requests_total[1m]))
```

**Settings:**
- **Title:** API Request Rate
- **Description:** Requests per second
- **Unit:** requests/sec (reqps)
- **Visualization:** Time series

---

### Panel 4: Error Rate

**Query:**
```promql
sum(rate(volatility_api_errors_total[5m]))
```

**Settings:**
- **Title:** Error Rate
- **Description:** Errors per second
- **Unit:** errors/sec
- **Visualization:** Time series
- **Thresholds:**
  - Base: Green
  - 0.1: Yellow
  - 1.0: Red

---

### Panel 5: Error Percentage ⭐ (SLO Metric)

**Query:**
```promql
(sum(rate(volatility_api_errors_total[5m])) / sum(rate(volatility_api_requests_total[5m]))) * 100
```

**Settings:**
- **Title:** Error Percentage (should be < 1%)
- **Description:** Percentage of requests that fail
- **Unit:** percent (0-100)
- **Visualization:** Stat (big number) or Time series
- **Thresholds:**
  - Base: Green
  - 0.5: Yellow
  - 1.0: Red
- **Min:** 0
- **Max:** 100

**Why it matters:** Week 6 SLO requires error rate < 1%

---

### Panel 6: Consumer Lag ⭐ (Freshness SLO)

**Query:**
```promql
volatility_consumer_lag_seconds
```

**Settings:**
- **Title:** Consumer Lag (Data Freshness)
- **Description:** How far behind consumer is from real-time
- **Unit:** seconds (s)
- **Visualization:** Gauge or Time series
- **Thresholds:**
  - Base: Green (< 30s)
  - 30: Yellow
  - 60: Red
- **Min:** 0
- **Max:** 120

**Why it matters:** Shows if your predictions are based on fresh data

---

### Panel 7: Consumer Processing Rate

**Query:**
```promql
volatility_consumer_processing_rate
```

**Settings:**
- **Title:** Consumer Throughput
- **Description:** Messages processed per second
- **Unit:** messages/sec
- **Visualization:** Time series

---

### Panel 8: Total Predictions

**Query:**
```promql
sum(volatility_predictions_total)
```

**Settings:**
- **Title:** Total Predictions
- **Description:** Cumulative prediction count
- **Unit:** none
- **Visualization:** Stat (big number)

---

### Panel 9: API Health Status

**Query:**
```promql
volatility_api_health_status
```

**Settings:**
- **Title:** API Health
- **Description:** 1 = Healthy, 0 = Unhealthy
- **Unit:** none
- **Visualization:** Stat
- **Thresholds:**
  - 0: Red (Unhealthy)
  - 1: Green (Healthy)
- **Value mappings:**
  - 0 → Unhealthy
  - 1 → Healthy

---

### Panel 10: Prediction Distribution (Bonus)

**Query A (Spike Predictions):**
```promql
sum(volatility_predictions_total{prediction="1"})
```

**Query B (Normal Predictions):**
```promql
sum(volatility_predictions_total{prediction="0"})
```

**Settings:**
- **Title:** Prediction Distribution
- **Description:** Spikes vs Normal
- **Visualization:** Pie chart or Bar chart
- **Legend:** Show

---

## Dashboard Layout Suggestions

Arrange panels in this order (top to bottom, left to right):

```
┌─────────────────────────────────────────┐
│  Row 1: Latency (Key SLO Metrics)      │
├───────────────────┬─────────────────────┤
│  P95 Latency      │  P50 Latency       │
│  (⭐ SLO)         │  (Median)          │
└───────────────────┴─────────────────────┘

┌─────────────────────────────────────────┐
│  Row 2: Errors (Key SLO Metrics)       │
├───────────────────┬─────────────────────┤
│  Error Rate       │  Error Percentage  │
│  (per second)     │  (⭐ SLO)          │
└───────────────────┴─────────────────────┘

┌─────────────────────────────────────────┐
│  Row 3: Consumer Health (Freshness)    │
├───────────────────┬─────────────────────┤
│  Consumer Lag     │  Processing Rate   │
│  (⭐ SLO)         │  (throughput)      │
└───────────────────┴─────────────────────┘

┌─────────────────────────────────────────┐
│  Row 4: Summary Stats                   │
├──────────┬──────────┬──────────┬────────┤
│ Request  │ Total    │ API      │ Pred   │
│ Rate     │ Preds    │ Health   │ Dist   │
└──────────┴──────────┴──────────┴────────┘
```

---

## Dashboard Settings

**Top of Dashboard:**
- **Time range:** Last 1 hour (adjustable)
- **Refresh:** 5s or 10s auto-refresh
- **Timezone:** Local time

**Variables (Optional but useful):**
- Add a variable for time range: 5m, 15m, 1h, 6h, 24h

---

## Testing Your Dashboard

### 1. Generate Some Traffic

Open a new terminal and run:

```bash

# Make multiple predictions
for i in {1..50}; do
  curl -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"price": 50000.0}' &
done

wait
```

**Result:** You should see:
- Request rate spike
- Latency values populate
- Prediction counter increase

---

### 2. Check All Panels Have Data

In Grafana, verify each panel shows data:
- ✅ Latency panels show lines (not "No data")
- ✅ Request rate shows activity
- ✅ Error rate is low (near 0)
- ✅ Consumer lag shows a value
- ✅ API health shows "1" (healthy)

---

### 3. Verify SLO Metrics

Check that your system meets SLOs:
- **P95 Latency:** Should be < 800ms (green/yellow zone)
- **Error Percentage:** Should be < 1% (green zone)
- **Consumer Lag:** Should be < 30s (green zone)

---

## Export Dashboard for Submission

### Method 1: Export JSON

1. Click **⚙️ Dashboard settings** (top right)
2. Click **"JSON Model"** (left sidebar)
3. Click **"Copy to clipboard"**
4. Save to file: `docs/grafana_dashboard.json`

### Method 2: Take Screenshot

1. Set time range to "Last 1 hour"
2. Press `Cmd + Shift + 4` (Mac screenshot tool)
3. Drag to capture entire dashboard
4. Save as: `docs/grafana_dashboard_screenshot.png`

**Or use Grafana's built-in screenshot:**
- Click **Share** icon (top right)
- Click **"Snapshot"**
- Click **"Publish to snapshot.raintank.io"** (optional)
- Or just take a regular screenshot

---

## Troubleshooting

### No Data in Panels

**Problem:** Panels show "No data"

**Solutions:**
1. Check time range (try "Last 5 minutes" or "Last 1 hour")
2. Make a test prediction: `curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"price": 50000}'`
3. Verify Prometheus is scraping: http://localhost:9090/targets
4. Check query syntax in panel (try running in Prometheus first)

---

### Data Source Not Working

**Problem:** "Data source is working" fails

**Solutions:**
1. Use `http://prometheus:9090` (NOT `localhost:9090`)
2. Select "Server" access mode (NOT "Browser")
3. Check Prometheus is running: `docker ps | grep prometheus`

---

### Queries Return Errors

**Problem:** "Bad data" or "Parse error"

**Solutions:**
1. Test query in Prometheus UI first: http://localhost:9090
2. Check metric names match exactly (case-sensitive)
3. Try simpler query first, then add complexity

---

## Week 6 Deliverable Checklist

For submission, you need:

- [ ] Dashboard with at least 6 panels
- [ ] P50/P95 latency graphs ⭐
- [ ] Error rate graph ⭐
- [ ] Consumer lag/freshness graph ⭐
- [ ] Request rate graph
- [ ] Grafana dashboard JSON exported (`docs/grafana_dashboard.json`)
- [ ] Screenshot of dashboard (`docs/grafana_dashboard_screenshot.png`)
- [ ] All panels showing real data (not "No data")
- [ ] Thresholds configured (800ms for latency, 1% for errors)

---

## Next Steps After Dashboard

Once dashboard is created:

1. ✅ Take screenshot for submission
2. ✅ Export JSON
3. ⬜ Write `docs/slo.md` (use dashboard metrics as evidence)
4. ⬜ Generate Evidently drift report
5. ⬜ Write `docs/runbook.md`
6. ⬜ Add model rollback feature

---

## Quick Reference: Key Queries

Copy these into Grafana panels:

```promql
# P95 Latency (ms)
histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m])) * 1000

# P50 Latency (ms)
histogram_quantile(0.50, rate(volatility_prediction_latency_seconds_bucket[5m])) * 1000

# Request Rate (req/s)
sum(rate(volatility_api_requests_total[1m]))

# Error Rate (errors/s)
sum(rate(volatility_api_errors_total[5m]))

# Error Percentage (%)
(sum(rate(volatility_api_errors_total[5m])) / sum(rate(volatility_api_requests_total[5m]))) * 100

# Consumer Lag (seconds)
volatility_consumer_lag_seconds

# Processing Rate (msg/s)
volatility_consumer_processing_rate

# API Health (0 or 1)
volatility_api_health_status

# Total Predictions
sum(volatility_predictions_total)
```

---

## Pro Tips

1. **Use Templates:** Search for "Prometheus FastAPI" dashboards to import and customize
2. **Color Code:** Use red for SLO violations, green for good performance
3. **Add Descriptions:** Help your professor understand each panel
4. **Test Under Load:** Run load test to populate metrics
5. **Document:** Take notes on what each metric means for your report

Good luck! 🚀

