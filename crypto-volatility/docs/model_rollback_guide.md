# Model Rollback Feature Guide

## Overview

The Model Rollback feature allows you to quickly switch from the Machine Learning model to a simple baseline model if issues arise. This provides a safety mechanism for production incidents.

**Use Cases:**
- ML model starts producing errors
- Model performance degrades suddenly
- High latency from complex model
- Emergency fallback during incidents

---

## How It Works

### Normal Operation (ML Model)
```
User Request → API → ML Model (XGBoost) → Prediction
```
- Uses trained XGBoost model
- Higher accuracy
- More complex predictions
- Latency: ~45ms (P95)

### Rollback Mode (Baseline Model)
```
User Request → API → Baseline Model (Simple Rules) → Prediction
```
- Uses simple statistical rules
- Lower accuracy but reliable
- Fast predictions
- Latency: ~5-10ms (P95)

---

## Quick Start

### Option 1: Environment Variable (Recommended)

**Activate Rollback:**
```bash
# Set environment variable before starting
export MODEL_VARIANT=baseline
docker compose up -d
```

**Or inline:**
```bash
MODEL_VARIANT=baseline docker compose up -d
```

---

### Option 2: Docker Compose File

**Edit `docker/compose.yaml`:**

```yaml
api:
  environment:
    MODEL_VARIANT: "baseline"  # Uncomment and set this line
```

```yaml
prediction-consumer:
  environment:
    MODEL_VARIANT: "baseline"  # Uncomment and set this line
```

**Then restart:**
```bash
docker compose down
docker compose up -d
```

---

### Option 3: Runtime Rollback (Hot Swap)

**For API only:**
```bash
# Stop API
docker compose stop api

# Start with baseline model
MODEL_VARIANT=baseline docker compose up -d api
```

**For both API and Consumer:**
```bash
# Stop services
docker compose stop api prediction-consumer

# Start with baseline model
MODEL_VARIANT=baseline docker compose up -d api prediction-consumer
```

---

## Verification

### Check Which Model is Loaded

**API:**
```bash
curl http://localhost:8000/version
```

**Expected Output (Rollback Mode):**
```json
{
  "api_version": "1.0.0",
  "model_version": "baseline-1764545017",
  "model_loaded_at": 1733450123.45,
  "python_version": "3.11.5"
}
```

Look for `"model_version"` starting with `"baseline-"`

---

**Check Logs:**
```bash
docker compose logs api | grep -i baseline
```

**Expected Log Output:**
```
🔄 ROLLBACK MODE: Loading baseline model...
✅ Loaded BASELINE model from: models/artifacts/baseline_model.pkl
⚠️  ROLLBACK MODE ACTIVE - Using simple baseline predictor
```

---

### Test Prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "price": 50000.0,
    "midprice": 50000.0,
    "return_1s": 0.001,
    "return_5s": 0.002,
    "volatility": 0.02
  }'
```

**Response should work normally:**
```json
{
  "prediction": 0,
  "probability": 0.15,
  "model_version": "baseline-1764545017",
  "timestamp": 1733450234.56
}
```

---

## Rollback Procedure (Step-by-Step)

### Scenario: ML Model Failing in Production

**1. Detect Issue**
- Grafana shows error rate > 5%
- Logs show model prediction errors
- API returning 500 errors

**2. Immediate Rollback**
```bash
cd crypto-volatility/docker

# Quick rollback (fastest)
docker compose stop api prediction-consumer
MODEL_VARIANT=baseline docker compose up -d api prediction-consumer
```

**3. Verify Rollback**
```bash
# Check version
curl http://localhost:8000/version | jq .

# Check health
curl http://localhost:8000/health | jq .

# Check logs
docker compose logs api | tail -20
```

**4. Monitor Metrics**
```bash
# Open Grafana
open http://localhost:3000

# Watch:
# - Error rate should drop to 0%
# - Latency should remain low
# - Predictions still working
```

**5. Investigate Root Cause**
```bash
# Check ML model logs
docker compose logs api | grep -i error

# Check for data drift
open reports/evidently/evidently_report_drift.html

# Review recent changes
git log --oneline -10
```

**6. Fix and Roll Forward**
Once issue is resolved:
```bash
# Remove MODEL_VARIANT to use ML model again
unset MODEL_VARIANT
docker compose down
docker compose up -d

