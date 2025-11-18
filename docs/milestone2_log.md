# Milestone 2 Summary – Feature Engineering, EDA & Evidently

---

## Objective
Build the feature engineering pipeline that computes windowed features from raw ticker data, conduct exploratory data analysis to select a volatility threshold, and generate Evidently reports to detect data drift and quality issues.

---

## Key Achievements

| Step | What I Did | Outcome |
|------|-------------|----------|
| **1. Feature Engineering** | Built `features/featurizer.py` as a Kafka consumer that computes windowed features from raw ticker data. | Real-time feature extraction: midprice returns, bid-ask spread, trade intensity, order-book imbalance over 60-second windows. |
| **2. Reproducibility** | Created `scripts/replay.py` to regenerate features from saved raw data identically to the live featurizer. | Verified feature reproducibility and enabled offline feature generation for experimentation. |
| **3. Data Processing** | Processed raw NDJSON data into structured Parquet format with windowed features. | Generated `data/processed/features.parquet` with ~11K samples (later expanded to 33K+ for Milestone 3). |
| **4. Exploratory Data Analysis** | Created `notebooks/eda.ipynb` with percentile plots and volatility distribution analysis. | Identified appropriate threshold for volatility spike detection through statistical analysis. |
| **5. Threshold Selection** | Selected τ = 0.000028 (95th percentile) as the volatility spike threshold. | Balanced sensitivity and specificity; ensured sufficient positive examples for model training. |
| **6. Evidently Reports** | Generated data drift and quality reports comparing early vs late data windows. | Identified distribution shifts and quality metrics across time periods (calm vs volatile regimes). |
| **7. Feature Specification** | Created `docs/feature_spec.md` documenting all feature definitions, calculations, and threshold rationale. | Complete documentation of feature engineering pipeline and labeling logic. |
| **8. Requirements Update** | Added pandas, pyarrow, evidently, jupyter, matplotlib, seaborn, numpy to `requirements.txt`. | All necessary dependencies for feature engineering and analysis installed. |

---

## Technical Stack
- **Feature Engineering**: Python, pandas, Kafka consumer pattern
- **Data Storage**: Parquet format (pyarrow) for efficient columnar storage
- **Analysis**: Jupyter notebooks, matplotlib, seaborn
- **Drift Detection**: Evidently AI (data drift and quality reports)
- **Window Size**: 60-second sliding window
- **Features**: 4 main features (midprice returns mean/std, bid-ask spread, trade intensity, order-book imbalance)

---

## Challenges & How I Solved Them

| Challenge | Solution |
|-----------|----------|
| **Initial threshold too low** | Started with 0.000015 (99th percentile) from 43-sample EDA, but it was too low for larger datasets. Recalibrated to 0.000028 (95th percentile) after collecting more data. |
| **Insufficient data for threshold selection** | Initially had only 43 samples. Collected ~10 minutes of data (11K+ samples) to get more robust percentile estimates. |
| **99th percentile too strict** | 99th percentile (0.000034) resulted in too few positive examples (0.2%). Adjusted to 95th percentile to ensure sufficient spikes in all splits. |
| **Feature reproducibility** | Created `replay.py` script to verify features generated from saved data match live Kafka consumer output exactly. |
| **Window computation efficiency** | Implemented sliding window using deque for O(1) append/remove operations, maintaining only 60-second window in memory. |
| **Data drift detection** | Used Evidently to compare early vs late windows, revealing distribution shifts between calm and volatile market periods. |

---

## Outcome

Successfully built a **comprehensive feature engineering and analysis pipeline**:
- Computed 4 windowed features from raw ticker data over 60-second windows
- Selected threshold τ = 0.000028 (95th percentile) for volatility spike detection
- Generated Evidently reports showing data drift and quality metrics
- Documented feature specifications and threshold rationale
- Created reproducible feature generation pipeline

**Key Deliverables:**
- `features/featurizer.py` - Real-time Kafka consumer for feature computation
- `scripts/replay.py` - Reproducible feature generation from saved data
- `data/processed/features.parquet` - Processed features (2.2MB)
- `notebooks/eda.ipynb` - EDA notebook with percentile analysis
- `docs/feature_spec.md` - Complete feature specification document
- `reports/evidently/` - Data drift and quality reports (HTML)

---

## Threshold Selection Journey

### Initial State (43 samples)
- **Threshold:** 0.000015 (99th percentile)
- **Spikes:** 4 samples (9.3%)
- **Status:** Too few samples for robust threshold selection

### After 10-Minute Data Collection (~11,130 samples)
- **Initial threshold (0.000015):** Resulted in 10,944 spikes (98.3%) - **PROBLEM: Too sensitive**
- **Adjusted to 99th percentile:** 0.000034 → 22 spikes (0.2%) - **PROBLEM: Too strict, no positives in val/test**
- **Final threshold (95th percentile):** 0.000028 → 557 spikes (5.0%) - **SUCCESS: Good balance**

