# Strategy specifications

Auto-generated from `strategies.SPECS` (kept beside the code). Shared controls:

- **Universe** — Nifty200 for mean-reversion, Nifty500 otherwise; 20-day ADV liquidity floor.
- **Regime gate** — exposure × {1.0 weak/sideways · 0.5 strong uptrend · 0.3 crash-brake when 10-day market return < −8%}; seasonal strategies excepted.
- **Execution** — next-close fill, LC/UC circuit blocking, size-aware slippage.
- **Stops** — NO hard price stop-loss and NO trailing stop anywhere; exits are signal + time-stop. Add an SL/trailing overlay if you want hard stops.

## Mean-Reversion  ·  NIFTY200
### A_rsi2
- **entry** — RSI(2) < 10 and close > 200-DMA
- **exit** — RSI(2) > 70, else 6-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — 200-DMA uptrend + regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤6d  ·  **data** — Close

### A_connors_rsi
- **entry** — ConnorsRSI ≈ ½[RSI(3) of price + RSI(2) of up/down streak] < 15
- **exit** — ConnorsRSI > 65, else 6-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤6d  ·  **data** — Close

### A_cumulative_rsi
- **entry** — 2-day sum of RSI(2) < 35 and close > 200-DMA
- **exit** — RSI(2) > 65, else 6-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — 200-DMA uptrend + regime + ADV
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤6d  ·  **data** — Close

