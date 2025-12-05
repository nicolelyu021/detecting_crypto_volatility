# Demo Commands Reference - Complete Team

## 🎬 Pre-Recording Setup (15 minutes before demo)

Run these commands **before** you start recording:

```bash
# 1. Navigate to project
cd ~/Documents/CMU/94-879\ Operationalizing\ AI_Rao/Crypto\ Volatility\ Analysis/crypto-volatility

# 2. Clean slate (optional but recommended)
cd docker
docker compose down -v

# 3. Start all services
docker compose up -d

# 4. Wait for services to initialize
sleep 60

# 5. Verify all healthy
docker compose ps
# All should show "Up" and "healthy"

# 6. Make a few test predictions to populate dashboards
cd ..
for i in {1..10}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"price": 50000.0}' > /dev/null
done

# 7. Open required tabs in browser
open http://localhost:3000  # Grafana
open http://localhost:9090  # Prometheus
open http://localhost:8000/docs  # API docs
open http://localhost:5001  # MLflow

# 8. Login to Grafana (admin/admin)
# 9. Open dashboard: "Crypto Volatility Monitoring"
# 10. Set time range to "Last 6 hours"

# 11. Pre-open all documents you'll reference
open docs/slo.md
open docs/runbook.md
open docs/drift_summary.md
open docs/model_rollback_guide.md
open docker/compose.yaml

# 12. Ready to record!
```

---

## 📍 Minute 0-1: Introduction & Startup (Week 4)

### Commands:

```bash
# Already running from pre-setup, just show:
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/version
```

### Script:
- Introduce team and project
- Show architecture diagram
- Show services running
- Verify API health

---

## 📊 Minute 1-3: Monitoring Dashboard (Week 6) ⭐

### Commands:

```bash
# Grafana should already be open at http://localhost:3000

# Generate traffic while talking:
for i in {1..20}; do
  curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d '{"price": 50000.0}' > /dev/null
  sleep 0.5
done

# Open Prometheus
open http://localhost:9090

# Run sample query in Prometheus:
histogram_quantile(0.95, rate(volatility_prediction_latency_seconds_bucket[5m]))
```

### What to Show:
1. Grafana dashboard with 4 panels
2. Metrics updating in real-time
3. Quick scroll through docs (SLO, runbook, drift summary)
4. Prometheus query example

### Script:
- Explain monitoring implementation
- Walk through each dashboard panel
- Show real-time updates
- Reference documentation

---

## 🔌 Minute 3-4: API & Predictions (Week 4)

### Commands:

```bash
# Show API documentation
open http://localhost:8000/docs

# Make a prediction (show in terminal)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "price": 50000.0,
    "midprice": 50000.0,
    "return_1s": 0.001,
    "return_5s": 0.002,
    "return_30s": 0.005,
    "return_60s": 0.01,
    "volatility": 0.02,
    "trade_intensity": 10.0,
    "spread_abs": 1.0,
    "spread_rel": 0.0001,
    "order_book_imbalance": 0.05
  }'

# Show response (pretty print)
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"price": 50000.0}' | jq .

# Show other endpoints
curl http://localhost:8000/health | jq .
curl http://localhost:8000/version | jq .
```

### What to Show:
1. FastAPI interactive docs (Swagger UI)
2. Make live prediction
3. Show JSON response with prediction and probability
4. Verify all endpoints working

### Script:
- Explain API architecture
- Demonstrate prediction endpoint
- Show model returning results
- Highlight speed and reliability

---

## 🧪 Minute 4-5: CI/CD & Testing (Week 5)

### Commands:

```bash
# Show GitHub Actions (in browser)
open https://github.com/nicolelyu021/detecting_crypto_volatility/actions

# Show load test results (if file exists)
cat LATENCY_REPORT.md

# Or run quick load test
python scripts/load_test.py --url http://localhost:8000 --requests 50

# Show test results
cat load_test_report.json | jq .
```

### What to Show:
1. GitHub Actions CI/CD pipeline (passing)
2. Load test results
3. Latency statistics
4. Code quality tools (Black, Ruff)

### Script:
- Explain CI/CD implementation
- Show passing tests
- Demonstrate load handling
- Highlight resilience features

---

## 🔄 Minute 5-6: Rollback & Reliability (Week 6) ⭐

### Commands:

```bash
# Check current model
curl http://localhost:8000/version | jq .model_version

# Show docker-compose config
# (Should already be open, just point to it)

# Show rollback guide
open docs/model_rollback_guide.md
```

### What to Show:
1. Current model version
2. Docker-compose MODEL_VARIANT configuration
3. Explain rollback procedure
4. Show documentation

### Script:
- Explain why rollback is important
- Show how to activate (environment variable)
- Explain baseline vs ML model trade-offs
- Reference rollback guide

**Note:** Don't actually perform rollback during demo (takes 2 minutes) - just explain it!

---

## 📚 Minute 6-7: Documentation & Best Practices

### Commands:

```bash
# Show README
open README.md

# Show documentation folder
ls -lh docs/

# Quick scroll through key docs
open docs/architecture.md
open docs/team_charter.md
open docs/selection_rationale.md

# Show reports
open reports/evidently/evidently_report_drift.html
```

### What to Show:
1. Complete documentation structure
2. README with setup instructions
3. Architecture documentation
4. Team charter and rationale
5. Reports (Evidently, evaluation)

