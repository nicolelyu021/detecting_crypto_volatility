# Model Card v1.0
## Crypto Volatility Spike Detection Model

**Date:** 2024  
**Version:** 1.0  
**Model Type:** Binary Classification (Volatility Spike Detection)

---

## 1. Model Details

### Model Information
- **Name:** Crypto Volatility Spike Detector
- **Version:** 1.0
- **Type:** Binary Classification
- **Framework:** scikit-learn / XGBoost
- **Training Date:** [To be filled after training]

### Model Architecture
- **Baseline Model:** Z-score threshold on volatility feature
- **ML Model:** Logistic Regression or XGBoost Classifier
- **Input Features:** 11 numeric features (price, returns, volatility, spreads, etc.)
- **Output:** Binary prediction (0 = normal, 1 = volatility spike)

---

## 2. Intended Use

### Primary Use Case
Detect short-term volatility spikes in cryptocurrency markets 60 seconds in advance for:
- Risk management alerts
- Trading signal generation
- Portfolio rebalancing triggers

### Out-of-Scope Uses
- **NOT** for long-term volatility forecasting (> 5 minutes)
- **NOT** for price direction prediction
- **NOT** for trading execution (research/analysis only)

### Target Users
- Algorithmic traders
- Risk management systems
- Quantitative researchers
- Portfolio managers

---

## 3. Training Data

### Dataset
- **Source:** Coinbase Advanced Trade WebSocket API
- **Products:** BTC-USD, ETH-USD
- **Time Period:** [To be filled]
- **Total Samples:** [To be filled]
- **Features:** 11 numeric features computed from tick data

### Data Splits
- **Training:** 60% (chronological)
- **Validation:** 20% (chronological)
- **Test:** 20% (chronological)

### Preprocessing
- Time-based splitting (no random shuffle to preserve temporal order)
- Feature scaling (StandardScaler for ML models)
- Missing value handling (forward-fill for minor gaps, exclude major gaps)
- Label creation: Binary classification based on 99th percentile threshold of future volatility

### Data Quality
- **Missing Data:** < 1% after preprocessing
- **Class Imbalance:** ~1% positive class (spikes)
- **Temporal Coverage:** Continuous during trading hours

---

## 4. Evaluation Data

### Test Set Characteristics
- **Size:** [To be filled]
- **Time Period:** [To be filled]
- **Spike Rate:** [To be filled]%
- **Distribution:** Matches training distribution (temporal split)

### Evaluation Metrics
- **PR-AUC (Primary):** [To be filled]
- **F1 Score:** [To be filled]
- **Precision:** [To be filled]
- **Recall:** [To be filled]
- **ROC-AUC:** [To be filled]
- **F1@Threshold:** [To be filled]

---

## 5. Ethical Considerations

### Limitations
- Model trained on historical data - may not generalize to new market regimes
- High false positive rate may cause alert fatigue
- Not suitable for high-frequency trading without additional latency optimization

### Bias and Fairness
- Model treats all products equally (BTC-USD, ETH-USD)
- No demographic or personal data used
- Potential bias toward training period market conditions

### Privacy
- Uses only public market data (no personal information)
- No user data collected or stored

---

## 6. Caveats and Recommendations

### Known Limitations
1. **Temporal Dependence:** Model assumes similar market conditions between training and deployment
2. **Class Imbalance:** Rare event prediction (1% spike rate) may limit precision
3. **Feature Drift:** Market microstructure may change over time
4. **Latency:** Current implementation may not meet sub-second requirements for HFT

### Recommendations
1. **Monitor Drift:** Use Evidently to detect feature distribution changes
2. **Retrain Regularly:** Monthly retraining recommended
3. **A/B Testing:** Compare model performance against baseline in production
4. **Threshold Tuning:** Adjust prediction threshold based on business requirements

---

## 7. Model Performance

### Baseline Model (Z-Score)
- **Validation PR-AUC:** [To be filled]
- **Validation F1:** [To be filled]
- **Method:** Z-score threshold (2 standard deviations) on volatility feature

### ML Model
- **Validation PR-AUC:** [To be filled]
- **Validation F1:** [To be filled]
- **Model Type:** [Logistic Regression / XGBoost]
- **Hyperparameters:** [To be filled]

### Comparison
- **Improvement over Baseline:** [To be filled]
- **Best Model:** [To be filled]

---

## 8. Model Details

### Feature Importance
[To be filled after training - XGBoost feature importance or logistic regression coefficients]

### Hyperparameters
- **Baseline:**
  - Threshold: 2.0 standard deviations
- **ML Model:**
  - [To be filled based on model type]

### Inference Performance
- **Latency:** [To be filled] ms per sample
- **Throughput:** [To be filled] samples/second
- **Real-time Factor:** [To be filled]x (target: < 2x)

---

## 9. Monitoring

### Production Monitoring
- **Data Quality:** Evidently reports for feature drift
- **Model Performance:** Track precision, recall, F1 in production
- **Prediction Distribution:** Monitor spike prediction rate

### Alerting
- Alert on significant feature drift (> 10% distribution shift)
- Alert on performance degradation (F1 < baseline)
- Alert on prediction rate anomalies

---

## 10. Maintenance

### Retraining Schedule
- **Frequency:** Monthly or when drift detected
- **Trigger:** Evidently drift detection or performance degradation
- **Process:** Retrain on most recent 30 days of data

### Version History
- **v1.0:** Initial model release
  - Baseline: Z-score threshold
  - ML: [Logistic Regression / XGBoost]
  - Features: 11 numeric features
  - PR-AUC: [To be filled]

---

## 11. References

- **Data Source:** Coinbase Advanced Trade WebSocket API
- **Feature Engineering:** See `docs/feature_spec.md`
- **Training Code:** `models/train.py`
- **Inference Code:** `models/infer.py`
- **Evaluation:** `scripts/generate_evaluation_report.py`

---

**Document Status:** Draft - To be updated after model training

