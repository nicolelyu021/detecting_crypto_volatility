# Week 5 Demo Script - CI/CD, Testing & Resilience
## 3-Person Presentation Script (~8 minutes total)

---

## 🎯 Overview

**Total Duration:** ~8 minutes  
**Number of Presenters:** 3  
**Topics Covered:**
- Part 1: CI/CD Pipeline (Person 1) - ~2.5 minutes
- Part 2: Load Testing & Performance (Person 2) - ~2.5 minutes  
- Part 3: Resilience & Error Handling (Person 3) - ~3 minutes

---

## 📋 Part 1: CI/CD Pipeline (Person 1)
**Duration:** ~2.5 minutes  
**Presenter:** Person 1

### Setup (Before Recording)
- [ ] GitHub repository open in browser
- [ ] GitHub Actions tab ready
- [ ] Recent CI run visible (green checkmarks)
- [ ] Terminal ready with commands
- [ ] Code editor open with `.github/workflows/ci.yml`

---

### Script for Person 1

#### Introduction (0:00 - 0:15)
> "Hi, I'm [Name], and I'll be demonstrating the CI/CD pipeline we built for Week 5. Our continuous integration setup ensures code quality and reliability before any code reaches production."

#### Show GitHub Actions (0:15 - 0:45)

**Action:** Navigate to GitHub repository → Actions tab

> "Let me show you our GitHub Actions workflow. Here you can see our CI pipeline running automatically on every push and pull request. The pipeline consists of two main jobs running in parallel."

**Action:** Click on a recent successful workflow run

> "This pipeline runs on three branches: main, week4, and week5. You can see both jobs passed - the green checkmarks indicate success."

**Action:** Expand the workflow run to show both jobs:
- `lint-and-format` job
- `integration-test` job

> "Our pipeline has two parallel jobs: First, a linting and formatting job that checks code style. Second, an integration test job that validates all API endpoints work correctly."

#### Explain CI Workflow File (0:45 - 1:15)

**Action:** Open `.github/workflows/ci.yml` in code editor

> "Let me show you the workflow configuration. The pipeline triggers on push and pull requests, and can also be manually triggered. This ensures every code change goes through the same quality gates."

**Action:** Scroll through the file, highlighting key sections

**Say while scrolling:**

> "Here's the lint-and-format job. It installs Black for code formatting and Ruff for linting, then checks our entire codebase against style standards."

> "And here's the integration-test job. It sets up Python, installs all dependencies, and runs our comprehensive test suite using pytest."

#### Show Linting Tools (1:15 - 1:45)

**Action:** Open terminal and run:
```bash
cd crypto-volatility
black --check --diff .
```

**Say:**
> "Let me demonstrate the linting tools locally. Black ensures all Python code follows consistent formatting. The `--check` flag verifies formatting without modifying files."

**Action:** Run Ruff:
```bash
cd crypto-volatility
ruff check .
```

**Say:**
> "Ruff is a fast linter that catches code quality issues, unused imports, and potential bugs. Both tools run automatically in our CI pipeline, preventing poorly formatted code from being merged."

#### Show Integration Tests (1:45 - 2:15)

**Action:** Open `tests/test_api_integration.py` in editor, scroll through it

**Say:**
> "Our integration tests cover all critical API endpoints. We test the health endpoint, version endpoint, prediction endpoint, and metrics endpoint. These tests ensure the API works correctly in all scenarios."

**Action:** Run tests in terminal:
```bash
cd crypto-volatility
python -m pytest tests/ -v
```

**Say:**
> "The tests run automatically in CI. You can see all tests passing - this gives us confidence that our code changes don't break existing functionality."

#### Show Test Results (2:15 - 2:30)

**Action:** Show the pytest output with all passing tests

**Say:**
> "All tests pass locally, just like they do in CI. This automated testing catches issues early, before they reach production. Our CI pipeline is a critical part of maintaining code quality and system reliability."

**Transition:**
> "Now let me hand it over to [Person 2] who will demonstrate our load testing and performance validation."

---

## 📊 Part 2: Load Testing & Performance (Person 2)
**Duration:** ~2.5 minutes  
**Presenter:** Person 2

### Setup (Before Recording)
- [ ] API running (`docker compose up -d`)
- [ ] Terminal ready with load test script
- [ ] Load test report file visible (previous run)
- [ ] API health check confirmed working
- [ ] Browser ready to show results

---

### Script for Person 2

