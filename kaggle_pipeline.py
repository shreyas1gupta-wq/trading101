"""
Kaggle orchestrator  |  end-to-end: constituents -> strategies -> final portfolio
================================================================================
Runs the whole pipeline in one place, designed to execute on a Kaggle notebook
(free compute + internet + datasets) where real NSE price data lives. It runs
immediately on SYNTHETIC prices so you can validate the plumbing, then switches
to REAL data the moment you point CONFIG at a price dataset.

HOW TO RUN ON KAGGLE
--------------------
1. New Notebook. Add data:
     • this repo's files (universe.py, portfolio.py, strategies.py, swing_backtest.py,
       data/NIFTY200_constituents_2005_2025.xlsx)  -> upload as a Dataset or Utility Script
     • a price dataset (see DATA CONTRACT below) -> Add Input
2. Set CONFIG["price_path"] to the price dataset path under /kaggle/input/...
3. Run.  -> prints per-strategy + combined metrics (in-sample AND out-of-sample),
            saves equity curves, weights, and an equity-curve PNG.

DATA CONTRACT (what the price dataset must provide)
---------------------------------------------------
ADJUSTED (split/bonus) daily OHLCV, 2005-2025, for NSE symbols matching the
constituent tickers. Two accepted layouts (auto-detected):
  (a) one CSV per ticker:  <SYMBOL>.csv  with Date,Open,High,Low,Close,Volume
      (and optionally 'Adj Close' / 'Adjusted' — used in preference to Close)
  (b) one long CSV:        Date,Symbol,Open,High,Low,Close,Volume[,Adj Close]

CRITICAL: the dataset must include DELISTED names (the ~233 Nifty-200 tickers that
left the index, many of which blew up). The coverage report below tells you how
many constituents matched — if it's far below the universe size, your prices are
survivor-only and results will be optimistically biased even though membership is
point-in-time. (Aim for >90% coverage.)
"""

import os
import glob
import numpy as np
import pandas as pd

import portfolio
import strategies as S
from universe import IndexUniverse, NIFTY200, NIFTY500

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CONFIG = {
    "index":       "NIFTY200",          # or "NIFTY500"
    "constituents": NIFTY200,           # path to the constituent xlsx
    "price_path":  None,                # e.g. "/kaggle/input/nse-eod/prices"  (dir or .csv); None -> synthetic
    "start":       "2006-01-01",
    "end":         "2024-12-31",
    "min_sharpe":  0.5,                 # selection bar (applied on the TRAIN window only)
    "holdout":     0.5,                 # fraction of time used for in-sample selection; rest is OOS
    "out_dir":     ".",
}


# ── real price loaders (adaptable; synthetic fallback) ─────────────────────────
def _norm(sym):
    return str(sym).strip().upper().replace(".NS", "").replace(".BO", "")


def _adj_col(cols):
    for c in cols:
        if str(c).strip().lower() in ("adj close", "adjusted", "adj_close", "adjclose"):
            return c
    return None


