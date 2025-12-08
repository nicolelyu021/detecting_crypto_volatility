# Milestone 3: Step-by-Step Guide
## Modeling, Tracking, and Evaluation

---

## 🎯 Overview

This guide walks you through Milestone 3: training models, logging experiments to MLflow, and evaluating performance.

**What you'll do:**
1. Install new packages
2. Run the training pipeline
3. View results in MLflow UI
4. Generate Evidently drift report (train vs test)
5. Generate model evaluation PDF
6. Review and update model card

---

## Step 1: Install New Packages

**Where to run:** Terminal

**What to do:**
1. Navigate to project folder:
   ```bash
   cd "/Users/YueningLyu/Documents/CMU/94-879 Operationalizing AI_Rao/Crypto Volatility Analysis"
   ```

2. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

3. Install new packages:
   ```bash
   pip install -r requirements.txt
   ```
   
   This installs: scikit-learn, xgboost, joblib

---

## Step 2: Make Sure MLflow is Running

**Where to check:** Terminal

**What to do:**
1. Check if Docker containers are running:
   ```bash
   docker ps
   ```
   
   You should see: zookeeper, kafka, and **mlflow** containers

2. If MLflow is not running, start it:
   ```bash
   cd docker
   docker-compose up -d mlflow
   cd ..
   ```

3. Open MLflow UI in your browser:
   - Go to: http://localhost:5001
   - You should see the MLflow interface

---

## Step 3: Run the Training Pipeline

**Where to run:** Terminal

**What this does:** Trains both baseline and Logistic Regression models, logs everything to MLflow.

**What to do:**
```bash
python models/train.py
```

**Expected output:**
- "Loading and preparing data..."
- "Splitting data chronologically..."
- "Training Baseline Model (Z-Score)..."
- "Training ML Model (Logistic Regression)..."
- "Train Metrics: PR-AUC: X.XXXX"
- "Test Metrics: PR-AUC: X.XXXX"
- "Baseline model saved to: models/artifacts/baseline/baseline_model.pkl"
- "Logistic Regression model saved to: models/artifacts/logistic_regression/lr_model.pkl"
- "TRAINING COMPLETE"

**How long:** About 10-30 seconds

**What it creates:**
- `models/artifacts/baseline/` - baseline model files
- `models/artifacts/logistic_regression/` - ML model files
- `data/processed/train_data.parquet` - training data
- `data/processed/test_data.parquet` - test data
- MLflow runs with all metrics and artifacts

---

## Step 4: View Results in MLflow

**Where to click:** Web browser

**What to do:**
1. Open http://localhost:5001 in your browser

2. You should see an experiment called `crypto_volatility_detection`

3. Click on the experiment to see runs:
   - `baseline_zscore` run
   - `logistic_regression` run

4. Click on each run to see:
   - **Parameters:** Model settings
   - **Metrics:** PR-AUC, F1-Score, etc.
   - **Artifacts:** Saved models, plots, metrics files

5. Compare the two runs:
   - Look at the PR-AUC metric
   - Which model performs better?

**What to look for:**
- PR-AUC ≥ 0.60 (target from requirements)
- F1-Score (balance of precision and recall)
- Confusion matrices (how many false positives/negatives)

---

## Step 5: Generate Train vs Test Drift Report

**Where to run:** Terminal

**What this does:** Compares training and test data distributions to detect drift.

**What to do:**
```bash
python scripts/generate_train_test_drift_report.py
```

**Expected output:**
- "Loading training data from: data/processed/train_data.parquet"
- "Loading test data from: data/processed/test_data.parquet"
- "Generating Train vs Test Data Drift Report..."
- "✓ Saved HTML report: reports/evidently/train_test_drift_report.html"
- "✓ Saved HTML report: reports/evidently/train_test_quality_report.html"

**View the report:**
1. Open Finder
2. Navigate to: `Crypto Volatility Analysis/reports/evidently/`
3. Double-click `train_test_combined_report.html`
4. Review the drift metrics

**What to look for:**
- Are features drifting between train and test?
- Are distributions significantly different?
- Is the label distribution similar?

---

## Step 6: Generate Model Evaluation PDF

**Where to run:** Terminal

**What this does:** Creates a PDF report with model comparison and visualizations.

**What to do:**
```bash
python scripts/generate_model_eval_report.py
```

**Expected output:**
- "Generating Model Evaluation PDF Report"
- "✓ PDF report generated: reports/model_eval.pdf"

**View the report:**
1. Open Finder
2. Navigate to: `Crypto Volatility Analysis/reports/`
3. Double-click `model_eval.pdf`
4. Review the 4-page report with:
   - Title page
   - Metrics comparison
   - PR curves
   - Summary and recommendations

---

## Step 7: Update Model Card

**Where to click:** Code editor

**What to do:**
1. Open `docs/model_card_v1.md`

