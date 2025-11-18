# Model Card v1: Crypto Volatility Spike Detection

**Version:** 1.0  
**Date:** November 2025  
**Status:** Milestone 3 Complete

---

## Model Overview

### Purpose
Detect short-term volatility spikes in BTC-USD cryptocurrency trading data in real-time. The model predicts whether the next 60 seconds will experience unusually high price volatility.

### Model Types

**1. Baseline Model: Z-Score Rule**
- **Type:** Rule-based anomaly detection
- **Algorithm:** Statistical threshold (mean + 2σ)
- **Input:** Single feature (`midprice_return_std`)
- **Output:** Binary classification (0 = normal, 1 = spike)

**2. ML Model: Logistic Regression**
- **Type:** Supervised classification
- **Algorithm:** Logistic Regression with balanced class weights
- **Input:** 5 features (see below)
- **Output:** Binary classification with probability scores

---

## Data

### Data Source
- **Source:** Coinbase WebSocket API (live BTC-USD ticker data)
- **Collection Period:** November 13-14, 2025
- **Total Samples:** 33,881 (collected over ~30 minutes)
- **Spikes:** 5,234 samples (15.45% at 95th percentile threshold)
- **Streaming:** Real-time data ingestion via Kafka

### Features

| Feature | Description | Type |
|---------|-------------|------|
| `midprice_return_mean` | Mean log return of midprice in 60s window | Numeric |
| `midprice_return_std` | Std dev of log returns (volatility proxy) | Numeric |
| `bid_ask_spread` | Average bid-ask spread in window | Numeric |
| `trade_intensity` | Trades per second in window | Numeric |
| `order_book_imbalance` | Spread normalized by midprice | Numeric |

### Label Definition

**Target:** Binary volatility spike indicator

**Labeling Rule (Forward-Looking):**
```
Label_t = 1 if midprice_return_std_{t+1} >= τ; else 0
```

**Prediction Task:** Given features from the current 60-second window, predict if the **NEXT** 60-second window will have high volatility.

Where:
- `τ` (tau) = 0.000028 (95th percentile threshold from updated EDA)
- Captures top ~15% of volatility events after adding 30 minutes of data (5,234 out of 33,881 samples)
- Adjusted from 99th percentile to ensure sufficient positive examples across all data splits
- **Forward-looking:** Each sample uses current window features to predict next window's volatility

**Class Distribution:**
- **Normal (0):** 84.6% of samples
- **Spike (1):** 15.4% of samples (late market window became highly volatile)
- **Note:** Class imbalance addressed via balanced class weights in Logistic Regression
- **Threshold Adjustment:** Initially used 99th percentile (0.000034) but adjusted to 95th percentile (0.000028) to ensure sufficient positive examples across train/validation/test splits

### Data Splits

**Chronological (time-based) splits:**
- **Training:** 23,716 samples (70%) – early calmer period (3.8% spikes)
- **Validation:** 5,082 samples (15%) – mid window (38.9% spikes)
- **Test:** 5,083 samples (15%) – late highly volatile window (46.3% spikes)

**Rationale:** Time-based splits preserve temporal ordering and highlight the regime shift (calm → volatile) the model must handle.

---

## Performance

### Primary Metric: PR-AUC

**PR-AUC (Precision-Recall Area Under Curve)**
- Preferred over ROC-AUC due to class imbalance
- Higher values indicate better precision-recall trade-off
- Target: ≥ 0.60 (baseline comparison threshold)

### Test Set Results

| Model | PR-AUC | F1-Score | Precision | Recall |
|-------|--------|----------|-----------|--------|
| Baseline (Z-Score) | 0.9997 | 0.9595 | 0.9995 | 0.9226 |
| Logistic Regression | 0.7398 | 0.3309 | 0.7157 | 0.2152 |
| XGBoost | 0.9997 | 0.9882 | 0.9779 | 0.9987 |

**Note:** After expanding the dataset to ~34k samples, baseline and XGBoost both achieve near-perfect PR-AUC/F1. Logistic Regression now predicts positive spikes but still lags (PR-AUC 0.74) because the relationship between features and spikes becomes highly non-linear in the volatile regime.

### Validation Results

Validation set used for:
- Hyperparameter tuning (if applicable)
- Early stopping checks
- Model selection

---

## Training

### Baseline Model

**Algorithm:** Z-score thresholding
```
spike = 1 if midprice_return_std > mean + 2*std
```

**Hyperparameters:**
- `threshold`: 2.0 (standard deviations)
- `feature`: midprice_return_std

**Training:**
- Compute mean and std on training data
- No iterative optimization
- Training time: < 1 second

### Logistic Regression Model

**Algorithm:** Logistic Regression (sklearn)

**Hyperparameters:**
- `class_weight`: balanced (handles class imbalance)
- `max_iter`: 1000
- `solver`: lbfgs
- `random_state`: 42

**Training:**
- Fitted on all 5 features
- Balanced class weights adjust for 99:1 imbalance
- Training time: < 5 seconds

---

## MLflow Tracking

All experiments logged to MLflow:
- **Tracking URI:** http://localhost:5001
- **Experiment Name:** crypto_volatility_detection