def load_prices(price_path, tickers, dates):
    """Return (Prices, source_str). Falls back to synthetic if price_path is None/empty."""
    if not price_path or not os.path.exists(price_path):
        px, src = S.make_synthetic_ohlcv(tickers, dates)
        return px, src + "  [no price_path -> SYNTHETIC]"

    frames = {f: {} for f in ("open", "high", "low", "close", "volume")}
    want = set(tickers)

    def _ingest(sym, df):
        sym = _norm(sym)
        if sym not in want:
            return
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        adj = _adj_col(df.columns)
        close = df[adj] if adj else df["Close"]
        # if an adjusted close exists, scale OHLC by the same factor to stay consistent
        scale = (close / df["Close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
        frames["open"][sym]   = df["Open"] * scale
        frames["high"][sym]   = df["High"] * scale
        frames["low"][sym]    = df["Low"] * scale
        frames["close"][sym]  = close
        frames["volume"][sym] = df.get("Volume", pd.Series(np.nan, index=df.index))

    if os.path.isdir(price_path):                       # layout (a): one CSV per ticker
        for fp in glob.glob(os.path.join(price_path, "*.csv")):
            _ingest(os.path.splitext(os.path.basename(fp))[0], pd.read_csv(fp))
    else:                                               # layout (b): one long CSV
        big = pd.read_csv(price_path)
        big.columns = [str(c).strip() for c in big.columns]
        symcol = next(c for c in big.columns if c.lower() in ("symbol", "ticker", "name"))
        for sym, df in big.groupby(symcol):
            _ingest(sym, df)

    idx = pd.bdate_range(dates.min(), dates.max())
    def panel(d):
        return pd.DataFrame(d).reindex(idx).sort_index().ffill(limit=5)
    px = S.Prices(panel(frames["open"]), panel(frames["high"]), panel(frames["low"]),
                  panel(frames["close"]), panel(frames["volume"]))
    return px, f"REAL prices from {price_path}"


def coverage_report(px, uni):
    matched = [t for t in uni.all_tickers() if t in px.close.columns
               and px.close[t].notna().any()]
    n_all = len(uni.all_tickers())
    pct = 100 * len(matched) / n_all
    print(f"\n=== Price coverage ===  {len(matched)}/{n_all} constituents matched ({pct:.0f}%)")
    if pct < 90:
        print("  ⚠ LOW COVERAGE: delisted names are likely missing -> survivorship bias on the")
        print("    PRICE side even though membership is point-in-time. Treat results as optimistic.")
    return matched


# ── out-of-sample evaluation ───────────────────────────────────────────────────
def holdout_combine(R, split=0.5, min_sharpe=0.5):
    """Select strategies + fit allocation weights on the TRAIN window, then apply
    those fixed weights to the unseen TEST window. Honest (no look-ahead) estimate."""
    cut = int(len(R) * split)
    Rtr, Rte = R.iloc[:cut], R.iloc[cut:]
    keep = [c for c in Rtr.columns if portfolio._perf(Rtr[c])["sharpe"] >= min_sharpe]
    if len(keep) < 2:
        return None, None, keep
    _, weights, _, _ = portfolio.combine(Rtr[keep])
    oos = {m: portfolio._perf(Rte[keep] @ weights[m]) for m in weights.columns}
    is_ = {m: portfolio._perf(Rtr[keep] @ weights[m]) for m in weights.columns}
    return (pd.DataFrame(is_).T[["cagr", "sharpe", "maxdd"]],
            pd.DataFrame(oos).T[["cagr", "sharpe", "maxdd"]], keep)


# ── main ────────────────────────────────────────────────────────────────────────
def main(cfg=CONFIG):
    uni = IndexUniverse(cfg["constituents"])
    print(uni.summary())
    tickers = uni.all_tickers()
    dates = pd.bdate_range(cfg["start"], cfg["end"])

    px, src = load_prices(cfg["price_path"], tickers, dates)
    print(f"Prices: {src}  shape={px.close.shape}")
    matched = coverage_report(px, uni)
    ctx = {"membership": uni.daily_mask(px.close.index, tickers), "universe": uni}

    print(f"\n=== Backtesting {len(S.REGISTRY)} strategies on {cfg['index']} ===")
    table, R = S.run_all(px, ctx)
    table.to_csv(os.path.join(cfg["out_dir"], "per_strategy_metrics.csv"))

    print("\n=== FULL-SAMPLE combine (in-sample selection — optimistic) ===")
    Rsel, keep = S.select_by_sharpe(table, R, cfg["min_sharpe"])
    if Rsel.shape[1] >= 2:
        mtab, weights, k, corr = portfolio.combine(Rsel)
        print(mtab.to_string())
        weights.to_csv(os.path.join(cfg["out_dir"], "final_weights.csv"))
        print(f"avg strategy correlation = {corr['avg']:.2f}; "
              f"Kelly leverage (unlevered cap) = {k['leverage_unlevered']:.2f}x")

    print("\n=== HOLD-OUT combine (select+weight on train, report on unseen test) ===")
    is_, oos, keep_h = holdout_combine(R, cfg["holdout"], cfg["min_sharpe"])
    if oos is not None:
        print(f"selected on train: {keep_h}")
        cmp = is_.join(oos, lsuffix="_IS", rsuffix="_OOS")
        print(cmp.to_string())
        print("\n-> Trust the _OOS columns. A big IS->OOS drop = overfit selection;")
        print("   production should roll this train/test split forward through time.")
    else:
        print("Too few strategies cleared the bar on the train window.")

    _plot(R, keep, cfg)
    print("\nDone. Outputs: per_strategy_metrics.csv, final_weights.csv, equity_curves.png")


def _plot(R, keep, cfg):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    if not keep:
        return
    Rsel = R[keep]
    _, weights, _, _ = portfolio.combine(Rsel)
    fig, ax = plt.subplots(figsize=(11, 6))
    for m in ["equal", "hrp", "tangency/kelly", "min_variance"]:
        if m in weights:
            (1 + (Rsel @ weights[m])).cumprod().plot(ax=ax, label=m, lw=1.6)
    (1 + Rsel.mean(axis=1)).cumprod().plot(ax=ax, label="avg of selected", ls="--", c="grey")
    ax.set_yscale("log"); ax.legend(); ax.set_title(f"Combined portfolio equity — {cfg['index']}")
    ax.set_ylabel("growth of 1 (log)")
    fig.tight_layout(); fig.savefig(os.path.join(cfg["out_dir"], "equity_curves.png"), dpi=110)


if __name__ == "__main__":
    main()
