# Complete Team Demo Guide - 8 Minutes

## Overview

This guide shows how to create a comprehensive 8-minute demo video showcasing **all team members' work** from Weeks 4, 5, 6, and 7.

**Target Audience:** Professor and TAs  
**Duration:** 8 minutes  
**Format:** Screen recording with voiceover  
**Goal:** Demonstrate production-ready AI service

---

## 🎬 Complete Demo Structure (8 minutes)

### Minute 0-1: Introduction & System Startup (Week 4)
### Minute 1-3: Monitoring & Dashboards (Week 6) ⭐ YOU
### Minute 3-4: API & Predictions (Week 4)
### Minute 4-5: CI/CD & Testing (Week 5)
### Minute 5-6: Reliability & Rollback (Week 6) ⭐ YOU
### Minute 6-7: Documentation & Best Practices (All weeks)
### Minute 7-8: Summary & Q&A

---

## Detailed Demo Script

---

## 📍 Minute 0-1: Introduction & System Startup

**Presenter:** Team lead or Week 4 person

**Script:**
> "Hello! We're presenting our Crypto Volatility Detection System - a production-ready AI service that predicts Bitcoin volatility spikes in real-time. Our system uses FastAPI, Kafka, MLflow, Prometheus, and Grafana to deliver predictions with 45-millisecond latency and zero errors."

**What to show:**

1. **Show system architecture** (5 seconds):
   ```bash
   # Have architecture.md open
   cat docs/architecture.md
   # Or show the diagram from README
   ```

2. **Start the system** (30 seconds):
   ```bash
   cd crypto-volatility/docker
   docker compose up -d
   ```
   
   **While services starting, say:**
   > "Let me start all services with a single command. This launches six services: Kafka for message streaming, MLflow for model tracking, our FastAPI service, a Kafka consumer, Prometheus for metrics, and Grafana for dashboards."

3. **Show services running** (10 seconds):
   ```bash
   docker compose ps
   ```
   
   **Say:**
   > "All six services are now running and healthy."

4. **Quick health check** (15 seconds):
   ```bash
   curl http://localhost:8000/health
   ```
   
   **Say:**
   > "The API is healthy and our XGBoost model is loaded and ready."

**Timing: 0:00 - 1:00** ✅

---

## 📊 Minute 1-3: Monitoring & Dashboards (Week 6)

**Presenter:** Week 6 person (YOU!) ⭐

**Script:**
> "I'll now demonstrate the monitoring and observability features I built for Week 6."

### Part 1: Grafana Dashboard (60 seconds)

1. **Open Grafana** (5 seconds):
   ```bash
   open http://localhost:3000
   ```
   
   **Say:**
   > "Here's our Grafana monitoring dashboard showing four key metrics in real-time."

2. **Explain each panel** (30 seconds):
   - **Point to P50 Latency:**
   > "P50 latency - the median - is just 1.67 milliseconds."
   
   - **Point to P95 Latency:**
   > "P95 latency is 45 milliseconds - that means 95% of predictions complete in under 45ms. This is 18 times better than our 800-millisecond SLO target."
   
   - **Point to Error Rate:**
   > "Error rate is zero percent - perfect reliability."
   
   - **Point to Consumer Lag:**
   > "Consumer lag is zero seconds - our predictions use real-time data with no delay."

3. **Generate traffic and show updates** (25 seconds):
   ```bash
   # Have this ready in terminal
   for i in {1..20}; do
     curl -s -X POST http://localhost:8000/predict \
       -H "Content-Type: application/json" \
       -d '{"price": 50000.0}' > /dev/null
     sleep 0.5
   done
   ```
   
   **While running, say:**
   > "Let me generate some predictions. Watch the dashboard update in real-time - you can see the request rate increasing and latency staying consistently low."

### Part 2: Documentation (60 seconds)

4. **Show SLO Document** (15 seconds):
   ```bash
   open docs/slo.md
   ```
   
   **Quick scroll, say:**
   > "I created a comprehensive SLO document defining five service level objectives. Each SLO has a clear target, measurement methodology using Prometheus queries, and procedures for when thresholds are breached."

