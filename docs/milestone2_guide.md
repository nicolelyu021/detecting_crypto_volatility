# Milestone 2: Step-by-Step Guide

## 🎯 Overview
This guide walks you through completing Milestone 2: Feature Engineering, EDA & Evidently.

**What you'll do:**
1. Install new packages
2. Run the featurizer to compute features
3. Run the replay script to verify reproducibility
4. Conduct EDA in Jupyter notebook
5. Generate Evidently reports

---

## Step 1: Install New Packages

**Where to click:** Open your terminal (Terminal app on Mac)

**What to do:**
1. Navigate to your project folder:
   ```bash
   cd "/Users/YueningLyu/Documents/CMU/94-879 Operationalizing AI_Rao/Crypto Volatility Analysis"
   ```

2. Activate your virtual environment (if not already activated):
   ```bash
   source venv/bin/activate
   ```
   You should see `(venv)` at the start of your terminal prompt.

3. Install the new packages:
   ```bash
   pip install -r requirements.txt
   ```
   
   This will install: pandas, pyarrow, evidently, jupyter, matplotlib, seaborn, numpy

**Expected output:** You'll see packages being downloaded and installed. Wait until it says "Successfully installed..."

---

## Step 2: Start Docker Containers (if not running)

**Where to click:** Terminal

**What to do:**
1. Make sure Docker is running (check Docker Desktop app)
2. Start the containers:
   ```bash
   cd docker
   docker-compose up -d
   ```
   
3. Verify containers are running:
   ```bash
   docker ps
   ```
   
   You should see: zookeeper, kafka, and mlflow containers all showing "Up"

**If containers are already running:** Skip this step!

---

## Step 3: Generate Some Raw Data (if needed)

**Where to click:** Terminal

**What to do:**
1. Go back to project root:
   ```bash
   cd ..
   ```

2. Run the data ingestion script (collects 1 minute of data):
   ```bash
   python scripts/ws_ingest.py
   ```
   
   Wait for it to finish (about 1 minute). You'll see "Finished ingest run"

**If you already have data in `data/raw/slice.ndjson`:** Skip this step!

---

## Step 4: Run the Replay Script (Generate Features from Saved Data)

**Why:** This is easier to test than the live Kafka consumer. It reads your saved raw data and generates features.

**Where to click:** Terminal

**What to do:**
1. Make sure you're in the project root (you should be from Step 3)
2. Run the replay script:
   ```bash
   python scripts/replay.py
   ```

**Expected output:**
- You'll see messages like "Reading raw data from: data/raw/slice.ndjson"
- Then "Processed X ticks..."
- Finally "Saved X features to: data/processed/features.parquet"
- It will show feature statistics

**What this does:** Reads your saved raw data and computes features, saving them to a Parquet file.

---

## Step 5: Run the Live Featurizer (Optional - for real-time processing)

**Why:** This processes data in real-time from Kafka. Use this when you want to process live streaming data.

**Where to click:** Terminal (open a NEW terminal window/tab)

**What to do:**
1. Navigate to project folder and activate venv (same as Step 1)
2. In one terminal, start the data ingestion:
   ```bash
   python scripts/ws_ingest.py
   ```

3. In another terminal (new window), run the featurizer:
   ```bash
   python features/featurizer.py --max-messages 100
   ```
   
   The `--max-messages 100` limits it to 100 messages for testing.

**Expected output:** You'll see "Featurizer started..." and then periodic "Saved X features..." messages.

**Note:** For now, you can skip this and just use the replay script. The live featurizer is useful for production.

---

## Step 6: Conduct EDA in Jupyter Notebook

**Where to click:** Terminal

**What to do:**
1. Make sure you're in the project root
2. Start Jupyter Notebook:
   ```bash
   jupyter notebook
   ```
   
   This will open a web browser automatically showing the Jupyter interface.

3. **In the browser:**
   - Click on the `notebooks` folder
   - Click on `eda.ipynb` to open it

4. **In the notebook:**
   - Click on the first cell (the one with `import pandas as pd...`)
   - Press `Shift + Enter` to run the cell
   - Continue pressing `Shift + Enter` for each cell, one by one
   - Read the outputs and plots

