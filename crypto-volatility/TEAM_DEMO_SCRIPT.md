# Complete Team Demo Script - 8 Minutes
## 4-Part Presentation: Startup, Predictions, Failure Recovery, and Rollback

---

## 🎯 Overview

**Total Duration:** 8 minutes  
**Number of Presenters:** 3  
**Topics Covered:**
- Part 1: System Startup (Person 1) - 1.5 minutes
- Part 2: Predictions & API (Person 1 continues) - 1.5 minutes
- Part 3: Failure Recovery & Resilience (Person 2) - 2.5 minutes
- Part 4: Model Rollback (Person 3) - 2.5 minutes

---

## 📋 Pre-Demo Setup Checklist

### Before Recording (All Presenters)

- [ ] Stop any running Docker containers: `docker compose -f docker/compose.yaml down`
- [ ] Terminal windows ready (at least 3-4 tabs)
- [ ] Code editor open with key files
- [ ] All commands pre-typed in terminals (ready to run)
- [ ] Screen recording software configured
- [ ] Audio tested (microphone working)

### Files to Have Open

- [ ] `docker/compose.yaml` (for Person 1 & 3)
- [ ] `scripts/ws_ingest.py` (for Person 2)
- [ ] `scripts/prediction_consumer.py` (for Person 2)
- [ ] `docs/model_rollback_guide.md` (for Person 3)

---

## 🚀 Part 1: System Startup (Person 1)
**Duration:** 1.5 minutes  
**Timing:** 0:00 - 1:30

### Setup (Before Recording)
- [ ] All Docker containers stopped
- [ ] Terminal in `crypto-volatility/docker` directory
- [ ] Docker compose file visible

---

### Script for Person 1

#### Introduction (0:00 - 0:10)
> "Hello! I'm [Name]. I'll demonstrate our Crypto Volatility Detection System - a production-ready AI service that predicts Bitcoin volatility spikes in real-time with 45-millisecond latency."

#### Start All Services (0:10 - 0:50)

**Action:** Run:
```bash
cd crypto-volatility/docker
docker compose up -d
```

**Say while services start:**
> "Starting all services is simple - one command launches six services: Kafka, MLflow, FastAPI, prediction consumer, Prometheus, and Grafana."

**Action:** While waiting (~20 seconds), open `docker/compose.yaml` briefly

> "The Docker Compose configuration defines all services with health checks and proper dependencies. Services start automatically in the correct order."

#### Verify Services Running (0:50 - 1:15)

**Action:** Check services:
```bash
docker compose ps
```

**Say:**
> "All services are running and healthy. Health checks ensure services are ready, not just started."

#### Health Check (1:15 - 1:30)

**Action:** Verify API:
```bash
curl http://localhost:8000/health
```

**Say:**
> "The health check confirms our XGBoost model is loaded and ready. System is fully operational."

**Transition:**
> "Now I'll show predictions in action."

---

## 📊 Part 2: Predictions & API (Person 1 continues)
**Duration:** 1.5 minutes  
**Timing:** 1:30 - 3:00

### Setup (Before Recording)
- [ ] Services running from Part 1
- [ ] Terminal ready with curl commands
- [ ] Sample prediction payload ready

---

### Script for Person 1 (Continued)

#### Check Version (0:00 - 0:15)
**Action:**
```bash
curl http://localhost:8000/version | jq .
```

**Say:**
> "We're using our XGBoost ML model. Let me make a prediction."

#### Make Predictions (0:15 - 1:15)

**Action:** Make prediction:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "price": 50000.0,
    "midprice": 50000.5,
    "return_1s": 0.0001,
    "return_5s": 0.0005,
    "return_30s": 0.002,
    "volatility": 0.001,
    "trade_intensity": 2.5
  }' | jq .