# Or edit docker/compose.yaml and comment out MODEL_VARIANT line
```

**Duration: ~2 minutes from detection to rollback**

---

## Comparison: ML Model vs Baseline Model

| Aspect | ML Model (XGBoost) | Baseline Model |
|--------|-------------------|----------------|
| **Accuracy** | High (~80-90%) | Lower (~60-70%) |
| **Precision** | High | Medium |
| **Recall** | High | Medium |
| **Latency (P95)** | ~45ms | ~5-10ms |
| **Complexity** | High (tree ensemble) | Low (simple rules) |
| **Memory Usage** | ~50-100MB | ~1MB |
| **Reliability** | Can fail with bad data | Very reliable |
| **Training Required** | Yes (hours) | No (rules-based) |
| **Drift Sensitivity** | Medium | Low |

---

## Baseline Model Details

### How the Baseline Model Works

The baseline model uses simple statistical rules:

1. **Calculate volatility threshold**
   - Uses Z-score approach
   - Threshold: mean + 2 * std_dev

2. **Compare current volatility to threshold**
   - If volatility > threshold → Predict spike (1)
   - If volatility ≤ threshold → Predict normal (0)

3. **No complex features needed**
   - Only uses basic statistics
   - Fast computation
   - No ML inference

---

### Baseline Model Code

```python
class BaselineModel:
    """Simple rule-based baseline model."""
    
    def __init__(self, threshold_std=2.0):
        self.threshold_std = threshold_std
    
    def predict_proba(self, X):
        """Predict using simple threshold on volatility."""
        # Extract volatility feature
        volatility = X['volatility'].values
        
        # Calculate threshold
        mean_vol = volatility.mean()
        std_vol = volatility.std()
        threshold = mean_vol + self.threshold_std * std_vol
        
        # Predict
        predictions = (volatility > threshold).astype(int)
        
        # Convert to probabilities
        probabilities = np.zeros((len(X), 2))
        probabilities[:, 1] = predictions * 0.8  # Spike probability
        probabilities[:, 0] = 1 - probabilities[:, 1]  # Normal probability
        
        return probabilities
```

---

## When to Use Rollback

### ✅ Good Reasons to Rollback

1. **High Error Rate**
   - Error rate > 5% for 5 minutes
   - ML model throwing exceptions

2. **Severe Latency Issues**
   - P95 latency > 5 seconds
   - Model inference hanging

3. **Data Quality Issues**
   - Receiving malformed features
   - NaN/Inf values causing crashes

4. **Model Corruption**
   - Model file corrupted
   - Model won't load

5. **Emergency Maintenance**
   - Need to debug ML model
   - Testing new model version

---

### ❌ Bad Reasons to Rollback

1. **Slight accuracy drop**
   - Normal drift (< 10% accuracy change)
   - Should retrain, not rollback

2. **Minor latency increase**
   - Still under SLO (< 800ms)
   - Not worth accuracy trade-off

3. **Single prediction error**
   - One-off errors happen
   - Not systemic issue

4. **Panic reaction**
   - Always investigate first
   - Rollback is last resort

---

## Testing the Rollback Feature

### Test Script

Create `scripts/test_rollback.sh`:

```bash
#!/bin/bash
# Test model rollback feature

echo "=== Testing Model Rollback Feature ==="

# 1. Test normal ML model
echo -e "\n1. Testing ML Model (Normal Mode)"
docker compose down
docker compose up -d
sleep 30

