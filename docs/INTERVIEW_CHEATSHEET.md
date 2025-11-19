# Interview Cheat Sheet - Quick Reference

## 🎯 30-Second Elevator Pitch

"I built a real-time ML system that predicts 60-second volatility spikes in BTC-USD. It streams live data via Kafka, computes windowed features, and uses XGBoost to achieve 99.97% PR-AUC. The system includes full MLOps: drift monitoring, experiment tracking, and model versioning."

---

## 📊 Key Numbers to Remember

- **Data**: 33,881 samples (30 minutes of trading data)
- **Features**: 5 windowed features over 60-second windows
- **Models**: 3 (baseline, LR, XGBoost)
- **Best Model**: XGBoost - PR-AUC: 0.9997, F1: 0.9882
- **Latency**: < 0.1 seconds for 5,000 samples
- **Threshold**: 0.000028 (95th percentile)

---

## 🔄 System Flow (Memorize This)

```
Coinbase WebSocket 
    ↓
Kafka (ticks.raw)
    ↓
Feature Engineering (60s sliding window)
    ↓
Kafka (ticks.features) + Parquet storage
    ↓
Model Training (XGBoost)
    ↓
MLflow (experiment tracking)
    ↓
Inference (predictions)
```

---

## 💬 Common Questions & Answers

### Q: "What does this system do?"

**A**: "It predicts if the next 60 seconds will have unusually high volatility in BTC-USD trading. The system streams live data, computes features in real-time, and makes predictions that help traders react faster to market swings."

### Q: "Why Kafka?"

**A**: "Kafka decouples data ingestion from feature engineering. This allows independent scaling and provides message persistence for replay. It's similar to how you'd handle data pipelines for LLM training - you want robust, scalable data flow."

### Q: "What features did you use?"

**A**: "Five features computed over 60-second windows: midprice return mean and standard deviation (the std is our volatility proxy), bid-ask spread, trade intensity, and order-book imbalance. All features capture different aspects of market microstructure."

### Q: "How did you prevent data leakage?"

**A**: "Two key things: 1) Forward-looking labels using `.shift(-1)` - we predict the NEXT window's volatility, not current. 2) Chronological splits - we split by time, not randomly, so training data can't see future patterns."

### Q: "What was the biggest challenge?"

**A**: "Threshold calibration. I started with limited data and had to iterate as I collected more. The key was balancing statistical rigor (high percentile) with practical constraints (enough positive examples for training). I used percentile analysis to visualize the trade-offs."

### Q: "How is this relevant to LLM data work?"

**A**: "The data quality monitoring I built is directly applicable - detecting distribution shifts that degrade model performance. The replay mechanism ensures reproducible data processing, critical for LLM training pipelines. The streaming architecture scales to large datasets, similar to processing text data for LLM training."

---

## 🎓 Technical Terms (Know These)

- **Sliding Window**: Maintains last 60 seconds, updates with each tick
- **Forward-Looking Labels**: Predicts future, not current state
- **Chronological Split**: Time-based split (prevents leakage)
- **PR-AUC**: Precision-Recall AUC (best for imbalanced data)
- **Data Drift**: Distribution changes over time
- **Replay Mechanism**: Regenerate features from saved raw data
- **MLflow**: Experiment tracking and model versioning

---

## 🗣️ Practice Your 2-Minute Story

**Structure**:
1. **Problem**: Traders need faster reaction to volatility
2. **Solution**: Real-time ML system with streaming data
3. **Architecture**: Kafka → Features → XGBoost → Predictions
4. **Results**: 99.97% PR-AUC, < 0.1s latency
5. **Key Learnings**: Data quality monitoring, preventing leakage, production ML

---

## ✅ Confidence Boosters

- You made all the **decisions** (threshold, features, models)
- You **iterated** on challenges (threshold calibration, data collection)
- You **understood** the requirements and delivered
- You **learned** from each milestone
- The **code** is just implementation - you own the **design**

---

**Remember**: You understand the problem, the solution, and the trade-offs. That's what matters in interviews!

