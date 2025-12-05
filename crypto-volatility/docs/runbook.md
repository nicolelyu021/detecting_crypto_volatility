# Crypto Volatility Detection System - Runbook

## Overview

This runbook provides operational procedures for running, monitoring, and troubleshooting the Crypto Volatility Detection system. Follow these procedures for system startup, shutdown, monitoring, and incident response.

**System Components:**
- FastAPI (Prediction API)
- Kafka (Message Queue)
- MLflow (Model Registry)
- Prometheus (Metrics Collection)
- Grafana (Monitoring Dashboard)
- Prediction Consumer (Stream Processor)

**Last Updated:** December 5, 2024  
**Version:** 1.0 (Week 6)

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Startup Procedures](#startup-procedures)
3. [Shutdown Procedures](#shutdown-procedures)
4. [Health Checks](#health-checks)
5. [Monitoring](#monitoring)
6. [Common Issues & Solutions](#common-issues--solutions)
7. [Emergency Procedures](#emergency-procedures)
8. [Configuration Management](#configuration-management)
9. [Performance Tuning](#performance-tuning)
10. [Escalation](#escalation)

---

## Quick Reference

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8000 | Prediction endpoint |
| API Health | http://localhost:8000/health | Health check |
| API Metrics | http://localhost:8000/metrics | Prometheus metrics |
| Consumer Metrics | http://localhost:8001/metrics | Consumer metrics |
| Prometheus | http://localhost:9090 | Metrics database |
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |
| MLflow | http://localhost:5001 | Model registry |

### Quick Commands

```bash
# Start all services
cd crypto-volatility/docker
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f [service-name]

# Restart a service
docker compose restart [service-name]

# Stop all services
docker compose down

# Full restart
docker compose down && docker compose up -d
```

---

## Startup Procedures

### Standard Startup

**Prerequisites:**
- Docker Desktop is running
- At least 4GB RAM available
- Ports 3000, 5001, 8000, 8001, 9090, 9092, 9093 are free

**Procedure:**

1. **Navigate to docker directory**
   ```bash
   cd /path/to/crypto-volatility/docker
   ```

2. **Start all services**
   ```bash
   docker compose up -d
   ```

3. **Wait for services to initialize** (30-60 seconds)
   ```bash
   # Watch services come up
   watch docker compose ps
   ```

4. **Verify all services are healthy**
   ```bash
   docker compose ps
   ```
   
   Expected output: All services show "Up" and "healthy" status

5. **Perform health checks** (see [Health Checks](#health-checks) section)

**Startup Order:**
Services start in this dependency order:
1. Kafka (message queue)
2. MLflow (model registry)
3. API (prediction service)
4. Prometheus (metrics collection)
5. Grafana (dashboards)
6. Prediction Consumer (stream processor)

**Expected Startup Time:**
- Kafka: 15-20 seconds
- MLflow: 10-15 seconds
- API: 10-20 seconds (includes model loading)
- Other services: 5-10 seconds each

**Total startup time: ~60 seconds**

---

### First-Time Setup

If running for the first time:

1. **Ensure model files exist**
   ```bash
   ls -lh models/artifacts/
   # Should see: xgboost_model.pkl or similar
   ```

2. **Start services**
   ```bash
   cd docker
   docker compose up -d
   ```

3. **Configure Grafana** (one-time)
   - Open http://localhost:3000
   - Login: admin/admin
   - Add Prometheus data source: http://prometheus:9090
   - Import dashboard from `docs/grafana_dashboard.json`

4. **Verify model is loaded**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status": "healthy", "model_loaded": true}
   ```

---

## Shutdown Procedures

### Standard Shutdown

**Graceful Shutdown:**

1. **Stop all services**
   ```bash
   cd crypto-volatility/docker
   docker compose down
   ```
   
   This will:
   - Stop all containers gracefully
   - Remove containers
   - Preserve volumes (data persists)

2. **Verify shutdown**
   ```bash
   docker compose ps
   # Should show: No services running
   ```

**Expected Shutdown Time:** ~15-30 seconds

---

### Emergency Shutdown

If services are unresponsive:

```bash
# Force stop all containers
docker compose kill

# Clean up
docker compose down
```

---

### Shutdown with Data Cleanup

**⚠️ WARNING: This deletes all data!**

```bash
# Stop and remove everything including volumes
docker compose down -v

# Remove all unused Docker resources
docker system prune -a --volumes
```

Use this only for:
- Complete system reset
- Freeing disk space
- Troubleshooting persistent issues

---

## Health Checks

### Quick Health Check

```bash
# Check all services
docker compose ps

# API health
curl http://localhost:8000/health

# Check if model is loaded
curl http://localhost:8000/version
```

**Expected Outputs:**

```json
// /health
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "local-1764545017",
  "timestamp": 1733450123.45
}

// /version
{
  "api_version": "1.0.0",
  "model_version": "local-1764545017",
  "python_version": "3.11.5"
}
```

---

### Comprehensive Health Check

Run this script to check all services:

```bash
#!/bin/bash
# comprehensive-health-check.sh

echo "=== Docker Services ==="
docker compose ps

echo -e "\n=== API Health ==="
curl -s http://localhost:8000/health | jq .

echo -e "\n=== API Metrics Available ==="
curl -s http://localhost:8000/metrics | head -5

echo -e "\n=== Consumer Metrics Available ==="
curl -s http://localhost:8001/metrics | head -5

echo -e "\n=== Prometheus Targets ==="
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'

echo -e "\n=== Grafana Alive ==="
curl -s http://localhost:3000/api/health | jq .

echo -e "\n=== MLflow Alive ==="
curl -s http://localhost:5001/health

echo -e "\n=== All checks complete ==="
```

**Save this as:** `scripts/health_check.sh`

**Run:** `bash scripts/health_check.sh`

---

### Individual Service Checks

**Kafka:**
```bash
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

**MLflow:**
```bash
curl http://localhost:5001/health
```

**API:**
```bash
curl http://localhost:8000/health
```

**Consumer:**
```bash
docker logs volatility-prediction-consumer | tail -20
# Look for: "✅ Prediction consumer started"
```

**Prometheus:**
```bash
curl http://localhost:9090/-/healthy
```

**Grafana:**
```bash
curl http://localhost:3000/api/health
```

---

## Monitoring

### Real-Time Monitoring

**Grafana Dashboard:** http://localhost:3000
- Login: admin/admin
- Dashboard: "Crypto Volatility Monitoring"

**Key Metrics to Watch:**
1. **P95 Latency:** Should be < 800ms (ours: ~45ms ✅)
2. **Error Rate:** Should be < 1% (ours: 0% ✅)
3. **Consumer Lag:** Should be < 30 seconds (ours: 0s ✅)
4. **Request Rate:** Normal baseline ~0-5 req/s
5. **API Health:** Should be 1 (healthy)

---

### Viewing Logs

**All services:**
```bash
docker compose logs -f
```

**Specific service:**
```bash
# API logs
docker compose logs -f api

# Consumer logs
docker compose logs -f prediction-consumer

# Kafka logs
docker compose logs -f kafka

# Prometheus logs
docker compose logs -f prometheus
```

**Last 100 lines:**
```bash
docker compose logs --tail=100 api
```

**Since specific time:**
```bash
docker compose logs --since 10m api
```

---

### Log Locations

Logs are stored in Docker containers and can be accessed via:
- `docker compose logs [service]`
- Docker Desktop → Containers → [service] → Logs

**Log Retention:**
- Max size: 10MB per file
- Max files: 3 (30MB total per service)
- Configured in: `docker/compose.yaml`

---

## Common Issues & Solutions

### Issue 1: Services Won't Start

**Symptoms:**
- `docker compose up` fails
- Services show "unhealthy" status

**Possible Causes & Solutions:**

**A. Docker is not running**
```bash
# Check if Docker is running
docker ps

# Solution: Start Docker Desktop
open -a Docker
# Wait for Docker to start (~30 seconds)
```

**B. Port conflicts**
```bash
# Check which ports are in use
lsof -i :8000  # API
lsof -i :9092  # Kafka
lsof -i :3000  # Grafana

# Solution: Stop conflicting service or change port in compose.yaml
```

**C. Insufficient resources**
```bash
# Check Docker resources
docker stats

# Solution: Increase Docker Desktop memory limit
# Docker Desktop → Settings → Resources → Memory (set to ≥ 4GB)
```

**D. Corrupted volumes**
```bash
# Solution: Remove volumes and restart
docker compose down -v
docker compose up -d
```

---

### Issue 2: API Returns 503 "Model Not Loaded"

**Symptoms:**
```json
{"status": "unhealthy", "model_loaded": false}
```

**Diagnosis:**
```bash
# Check API logs
docker compose logs api | grep -i error
```

**Common Causes:**

**A. Model file missing**
```bash
# Check if model exists
ls -lh models/artifacts/

# Solution: Ensure model file exists or train a new model
```

**B. MLflow unavailable**
```bash
# Check MLflow health
curl http://localhost:5001/health

# Solution: Restart MLflow
docker compose restart mlflow
```

**C. Model loading timeout**
```bash
# Solution: Wait 30 seconds after API starts, then check again
sleep 30 && curl http://localhost:8000/health
```

---

### Issue 3: High Latency (P95 > 800ms)

**Symptoms:**
- Grafana shows P95 latency exceeding 800ms
- Slow prediction responses

**Diagnosis:**
```bash
# Check resource usage
docker stats

# Check for errors
docker compose logs api | grep -i error
```

**Solutions:**

**A. High CPU usage**
```bash
# Check CPU
docker stats --no-stream

# Solution: Reduce load or scale horizontally
```

**B. Model inference slow**
```bash
# Solution: Optimize model (smaller model, quantization)
# Or: Use faster hardware
```

**C. Database/disk I/O bottleneck**
```bash
# Solution: Move to SSD or increase Docker disk performance limit
```

---

### Issue 4: Consumer Lag Increasing

**Symptoms:**
- `volatility_consumer_lag_seconds` > 30s
- Consumer falling behind

**Diagnosis:**
```bash
# Check consumer logs
docker compose logs prediction-consumer | tail -50

# Check processing rate
curl http://localhost:8001/metrics | grep processing_rate
```

**Solutions:**

**A. Consumer processing too slow**
```bash
# Solution: Scale consumer (add more instances)
docker compose up -d --scale prediction-consumer=2
```

**B. Kafka backlog**
```bash
# Check Kafka lag
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe --group volatility-predictor

# Solution: Clear old messages or increase retention
```

**C. Consumer errors**
```bash
# Check for errors
docker compose logs prediction-consumer | grep -i error

# Solution: Fix errors and restart
docker compose restart prediction-consumer
```

---

### Issue 5: Kafka Connection Errors

**Symptoms:**
- Consumer logs: "Failed to connect to Kafka"
- Producer errors

**Diagnosis:**
```bash
# Check Kafka status
docker compose ps kafka

# Check Kafka logs
docker compose logs kafka | tail -50
```

**Solutions:**

**A. Kafka not ready**
```bash
# Solution: Wait for Kafka to fully start (15-20 seconds)
sleep 20 && docker compose restart prediction-consumer
```

**B. Network issues**
```bash
# Check Docker network
docker network ls
docker network inspect kafka-network

# Solution: Recreate network
docker compose down
docker compose up -d
```

**C. Kafka crashed**
```bash
# Solution: Restart Kafka
docker compose restart kafka
# Wait 20 seconds
sleep 20
# Restart dependent services
docker compose restart api prediction-consumer
```

---

### Issue 6: Grafana Dashboards Not Loading

**Symptoms:**
- Grafana shows "No data"
- Dashboards empty

**Solutions:**

**A. Prometheus not scraping**
```bash
# Check Prometheus targets
open http://localhost:9090/targets

# Solution: Ensure all targets show "UP"
# If DOWN: restart the down service
```

**B. Wrong data source URL**
```bash
# Grafana data source should be: http://prometheus:9090
# NOT: http://localhost:9090

# Solution: Update data source in Grafana settings
```

**C. No traffic/data yet**
```bash
# Solution: Generate some predictions
for i in {1..20}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"price": 50000.0}' > /dev/null
done
```

---

### Issue 7: Error Rate Spiking

**Symptoms:**
- Grafana shows error rate > 1%
- Many 500 errors in logs

**Immediate Action:**
```bash
# 1. Check error logs
docker compose logs api | grep ERROR

# 2. Check API health
curl http://localhost:8000/health

# 3. If critical, rollback to baseline model (see Emergency Procedures)
```

**Common Causes:**

**A. Model errors**
```bash
# Check for prediction errors
docker compose logs api | grep "Prediction error"

# Solution: Rollback to baseline model or previous version
```

**B. Resource exhaustion**
```bash
# Check memory/CPU
docker stats --no-stream

# Solution: Restart services or increase resources
```

**C. Input validation errors**
```bash
# Check for malformed requests
docker compose logs api | grep "422"

# Solution: Fix client requests or add better validation
```

---

## Emergency Procedures

### Procedure 1: Total System Restart

**When to use:**
- Multiple services failing
- Unresponsive system
- After configuration changes

**Steps:**
```bash
# 1. Stop everything
cd crypto-volatility/docker
docker compose down

# 2. Verify all stopped
docker compose ps
# Should show: No services

# 3. Start fresh
docker compose up -d

# 4. Wait for startup
sleep 60

# 5. Verify health
curl http://localhost:8000/health
```

**Duration:** ~2 minutes

---

### Procedure 2: Rollback to Baseline Model

**When to use:**
- ML model causing errors
- Prediction quality degraded
- High error rate (> 5%)

**Steps:**
```bash
# 1. Stop API
docker compose stop api

# 2. Set baseline model environment variable
# Edit docker/compose.yaml:
# Under api service, add/change:
#   environment:
#     MODEL_VARIANT: baseline

# 3. Restart API
docker compose up -d api

# 4. Verify rollback
curl http://localhost:8000/version
# Check model_version changed

# 5. Monitor metrics for 5 minutes
open http://localhost:3000
```

**Note:** Baseline model has lower accuracy but higher reliability.

---

### Procedure 3: Clear Kafka Backlog

**When to use:**
- Consumer lag > 300 seconds
- Old messages backing up
- Testing/development reset

**⚠️ WARNING: This deletes all messages!**

```bash
# 1. Stop consumer
docker compose stop prediction-consumer

# 2. Delete Kafka data
docker compose down
docker volume rm docker_kafka-data

# 3. Restart everything
docker compose up -d

# 4. Wait for services
sleep 60

# 5. Verify consumer lag is 0
curl http://localhost:8001/metrics | grep lag
```

---

### Procedure 4: Emergency Shutdown

**When to use:**
- System compromised
- Critical bug discovered
- Emergency maintenance

**Steps:**
```bash
# 1. Immediate stop (don't wait for graceful shutdown)
docker compose kill

# 2. Remove containers
docker compose down

# 3. Notify team (if production)
# Send alert via Slack/email

# 4. Document incident
# Create incident report in docs/incidents/
```

---

## Configuration Management

### Configuration Files

**Primary Config:**
- `config.yaml` - Main application configuration
- `docker/compose.yaml` - Docker services configuration
- `docker/prometheus.yml` - Prometheus scraping config

**Modifying Configuration:**

1. **Stop affected services**
   ```bash
   docker compose stop [service]
   ```

2. **Edit configuration file**
   ```bash
   vim config.yaml
   # or
   vim docker/compose.yaml
   ```

3. **Restart services**
   ```bash
   docker compose up -d [service]
   ```

4. **Verify changes**
   ```bash
   docker compose logs [service] | head -20
   ```

---

### Environment Variables

**Key Environment Variables:**

| Variable | Service | Purpose | Default |
|----------|---------|---------|---------|
| `CONFIG_PATH` | API, Consumer | Config file path | `config.yaml` |
| `MODEL_VARIANT` | API, Consumer | Model to use | `ml` |
| `MLFLOW_TRACKING_URI` | API, Consumer | MLflow URL | `http://mlflow:5000` |
| `KAFKA_BOOTSTRAP_SERVERS` | Consumer | Kafka URL | `kafka:29092` |
| `PORT` | API | API port | `8000` |
| `METRICS_PORT` | Consumer | Metrics port | `8001` |

**Example: Change model:**
```yaml
# In docker/compose.yaml
api:
  environment:
    MODEL_VARIANT: baseline  # Use baseline instead of ML model
```

---

### Backup Procedures

**What to backup:**
1. Configuration files
2. Model files (`models/artifacts/`)
3. MLflow data (`docker/mlflow-data/`)
4. Grafana dashboards (export JSON)

**Backup command:**
```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Backup configs
cp config.yaml backups/$(date +%Y%m%d)/
cp docker/compose.yaml backups/$(date +%Y%m%d)/

# Backup models
cp -r models/artifacts backups/$(date +%Y%m%d)/

# Backup MLflow (if needed)
docker compose stop mlflow
cp -r docker/mlflow-data backups/$(date +%Y%m%d)/
docker compose start mlflow
```

**Backup frequency:**
- Configs: Before any changes
- Models: After each training run
- MLflow: Weekly or before major changes

---

## Performance Tuning

### API Performance

**Current Performance:**
- P50 Latency: ~1.67ms
- P95 Latency: ~45ms
- Target: P95 < 800ms ✅

**Tuning Options:**

1. **Increase workers** (if needed)
   ```yaml
   # In Dockerfile.api
   CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
   ```

2. **Model optimization**
   - Use smaller model
   - Quantize model
   - Cache predictions (if applicable)

3. **Resource allocation**
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

### Consumer Performance

**Current Performance:**
- Processing rate: ~2 msg/sec
- Lag: 0 seconds ✅

**Scaling Options:**

1. **Horizontal scaling** (multiple consumers)
   ```bash
   docker compose up -d --scale prediction-consumer=3
   ```

2. **Batch processing**
   - Modify consumer to process messages in batches
   - Trade latency for throughput

3. **Resource allocation**
   ```yaml
   prediction-consumer:
     deploy:
       resources:
         limits:
           cpus: '1.0'
           memory: 1G
   ```

---

### Kafka Performance

**Current Setup:**
- Single broker (development)
- Auto-create topics
- Default retention

**Production Tuning:**

1. **Increase retention**
   ```yaml
   # In docker/compose.yaml
   kafka:
     environment:
       KAFKA_LOG_RETENTION_MS: 86400000  # 24 hours
   ```

2. **Tune partitions**
   ```bash
   # Create topic with 3 partitions
   docker exec kafka kafka-topics --create \
     --topic ticks.features \
     --partitions 3 \
     --replication-factor 1 \
     --bootstrap-server localhost:9092
   ```

---

## Escalation

### Issue Severity Levels

**P0 - Critical (Immediate Response)**
- API completely down
- All predictions failing (error rate > 50%)
- Data loss occurring
- Security breach

**Response Time:** Immediate (< 5 minutes)

---

**P1 - High (Urgent)**
- SLO violation (P95 > 800ms or error rate > 1%)
- Consumer lag > 300 seconds
- Single service down

**Response Time:** < 30 minutes

---

**P2 - Medium (Standard)**
- Warnings in logs
- Minor performance degradation
- Non-critical feature broken

**Response Time:** < 4 hours

---

**P3 - Low (Planned)**
- Feature requests
- Documentation updates
- Minor improvements

**Response Time:** Next sprint/iteration

---

### Escalation Path

**Level 1: On-call Engineer**
- Check runbook
- Follow standard procedures
- Attempt fixes

**Level 2: Team Lead**
- If issue persists > 30 minutes
- If P0 incident
- If requires configuration changes

**Level 3: System Architect**
- If architectural change needed
- If affects multiple systems
- If data integrity at risk

---

### Contact Information

| Role | Contact | Availability |
|------|---------|--------------|
| On-call Engineer | [Your Email] | 24/7 |
| Team Lead | [Lead Email] | Business hours |
| System Architect | [Architect Email] | On-call rotation |
| Product Owner | [PO Email] | Business hours |

---

## Maintenance

### Regular Maintenance Tasks

**Daily:**
- ✅ Check Grafana dashboards
- ✅ Review error logs
- ✅ Verify all services healthy

**Weekly:**
- ✅ Review SLO compliance
- ✅ Generate Evidently drift report
- ✅ Check disk space usage
- ✅ Review and archive old logs

**Monthly:**
- ✅ Update dependencies
- ✅ Review and optimize performance
- ✅ Backup configurations
- ✅ Update documentation

**Quarterly:**
- ✅ Review and update SLOs
- ✅ Disaster recovery drill
- ✅ Security audit
- ✅ Capacity planning

---

### Maintenance Windows

**Recommended Maintenance Window:**
- Day: Sunday
- Time: 2:00 AM - 4:00 AM (low traffic)
- Duration: 2 hours
- Frequency: Monthly

**Pre-maintenance Checklist:**
- [ ] Notify users (if production)
- [ ] Backup configurations
- [ ] Backup models
- [ ] Test rollback procedure
- [ ] Have rollback plan ready

**Post-maintenance Checklist:**
- [ ] Run health checks
- [ ] Monitor for 1 hour
- [ ] Verify SLOs met
- [ ] Document changes
- [ ] Update runbook if needed

---

## Appendix A: Service Dependencies

```
┌─────────────┐
│   Kafka     │ ← Base service (no dependencies)
└──────┬──────┘
       │
       ├────────┬────────────┬─────────────┐
       │        │            │             │
┌──────▼──┐ ┌──▼──────┐ ┌───▼────────┐ ┌─▼─────────┐
│ MLflow  │ │   API   │ │ Consumer   │ │Prometheus │
└──────┬──┘ └──┬──────┘ └────────────┘ └───┬───────┘
       │       │                            │
       │       └────────────────┬───────────┘
       │                        │
       └────────────┬───────────┘
                    │
              ┌─────▼─────┐
              │  Grafana  │
              └───────────┘
```

**Startup order:** Kafka → MLflow/Prometheus → API/Consumer → Grafana

**Shutdown order:** Reverse of startup

---

## Appendix B: Port Usage

| Port | Service | Protocol | External Access |
|------|---------|----------|-----------------|
| 3000 | Grafana | HTTP | Yes |
| 5001 | MLflow | HTTP | Yes |
| 8000 | API | HTTP | Yes |
| 8001 | Consumer Metrics | HTTP | Yes |
| 9090 | Prometheus | HTTP | Yes |
| 9092 | Kafka | TCP | No (internal) |
| 9093 | Kafka Controller | TCP | No (internal) |
| 29092 | Kafka Internal | TCP | No (internal) |

---

## Appendix C: Useful Commands Reference

```bash
# === Docker Compose ===
docker compose up -d              # Start all services
docker compose down               # Stop all services
docker compose ps                 # List services
docker compose logs -f [service]  # Follow logs
docker compose restart [service]  # Restart service
docker compose stop [service]     # Stop service
docker compose start [service]    # Start service

# === Docker ===
docker ps                         # List running containers
docker stats                      # Resource usage
docker logs [container]           # View logs
docker exec -it [container] bash  # Enter container

# === Health Checks ===
curl http://localhost:8000/health # API health
curl http://localhost:8000/metrics # API metrics
curl http://localhost:9090/-/healthy # Prometheus health

# === Troubleshooting ===
docker compose down -v            # Remove volumes
docker system prune -a            # Clean up Docker
docker volume ls                  # List volumes
docker network ls                 # List networks

# === Testing ===
# Make a prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"price": 50000.0}'

# Load test (generate traffic)
for i in {1..100}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"price": 50000.0}' > /dev/null
  sleep 0.5
done
```

---

## Appendix D: Grafana Dashboard Quick Start

1. **Access Grafana:** http://localhost:3000
2. **Login:** admin / admin
3. **Add Data Source:**
   - Configuration → Data Sources → Add data source
   - Select Prometheus
   - URL: `http://prometheus:9090`
   - Save & Test

4. **Import Dashboard:**
   - Dashboards → Import
   - Upload `docs/grafana_dashboard.json`
   - Select Prometheus data source
   - Import

5. **View Dashboard:**
   - Dashboards → Browse
   - Select "Crypto Volatility Monitoring"

---

## Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2024-12-05 | 1.0 | Initial runbook creation | Week 6 Team |

---

## Document Maintenance

**Review Schedule:** Monthly  
**Next Review:** January 5, 2025  
**Owner:** DevOps Team  
**Approvers:** Technical Lead, Product Owner

**Feedback:** Submit updates via GitHub issues or direct to team lead.

---

**END OF RUNBOOK**

