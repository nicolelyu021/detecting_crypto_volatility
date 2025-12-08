# Project Progress Tracker

- ✅ Milestone 1 – Completed Nov 2025  
  - Kafka + MLflow containers run successfully  
  - Live BTC-USD data streaming verified  
  - Sanity check passed (`messages_seen=20`)  
  - Scoping brief and milestone log written  

- ✅ Milestone 2 – Completed  
  - Built `features/featurizer.py` (Kafka consumer for feature engineering)  
  - Computed windowed features: midprice returns, bid-ask spread, trade intensity, order-book imbalance  
  - Built `scripts/replay.py` for reproducible feature regeneration  
  - Created `notebooks/eda.ipynb` for exploratory data analysis with percentile plots  
  - Generated Evidently reports comparing early vs late data windows (drift and quality reports)  
  - Created `docs/feature_spec.md` with feature specifications  
- **Threshold selected:** τ = 0.000028 (95th percentile) based on updated EDA (validated again after expanding dataset to 33,881 samples)  
  - Features saved to `data/processed/features.parquet`

- ✅ Milestone 3 – Completed
  - Built `models/baseline.py` (Z-score rule-based model)
  - Built `models/train.py` (training pipeline with MLflow tracking)
  - Built `models/infer.py` (inference script for predictions)
  - Trained baseline (z-score) and ML models (Logistic Regression, XGBoost) on ~34k samples
  - Logged parameters, metrics (PR-AUC, F1), and artifacts to MLflow
  - Generated Evidently drift report comparing train vs test
  - Created model evaluation PDF report (`reports/model_eval.pdf`)
  - Created Model Card v1 (`docs/model_card_v1.md`)
  - Time-based data splits (70/15/15 train/val/test)
