# Runbook: Crypto Volatility Detection System

## STARTUP

### 1. Environment Setup (One-time)
```powershell
# Navigate to repo
cd d:\AI Projects\crypto-volatility\detecting_crypto_volatility

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Infrastructure (Docker)
```powershell
cd docker
docker-compose up -d

# Verify services running
docker ps
# Expected: kafka, zookeeper, mlflow containers UP

# Check logs if needed
docker-compose logs
```

### 3. Verify Kafka is Ready
```powershell
# Wait 10-15 seconds for Kafka to initialize
Start-Sleep -Seconds 15

# Consume check (from repo root)
python scripts/kafka_consume_check.py --min 5
# Should show Kafka is responding or topic doesn't exist yet (OK)
```

### 4. Quick Smoke Test (Choose One)

**Option A: Replay Mode (Recommended - No live Coinbase needed)**
```powershell
# Generate features from saved 10-min slice
python scripts/replay.py --input data/raw/slice_10min.ndjson --output data/processed/features_test.parquet

# Run inference
python models/infer.py --model-path models/artifacts/xgboost/xgb_model.pkl --data-path data/processed/features_test.parquet --output-path predictions_test.parquet

# Verify output
python -c "import pandas as pd; print(pd.read_parquet('predictions_test.parquet')[['predicted_label', 'spike_probability']].head())"
```

**Option B: Live Ingestion (Requires internet, Coinbase access)**
```powershell
# Collect 2 minutes of live data (will pause after 2 min)
python scripts/ws_ingest.py  # Edit script or set env var to control duration

# Generate features from ingested data
python scripts/replay.py --input data/raw/slice.ndjson --output data/processed/features_live.parquet

# Run inference
python models/infer.py --model-path models/artifacts/xgboost/xgb_model.pkl --data-path data/processed/features_live.parquet
```

### 5. View Results (Optional)
```powershell
# Start MLflow UI to see all model runs & artifacts
mlflow ui --backend-store-uri file:./mlruns
# Open browser: http://localhost:5000
```

---

## TROUBLESHOOTING

### Issue 1: Kafka Services Won't Start
**Symptoms:** `docker ps` shows containers exited or health checks failing.

**Diagnosis:**
```powershell
docker-compose logs kafka
docker-compose logs zookeeper
```

**Recovery:**
```powershell
# Stop and remove containers
docker-compose down -v  # -v removes volumes (clears Kafka state)

# Restart
docker-compose up -d

# Wait and verify
Start-Sleep -Seconds 20
docker ps
```

---

### Issue 2: Python Import Errors (Missing packages)
**Symptoms:** `ModuleNotFoundError: No module named 'kafka'` or similar.

**Diagnosis:**
```powershell
pip list | grep -E "kafka|pandas|xgboost|mlflow"
```

**Recovery:**
```powershell
# Reinstall all dependencies
pip install --upgrade -r requirements.txt

# Or reinstall specific package
pip install kafka-python
```

---

### Issue 3: Parquet File Not Found
**Symptoms:** `FileNotFoundError: data/processed/features.parquet`

**Diagnosis:**
```powershell
# Check if raw data exists
Test-Path data/raw/slice_10min.ndjson

# Check if processed dir exists
Test-Path data/processed
```

**Recovery:**
```powershell
# If raw file missing, recreate it
python scripts/ws_ingest.py  # Run for 1-2 minutes to generate data

# Ensure processed dir exists
New-Item -ItemType Directory -Force -Path data/processed

# Regenerate features
python scripts/replay.py --input data/raw/slice_10min.ndjson --output data/processed/features.parquet
```

---

### Issue 4: Model Artifacts Missing
**Symptoms:** `FileNotFoundError: models/artifacts/xgboost/xgb_model.pkl`

**Diagnosis:**
```powershell
# List available models
Get-ChildItem models/artifacts -Recurse -Filter *.pkl
```

**Recovery:**
```powershell
# If no models exist, retrain
python models/train.py
# This will create all three models (baseline, LR, XGBoost)
# May take 5-10 minutes depending on data size

# Check again
Get-ChildItem models/artifacts -Recurse -Filter *.pkl
```

---

### Issue 5: Inference Script Fails
**Symptoms:** Error during `python models/infer.py` or latency check fails.

**Diagnosis:**
```powershell
# Check if model file is valid
Test-Path models/artifacts/xgboost/xgb_model.pkl

# Check if feature file is valid Parquet
python -c "import pandas as pd; df = pd.read_parquet('data/processed/features_test.parquet'); print(f'Shape: {df.shape}, Columns: {list(df.columns)}')"
```

**Recovery:**
```powershell
# Verify features have required columns
# Required: midprice_return_mean, midprice_return_std, bid_ask_spread, trade_intensity, order_book_imbalance

# If feature columns wrong, regenerate
python scripts/replay.py --input data/raw/slice_10min.ndjson --output data/processed/features_test.parquet

# Retry inference
python models/infer.py --model-path models/artifacts/xgboost/xgb_model.pkl --data-path data/processed/features_test.parquet
```

---

### Issue 6: Latency Exceeds Requirement (> 120 seconds)
**Symptoms:** Inference latency check shows "FAIL (exceeds 2x real-time)"

**Diagnosis:**
```powershell
# Check system resources
Get-Process | Where-Object {$_.ProcessName -eq "python"} | Select-Object ProcessName, WorkingSet, CPU

# Check data size
python -c "import pandas as pd; df = pd.read_parquet('data/processed/features_test.parquet'); print(f'Records: {len(df)}')"
```

**Recovery:**
```powershell
# Reduce batch size (use smaller feature file)
python scripts/replay.py --input data/raw/slice_10min.ndjson --output data/processed/features_small.parquet

