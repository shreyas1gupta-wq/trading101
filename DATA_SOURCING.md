# Price data — the free-data waterfall

The universe (`universe.py`) is survivorship-bias-free: it lists every name that was
**ever** a member (NIFTY200: 435 ever / ~202 live; NIFTY500: 1004 ever / ~501 live).
Prices must cover the delisted names too, or the backtest is biased on the price side.
No single *free* source has them all, so `data_sources.py` cascades **per ticker** and
takes the first source that covers it (per-ticker selection — never splicing adjusted
and raw quotes inside one series):

1. **yfinance** — free, unlimited, split/dividend **adjusted**. Covers survivors. Yahoo
   usually drops delisted Indian names, so they fall through to step 2.
2. **local** — your Kaggle EOD dump(s) **+ the bundled delisted price panel**
   (`data/NIFTY500_delisted_prices_2005_2025.xlsx`). This is where the dead names live.
3. **EODHD** — adjusted, but the free tier is **~20 calls/day**, so it runs **last** and
   only for names *still* missing, capped by `max_calls`, and every fetch is cached to
   disk so repeated runs accumulate coverage without re-spending the daily budget.

Configure it in `CONFIG["sources"]` (kaggle_pipeline.py). The default is already
yfinance → bundled delisted panel → EODHD.

## What's bundled in `data/`
| File | What it is | Used by |
|---|---|---|
| `NIFTY200_constituents_2005_2025.xlsx` | Nifty200 membership (Month-Year × Ticker, 42 snapshots) | `universe.py` |
| `NIFTY500_constituents_2005_2025.xlsx` | Nifty500 membership | `universe.py` |
| `NIFTY500_delisted_prices_2005_2025.xlsx` | **Daily price panel for 148 delisted names** (2005→2021, wide Date × ticker) | `local` source |
| `factor_navs_2005_2025.xlsx` | Daily NAV series (NIFTY 50/100/500, Midcap150, GOLDBEES…) | benchmark comparison |
| `nifty50_next50_composition.xlsx` | Monthly Nifty50/Next50 membership (2008→) | supplementary (not wired in) |

## Your EODHD key — keep it out of the repo
The key is read **only** from the `EODHD_API_KEY` environment variable, never hard-coded.
- **Kaggle:** Add-ons → Secrets → add `EODHD_API_KEY`; then in the notebook
  `os.environ["EODHD_API_KEY"] = UserSecretsClient().get_secret("EODHD_API_KEY")`.
- **Local:** `export EODHD_API_KEY=...`
- `.gitignore` blocks `.env`/`*.key`/`secrets.*`, and `cache/` (the per-ticker price cache).
- The free tier is ~20 calls/day and is **US-focused** — NSE/India coverage on free is
  limited, so treat EODHD as a gap-filler for a handful of still-missing names, not a bulk
  source. (If you upgrade, it just works — same code path.)

## Adding your saved Kaggle EOD dump
Add it as an Input on Kaggle, then add a line to `CONFIG["sources"]` (order = priority):
```python
{"type": "local", "path": "/kaggle/input/<your-nse-eod>"},   # dir of <SYMBOL>.csv, a long bhavcopy CSV, or a wide Date×ticker panel
```
`local` auto-detects three layouts: per-ticker dir, long CSV (`Date,Symbol,…` incl. NSE
bhavcopy), and wide panel (`Date` + one close column per ticker). Close-only is fine —
missing O/H/L are filled from close and volume left blank.

## Data hygiene (automatic)
- **Despike:** free EOD panels carry isolated bad ticks (e.g. `6649 → 46 → 6649`, or a
  `132 → 6000 → 129` spike). A long backtest that compounds the +144× "recovery" off such
  a tick reports fantasy CAGRs. The loader nulls any day deviating **>3× or <⅓** from its
  local median (far beyond NSE's ~±20% circuit bands → unambiguously a data error) and
  bridges the gap with a short ffill. Real multi-day declines are preserved. The run logs
  how many ticks were removed.
- **Close-only / no volume:** the liquidity filter can't assess a name with no volume, so
  it **doesn't exclude** it (unknown ≠ illiquid); the capacity report then degrades to a
  clear "not assessed" note instead of printing nonsense. Add a volume-bearing source to
  re-enable capacity analysis.

## Reading the output
`kaggle_pipeline.py` prints, per source, how many tickers it contributed and the final
**coverage** vs the universe (aim > 90%). Trust the **rolling walk-forward** numbers and
compare them to the **buy-&-hold NIFTY benchmark** — beating the index *after costs* is the
real test. Synthetic prices are used only when no sources are configured (offline plumbing
check).