### A_ibs
- **entry** — IBS < 0.2 (close near the day's low)
- **exit** — IBS > 0.7, else 5-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤5d  ·  **data** — High/Low/Close

### A_bollinger_pctb
- **entry** — %B < 0 (close below lower 20,2σ Bollinger band)
- **exit** — close > 20-SMA, else 8-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤8d  ·  **data** — Close

### A_dist_ma_z
- **entry** — (close − 50-SMA) / ATR(14) < −2.5
- **exit** — z > −0.2, else 10-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤10d  ·  **data** — High/Low/Close

### A_ou_reversion
- **entry** — 10-day z-score of close < −1.5
- **exit** — z > 0, else 12-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤12d  ·  **data** — Close

### A_williams_r
- **entry** — Williams %R(10) < −90
- **exit** — %R > −30, else 6-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤6d  ·  **data** — High/Low/Close

### A_cci
- **entry** — CCI(20) < −150
- **exit** — CCI > 0, else 8-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤8d  ·  **data** — High/Low/Close

### A_double7s
- **entry** — close = 7-day low and close > 200-DMA
- **exit** — close = 7-day high, else 10-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — 200-DMA uptrend + regime + ADV
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤10d  ·  **data** — Close

### A_rsi2_divergence
- **entry** — RSI(2) < 10 and RSI(14) rising vs 5 days ago
- **exit** — RSI(14) > 60, else 8-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤8d  ·  **data** — Close

### A_ensemble_mr
- **entry** — ≥2 of {RSI(2)<10, IBS<0.2, %B<0, z(10)<−2}
- **exit** — all four signals off, else 6-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤6d  ·  **data** — High/Low/Close

## Cross-Sectional  ·  NIFTY500
### D_xs_reversal_5d
- **entry** — long the bottom 10% by 5-day return (biggest losers)
- **exit** — hold to next rebalance
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — equal-weight selected decile × regime gate  ·  **hold** — rebalance 5d  ·  **data** — Close

### D_reversal_1m
- **entry** — long the bottom 10% by 21-day return
- **exit** — hold to next rebalance
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — equal-weight selected decile × regime gate  ·  **hold** — rebalance 21d  ·  **data** — Close

### D_rel_strength_4w
- **entry** — long the TOP 10% by 21-day return (winners)
- **exit** — hold to next rebalance
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — equal-weight selected decile × regime gate  ·  **hold** — rebalance 5d  ·  **data** — Close

### D_residual_momentum
- **entry** — long top 10% by 21-day sum of market-beta-residual return (β over 60d)
- **exit** — hold to next rebalance
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — equal-weight selected decile × regime gate  ·  **hold** — rebalance 21d  ·  **data** — Close

### D_low_vol_tilt
- **entry** — long the bottom 10% by 20-day volatility (lowest-vol names)
- **exit** — hold to next rebalance
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — equal-weight selected decile × regime gate  ·  **hold** — rebalance 21d  ·  **data** — Close

### D_beta_rotation
- **entry** — long the bottom 10% by 60-day market beta (low-beta)
- **exit** — hold to next rebalance
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — equal-weight selected decile × regime gate  ·  **hold** — rebalance 21d  ·  **data** — Close

### D_dispersion_gated_reversal
- **entry** — 5-day reversal bottom 10%, ONLY when cross-sectional 5-day dispersion > its 120-day median
- **exit** — hold to next rebalance
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — dispersion gate + regime gate + ADV floor
- **sizing** — equal-weight selected decile × regime gate  ·  **hold** — rebalance 5d  ·  **data** — Close

## Price-Action  ·  NIFTY500
### E_gap_down_fade
- **entry** — open < prev close × 0.97 (gap down > 3%)
- **exit** — close ≥ prev close (gap filled), else 5-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤5d  ·  **data** — Open/Close

### E_failed_breakdown
- **entry** — low < prior 20-day low AND close > that low (broke then reclaimed)
- **exit** — close > 20-SMA, else 8-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤8d  ·  **data** — Low/Close

### E_selling_climax
- **entry** — volume > 2× 20-day avg AND lower-wick > 66% of range AND down day
- **exit** — close > 5-SMA, else 5-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤5d  ·  **data** — OHLCV

### E_vwap_reversion
- **entry** — close < 20-day VWAP × 0.95
- **exit** — close ≥ VWAP, else 8-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤8d  ·  **data** — OHLCV

### E_pullback_to_ma
- **entry** — uptrend (close>50-SMA, 20-SMA rising) AND low ≤ 20-SMA AND close > 20-SMA
- **exit** — close = 10-day high, else 8-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤8d  ·  **data** — Low/Close

### E_n_down_days
- **entry** — 4 consecutive down days AND close > 50-SMA
- **exit** — first up day, else 5-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤5d  ·  **data** — Close

### E_nr7_breakout
- **entry** — prior day = narrowest range in 7 (NR7) AND close > prior day's high
- **exit** — close < 5-SMA, else 5-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤5d  ·  **data** — High/Low/Close

### E_bollinger_squeeze
- **entry** — prior-day bandwidth = 126-day minimum (squeeze) AND close > prev close
- **exit** — close < 10-SMA, else 10-day time-stop
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate + ADV floor
- **sizing** — inverse-vol across signalled members × regime gate  ·  **hold** — ≤10d  ·  **data** — Close

## Event  ·  NIFTY500
### C_index_reconstitution
- **entry** — buy names ADDED to the index at each semi-annual reconstitution
- **exit** — hold ~20 trading days
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — regime gate
- **sizing** — equal-weight the additions × regime gate  ·  **hold** — ~20d  ·  **data** — constituent snapshots

## Seasonal  ·  NIFTY500
### C_turn_of_month
- **entry** — hold ALL members on the last trading day + first 3 of each month
- **exit** — outside that window
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — universe + ADV (NO regime gate)
- **sizing** — equal-weight all members  ·  **hold** — ~4d/month  ·  **data** — Close + calendar

### C_expiry_week
- **entry** — hold ALL members during the last 5 trading days of each month (≈ F&O expiry week)
- **exit** — outside that window
- **stop / trail** — none (signal + time-stop only) / none
- **filters** — universe + ADV (NO regime gate)
- **sizing** — equal-weight all members  ·  **hold** — 5d/month  ·  **data** — Close + calendar

## Stubs (registered, need extra data)
- **C_pead** (event) — needs earnings-surprise data
- **C_earnings_gap_reversal** (event) — needs earnings dates
- **C_pre_earnings_drift** (event) — needs earnings calendar
- **C_estimate_revision** (event) — needs analyst estimates
- **C_buyback_insider** (event) — needs buyback/insider filings
- **C_bulk_block_deal** (event) — needs bulk/block-deal feed
- **C_ex_date_reversion** (event) — needs dividend/ex-dates
- **C_demerger_drift** (event) — needs corporate-action data
- **D_quality_minus_junk** (cross-sectional) — needs fundamentals
- **D_defensive_sector_rotation** (cross-sectional) — needs sector map
- **D_cointegration_pairs** (cross-sectional) — needs pair-selection step