5. **Show Runbook** (15 seconds):
   ```bash
   open docs/runbook.md
   ```
   
   **Quick scroll to Table of Contents, say:**
   > "The operational runbook is a 700-line guide covering startup procedures, shutdown, health checks, and seven common troubleshooting scenarios with solutions."

6. **Show Drift Summary** (15 seconds):
   ```bash
   open docs/drift_summary.md
   ```
   
   **Say:**
   > "For drift detection, I used Evidently AI. We found 50% of features showed drift, which is expected for volatile cryptocurrency markets. Despite this drift, our model continues performing excellently, so no retraining is needed yet."

7. **Show Prometheus** (15 seconds):
   ```bash
   open http://localhost:9090
   ```
   
   **In the query box, type:**
   ```promql
   histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m]))
   ```
   
   **Say:**
   > "Here's Prometheus, the metrics database. I can query any metric - this shows our P95 latency over time."

**Timing: 1:00 - 3:00** ✅

---

## 🔄 Minute 5-6: Model Rollback Feature (Week 6)

**Presenter:** Week 6 person (YOU!) ⭐

**This is your second part - comes after Week 4 and Week 5 demos**

**Script:**
> "Let me demonstrate the model rollback feature I built for reliability."

**What to do:**

1. **Check current model** (10 seconds):
   ```bash
   curl http://localhost:8000/version | jq .
   ```
   
   **Say:**
   > "Currently we're using our XGBoost ML model. Let me show how we can quickly switch to a baseline model if issues arise."

2. **Show docker-compose config** (10 seconds):
   ```bash
   # Open in editor or show on screen
   open docker/compose.yaml
   ```
   
   **Scroll to API section, point to MODEL_VARIANT line, say:**
   > "Rollback is as simple as uncommenting this MODEL_VARIANT line and setting it to baseline."

3. **Explain without actually doing it** (30 seconds):
   
   **Say:**
   > "In a real emergency, I would run: MODEL_VARIANT equals baseline, docker compose up. This takes under 2 minutes and switches to our simple rule-based baseline model."
   
   > "The baseline model is less accurate but extremely reliable - it uses simple statistical thresholds instead of machine learning. This gives us a safety net if the ML model encounters data it hasn't seen before or if there's a bug."
   
   > "Once the issue is resolved, we can roll forward to the ML model just as easily by removing the environment variable."

4. **Show rollback guide** (10 seconds):
   ```bash
   open docs/model_rollback_guide.md
   ```
   
   **Quick scroll, say:**
   > "I documented the complete rollback procedure including when to use it, testing procedures, and recovery steps."

**Timing: 5:00 - 6:00** ✅

---

## 📋 Your Complete Checklist

### Before Demo

- [ ] Services running: `docker compose up -d`
- [ ] Grafana logged in: http://localhost:3000
- [ ] Dashboard has data (run traffic once before recording)
- [ ] Documents ready to show:
  - [ ] `docs/slo.md`
  - [ ] `docs/runbook.md`
  - [ ] `docs/drift_summary.md`
  - [ ] `docs/model_rollback_guide.md`
  - [ ] `docker/compose.yaml`
- [ ] Terminal commands ready
- [ ] Screen recording software ready

### During Demo

Your two sections:
- [ ] **Minutes 1-3:** Monitoring & Dashboards
- [ ] **Minutes 5-6:** Rollback Feature

### What to Emphasize

- [ ] Real-time monitoring working
- [ ] Performance exceeds targets (18x better!)
- [ ] Zero errors (perfect reliability)
- [ ] Comprehensive documentation
- [ ] Production-ready quality
- [ ] Safety mechanisms (rollback)

---

## 💡 Pro Tips