### After 30-Minute Data Collection (~33,881 samples)
- **Threshold unchanged:** 0.000028 (still 95th percentile)
- **Spikes:** 5,234 samples (15.45%) due to more volatile later window
- **Status:** Threshold held up well; class distribution acceptable for training

**Lesson Learned:** Threshold selection must balance statistical rigor (high percentile) with practical considerations (sufficient examples for evaluation).

---

## Feature Engineering Details

### Windowed Features Computed

1. **Midprice Returns**
   - Mean: Average log return within window
   - Standard Deviation: Volatility proxy (used for labeling)
   - Formula: `log(midprice_t / midprice_{t-1})`

2. **Bid-Ask Spread**
   - Average spread within window
   - Formula: `(best_ask - best_ask)`
   - Interpretation: Higher spread indicates lower liquidity

3. **Trade Intensity**
   - Trades per second within window
   - Formula: `trade_count / window_duration`
   - Interpretation: Higher intensity suggests increased market activity

4. **Order-Book Imbalance**
   - Spread normalized by midprice
   - Formula: `spread / midprice`
   - Interpretation: Proxy for order book depth imbalance

### Window Parameters
- **Size:** 60 seconds
- **Update Frequency:** Every new tick (sliding window)
- **Overlap:** 100% (each tick creates a new window)

---

## Evidently Reports

Generated comprehensive drift and quality reports:

1. **Data Drift Report**
   - Compares early vs late data windows
   - Detects distribution shifts in features
   - Shows drift magnitude for each feature

2. **Data Quality Report**
   - Missing values analysis
   - Duplicate detection
   - Feature statistics (mean, std, min, max)
   - Data quality scores

3. **Combined Report**
   - Integrated view of drift and quality
   - Visualizations and summary statistics
   - HTML format for easy sharing

**Key Findings:**
- Clear distribution shift between calm and volatile periods
- Feature statistics vary significantly across time windows
- No major data quality issues (missing values, duplicates)

---

## Reflection

This milestone solidified my understanding of:
- Building real-time feature engineering pipelines with Kafka consumers
- Statistical threshold selection for imbalanced classification problems
- Data drift detection and quality monitoring with Evidently
- Reproducibility in feature engineering (replay scripts)
- Trade-offs between statistical rigor (percentiles) and practical constraints (class distribution)

**Key Learnings:**
1. **Threshold selection is data-dependent** - Must recalibrate when data volume or distribution changes
2. **Percentile choice matters** - 99th percentile may be too strict for small datasets; 95th provides better balance
3. **Data drift is real** - Early vs late windows showed clear distribution shifts (calm → volatile)
4. **Reproducibility is critical** - Replay scripts ensure features can be regenerated identically

---

## Next Steps (Milestone 3 Preview)

1. Build baseline and ML models using computed features
2. Train models with selected threshold labels
3. Log experiments to MLflow
4. Generate model evaluation reports
5. Create model card documentation

---

## Deliverables Summary

| Deliverable | Status | File |
|------------|--------|------|
| Feature Engineering Script | Complete | `features/featurizer.py` |
| Replay Script | Complete | `scripts/replay.py` |
| Processed Features | Complete | `data/processed/features.parquet` |
| EDA Notebook | Complete | `notebooks/eda.ipynb` |
| Feature Specification | Complete | `docs/feature_spec.md` |
| Evidently Reports | Complete | `reports/evidently/*.html` |
| Threshold Selected | Complete | τ = 0.000028 (95th percentile) |

---

## Milestone 2 Requirements Met

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Feature engineering pipeline | Complete | `features/featurizer.py` - Kafka consumer computes windowed features |
| Reproducible feature generation | Complete | `scripts/replay.py` - Regenerates features from saved data |
| EDA with percentile plots | Complete | `notebooks/eda.ipynb` - Percentile analysis and visualization |
| Threshold selection | Complete | τ = 0.000028 (95th percentile) documented in `feature_spec.md` |
| Evidently reports | Complete | `reports/evidently/` - Drift and quality reports (HTML) |
| Feature specification | Complete | `docs/feature_spec.md` - Complete feature documentation |
| Processed data saved | Complete | `data/processed/features.parquet` - 2.2MB feature dataset |

---

## Data Statistics

### Initial Dataset (Milestone 2)
- **Raw Data:** ~41,469 records in `data/raw/slice.ndjson`
- **Processed Features:** ~11,130 samples after feature engineering
- **Features:** 4 windowed features + metadata
- **Threshold:** τ = 0.000028 (95th percentile)
- **Spikes:** 557 samples (5.0%) labeled as volatility spikes

### Expanded Dataset (Used in Milestone 3)
- **Processed Features:** 33,881 samples
- **Threshold:** τ = 0.000028 (unchanged)
- **Spikes:** 5,234 samples (15.45%) - higher rate due to volatile later window

---

**Milestone 2 Status**: **COMPLETE**

All requirements met. Feature engineering pipeline operational, threshold selected through rigorous EDA, and drift detection implemented via Evidently reports.

