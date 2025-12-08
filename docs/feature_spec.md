# Feature Specification Document
## Crypto Volatility Detection Pipeline

**Date:** 2024  
**Version:** 1.0  
**Milestone:** 2

---

## 1. Target Horizon

**Prediction Horizon:** 60 seconds

The model predicts volatility spikes that will occur 60 seconds in the future. This provides sufficient time for:
- Risk management decisions
- Trading signal generation
- Portfolio rebalancing
- Alert processing

---

## 2. Volatility Proxy

**Definition:** Rolling standard deviation of midprice returns over the next 60 seconds

**Formula:**
```
σ_future = std(returns_{t+1}, returns_{t+2}, ..., returns_{t+60})
```

Where:
- `returns_{t+i}` = (midprice_{t+i} - midprice_{t+i-1}) / midprice_{t+i-1}
- `std()` = standard deviation
- Time window: next 60 seconds from current timestamp `t`

**Rationale:**
- Standard deviation captures the magnitude of price movements
- Midprice (average of bid and ask) is more stable than individual trade prices
- 60-second window balances responsiveness with statistical significance

---

## 3. Label Definition

**Binary Classification:**
- **Label = 1** (Volatility Spike): if `σ_future >= τ`
- **Label = 0** (Normal): if `σ_future < τ`

Where `τ` (tau) is the volatility threshold determined through EDA.

**Label Computation:**
1. For each timestamp `t`, compute `σ_future` using returns from `t+1` to `t+60`
2. Compare `σ_future` to threshold `τ`
3. Assign label: `1` if spike detected, `0` otherwise

---

## 4. Chosen Threshold τ

**Threshold Value:** [To be determined from EDA notebook]

**Selection Method:**
The threshold will be determined through percentile analysis in the EDA notebook:
1. Compute `σ_future` for all samples in the dataset
2. Generate percentile plots (50th, 75th, 90th, 95th, 97.5th, 99th, 99.5th, 99.9th)
3. Evaluate candidate thresholds:
   - 95th percentile
   - 97.5th percentile
   - 99th percentile
   - 2 standard deviations above mean
   - 3 standard deviations above mean
4. Select threshold that balances:
   - **Precision:** High percentage of predicted spikes actually occur
   - **Recall:** Captures a meaningful portion of actual spikes
   - **False Positive Rate:** Low enough to avoid alert fatigue

**Expected Threshold Range:** Based on typical cryptocurrency volatility distributions, the threshold is expected to be in the range of the 97.5th to 99th percentile.

**Justification:**
- Percentile-based thresholds are robust to outliers
- 99th percentile typically captures ~1% of periods as spikes
- Provides sufficient signal for model training while maintaining class balance

---

## 5. Feature Engineering

### 5.1 Input Features

**Price Features:**
- `price`: Current trade price
- `midprice`: (best_bid + best_ask) / 2
- `return_1s`: 1-second return
- `return_5s`: 5-second return
- `return_30s`: 30-second return
- `return_60s`: 60-second return

**Volatility Features:**
- `volatility`: Rolling standard deviation of returns over the lookback window

**Market Microstructure:**
- `spread_abs`: Absolute bid-ask spread (ask - bid)
- `spread_rel`: Relative bid-ask spread (spread_abs / midprice)
- `order_book_imbalance`: (ask - bid) / (ask + bid)

**Trading Activity:**
- `trade_intensity`: Number of trades per second in the last 60 seconds

### 5.2 Lookback Window

**Window Size:** 300 seconds (5 minutes)

**Rationale:**
- Captures short-term market dynamics
- Balances feature richness with computational efficiency
- Provides sufficient history for return calculations

### 5.3 Feature Computation

**Returns:**
```
return_Δt = (price_t - price_{t-Δt}) / price_{t-Δt}
```

**Volatility:**
```
volatility = std(returns_{t-window}, ..., returns_{t-1})
```

**Trade Intensity:**
```
trade_intensity = count(trades in [t-60, t]) / 60
```

---

## 6. Data Quality Requirements

**Minimum Data Points:**
- At least 10 data points in the lookback window for feature computation
- At least 2 data points in the prediction horizon for volatility calculation

**Missing Data Handling:**
- Skip feature computation if insufficient data
- Forward-fill for minor gaps (< 5 seconds)
- Mark as NaN and exclude from training if gaps are larger

**Validation:**
- Price > 0
- Midprice > 0
- Returns within reasonable bounds (-50% to +50%)
- Spread > 0

---

## 7. Output Format

**Kafka Topic:** `ticks.features`

**Parquet Schema:**
```
timestamp: float64
product_id: string
price: float64
midprice: float64
return_1s: float64
return_5s: float64
return_30s: float64
return_60s: float64
volatility: float64
trade_intensity: float64
spread_abs: float64
spread_rel: float64
order_book_imbalance: float64
window_size: int32
num_returns: int32
future_volatility: float64 (computed in EDA)
label: int32 (computed in EDA)
```

---

## 8. Replay Compatibility

**Requirement:** Features generated from replay must be identical to live features.

**Verification:**
- Run replay script on saved raw data
- Compare feature values with live consumer output
- Ensure deterministic computation (no randomness)

---

## 9. Performance Targets

**Latency:**
- Feature computation: < 10ms per tick
- End-to-end (tick → feature): < 100ms

**Throughput:**
- Handle at least 100 ticks/second per product
- Support 2+ products simultaneously

---

## 10. Future Enhancements

**Potential Additional Features:**
- Order book depth (level 2 data)
- Volume-weighted average price (VWAP)
- Technical indicators (RSI, MACD)
- Cross-product correlations
- Market regime indicators

---

**Document Status:** Draft - Threshold value to be updated after EDA completion

