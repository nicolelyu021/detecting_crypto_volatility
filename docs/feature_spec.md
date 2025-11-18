# Feature Specification Document

## Overview
This document specifies the feature engineering pipeline for detecting crypto volatility spikes in real-time.

---

## Target Horizon

**Prediction Window:** 60 seconds

The model predicts whether the next 60 seconds will experience unusually high volatility.

---

## Volatility Proxy

**Definition:** Rolling standard deviation of midprice returns over the next horizon (60 seconds)

**Calculation:**
- Midprice = (best_bid + best_ask) / 2
- Midprice returns = log(midprice_t / midprice_{t-1})
- Volatility proxy (σ_future) = standard deviation of midprice returns over a 60-second forward-looking window

**Rationale:** 
- Standard deviation of returns is a standard measure of volatility in financial markets
- Using log returns normalizes the measure across different price levels
- 60-second window captures short-term volatility dynamics relevant for real-time trading

---

## Label Definition

**Binary Classification (Forward-Looking):**
```
Label_t = 1 if σ_future_{t+1} >= τ; else 0
```

**Prediction Task:**
- Given features from window [t-60s, t], predict if window [t, t+60s] will have high volatility
- This is a **forward-looking prediction** task, not detection of current conditions

Where:
- `σ_future_{t+1}` = rolling standard deviation of midprice returns for the NEXT 60-second window
- `τ` = chosen threshold (see below)

**Interpretation:**
- `Label = 1`: Volatility spike expected in next window (high volatility predicted)
- `Label = 0`: Normal volatility expected (no spike predicted)

**Implementation:**
In code, this is achieved via: `df['label'] = (df['midprice_return_std'].shift(-1) >= τ).astype(int)`

---

## Chosen Threshold τ

**Threshold Value:** 0.000028

**Percentile:**  95th

**Justification:**
- Originally captured the top 5% of volatility events (11,130-sample dataset)
- After expanding to 33,881 samples, the same absolute value now labels ~15% of samples because the late window became much more volatile (still acceptable for spike detection)
- Updated from 99th percentile (0.000034) to 95th percentile for better distribution across train/val/test splits
- Initial threshold (0.000015) from 43-sample EDA was recalibrated after collecting 10 minutes of data
- 95th percentile chosen over 99th to ensure sufficient positive examples in validation and test sets
- This provides a good balance between sensitivity and specificity for the available data volume

The threshold is selected based on:
1. Percentile analysis of historical volatility proxy values
2. Trade-off between sensitivity (detecting true spikes) and specificity (avoiding false alarms)
3. Business requirements for alert frequency

**Typical considerations:**
- 95th percentile: Captures top 5% of volatility events (more sensitive)
- 99th percentile: Captures top 1% of volatility events (more conservative)
- 99.5th percentile: Captures top 0.5% of volatility events (very conservative)

---

## Feature Engineering

### Windowed Features

All features are computed over a sliding window of 60 seconds.

#### 1. Midprice Returns
- **Mean:** Average log return of midprice within the window
- **Standard Deviation:** Standard deviation of log returns (used as volatility proxy)
- **Formula:** `log(midprice_t / midprice_{t-1})`

#### 2. Bid-Ask Spread
- **Definition:** Average bid-ask spread within the window
- **Formula:** `(best_ask - best_bid)`
- **Normalized:** Can be normalized by midprice: `spread / midprice`
- **Interpretation:** Higher spread indicates lower liquidity and potential volatility

#### 3. Trade Intensity
- **Definition:** Number of trades per second within the window
- **Formula:** `trade_count / window_duration`
- **Interpretation:** Higher intensity may indicate increased market activity and volatility

#### 4. Order-Book Imbalance (Optional)
- **Definition:** Measure of imbalance between bid and ask sides
- **Simplified Proxy:** `average_spread / midprice`
- **Interpretation:** Higher imbalance suggests potential price movement

### Feature Window Parameters

- **Window Size:** 60 seconds
- **Update Frequency:** Every new tick (real-time)
- **Overlap:** Sliding window with 100% overlap (each tick creates a new window)

---

## Data Flow

1. **Raw Data Source:** Coinbase WebSocket ticker channel (BTC-USD)
2. **Kafka Topic (Input):** `ticks.raw`
3. **Feature Computation:** `features/featurizer.py` (Kafka consumer)
4. **Kafka Topic (Output):** `ticks.features`
5. **Storage:** `data/processed/features.parquet` (Parquet format)

---

## Reproducibility

### Replay Script
The `scripts/replay.py` script ensures feature reproducibility by:
- Reading saved raw data from `data/raw/slice.ndjson`
- Regenerating features using identical logic to `featurizer.py`
- Outputting to `data/processed/features.parquet`

**Verification:** Replay and live consumer should yield identical features (within floating-point precision).

---

## Feature Schema

### Input Schema (from Kafka `ticks.raw`)
```json
{
  "ts": <float>,      // Timestamp
  "pair": "BTC-USD",  // Trading pair
  "raw": "<string>"   // Raw JSON string from Coinbase
}
```

### Output Schema (to Kafka `ticks.features` and Parquet)
```json
{
  "ts": <float>,                      // Timestamp
  "pair": "BTC-USD",                  // Trading pair
  "midprice_return_mean": <float>,    // Mean of log returns
  "midprice_return_std": <float>,     // Std of log returns (volatility proxy)
  "bid_ask_spread": <float>,          // Average bid-ask spread
  "trade_intensity": <float>,         // Trades per second
  "order_book_imbalance": <float>,    // Spread normalized by midprice
  "window_size": <int>,               // Number of ticks in window
  "window_duration": <float>,         // Actual window duration in seconds
  "raw_price": <float>                // Last observed price
}
```

---

## Notes

- Features are computed in real-time as data streams in
- Window maintains state across ticks (sliding window)
- Missing or invalid ticks are skipped (no forward-filling)
- All features are computed synchronously (no async feature computation)

---

## Updates

- **Initial Version:** Milestone 2
- **Last Updated:** <DATE>
- **Next Review:** After EDA completion and threshold selection