```

**Say:**
> "I'm sending market data - price, returns, volatility. The API returns prediction, probability, model version, and timestamp. Response time: under 45 milliseconds."

**Action:** Make another prediction quickly:
```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"price": 50000.0, "return_1s": 0.01, "volatility": 0.05}' | jq .prediction, .probability
```

**Say:**
> "High volatility scenario - the model predicts a spike with high probability. Our system handles real-time market data consistently."

#### Quick Summary (1:15 - 1:30)
**Say:**
> "Predictions work perfectly with sub-50ms latency. The system tracks all predictions in Prometheus metrics for monitoring."

**Transition:**
> "Now [Person 2] will show how our system handles failures automatically."

---

## 🔄 Part 3: Failure Recovery & Resilience (Person 2)
**Duration:** 2.5 minutes  
**Timing:** 3:00 - 5:30

### Setup (Before Recording)
- [ ] Services running
- [ ] Code files open (`ws_ingest.py`, `prediction_consumer.py`)
- [ ] Terminal ready

---

### Script for Person 2

#### Introduction (0:00 - 0:15)
> "Hi, I'm [Name]. I'll demonstrate our resilience features. Production systems must handle failures automatically - network interruptions, Kafka restarts, WebSocket disconnections."

#### Show Kafka Producer Resilience (0:15 - 0:55)

**Action:** Open `scripts/ws_ingest.py`, scroll to Kafka producer config (around line 80)

**Say:**
> "First, Kafka producer resilience. I configured retries increased from 3 to 10 attempts, exponential backoff from 1 to 10 seconds, and socket keepalive for persistent connections."

**Action:** Point to configuration lines

> "If Kafka goes down, messages queue and automatically retry when it recovers - zero data loss."

#### Show Kafka Consumer Resilience (0:55 - 1:25)

**Action:** Open `scripts/prediction_consumer.py`, scroll to consumer config

**Say:**
> "Consumer side: automatic reconnection on transport errors, exponential backoff, and graceful offset commits on shutdown. If connection drops, consumer automatically reconnects with increasing delays."

#### Show WebSocket Reconnection (1:25 - 1:55)

**Action:** Scroll to WebSocket reconnection code in `ws_ingest.py` (around line 240)

**Say:**
> "WebSocket reconnection uses exponential backoff: 5 seconds, doubling up to 60 seconds max. Prevents overwhelming the Coinbase API while still recovering automatically. Includes heartbeat monitoring to detect dead connections quickly."

#### Explain Benefits (1:55 - 2:30)

**Say:**
> "Together, these features ensure 24/7 reliability. Network failures, service restarts, temporary outages - the system recovers automatically without manual intervention or data loss. Essential for production real-time systems."

**Action:** Optionally show logs (quick):
```bash
docker logs volatility-prediction-consumer | tail -5
```

**Say:**
> "Logs show automatic reconnection attempts. In production, this means zero downtime during infrastructure issues."

**Transition:**
> "Now [Person 3] will demonstrate our model rollback feature."

---

## 🔙 Part 4: Model Rollback (Person 3)
**Duration:** 2.5 minutes  
**Timing:** 5:30 - 8:00

### Setup (Before Recording)
- [ ] Services running
- [ ] Docker compose file open
- [ ] Rollback documentation ready

---

### Script for Person 3

#### Introduction (0:00 - 0:10)
> "Hi, I'm [Name]. I'll demonstrate our model rollback feature - a critical safety mechanism for production ML systems."

#### Check Current Model (0:10 - 0:25)

**Action:**
```bash
curl http://localhost:8000/version | jq .
```

**Say:**
> "Currently using our XGBoost ML model. Let me show how we quickly switch to a baseline model if issues arise."

#### Show Rollback Configuration (0:25 - 0:55)

**Action:** Open `docker/compose.yaml`, scroll to API service section (around line 70)

**Say:**
> "Rollback is simple. This MODEL_VARIANT environment variable - when set to 'baseline', switches to our backup model. Just uncomment this line and restart."

**Action:** Point to MODEL_VARIANT line

> "One environment variable change, under 2 minutes to rollback."

#### Explain Baseline Model (0:55 - 1:25)

**Say:**
> "The baseline model uses simple statistical thresholds instead of machine learning. Less accurate but extremely reliable - always works. It's like a spare tire - gets you home safely."

#### Demonstrate Rollback Process (1:25 - 2:10)

**Say:**
> "In an emergency: stop services, set MODEL_VARIANT to baseline, restart. Takes under 2 minutes with zero downtime."

**Action:** Show commands (explain, don't execute):
```bash
cd crypto-volatility/docker
docker compose down
# Edit compose.yaml: uncomment MODEL_VARIANT: "baseline"
docker compose up -d
```

**Say:**
> "Services restart using baseline model. API continues serving predictions - zero downtime, just using the simpler model."

#### Show Rollback Documentation (2:10 - 2:35)

**Action:** Quick scroll through `docs/model_rollback_guide.md`

**Say:**
> "Complete rollback procedure is documented - when to use it, testing steps, recovery procedures. Anyone on the team can execute a rollback quickly."

#### Summary & Roll Forward (2:35 - 2:50)

**Say:**
> "Rolling forward is just as easy - remove MODEL_VARIANT and restart. This rollback feature ensures we can maintain service even when the ML model has issues."

**Final Transition:**
> "That concludes our demo. We've shown system startup, real-time predictions, automatic failure recovery, and model rollback. Our system is production-ready with comprehensive reliability features."

---

## ⏱️ Timing Breakdown

| Part | Presenter | Duration | Start | End | Key Actions |
|------|-----------|----------|-------|-----|-------------|
| **Part 1: Startup** | Person 1 | 1.5 min | 0:00 | 1:30 | Start services, verify health |
| **Part 2: Predictions** | Person 1 | 1.5 min | 1:30 | 3:00 | Make predictions, show API |
| **Part 3: Failure Recovery** | Person 2 | 2.5 min | 3:00 | 5:30 | Show resilience code |
| **Part 4: Rollback** | Person 3 | 2.5 min | 5:30 | 8:00 | Demonstrate rollback |
| **Total** | | **8.0 min** | | | |

---

## 📝 Quick Checklist

### Before Recording

- [ ] All containers stopped
- [ ] Terminal tabs ready
- [ ] Code files open
- [ ] Commands pre-typed
- [ ] Audio tested

### During Recording

**Person 1:**
- [ ] Start services (1 command)
- [ ] Verify running
- [ ] Health check
- [ ] Make 2 predictions

**Person 2:**
- [ ] Show producer resilience code
- [ ] Show consumer resilience code
- [ ] Show WebSocket reconnection
- [ ] Explain benefits

**Person 3:**
- [ ] Check current model
- [ ] Show rollback config
- [ ] Explain baseline model
- [ ] Show rollback process
- [ ] Show documentation

---

## 💡 Key Phrases

### Person 1
- "Production-ready AI service"
- "One command starts everything"
- "Under 45 milliseconds"
- "Real-time market data"

### Person 2
- "Automatic recovery from failures"
- "Zero data loss"
- "24/7 reliability"
- "Zero manual intervention"

### Person 3
- "Critical safety mechanism"
- "Under 2 minutes to rollback"
- "Zero downtime"
- "Production-ready reliability"

---

## 🎯 Success Criteria

- ✅ All services start with one command
- ✅ Predictions work with fast latency
- ✅ Resilience features explained clearly
- ✅ Rollback capability demonstrated
- ✅ Exactly 8 minutes total
- ✅ Smooth transitions between presenters
- ✅ Clear audio and visible demonstrations

---

## 🚨 Troubleshooting

**Services slow to start?**
- Can explain startup process while waiting
- Health checks catch issues early

**Predictions fail?**
- Check health endpoint first
- Show error handling in action

**Code files won't open?**
- Describe features verbally
- Use documentation as backup

---

## 📹 Recording Tips

- **Screen:** Browser/editor (70%) + Terminal (30%)
- **Audio:** Headphones with mic, quiet room
- **Practice:** Time each section separately
- **Handoffs:** Practice transitions between presenters

---

## ✅ Ready!

With this script, your team can record a professional 8-minute demo showing:
- ✅ Easy system startup
- ✅ Real-time predictions
- ✅ Automatic failure recovery
- ✅ Model rollback capability

**Good luck with your demo!** 🚀
