# Demo Video Guide - Week 6 Portion

## Your Part: Week 6 Monitoring & Operations (2 minutes)

As the Week 6 team member, you'll demonstrate the **monitoring, SLOs, drift detection, and rollback features** you built.

---

## 🎬 Your Demo Script (2 minutes)

### **Minute 1: Show Monitoring Dashboard (60 seconds)**

**What to say:**
> "For Week 6, I implemented comprehensive monitoring using Prometheus and Grafana. Let me show you our real-time dashboard."

**What to do:**
1. **Open Grafana** (should already be running):
   ```bash
   open http://localhost:3000
   ```

2. **Point to each panel** and explain:
   - **"Here's our P50 latency - the median response time is just 1.67 milliseconds"**
   - **"The P95 latency shows 95% of requests complete in under 45ms - that's 18 times better than our 800ms SLO target"**
   - **"Error rate is at 0% - we have perfect reliability"**
   - **"Consumer lag shows 0 seconds - our predictions are based on real-time data"**

3. **Generate some traffic** to show metrics updating:
   ```bash
   # Have this ready in a terminal
   for i in {1..20}; do
     curl -s -X POST http://localhost:8000/predict \
       -H "Content-Type: application/json" \
       -d '{"price": 50000.0}' > /dev/null
     sleep 0.5
   done
   ```

4. **While traffic runs, say:**
   > "Watch the dashboard update in real-time as predictions come in. You can see the latency staying low and request rate increasing."

---

### **Minute 2: Show Documentation & Rollback (60 seconds)**

**What to say:**
> "I also created comprehensive operational documentation including SLOs, a runbook, and a model rollback feature for reliability."

**What to do:**

1. **Quick scroll through SLO document** (3 seconds):
   ```bash
   open crypto-volatility/docs/slo.md
   ```
   - **Say:** "Our SLO document defines 5 service level objectives with clear targets and measurement queries."

2. **Show Runbook** (3 seconds):
   ```bash
   open crypto-volatility/docs/runbook.md
   ```
   - **Say:** "The runbook provides complete operational procedures - startup, shutdown, troubleshooting, and emergency responses."

3. **Show Drift Summary** (3 seconds):
   ```bash
   open crypto-volatility/docs/drift_summary.md
   ```
   - **Say:** "We detected 50% data drift using Evidently, which is expected for cryptocurrency markets. Despite this drift, our model continues performing excellently."

4. **Demonstrate Rollback Feature** (45 seconds):
   - **Say:** "Finally, we have a model rollback capability. If the ML model starts failing, we can switch to a simple baseline model in under 2 minutes."
   
   - **Show the version endpoint:**
   ```bash
   curl http://localhost:8000/version
   ```
   - **Point out:** "You can see we're currently using the ML model."
   
   - **Say:** "To activate rollback, we simply set an environment variable."
   
   - **Show the docker-compose file** (already have it open):
   ```bash
   # Just point to the screen showing docker/compose.yaml
   # Show the commented line:
   # MODEL_VARIANT: "baseline"
   ```
   
   - **Say:** "By uncommenting this line and restarting, we switch to the baseline model. This provides a safety mechanism for production incidents."

5. **Wrap up your section:**
   > "All of Week 6's monitoring and operational excellence features are now production-ready and documented."

---

## 📋 Pre-Demo Checklist (Your Part)

Before recording, make sure:

- [ ] All services running: `docker compose ps`
- [ ] Grafana accessible: http://localhost:3000 (logged in as admin/admin)
- [ ] Grafana dashboard has some data (run traffic generation once)
- [ ] Documents are open in separate tabs/windows:
  - [ ] `docs/slo.md`
  - [ ] `docs/runbook.md`
  - [ ] `docs/drift_summary.md`
- [ ] Have terminal ready with commands
- [ ] Screen is clean (close unnecessary windows)
- [ ] Set time range in Grafana to "Last 6 hours" or "Last 1 hour"

---

## 🎯 Key Points to Emphasize

**Your Achievements:**
1. ✅ **14 Prometheus metrics** tracking system health
2. ✅ **Real-time Grafana dashboards** with 4 key panels
3. ✅ **Performance exceeds all targets** (18x better latency!)
4. ✅ **Complete operational documentation** (2000+ lines)
5. ✅ **Model rollback feature** for reliability
6. ✅ **Drift detection** with Evidently

**What Makes It Production-Ready:**
- Real-time monitoring and alerting
- Defined SLOs with measurement methodology
- Complete troubleshooting procedures
- Safety mechanisms (rollback)
- Professional documentation

---

## 🎤 Practice Script (Exactly 2 minutes)

**0:00 - 0:05** "For Week 6, I implemented comprehensive monitoring using Prometheus and Grafana."

**0:05 - 0:10** [Open Grafana] "Here's our real-time monitoring dashboard."

**0:10 - 0:30** [Point to panels] "P50 latency is 1.67ms, P95 is 45ms - 18 times better than our 800ms target. Error rate is 0%, and consumer lag is 0 seconds showing real-time processing."

**0:30 - 0:40** [Run traffic generation] "Let me generate some traffic to show the dashboard updating in real-time."

**0:40 - 0:50** [Watch metrics update] "You can see the metrics updating live as predictions come in."

**0:50 - 1:00** "I also created comprehensive documentation including SLOs, a runbook, and drift detection."

**1:00 - 1:10** [Quick scroll through docs] "The SLO document defines 5 objectives. The runbook covers all operational procedures."

**1:10 - 1:20** [Show drift summary] "We detected 50% drift which is expected for crypto, but the model still performs excellently."

**1:20 - 1:40** [Show version endpoint] "We also have a model rollback feature. Currently using the ML model."

**1:40 - 1:55** [Show docker-compose] "By setting this environment variable, we can switch to a baseline model in under 2 minutes for reliability."

**1:55 - 2:00** "All Week 6 monitoring and operational features are production-ready."

**Total: Exactly 2 minutes** ⏱️

---

## 💡 Tips for Recording

1. **Practice once** before recording
2. **Speak slowly and clearly** (non-engineers need to understand)
3. **Point with cursor** to what you're explaining
4. **Zoom in** on important parts (metrics, thresholds)
5. **Keep energy up** - be enthusiastic!
6. **If you make a small mistake**, keep going (don't restart)
7. **Have water nearby** - 2 minutes of talking is longer than you think!

---

## 🎥 Screen Recording Setup

**Recommended Tools:**
- **Mac:** QuickTime (built-in) or Loom
- **Resolution:** 1920x1080 (full HD)
- **Audio:** Use good microphone or headphones with mic

**What to Show on Screen:**
- Browser with Grafana dashboard (main window)
- Terminal window (smaller, on the side)
- Documents (switch to as needed)

**What NOT to show:**
- Personal information
- Unnecessary tabs or windows
- Messy desktop

---

## 🚀 Ready to Record?

Once you're comfortable with this script, you can record your 2-minute Week 6 portion!

---

**Want me to create the FULL TEAM DEMO GUIDE now?** That will show how to integrate all team members' parts into an 8-minute video! 🎬