# Retry with smaller dataset
python models/infer.py --model-path models/artifacts/xgboost/xgb_model.pkl --data-path data/processed/features_small.parquet

# If still slow:
# - Check CPU/RAM availability
# - Close other applications
# - Consider using Baseline model instead (faster than XGBoost)
python models/infer.py --model-path models/artifacts/baseline/baseline_model.pkl --data-path data/processed/features_test.parquet
```

---

### Issue 7: Docker Compose Port Already in Use
**Symptoms:** `docker-compose up` fails with "port already in use" (e.g., 9092, 5001)

**Diagnosis:**
```powershell
# Check which process is using port (e.g., 9092 for Kafka)
netstat -ano | findstr :9092
# Or: Get-NetTCPConnection -LocalPort 9092 | Select-Object State, OwningProcess
```

**Recovery:**
```powershell
# Stop existing container using that port
docker stop <container_id>
docker rm <container_id>

# Or change port in docker-compose.yaml and restart
# Then retry
docker-compose up -d
```

---

### Issue 8: Git Pull Conflicts
**Symptoms:** After `git pull`, merge conflicts or modified files.

**Diagnosis:**
```powershell
git status
```

**Recovery:**
```powershell
# If local changes, stash them
git stash

# Pull latest
git pull

# Reapply changes if needed
git stash pop
```

---

## RECOVERY PROCEDURES

### Full Reset (Nuclear Option)
```powershell
# Stop all Docker containers
docker-compose down -v  # -v removes volumes

# Clear Python cache
Remove-Item -Recurse -Force __pycache__ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue

# Reinstall environment
pip install --upgrade -r requirements.txt --force-reinstall

# Restart Docker
docker-compose up -d

# Regenerate data
python scripts/replay.py --input data/raw/slice_10min.ndjson --output data/processed/features.parquet

# Smoke test
python models/infer.py --model-path models/artifacts/xgboost/xgb_model.pkl --data-path data/processed/features.parquet
```

### Data Pipeline Reset (Keep Docker)
```powershell
# Clear processed data
Remove-Item data/processed/*.parquet -Force -ErrorAction SilentlyContinue

# Regenerate from raw
python scripts/replay.py --input data/raw/slice_10min.ndjson --output data/processed/features.parquet

# Verify
python -c "import pandas as pd; print(pd.read_parquet('data/processed/features.parquet').shape)"
```

### Model Retraining (If Performance Degrades)
```powershell
# Retrain all models
python models/train.py
# Logs metrics to MLflow and saves artifacts to models/artifacts/

# View training results
mlflow ui --backend-store-uri file:./mlruns

# Verify new models created
Get-ChildItem models/artifacts -Recurse -Filter *.pkl
```

### Kafka Reset (If Topics Corrupt)
```powershell
# Stop Kafka
docker-compose stop kafka

# Remove Kafka volumes
docker volume rm detecting_crypto_volatility_kafka_data 2>$null

# Restart
docker-compose up -d kafka

# Wait for Kafka to reinitialize
Start-Sleep -Seconds 20

# Verify
python scripts/kafka_consume_check.py --min 1
```

---

## HEALTH CHECKS

### Quick Health Check (< 1 min)
```powershell
# 1. Check Docker services
docker ps --filter "status=running"

# 2. Check files exist
Test-Path data/raw/slice_10min.ndjson
Test-Path models/artifacts/xgboost/xgb_model.pkl

# 3. Quick inference
python models/infer.py --model-path models/artifacts/xgboost/xgb_model.pkl --data-path data/processed/features.parquet 2>&1 | Select-String "Predictions\|FAIL"
```

### Full Health Check (~ 2 min)
```powershell
# 1. Docker services
docker-compose ps

# 2. File integrity
Get-ChildItem data/raw/*.ndjson, models/artifacts -Recurse -Filter *.pkl

# 3. Feature generation
python scripts/replay.py --input data/raw/slice_10min.ndjson --output data/processed/health_check.parquet

# 4. Inference + latency
python models/infer.py --model-path models/artifacts/xgboost/xgb_model.pkl --data-path data/processed/health_check.parquet

# 5. Clean up test
Remove-Item data/processed/health_check.parquet
```

---

## COMMON COMMANDS QUICK REFERENCE

| Task | Command |
|------|---------|
| Start fresh | `docker-compose down -v && docker-compose up -d && python scripts/replay.py` |
| Test pipeline | `python scripts/replay.py && python models/infer.py --model-path models/artifacts/xgboost/xgb_model.pkl --data-path data/processed/features.parquet` |
| View models | `Get-ChildItem models/artifacts -Recurse -Filter *.pkl` |
| Check Kafka | `python scripts/kafka_consume_check.py --min 5` |
| Retrain | `python models/train.py` |
| MLflow UI | `mlflow ui --backend-store-uri file:./mlruns` |
| Check Docker logs | `docker-compose logs <service_name>` |
| Reset all | `docker-compose down -v && pip install --upgrade -r requirements.txt --force-reinstall && docker-compose up -d` |

---

## CONTACTS / ESCALATION

- **Infrastructure issues (Docker/Kafka):** Check Docker logs, restart services.
- **Model/inference issues:** Regenerate features via replay, retrain models.
- **Data pipeline issues:** Verify raw data, regenerate processed features.
- **Latency issues:** Profile code, reduce batch size, consider simpler model.

---

**Last Updated:** December 7, 2025
**Status:** Ready for deployment