1. **Practice your 2 sections separately** (1-3 and 5-6)
2. **Have all windows/tabs pre-opened** before recording
3. **Use a second monitor** if available (commands on one, browser on other)
4. **Speak to a non-technical audience** - explain clearly
5. **Zoom in on important details** (metrics, numbers)
6. **Show enthusiasm!** You built something impressive!
7. **Time yourself** - use a timer to stay on track

---

## 🎯 Key Phrases to Use

**Your contributions:**
- "I implemented comprehensive monitoring..."
- "As you can see, our system exceeds all targets..."
- "I created extensive documentation including..."
- "The rollback feature provides a safety mechanism..."
- "All of this is production-ready and documented..."

**Emphasize impact:**
- "18 times better than the SLO target"
- "Zero errors - perfect reliability"
- "Real-time with no lag"
- "Production-grade monitoring"
- "Complete operational procedures"

---

## 📹 Recording Tips

### Screen Setup

**Recommended layout:**
```
┌─────────────────────────────────────────┐
│  Browser (Grafana/Docs)    70% width   │
│  - Main window                          │
│  - Multiple tabs ready                  │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  Terminal                  30% width    │
│  - Commands ready to run                │
│  - Clean prompt                         │
└─────────────────────────────────────────┘
```

### Audio Quality

- **Use headphones with mic** (better than laptop mic)
- **Record in quiet room**
- **Test audio first** (record 10 seconds and play back)
- **Speak clearly** at moderate pace
- **Avoid "um", "uh", "like"** - pause instead

### Video Quality

- **Close unnecessary apps** (Slack, email, etc.)
- **Hide dock/taskbar** if possible
- **Use clean background** (solid color desktop)
- **Good lighting** if showing face
- **Full screen browser** for Grafana

---

## 🎬 What Your Team Members Show

### Week 4 Team Member (Minute 0-1)
- System architecture
- Starting services
- API endpoints

### Week 5 Team Member (Minute 4-5)
- CI/CD pipeline
- GitHub Actions passing
- Load testing results
- Resilience features (retry, reconnect)

### YOU - Week 6 (Minutes 1-3 and 5-6)
- Grafana dashboards
- Prometheus metrics
- SLOs and documentation
- Drift detection
- Model rollback feature

### Week 7 Team Member (Minute 6-7)
- Handoff package
- Final documentation
- Production readiness
- Team collaboration

---

## ⏱️ Timing is Critical

**Your total time: 3 minutes (1-3 and 5-6)**

**Use a visible timer:**
- Set timer for 2:00 for each section
- Practice until you can hit exactly 2:00
- In final recording, slightly faster is OK (1:50 is fine)
- Don't go over! (Will cut into team time)

---

## 🎯 Success Criteria

Your demo is successful if:
- ✅ Shows all 4 Grafana panels clearly
- ✅ Demonstrates real-time metric updates
- ✅ Explains all key Week 6 features
- ✅ Shows documentation quality
- ✅ Demonstrates rollback capability
- ✅ Stays within 3-minute time limit
- ✅ Audio is clear and understandable
- ✅ Shows professionalism and preparation

---

## 📞 Questions to Anticipate

Your professor might wonder:

**Q: Why 50% drift but model still works?**  
**A:** "Crypto markets are inherently volatile, so drift is expected. Our model uses normalized features and was trained on diverse conditions, making it robust to this level of drift. Most importantly, performance metrics show the model continues working perfectly."

**Q: Why is rollback important?**  
**A:** "In production, if the ML model encounters unexpected data or has a bug, we need a quick safety mechanism. The baseline model provides reliable predictions while we fix the issue. It's like having a spare tire - less fancy but gets you home safely."

**Q: How often should you check drift?**  
**A:** "We recommend weekly drift reports. If drift share exceeds 75% or performance degrades, that triggers retraining."

---

## ✅ You're Ready!

With this guide, you can:
- ✅ Record your Week 6 portion (2 minutes split into 2 sections)
- ✅ Coordinate with team on full 8-minute video
- ✅ Show all Week 6 features professionally
- ✅ Answer potential questions

**Good luck with your demo! You've built something impressive!** 🚀

