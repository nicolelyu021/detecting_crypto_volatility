# Crypto Volatility Detection System - Concise Runbook

**Quick Reference for Operations**

---

## 🚀 Startup

### Standard Startup
```bash
cd docker
docker compose up -d
```

**Wait 60 seconds**, then verify:
```bash
docker compose ps                    # All services "Up"
curl http://localhost:8000/health   # {"status": "healthy"}
```

**Service URLs:**
- API: http://localhost:8000
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- MLflow: http://localhost:5001

### First-Time Setup
1. Ensure model files exist: `ls models/artifacts/*.pkl`
2. Start services: `docker compose up -d`
3. Configure Grafana (one-time):
   - Open http://localhost:3000
   - Login: admin/admin
   - Add Prometheus data source: http://prometheus:9090
   - Import dashboard: `docs/grafana_dashboard.json`

---

## 📡 Realtime Ingestion & Prediction

### Prerequisites - Install Dependencies

**Option 1: Install all dependencies (recommended)**

**macOS users - Install OpenMP first (required for XGBoost):**
```bash
brew install libomp
```

**Then install Python dependencies:**
```bash
# Install all project dependencies
pip install -r requirements.txt
```

**Option 2: Install minimal dependencies separately**

**For WebSocket Ingestion:**
```bash
pip install confluent-kafka websocket-client pyyaml python-dotenv pandas pyarrow numpy
```

**For Prediction Consumer (requires ML dependencies):**

**macOS users - Install OpenMP first:**
```bash
brew install libomp
```

**Then install Python packages:**
```bash
pip install confluent-kafka pyyaml python-dotenv pandas pyarrow numpy \
            xgboost scikit-learn mlflow prometheus-client
```

**Verify Installation:**
```bash
# Test ingestion dependencies
python3 -c "import confluent_kafka; import websocket; print('✅ Ingestion deps OK')"

# Test consumer dependencies (including XGBoost)
python3 -c "import xgboost; import sklearn; import confluent_kafka; print('✅ Consumer deps OK')"

# Test all critical imports
python3 -c "
import confluent_kafka
import websocket
import xgboost
import sklearn
import pandas
import numpy
import yaml
import prometheus_client
print('✅ All dependencies installed')
"
```

### Start WebSocket Ingestion
```bash
# From project root
python3 scripts/ws_ingest.py

# With custom config
CONFIG_PATH=config.yaml python3 scripts/ws_ingest.py
```

**What it does:**
- Connects to Coinbase WebSocket API
- Subscribes to ticker channels (BTC-USD, ETH-USD)
- Featurizes data and publishes to Kafka topic: `crypto-features`

**Stop:** Press `Ctrl+C`

### Start Feature Engineering
```bash
# From project root
python3 features/featurizer.py

# With custom config
CONFIG_PATH=config.yaml python3 features/featurizer.py
```

**What it does:**
- Consumes raw tick data from Kafka (`crypto-ticks` or `topic_raw`)
- Computes windowed features (returns, spreads, volatility, trade intensity)
- Publishes processed features to Kafka topic: `crypto-features`

**Stop:** Press `Ctrl+C`

### Start Prediction Consumer
```bash
# From project root
python3 scripts/prediction_consumer.py

# With custom config
python3 scripts/prediction_consumer.py --config config.yaml
```

**What it does:**
- Consumes features from Kafka (`crypto-features`)
- Makes predictions using loaded model
- Publishes predictions to Kafka (`crypto-predictions`)
- Exposes metrics on port 8001

**Stop:** Press `Ctrl+C`

### Verify Pipeline
```bash
# Check Kafka topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Monitor feature messages
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic crypto-features \
  --from-beginning

# Check consumer metrics
curl -s http://localhost:8001/metrics | grep consumer_lag
```

---

## 🔧 Troubleshooting

### Issue: ModuleNotFoundError: No module named 'xgboost'
```bash
# Install XGBoost and dependencies
pip install xgboost scikit-learn

# macOS users: Install OpenMP library first (required for XGBoost)
brew install libomp
pip install --upgrade xgboost
```

### Issue: XGBoost Library (libxgboost.dylib) could not be loaded
```bash
# macOS only - Install OpenMP runtime
brew install libomp

# Reinstall XGBoost
pip uninstall xgboost
pip install xgboost

# Verify
python3 -c "import xgboost; print('✅ XGBoost installed')"
```