2. Find sections with `<TBD>` or `<TO_BE_FILLED_AFTER_TRAINING>`

3. Fill in actual values from your training results:
   - Total samples
   - Test set metrics (PR-AUC, F1, etc.)
   - Evidently findings

**Where to get values:**
- From terminal output after running `train.py`
- From MLflow UI (http://localhost:5001)
- From Evidently reports

**Example:**
```markdown
| Model | PR-AUC | F1-Score | Precision | Recall |
|-------|--------|----------|-----------|--------|
| Baseline (Z-Score) | 0.7234 | 0.6543 | 0.7000 | 0.6200 |
| Logistic Regression | 0.8156 | 0.7321 | 0.7800 | 0.6900 |
```

---

## Step 8: Verify Everything is Complete

**Where to run:** Terminal

**What to do:**

1. Check model artifacts exist:
   ```bash
   ls -la models/artifacts/baseline/
   ls -la models/artifacts/logistic_regression/
   ```
   Should show: model files, metrics.json, plots

2. Check reports exist:
   ```bash
   ls -la reports/
   ```
   Should show: `model_eval.pdf`, `model_comparison.png`, `evidently/` folder

3. Check data files exist:
   ```bash
   ls -la data/processed/
   ```
   Should show: `features.parquet`, `train_data.parquet`, `test_data.parquet`

4. Check MLflow tracking:
   - Open http://localhost:5001
   - Verify both runs are logged with metrics

---

## Troubleshooting

### "MLflow connection error"
- Check MLflow container is running: `docker ps`
- Restart MLflow: `cd docker && docker-compose restart mlflow`
- Verify port 5001 is accessible: http://localhost:5001

### "No features file found"
- Make sure you completed Milestone 2
- Run replay script: `python scripts/replay.py`
- Check file exists: `ls data/processed/features.parquet`

### "Module not found" errors
- Activate venv: `source venv/bin/activate`
- Reinstall packages: `pip install -r requirements.txt`

### "Not enough data" or "division by zero"
- Collect more data with: `python scripts/ws_ingest.py`
- Run replay to generate features: `python scripts/replay.py`
- Need at least 30-40 samples for meaningful training

### PDF generation fails
- Make sure matplotlib is installed: `pip install matplotlib`
- Check artifacts directory has model files
- Run training first: `python models/train.py`

---

## Deliverables Checklist

Before submitting, verify you have:

- ✅ `models/train.py` - Training pipeline script
- ✅ `models/infer.py` - Inference script
- ✅ `models/baseline.py` - Baseline model implementation
- ✅ `models/artifacts/` - Saved model files and metrics
- ✅ `reports/model_eval.pdf` - Model evaluation PDF report
- ✅ `reports/evidently/train_test_*_report.html` - Drift reports
- ✅ `docs/model_card_v1.md` - Model card (with values filled in)
- ✅ MLflow runs logged with metrics and artifacts

---

## Understanding Your Results

### What is PR-AUC?

**PR-AUC (Precision-Recall Area Under Curve)**
- Measures how well the model balances precision and recall
- Range: 0 to 1 (higher is better)
- **Good:** > 0.60 (your target)
- **Excellent:** > 0.80

**Why PR-AUC and not accuracy?**
- Your data has class imbalance (99% normal, 1% spikes)
- A naive model predicting "always normal" would be 99% accurate
- PR-AUC focuses on the minority class (spikes), which is what matters

### What is F1-Score?

**F1-Score**
- Harmonic mean of precision and recall
- Range: 0 to 1 (higher is better)
- Balances false positives and false negatives
- **Good:** > 0.50
- **Excellent:** > 0.70

### Interpreting the Confusion Matrix

```
              Predicted
           Normal  Spike
Actual Normal  TN     FP    <- False alarms
       Spike   FN     TP    <- Missed spikes
```

- **TN (True Negatives):** Correctly identified normal periods
- **TP (True Positives):** Correctly identified spikes
- **FP (False Positives):** False alarms (predicted spike, but was normal)
- **FN (False Negatives):** Missed spikes (predicted normal, but was spike)

### What if PR-AUC < 0.60?

**Possible reasons:**
1. Not enough data (need more samples)
2. Features aren't predictive enough
3. Threshold might be too strict or too loose
4. Market conditions changed (drift)

**What to do:**
1. Collect more data (run ingestion longer)
2. Try different features
3. Adjust the threshold in EDA
4. Consider more complex models

---

## Next Steps After Milestone 3

1. **Monitor:** Set up real-time monitoring
2. **Deploy:** Create production pipeline
3. **Iterate:** Collect more data and retrain
4. **Optimize:** Tune hyperparameters
5. **Scale:** Add more cryptocurrencies

---

## Questions?

If you get stuck:
1. Check error messages carefully
2. Verify all previous milestones are complete
3. Ensure Docker containers (especially MLflow) are running
4. Check that feature data exists

Good luck! 🚀

