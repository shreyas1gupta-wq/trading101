# trading101 — survivorship-bias-free NSE swing-strategy backtester

A long-only, days-to-weeks swing backtesting system for Indian equities (NSE), built to
be **honest**: point-in-time index membership, delisted names included, realistic costs
and circuit-limit fills, and out-of-sample evaluation. It runs immediately on synthetic
data and switches to real data via a free-data waterfall.

## What makes it honest
- **Survivorship-bias-free universe** — every name that was *ever* a Nifty200/500 member
  (incl. the ~233/~503 that left, many because they collapsed), not just today's survivors.
- **Delisted prices included** — a bundled delisted price panel + a price waterfall, so the
  backtest can actually trade the dead names.
- **Realistic execution** — size-aware slippage, LC/UC circuit blocking, liquidity floor.
- **Out-of-sample first** — the number to trust is the rolling walk-forward, benchmarked
  against buy-&-hold of the index.

## Modules
| File | Role |
|---|---|
| `universe.py` | Point-in-time index membership from the constituent snapshots |
| `data_sources.py` | Free-data **waterfall** loader (yfinance → local/delisted → EODHD), despiking, benchmarks |
| `strategies.py` | 30 long-only strategies + registry; mean-reversion / cross-sectional / price-action / seasonal |
| `execution.py` | Realistic costs, **LC/UC circuit** fills, **trade blotter**, trade-stats |
| `portfolio.py` | Combine strategies (equal / inverse-vol / min-var / risk-parity / tangency-Kelly / HRP) |
| `swing_backtest.py` | Base backtest engine (flat-cost) |
| `kaggle_pipeline.py` | Orchestrator — `main()` runs the whole thing |
| `DATA_SOURCING.md` | How the price-data waterfall + your EODHD key work |
| `STRATEGY_CATALOG.md` | The strategy catalogue |

## Universe split
- **Nifty500** is the main test universe (cross-sectional, price-action, seasonal).
- **Mean-reversion runs on the more-liquid Nifty200** — catching falling knives in illiquid
  small-caps isn't tradable. Configurable via `CONFIG["mr_*"]`.

## Price-data waterfall (per ticker, first source that covers it)
1. **yfinance** — free, unlimited, split/dividend adjusted → survivors
2. **local** — your Kaggle EOD dump(s) + the bundled delisted panel → dead names Yahoo dropped
3. **EODHD** — adjusted but ~20 calls/day free tier → last resort, capped & cached;
   key read **only** from `$EODHD_API_KEY` (never committed)

Data hygiene: a despike filter nulls isolated bad ticks (>3× / <⅓ local median) before they
compound into fantasy returns. See `DATA_SOURCING.md`.

## Realistic execution
- **Slippage**: `per_side_bps = cost_bps + impact_coef × daily_vol_bps × √(trade_value/ADV)`;
  no-volume names pay `cost_bps + illiquid_surcharge_bps`.
- **Circuits**: can't BUY a name locked at the upper circuit, can't SELL one at the lower
  circuit → the trade is blocked and the position held (you miss the up-gap, you eat the down-gap).
- **Liquidity floor**: strategies only target names clearing a 20-day ADV minimum.

## Run it
**On Kaggle (real data):** new notebook, internet ON. Add this repo (incl. `data/`) as a
Dataset/Utility Script and optionally your NSE EOD dump as another Input; add a Kaggle Secret
`EODHD_API_KEY`. Point an extra `{"type":"local","path":"/kaggle/input/<your-eod>"}` at your
dump in `CONFIG["sources"]`, then:
```python
import kaggle_pipeline as kp
kp.main()
```
**Offline (plumbing/realism check):** runs on synthetic prices if no sources are configured,
or on the bundled delisted panel. `python kaggle_pipeline.py`.

The run: load universe → fetch prices (waterfall + coverage report) → backtest all strategies
**5 at a time**, saving each → trade-stats → combine (in-sample) → hold-out IS/OOS →
**rolling walk-forward** → benchmark vs NIFTY.

## Outputs
| File | Contents |
|---|---|
| `per_strategy_metrics.csv` | Per-strategy CAGR/vol/Sharpe/MaxDD/Calmar + trades + turnover |
| `per_strategy/<name>.csv` | Each strategy's daily net returns |
| `trades/<name>_trades.csv` | Full trade blotter: entry/exit dates+prices, hold, return, MFE/MAE trail |
| `trades_summary.csv` | Win rate / payoff / **expectancy** per strategy |
| `final_weights.csv` | Strategy allocation weights (each combiner) |
| `walkforward_returns.csv` | Out-of-sample walk-forward return series |
| `equity_curves.png`, `walkforward_equity.png` | Equity curves |

## What to trust
The **rolling walk-forward** numbers (every allocation decision used only past data) versus
the **buy-&-hold NIFTY benchmark** after costs. In-sample/full-sample numbers are optimistic
by construction. On synthetic or coverage-poor data, treat results as plumbing checks — the
coverage report (aim >90%) tells you which it is.
