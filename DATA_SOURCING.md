# Sourcing price data (the one remaining blocker)

Your **constituent lists** make index membership survivorship-bias-free. The
**price data** must match: include the **delisted** names (the ~233 Nifty-200
tickers that left the index — many because they collapsed) and be
**split/bonus-adjusted**. Survivor-only or unadjusted prices make a backtest look
better than reality even with a clean membership list.

`kaggle_pipeline.coverage_report()` checks coverage automatically and warns when
matched tickers < 90% of the universe.

## What a scan of available data actually shows
- **Free NSE data is unadjusted.** Confirmed across sources — NSE historical
  prices are *not* adjusted for splits/bonuses; you adjust them yourself or buy
  adjusted data.
- **Free + delisted-inclusive** exists only via **bhavcopy** (each day's report
  lists every stock that traded, so dead names appear historically), or large
  multi-thousand-ticker dumps that happen to retain delisted names.
- **Turnkey bias-free + adjusted = paid** (EODHD, QuantRocket, TickData).

## Pick your tier

| Tier | Source | Bias-free? | Adjusted? | Effort / cost |
|---|---|---|---|---|
| **A — Turnkey (recommended if you'll spend a little)** | [EODHD](https://eodhd.com/) NSE EOD (markets itself survivorship-bias-free incl. delisted) or [QuantRocket](https://www.quantrocket.com/data/) | ✅ | ✅ | ~$20–60/mo; lowest effort, correct data |
| **B — Free + correct (DIY)** | NSE **bhavcopy** via [`jugaad-data`](https://github.com/jugaad-py/jugaad-data) on Kaggle, 2005–2025 | ✅ (bhavcopy = every stock trading that day) | ❌ you adjust | free; you build + adjust the panel |
| **C — Free + quick (biased)** | [stoicstatic 1990–2021](https://www.kaggle.com/datasets/stoicstatic/india-stock-data-nse-1990-2020) (1700+ tickers → likely many delisted) or survivor-only adjusted dumps | partial | varies | free; machinery sanity-check only, ends 2021 |

Survivor-only adjusted dumps for a fast first run:
[bhaktij](https://www.kaggle.com/datasets/bhaktij/nse-stock-market-historical-data),
[andrewmvd](https://www.kaggle.com/datasets/andrewmvd/india-stock-market),
[tilak123](https://www.kaggle.com/datasets/tilak123/nse-india-stock-prices),
[akshaypawar7/nse-daily-bhavcopy](https://www.kaggle.com/datasets/akshaypawar7/nse-daily-bhavcopy) (pre-collected bhavcopy — skips the download step in Tier B).

## Free bias-free route (Tier B): build the panel from bhavcopy on Kaggle
```python
# Kaggle cell, internet ON. Produces the delisted-inclusive long CSV the loader reads.
!pip -q install jugaad-data
from jugaad_data.nse import bhavcopy_save
from datetime import date, timedelta
import glob, os, pandas as pd

os.makedirs("bhav", exist_ok=True)
d, end = date(2005, 1, 1), date(2025, 9, 30)
while d <= end:
    try: bhavcopy_save(d, "bhav")        # raises on weekends/holidays -> skip
    except Exception: pass
    d += timedelta(days=1)               # NB: ~5000 files; throttle / resume if NSE rate-limits

df = pd.concat(pd.read_csv(f) for f in glob.glob("bhav/*.csv"))
df = df[df["SERIES"] == "EQ"][["SYMBOL","SERIES","OPEN","HIGH","LOW","CLOSE","TOTTRDQTY","TIMESTAMP"]]
df.to_csv("nse_bhavcopy_2005_2025.csv", index=False)   # -> CONFIG["price_path"] = ".../nse_bhavcopy_2005_2025.csv"
```
(To skip the slow download, attach the pre-collected `akshaypawar7/nse-daily-bhavcopy` dataset and `pd.concat` its CSVs instead.)

Then **adjust for splits/bonuses** — otherwise mean-reversion signals misread
ex-dates as crashes. Pull corporate actions from
[NSE corporate actions](https://www.nseindia.com/companies-listing/corporate-filings-actions),
build a cumulative factor per symbol, divide pre-event OHLC by it, and write the
result as an **`Adj Close`** column — the loader auto-detects it and back-adjusts OHLC.

## Wiring it in
- Per-ticker CSVs in a folder → `CONFIG["price_path"] = "<folder>"`.
- One long CSV (bhavcopy) → `CONFIG["price_path"] = "<file>.csv"`.
- The loader auto-handles bhavcopy/Yahoo column names and the `SERIES==EQ` filter.
- Run `kaggle_pipeline.py`, read the **coverage report** (aim > 90%), then trust
  the **walk-forward** numbers.

## Bottom line
- Correct with least effort → **EODHD / QuantRocket (Tier A)**.
- Free and correct → **bhavcopy + adjustment (Tier B)**; I can write the adjustment step next.
- Just see the machine run → **Tier C**, knowing it's optimistic (coverage report will warn).