5. **Important:** In the last cell, you'll see the threshold selection. Update the threshold value based on your analysis.

**What to look for:**
- Percentile plots showing volatility distribution
- Choose a threshold (e.g., 99th percentile) based on the plots
- Document your choice in the notebook

**To stop Jupyter:** Go back to terminal and press `Ctrl + C`, then type `y` and press Enter.

---

## Step 7: Generate Evidently Reports

**Where to click:** Terminal

**What to do:**
1. Make sure you're in the project root
2. Run the Evidently report generator:
   ```bash
   python scripts/generate_evidently_report.py
   ```

**Expected output:**
- "Loading features from: ..."
- "Generating Data Drift Report..."
- "✓ Saved HTML report: reports/evidently/data_drift_report.html"
- "✓ Saved HTML report: reports/evidently/data_quality_report.html"
- "✓ Saved HTML report: reports/evidently/combined_report.html"

3. **View the reports:**
   - Open Finder (on Mac)
   - Navigate to: `Crypto Volatility Analysis/reports/evidently/`
   - Double-click `combined_report.html` to open in your browser
   - Review the visualizations showing data drift and quality metrics

**What the reports show:**
- **Data Drift:** How much the data distribution changed between early and late windows
- **Data Quality:** Missing values, duplicates, feature statistics

---

## Step 8: Update Feature Specification Document

**Where to click:** 
- Open in your code editor: `docs/feature_spec.md`

**What to do:**
1. Open the file `docs/feature_spec.md`
2. Find the section "Chosen Threshold τ"
3. Replace `<TO_BE_DETERMINED_FROM_EDA>` with:
   - The actual threshold value from your EDA notebook
   - The percentile you chose (e.g., "99th percentile")
   - Your justification (why you chose that threshold)

**Example:**
```markdown
**Threshold Value:** 0.001234

**Percentile:** 99th percentile

**Justification:**
- This threshold captures the top 1% of volatility events
- Based on percentile analysis in eda.ipynb
- Provides good balance between detecting true spikes and avoiding false alarms
```

---

## Step 9: Verify Everything Works

**Where to click:** Terminal

**What to do:**
1. Check that files exist:
   ```bash
   ls -la data/processed/
   ```
   Should show: `features.parquet`

2. Check that reports exist:
   ```bash
   ls -la reports/evidently/
   ```
   Should show: HTML and JSON report files

3. Check that notebook exists:
   ```bash
   ls -la notebooks/
   ```
   Should show: `eda.ipynb`

---

## Troubleshooting

### "Module not found" error
- Make sure you activated the virtual environment: `source venv/bin/activate`
- Reinstall packages: `pip install -r requirements.txt`

### "No features file found" error
- Run the replay script first: `python scripts/replay.py`
- Make sure you have raw data: `ls -la data/raw/slice.ndjson`

### "Kafka connection error"
- Make sure Docker containers are running: `docker ps`
- Start containers: `cd docker && docker-compose up -d`

### Jupyter notebook won't start
- Make sure jupyter is installed: `pip install jupyter`
- Try: `python -m jupyter notebook`

---

## Deliverables Checklist

Before submitting, make sure you have:

- ✅ `features/featurizer.py` - Feature computation script
- ✅ `scripts/replay.py` - Replay script
- ✅ `data/processed/features.parquet` - Processed features
- ✅ `notebooks/eda.ipynb` - EDA notebook with percentile plots
- ✅ `docs/feature_spec.md` - Feature specification (with threshold filled in)
- ✅ `reports/evidently/` - Evidently reports (HTML and JSON)

---

## Next Steps (Milestone 3 Preview)

After completing Milestone 2, you'll move to:
- Training baseline and ML models
- Logging to MLflow
- Model evaluation and metrics
- Model cards

---

## Questions?

If you get stuck:
1. Check the error message carefully
2. Make sure all steps were followed in order
3. Verify Docker containers are running
4. Check that you're in the correct directory

Good luck! 🚀