**Logged Artifacts:**
- Parameters (threshold, solver, etc.)
- Metrics (PR-AUC, F1, precision, recall)
- Model artifacts (.pkl files)
- Visualizations (PR curves, confusion matrices)
- Metrics JSON files

---

## Drift Analysis

### Evidently AI Reports

**Comparison:** Training data vs Test data

**Metrics Monitored:**
- Feature distribution drift (Kolmogorov-Smirnov test)
- Data quality metrics
- Statistical properties (mean, std, percentiles)

**Findings:**
Drift analysis will be available after generating the Evidently report. Run:
```bash
python scripts/generate_train_test_drift_report.py
```

**Location:** `reports/evidently/train_test_drift_report.html`

---

## Limitations

### Known Limitations

1. **Limited Historical Coverage:** Model trained on ~30 minutes of streaming data (~34k samples)
   - Captures only one calm-to-volatile transition
   - Longer data collection (days/weeks) would improve robustness

2. **Class Distribution Shift:** Train split has 3.8% spikes while test split has 46%
   - Reflects real temporal drift but stresses linear models
   - Requires continuous monitoring of spike rate and potential rebalancing

3. **Temporal Drift:** Markets change over time
   - Model may degrade as market regime shifts
   - Periodic retraining recommended

4. **Feature Engineering:** Simple features
   - Could benefit from more sophisticated features
   - No technical indicators or market microstructure features

5. **Single Asset:** BTC-USD only
   - Not tested on other cryptocurrencies
   - May not transfer to different assets

### Out of Scope

- **No Trading:** This is an analysis/alerting system, not a trading bot
- **No Position Sizing:** No recommendations on trade size
- **No Risk Management:** Does not account for portfolio risk
- **Public Data Only:** No proprietary or private data sources

---

## Ethical Considerations

### Intended Use

**Appropriate:**
- Research and educational purposes
- Risk monitoring and alerting
- Market analysis and insights
- Academic projects

**Inappropriate:**
- Automated trading without human oversight
- Financial advice to unqualified individuals
- High-frequency trading decisions
- Any use without proper risk disclosure

### Risks

1. **Financial Loss:** Predictions may be incorrect, leading to poor decisions
2. **Over-Reliance:** Should not replace human judgment and risk management
3. **Market Impact:** Not designed for high-frequency or high-volume trading
4. **Regulatory:** Users responsible for compliance with financial regulations

---

## Monitoring and Maintenance

### Monitoring Plan

**What to Monitor:**
- Model performance metrics (PR-AUC, F1)
- Prediction distribution (spike rate)
- Feature distributions (detect drift)
- Data quality (missing values, outliers)

**How Often:**
- **Real-time:** Data quality checks
- **Daily:** Performance metrics review
- **Weekly:** Drift analysis
- **Monthly:** Model retraining evaluation

**Thresholds for Action:**
- PR-AUC drops below 0.50 → Investigate
- Spike rate > 5% → Check data quality
- Significant drift detected → Consider retraining

### Retraining Strategy

**When to Retrain:**
- Scheduled: Monthly or quarterly
- Triggered: Significant performance degradation or drift
- Ad-hoc: After major market events

**Process:**
1. Collect new data (minimum 1 week of streaming)
2. Re-run EDA and update threshold if needed
3. Retrain both baseline and ML models
4. Validate on held-out test set
5. Compare to previous model version
6. Deploy if improved or maintained performance

---

## Technical Details

### Dependencies
- Python 3.11
- scikit-learn 1.4.0
- pandas 2.2.0
- MLflow 2.16.0
- evidently 0.5.0

### Infrastructure
- Kafka: Data streaming
- MLflow: Experiment tracking
- Docker: Containerization

### Files
- **Training:** `models/train.py`
- **Inference:** `models/infer.py`
- **Baseline:** `models/baseline.py`
- **Artifacts:** `models/artifacts/`

---

## Contact & References

### Project Information
- **Course:** 94-879 Operationalizing AI
- **Institution:** Carnegie Mellon University
- **Semester:** Fall 2025

### References
- Coinbase Advanced Trade API Documentation
- MLflow Documentation: https://mlflow.org/docs/latest/
- Evidently AI Documentation: https://docs.evidentlyai.com/
- Scikit-learn Documentation: https://scikit-learn.org/

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Nov 2025 | Initial model card. Baseline and Logistic Regression models trained. |

---

## Appendix: Feature Engineering

### Windowed Features

All features computed over a sliding 60-second window:
- **Window Size:** 60 seconds
- **Update Frequency:** Every tick (real-time)
- **Overlap:** 100% (sliding window)

### Feature Calculation

**Midprice Returns:**
```python
midprice = (best_bid + best_ask) / 2
log_returns = log(midprice_t / midprice_{t-1})
mean_return = mean(log_returns)
std_return = std(log_returns)  # Volatility proxy
```

**Bid-Ask Spread:**
```python
spread = best_ask - best_bid
avg_spread = mean(spread)
```

**Trade Intensity:**
```python
trade_intensity = trade_count / window_duration
```

**Order-Book Imbalance:**
```python
imbalance = avg_spread / midprice
```

---

*This model card will be updated as the model evolves and more data becomes available.*

