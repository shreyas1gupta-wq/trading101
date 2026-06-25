# Sourcing price data (the one remaining blocker)

Your **constituent lists** make index membership survivorship-bias-free. But the
**price data** must match: it has to include the **delisted** names (the ~233
Nifty-200 tickers that left the index — many because they collapsed) and be
**split/bonus-adjusted**. Use survivor-only prices and your backtest looks far
better than reality even with a clean membership list.

`kaggle_pipeline.coverage_report()` checks this automatically and warns when
matched tickers < 90% of the universe.

## Options, ranked

| Option | Delisted-inclusive? | Adjusted? | Verdict |
|---|---|---|---|
| **NSE bhavcopy archives** (daily EOD for every stock that traded that day) | ✅ yes, by construction | ❌ raw — you must adjust | **Best for bias-free results.** The historical daily report lists delisted names while they still traded. |
| Survivor-only Kaggle dumps | ❌ current listings only | usually ✅ | Fine for a first sanity run; `coverage_report` will flag the bias. |
| Libraries (`jugaad-data`, `nsepy`, `yfinance` `.NS`) | ❌ mostly survivors | partial | Convenient on Kaggle (internet on), but gaps + survivor bias. |

### Concrete datasets the search surfaced
- **Bhavcopy (delisted-inclusive):** [akshaypawar7/nse-daily-bhavcopy](https://www.kaggle.com/datasets/akshaypawar7/nse-daily-bhavcopy) — bhavcopy dumps; the loader reads these directly (long format, `SYMBOL`/`SERIES`/`TOTTRDQTY`, auto-filters `SERIES==EQ`). Or pull NSE's [historical daily archives](https://www.nseindia.com/resources/historical-reports-capital-market-daily-monthly-archives) on Kaggle.
- **Survivor-only (easy first run):** [bhaktij/nse-stock-market-historical-data](https://www.kaggle.com/datasets/bhaktij/nse-stock-market-historical-data), [andrewmvd/india-stock-market](https://www.kaggle.com/datasets/andrewmvd/india-stock-market), [tilak123/nse-india-stock-prices](https://www.kaggle.com/datasets/tilak123/nse-india-stock-prices), [stacknishant/nse-stock-historical-price-data](https://www.kaggle.com/datasets/stacknishant/nse-stock-historical-price-data/data) (note: also filtered to mktcap > ₹500cr → extra large-cap bias), [pathikghugare/daily-indian-stock-price-dataset](https://www.kaggle.com/datasets/pathikghugare/daily-indian-stock-price-dataset), [adritpal08/indian-stock-market-dataset](https://www.kaggle.com/datasets/adritpal08/indian-stock-market-dataset).

## The adjustment problem (don't skip this)
Raw bhavcopy `CLOSE` is **unadjusted** — on an ex-split/bonus day the price gaps
(e.g. a 1:1 bonus halves the price overnight) and a mean-reversion strategy will
read that as a huge "crash to buy." You must either:
1. use a dataset that already provides **Adj Close** (the loader auto-uses it and
   back-adjusts OHLC), or
2. apply a **cumulative adjustment factor** from NSE corporate actions
   (splits/bonuses) to bhavcopy before backtesting.

## Wiring it in
- **Per-ticker CSVs in a folder** → set `CONFIG["price_path"]` to the folder.
- **One long CSV (bhavcopy)** → set `CONFIG["price_path"]` to the file.
- The loader auto-detects bhavcopy/Yahoo column names and the `SERIES==EQ` filter.
- Run `kaggle_pipeline.py`, read the **coverage report** (aim > 90%), then trust
  the **walk-forward** numbers.

## Recommended path
1. **First run:** a survivor-only *adjusted* dataset → confirms the machinery end-to-end (numbers will be optimistic; the coverage warning reminds you).
2. **Real conclusions:** bhavcopy + corporate-action adjustment → the only way to a backtest you can actually trust for a bear/sideways product.