### Issue: Services Won't Start
```bash
# Check Docker is running
docker ps

# Check port conflicts
lsof -i :8000 :9092 :3000

# Check Docker resources (need ≥4GB RAM)
docker stats

# Solution: Clean restart
docker compose down -v
docker compose up -d
```

### Issue: API Returns 503 "Model Not Loaded"
```bash
# Check API logs
docker compose logs api | grep -i error

# Verify model exists
ls -lh models/artifacts/

# Check MLflow
curl http://localhost:5001/health

# Solution: Restart API
docker compose restart api
```

### Issue: High Latency (P95 > 800ms)
```bash
# Check resource usage
docker stats

# Check for errors
docker compose logs api | grep ERROR

# Solution: Restart services or scale
docker compose restart api
```

### Issue: Consumer Lag > 30s
```bash
# Check consumer logs
docker compose logs prediction-consumer | tail -50

# Check Kafka
docker compose logs kafka | tail -50

# Solution: Restart consumer
docker compose restart prediction-consumer
```

### Issue: Kafka Connection Errors
```bash
# Check Kafka status
docker compose ps kafka

# Check network
docker network inspect kafka-network

# Solution: Restart Kafka and dependent services
docker compose restart kafka
sleep 20
docker compose restart api prediction-consumer
```

### Issue: Grafana Shows "No Data"
```bash
# Check Prometheus targets
open http://localhost:9090/targets

# Verify data source URL in Grafana: http://prometheus:9090

# Generate test traffic
for i in {1..20}; do
  curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"price": 50000.0}' > /dev/null 2>&1
done
```

---

## 🔄 Recovery Procedures

### Total System Restart
```bash
cd docker
docker compose down
docker compose up -d
sleep 60
curl http://localhost:8000/health
```

### Rollback to Baseline Model
```bash
# 1. Stop API
docker compose stop api

# 2. Edit docker/compose.yaml - add under api.environment:
#    MODEL_VARIANT: baseline

# 3. Restart API
docker compose up -d api

# 4. Verify rollback
curl http://localhost:8000/version | jq .model_version
```

### Clear Kafka Backlog (⚠️ Deletes Messages)
```bash
docker compose down
docker volume rm docker_kafka-data
docker compose up -d
```

### Emergency Shutdown
```bash
docker compose kill
docker compose down
```

---

## 📊 Health Checks

### Quick Check
```bash
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/version
```

### Comprehensive Check
```bash
# Services
docker compose ps

# API health
curl http://localhost:8000/health | jq .

# Metrics endpoints
curl -s http://localhost:8000/metrics | head -5
curl -s http://localhost:8001/metrics | head -5

# Prometheus targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

---

## 📝 Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f prediction-consumer
docker compose logs -f kafka

# Last 100 lines
docker compose logs --tail=100 api

# Since 10 minutes ago
docker compose logs --since 10m api
```

---

## 🔑 Key Commands

```bash
# Start/Stop
docker compose up -d              # Start all
docker compose down               # Stop all
docker compose restart [service]  # Restart service

# Status
docker compose ps                 # List services
docker stats                      # Resource usage

# Logs
docker compose logs -f [service]  # Follow logs

# Cleanup
docker compose down -v            # Remove volumes
docker system prune -a            # Clean up Docker
```

---

## ⚡ Performance Tuning

### Current Performance
- **P50 Latency:** ~1.67ms
- **P95 Latency:** ~45ms (target: <800ms ✅)
- **Error Rate:** 0% (target: <1% ✅)
- **Consumer Lag:** 0s (target: <30s ✅)

### If Performance Degrades

**API Slowdown:**
```bash
# Increase workers (edit Dockerfile.api)
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Consumer Lag:**
```bash
# Scale consumer
docker compose up -d --scale prediction-consumer=3
```

**Resource Limits:**
```yaml
# In docker/compose.yaml
api:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
```

---

## 📞 Escalation

**P0 - Critical (Immediate):**
- API completely down
- Error rate > 50%
- Data loss

**P1 - High (30 min):**
- SLO violation (P95 > 800ms, error rate > 1%)
- Consumer lag > 300s
- Single service down

**P2 - Medium (4 hours):**
- Warnings in logs
- Minor performance degradation

---

## 🔗 Quick Links

- **Full Runbook:** `docs/runbook.md`
- **SLO Document:** `docs/slo.md`
- **Architecture:** `docs/architecture.md`
- **Model Rollback Guide:** `docs/model_rollback_guide.md`

---

**Last Updated:** December 5, 2024  
**Version:** Concise 1.0