### Script:
- Highlight documentation completeness
- Show professional quality
- Reference operational readiness
- Team collaboration

---

## 🎯 Minute 7-8: Summary & Wrap-Up

### Commands:

```bash
# Show final metrics in Grafana (should still be open)
# Point to dashboard

# Show GitHub repo
open https://github.com/nicolelyu021/detecting_crypto_volatility/tree/week6
```

### What to Say:

**Performance Summary:**
> "Our system delivers production-ready performance: 45-millisecond P95 latency - 18 times better than the 800ms target. Zero errors with 100% availability. Real-time processing with no consumer lag."

**Features Summary:**
> "We've built a complete MLOps pipeline with real-time streaming, comprehensive monitoring, automated drift detection, and reliability features like model rollback."

**Production Readiness:**
> "This system is production-ready with defined SLOs, complete operational documentation, CI/CD pipeline, and proven performance under load."

**Team Collaboration:**
> "Each team member contributed: Week 4 built the foundation, Week 5 added reliability and testing, Week 6 added monitoring and operations, and Week 7 prepared the handoff."

**Closing:**
> "Thank you for watching! The complete code and documentation are available on our GitHub repository. Questions?"

---

## 🎥 Recording Logistics

### Tools

**Screen Recording:**
- **Mac:** QuickTime Player (File → New Screen Recording)
- **Alternative:** Loom (https://loom.com) - free, easy to share
- **Alternative:** OBS Studio (free, professional)

**Video Settings:**
- **Resolution:** 1920x1080 (1080p)
- **Frame Rate:** 30 fps
- **Format:** MP4 (H.264)
- **Audio:** 44.1kHz or 48kHz

### Upload to YouTube

1. **Create unlisted video** (not public, not private)
2. **Title:** "CMU 94-879 - Crypto Volatility Detection - Team [Your Team Name]"
3. **Description:**
   ```
   Real-Time Crypto Volatility Detection System
   CMU 94-879 - Operationalizing AI
   
   Features:
   - Real-time predictions with 45ms P95 latency
   - Comprehensive Prometheus + Grafana monitoring
   - Model rollback capability
   - Drift detection with Evidently
   - Complete operational documentation
   
   GitHub: https://github.com/nicolelyu021/detecting_crypto_volatility
   Branch: week6
   Tag: week6-complete
   ```
4. **Visibility:** Unlisted
5. **Get shareable link**

---

## 📋 Team Coordination

### Before Recording

**Team Meeting (30 minutes):**
1. Decide who presents what (follow timing guide)
2. Practice transitions between presenters
3. Agree on who starts services (Week 4 person)
4. Test all commands work
5. Do a dry run (record practice video)

**Roles:**
- **Week 4:** Introduction, startup, API demo (2 min)
- **Week 5:** CI/CD, testing, resilience (1 min)
- **Week 6 (YOU):** Monitoring, docs, rollback (3 min) ⭐
- **Week 7:** Handoff, summary (2 min)

### During Recording

**Option 1: Single Recording**
- One person screen shares
- Team members take turns talking
- Smooth transitions: "Now [Name] will show Week 6..."

**Option 2: Individual Recordings**
- Each person records their section
- Video editor combines clips
- Requires video editing software

**Recommended: Option 1** (simpler, more natural)

---

## 🔧 Troubleshooting During Demo

### If Something Fails

**API not responding:**
```bash
docker compose restart api
sleep 20
```

**Grafana blank:**
```bash
# Generate quick traffic
for i in {1..5}; do curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"price": 50000.0}' > /dev/null; done
# Refresh Grafana
```

**Services down:**
```bash
docker compose down
docker compose up -d
sleep 60
# Continue demo
```

**Keep calm and troubleshoot!** Or use pre-recorded segments.

---

## 💡 Pro Tips from Real Demos

1. **Record in the morning** - you're more alert
2. **Practice 2-3 times** minimum
3. **Have water nearby** - you'll need it
4. **Close Slack, email, notifications** - avoid distractions
5. **Test recording first** - do a 30-second test
6. **Use bathroom before!** - 8 minutes is long
7. **Smile!** - enthusiasm shows in your voice
8. **Pause between sections** - makes editing easier
9. **If you mess up badly** - stop and restart (better than a bad video)
10. **Review before uploading** - watch it once to check quality

---

## ✅ Final Checklist Before Recording

- [ ] Services running and healthy (60+ seconds uptime)
- [ ] Grafana dashboard showing data
- [ ] All browser tabs open
- [ ] All documents ready
- [ ] Terminal commands prepared
- [ ] Screen recording software tested
- [ ] Audio tested (record and playback)
- [ ] Notifications disabled
- [ ] Clean screen (no clutter)
- [ ] Timer ready
- [ ] Script memorized (or notes nearby)
- [ ] Water available
- [ ] Team coordinated on timing

---

## 🎬 Ready to Record!

With these guides, your team has everything needed:
- ✅ Complete demo script (8 minutes)
- ✅ All commands ready to copy-paste
- ✅ Your Week 6 portions clearly defined (minutes 1-3 and 5-6)
- ✅ Timing breakdown
- ✅ Troubleshooting tips

**You've got this! Your Week 6 work is impressive and ready to showcase!** 🌟

---

**Good luck with the recording!** 🎥🚀