VERSION=$(curl -s http://localhost:8000/version | jq -r .model_version)
echo "Current model: $VERSION"

if [[ "$VERSION" == "baseline-"* ]]; then
    echo "❌ ERROR: Should be using ML model, but using baseline"
    exit 1
else
    echo "✅ ML model is active"
fi

# Make test prediction
PREDICTION=$(curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"price": 50000.0}')
echo "Prediction response: $PREDICTION"

# 2. Test rollback to baseline
echo -e "\n2. Testing Rollback to Baseline Model"
docker compose down
MODEL_VARIANT=baseline docker compose up -d
sleep 30

VERSION=$(curl -s http://localhost:8000/version | jq -r .model_version)
echo "Current model: $VERSION"

if [[ "$VERSION" == "baseline-"* ]]; then
    echo "✅ Successfully rolled back to baseline model"
else
    echo "❌ ERROR: Rollback failed, still using ML model"
    exit 1
fi

# Make test prediction with baseline
PREDICTION=$(curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"price": 50000.0}')
echo "Prediction response: $PREDICTION"

# Check that prediction still works
if echo "$PREDICTION" | jq -e .prediction > /dev/null 2>&1; then
    echo "✅ Baseline model predictions working"
else
    echo "❌ ERROR: Baseline predictions not working"
    exit 1
fi

# 3. Roll forward to ML model
echo -e "\n3. Testing Roll Forward to ML Model"
docker compose down
docker compose up -d
sleep 30

VERSION=$(curl -s http://localhost:8000/version | jq -r .model_version)
echo "Current model: $VERSION"

if [[ "$VERSION" == "baseline-"* ]]; then
    echo "❌ ERROR: Should have rolled forward to ML model"
    exit 1
else
    echo "✅ Successfully rolled forward to ML model"
fi

echo -e "\n=== ✅ All Rollback Tests Passed! ==="
```

**Run test:**
```bash
chmod +x scripts/test_rollback.sh
./scripts/test_rollback.sh
```

---

### Manual Testing Checklist

- [ ] Start system with ML model
- [ ] Verify `/version` shows ML model
- [ ] Make prediction - should work
- [ ] Stop services
- [ ] Set `MODEL_VARIANT=baseline`
- [ ] Start services
- [ ] Verify `/version` shows `baseline-*`
- [ ] Check logs for "ROLLBACK MODE" message
- [ ] Make prediction - should still work
- [ ] Check Grafana - latency should be lower
- [ ] Unset `MODEL_VARIANT`
- [ ] Restart services
- [ ] Verify back to ML model

---

## Monitoring During Rollback

### Metrics to Watch

**In Grafana:**

1. **Error Rate**
   - Should drop to 0% after rollback
   - If still high, investigate baseline model

2. **Latency**
   - Should decrease (baseline is faster)
   - P95 should drop from ~45ms to ~5-10ms

3. **Prediction Distribution**
   - May change (baseline is simpler)
   - Expect fewer spike predictions

4. **Request Rate**
   - Should remain stable
   - Rollback doesn't affect throughput

---

### Alerts During Rollback

**Set up alerts for:**

1. **Rollback activated** (baseline model loaded)
   - Alert: INFO level
   - Action: Monitor closely, investigate root cause

2. **Baseline predictions different from ML**
   - Alert: WARNING level
   - Action: Compare prediction quality

3. **Rollback duration > 1 hour**
   - Alert: WARNING level
   - Action: Fix ML model or accept baseline as temporary solution

---

## Rollback History

Track rollback incidents in `docs/rollback_history.md`:

```markdown
# Rollback History

| Date | Duration | Reason | Resolved | Notes |
|------|----------|--------|----------|-------|
| 2024-12-05 | 10min | Testing | Yes | Week 6 feature test |
| TBD | - | - | - | - |
```

---

## Frequently Asked Questions

### Q: How long does rollback take?
**A:** ~1-2 minutes from decision to active baseline model.

### Q: Do I lose any data during rollback?
**A:** No, rollback only changes the model, not the data pipeline.

### Q: Can I rollback just the API or just the Consumer?
**A:** Yes, you can rollback either independently using the docker commands.

### Q: What happens to in-flight requests during rollback?
**A:** They may fail (5-10 second window), but will succeed once baseline is loaded.

### Q: Is the baseline model trained?
**A:** No, it's rule-based. No training required.

### Q: How do I know if rollback is working?
**A:** Check `/version` endpoint and logs for "ROLLBACK MODE" message.

### Q: Can I use a different baseline model?
**A:** Yes, replace `models/artifacts/baseline_model.pkl` with your preferred simple model.

### Q: Should I retrain the baseline model?
**A:** No need - it's rules-based. But you can adjust the threshold in the code.

---

## Best Practices

### 1. Test Rollback Regularly
```bash
# Monthly drill
./scripts/test_rollback.sh
```

### 2. Document Every Rollback
- When and why
- Duration
- Resolution

### 3. Monitor Closely After Rollback
- Watch Grafana for 30 minutes
- Ensure error rate stays low
- Check prediction quality

### 4. Fix Root Cause
- Don't stay on baseline forever
- Investigate ML model issue
- Fix and roll forward ASAP

### 5. Have Rollback Plan Ready
- Keep this guide accessible
- Practice the procedure
- Know the commands by heart

---

## Integration with Runbook

This rollback feature is documented in:
- **Runbook:** `docs/runbook.md` → Emergency Procedures → Procedure 2
- **SLO Document:** `docs/slo.md` → Actions if SLO is Breached

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-12-05 | Initial rollback feature implementation |

---

**Author:** Week 6 Team  
**Last Updated:** December 5, 2024  
**Review Cycle:** Monthly