#### Introduction (0:00 - 0:15)
> "Hi, I'm [Name], and I'll demonstrate our load testing framework and performance validation. We built a comprehensive load testing tool to ensure our API can handle production-level traffic."

#### Show Load Test Script (0:15 - 0:45)

**Action:** Open `scripts/load_test.py` in code editor

**Say:**
> "This is our load testing script. It sends concurrent requests to our prediction API and measures detailed performance metrics. The script uses async/await to simulate realistic burst traffic patterns."

**Action:** Scroll through key parts of the script

**Say:**
> "By default, it sends 100 concurrent requests, which simulates a sudden spike in traffic. This tests how our system handles load under stress."

#### Verify API is Running (0:45 - 1:00)

**Action:** Run health check:
```bash
curl http://localhost:8000/health
```

**Say:**
> "First, let me verify the API is running and healthy. Perfect - the API is ready to handle requests."

#### Run Load Test (1:00 - 1:45)

**Action:** Run the load test:
```bash
cd crypto-volatility
python scripts/load_test.py --url http://localhost:8000 --requests 100
```

**Say while it's running:**
> "Now I'll run the load test. This sends 100 concurrent requests and measures latency for each one. Watch the terminal - it will show detailed statistics when complete."

**Wait for test to complete, then say:**
> "Excellent! The load test completed successfully. Let me break down these results."

#### Explain Load Test Results (1:45 - 2:15)

**Action:** Point to the terminal output showing results

**Say:**
> "Here are the key metrics: First, our success rate is 100 percent - every single request succeeded, which demonstrates perfect reliability."

> "Looking at latency: Our mean latency is under 50 milliseconds, and the P95 latency - meaning 95 percent of requests - completes in under 45 milliseconds. This is exceptional performance for a machine learning prediction service."

> "The system processed over 100 requests per second, which shows we can handle high traffic loads efficiently."

#### Show Load Test Report File (2:15 - 2:30)

**Action:** Open or show `load_test_report.json` file

**Say:**
> "The script also generates a detailed JSON report with all metrics. This report includes mean, median, P95, P99 latencies, success rates, and error details. We can use this data for performance monitoring and capacity planning."

**Action:** Quick scroll through the JSON to show structure

**Say:**
> "These load tests are part of our regular testing process. They help us validate performance before deploying to production and catch any regressions early."

**Transition:**
> "Now let me hand it over to [Person 3] who will demonstrate the resilience features we built for handling failures gracefully."

---

## 🔄 Part 3: Resilience & Error Handling (Person 3)
**Duration:** ~3 minutes  
**Presenter:** Person 3

### Setup (Before Recording)
- [ ] Services running with Docker Compose
- [ ] Terminal tabs ready:
  - One for checking logs
  - One for running commands
- [ ] Code editor with resilience code ready
- [ ] Documentation files ready to show

---

### Script for Person 3

#### Introduction (0:00 - 0:15)
> "Hi, I'm [Name], and I'll demonstrate the resilience and error handling features we implemented. Production systems must handle failures gracefully, and we've built robust recovery mechanisms."

#### Explain Resilience Requirements (0:15 - 0:45)

**Say:**
> "In production, services can fail for many reasons: network interruptions, Kafka broker restarts, WebSocket disconnections. Our system needs to automatically recover from these failures without losing data or requiring manual intervention."

> "I implemented resilience features in three key areas: Kafka producer resilience, Kafka consumer resilience, and WebSocket reconnection logic."

#### Show Kafka Producer Resilience (0:45 - 1:30)

**Action:** Open `scripts/ws_ingest.py` in editor, scroll to Kafka producer configuration

**Say:**
> "Let me show you the Kafka producer resilience. Here in the WebSocket ingestor, I've configured the Kafka producer with enhanced retry logic."

**Action:** Point to specific configuration lines

**Say:**
> "First, I increased retries from 3 to 10 attempts - this gives the system more chances to recover from temporary failures. Second, I added exponential backoff, starting at 1 second and increasing up to 10 seconds between retries. This prevents overwhelming a recovering service."

> "I also enabled socket keepalive, which maintains persistent connections and detects failures faster. These settings ensure that if Kafka briefly goes down, messages will be retried automatically when it comes back online."

#### Show Kafka Consumer Resilience (1:30 - 2:00)

**Action:** Open `scripts/prediction_consumer.py` in editor, scroll to consumer configuration

**Say:**
> "The consumer side has similar resilience features. The consumer automatically reconnects on transport errors, uses exponential backoff, and gracefully commits offsets on shutdown to prevent message loss."

**Action:** Scroll to reconnection logic

**Say:**
> "If the connection drops, the consumer will automatically attempt to reconnect with increasing delays. This ensures predictions continue flowing even after temporary network issues."

#### Show WebSocket Reconnection (2:00 - 2:30)

**Action:** Scroll to WebSocket reconnection code in `scripts/ws_ingest.py`

**Say:**
> "For the WebSocket connection to Coinbase, I implemented exponential backoff reconnection. It starts with a 5-second delay, doubling each time up to a maximum of 60 seconds. This prevents hammering the Coinbase API during outages while still recovering automatically."

**Action:** Point to the reconnection logic

**Say:**
> "The reconnection logic also includes heartbeat monitoring, so we detect dead connections quickly and reconnect before too much data is missed."

#### Demonstrate Graceful Shutdown (2:30 - 2:45)

**Say:**
> "Another critical feature is graceful shutdown. When we stop a service, it properly closes connections, flushes pending messages, and commits Kafka offsets. This prevents data loss during deployments or restarts."

#### Summary (2:45 - 3:00)

**Say:**
> "Together, these resilience features ensure our system is production-ready. It can handle network failures, service restarts, and temporary outages without losing data or requiring manual intervention. This is essential for a real-time system that needs to run 24/7."

**Final Transition:**
> "That concludes our Week 5 demonstration. We've shown CI/CD automation, comprehensive load testing, and robust resilience features. All of this ensures our crypto volatility detection system is ready for production deployment."

---

## 📝 Complete Checklist for All Presenters

### Before Recording

- [ ] All services running (`docker compose up -d`)
- [ ] API health check works (`curl http://localhost:8000/health`)
- [ ] GitHub Actions has recent successful runs
- [ ] Load test script works (`python scripts/load_test.py`)
- [ ] All code files open in editor
- [ ] Terminal windows ready with commands
- [ ] Screen recording software configured
- [ ] Audio tested (microphone working)

### During Recording

**Person 1 (CI/CD):**
- [ ] Show GitHub Actions tab
- [ ] Show successful workflow run
- [ ] Explain workflow file
- [ ] Run linting commands locally
- [ ] Run integration tests locally

**Person 2 (Load Testing):**
- [ ] Show load test script
- [ ] Verify API is running
- [ ] Run load test
- [ ] Explain results (success rate, latency)
- [ ] Show JSON report file

**Person 3 (Resilience):**
- [ ] Explain resilience requirements
- [ ] Show Kafka producer resilience code
- [ ] Show Kafka consumer resilience code
- [ ] Show WebSocket reconnection logic
- [ ] Explain graceful shutdown

### After Recording

- [ ] Verify all parts are clear and audible
- [ ] Check timing (~8 minutes total)
- [ ] Ensure smooth transitions between presenters
- [ ] Verify all technical demonstrations are visible

---

## 💡 Key Phrases for Each Presenter

### Person 1 (CI/CD)
- "Our CI pipeline runs automatically..."
- "This ensures code quality before merging..."
- "The pipeline catches issues early..."
- "Automated testing gives us confidence..."

### Person 2 (Load Testing)
- "We validate performance under load..."
- "The system handles high traffic efficiently..."
- "100% success rate demonstrates reliability..."
- "P95 latency under 45 milliseconds..."

### Person 3 (Resilience)
- "Automatic recovery from failures..."
- "Production-ready error handling..."
- "The system recovers without manual intervention..."
- "These features ensure 24/7 reliability..."

---

## ⏱️ Timing Breakdown

| Part | Presenter | Duration | Start Time |
|------|-----------|----------|------------|
| Part 1: CI/CD | Person 1 | ~2.5 min | 0:00 |
| Part 2: Load Testing | Person 2 | ~2.5 min | 2:30 |
| Part 3: Resilience | Person 3 | ~3.0 min | 5:00 |
| **Total** | | **~8 min** | |

---

## 🎯 Success Criteria

Your demo is successful if you:
- ✅ Show GitHub Actions pipeline running
- ✅ Demonstrate load testing with real results
- ✅ Explain resilience features clearly
- ✅ Stay within 8-minute total time limit
- ✅ Show smooth handoffs between presenters
- ✅ All technical demonstrations are visible and clear
- ✅ Audio is clear and understandable

---

## 🚀 Good Luck!

Practice each part separately, then practice handoffs. You've built impressive production-ready features! 🎉

