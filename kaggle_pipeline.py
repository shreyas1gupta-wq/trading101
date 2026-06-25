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
    "wf_train":    756,                 # walk-forward train window (~3y of trading days)
    "wf_test":     126,                 # walk-forward test window  (~6m); also the re-fit step
    "cost_bps":    18.0,                # per-side slippage+cost in bps (round-trip ~2x); stress-test small-caps higher
    "min_adv_cr":  5.0,                 # liquidity floor: drop names with 20d avg daily value < this (₹ crore)
    "aum_cr":      50.0,                # assumed book size for the capacity report (₹ crore)
    "max_participation": 0.10,          # a position may be at most this fraction of a name's ADV
    "out_dir":     ".",
}


# ── real price loaders (adaptable; synthetic fallback) ─────────────────────────
def _norm(sym):
    return str(sym).strip().upper().replace(".NS", "").replace(".BO", "")


# canonical column <- accepted aliases (covers NSE bhavcopy and Yahoo-style exports)
_ALIASES = {
    "Date":     {"date", "timestamp", "tradedate", "trade_date", "dt", "time"},
    "Open":     {"open", "open price", "openprice"},
    "High":     {"high", "high price"},
    "Low":      {"low", "low price"},
    "Close":    {"close", "close price", "closeprice"},  # NOT 'last'/'ltp' (distinct fields)
    "AdjClose": {"adj close", "adjusted", "adj_close", "adjclose", "adjusted close"},
    "Volume":   {"volume", "tottrdqty", "total traded quantity", "totaltradedquantity", "qty", "vol"},
    "Symbol":   {"symbol", "ticker", "name", "scrip", "scripname"},
    "Series":   {"series"},
}


def _canon(df):
    """Rename columns to canonical names and keep cash-equity rows (SERIES==EQ) if present."""
    df = df.copy()
    ren = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        for canon, al in _ALIASES.items():
            if lc in al:
                ren[c] = canon
    df = df.rename(columns=ren)
    df = df.loc[:, ~df.columns.duplicated()]             # guard against alias collisions
    if "Series" in df.columns:                          # bhavcopy carries EQ/BE/SM... keep EQ
        df = df[df["Series"].astype(str).str.strip() == "EQ"]
    return df


def load_prices(price_path, tickers, dates):
    """Return (Prices, source_str). Falls back to synthetic if price_path is None/empty.
    Auto-handles bhavcopy (long, SYMBOL/SERIES/TOTTRDQTY) and Yahoo-style (Adj Close) layouts."""
    if not price_path or not os.path.exists(price_path):
        px, src = S.make_synthetic_ohlcv(tickers, dates)
        return px, src + "  [no price_path -> SYNTHETIC]"

    frames = {f: {} for f in ("open", "high", "low", "close", "volume")}
    want = set(tickers)

    def _ingest(sym, df):
        sym = _norm(sym)
        if sym not in want:
            return
        df = _canon(df)
        if "Date" not in df.columns or "Close" not in df.columns:
            return
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
        df = df[~df.index.duplicated(keep="last")]       # drop accidental dup rows
        close = df["AdjClose"] if "AdjClose" in df.columns else df["Close"]
        scale = (close / df["Close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)  # back-adjust OHLC
        frames["open"][sym]   = df.get("Open", close) * scale
        frames["high"][sym]   = df.get("High", close) * scale
        frames["low"][sym]    = df.get("Low", close) * scale
        frames["close"][sym]  = close
        frames["volume"][sym] = df.get("Volume", pd.Series(np.nan, index=df.index))

    if os.path.isdir(price_path):                       # layout (a): one CSV per ticker
        for fp in glob.glob(os.path.join(price_path, "*.csv")):
            _ingest(os.path.splitext(os.path.basename(fp))[0], pd.read_csv(fp))
    else:                                               # layout (b): one long CSV (e.g. bhavcopy)
        big = _canon(pd.read_csv(price_path))
        if "Symbol" not in big.columns:
            raise ValueError("long CSV needs a Symbol/Ticker column (or use a per-ticker dir)")
        for sym, df in big.groupby("Symbol"):
            _ingest(sym, df)

    idx = pd.bdate_range(dates.min(), dates.max())
    def panel(d):
        return pd.DataFrame(d).reindex(idx).sort_index().ffill(limit=5)
    px = S.Prices(panel(frames["open"]), panel(frames["high"]), panel(frames["low"]),
                  panel(frames["close"]), panel(frames["volume"]))
    return px, f"REAL prices from {price_path}"


def adv_crore(px, n=20):
    """20-day average daily traded value in ₹ crore (1 cr = 1e7)."""
    return (px.close * px.volume).rolling(n).mean() / 1e7


def liquidity_mask(px, min_adv_cr):
    """Tradable only where 20d ADV >= floor. Filtering out illiquids is more honest
    than modelling huge slippage on names you could never fill at swing size."""
    return adv_crore(px) >= min_adv_cr


def net_book_weights(px, ctx, strat_alloc):
    """Net STOCK-level book = Σ_strategy (allocation × that strategy's stock weights).
    portfolio.combine() gives weights ACROSS strategies; this turns them back into
    actual per-name positions over time, which is what capacity is about."""
    net = None
    for name, a in strat_alloc.items():
        w = S.REGISTRY[name][1](px, ctx) * a
        net = w if net is None else net.add(w, fill_value=0.0)
    return net.fillna(0.0)


def capacity_report(px, book, cfg):
    """`book` = dates x stocks net weight matrix. At the assumed AUM, how often does a
    position exceed `max_participation` of that name's ADV, and what's the max book
    size before the most-binding position breaches the cap?"""
    adv = adv_crore(px).reindex(columns=book.columns)
    held = book > 1e-6
    pos_value = book * cfg["aum_cr"]                          # ₹cr per name per day
    breaches = (pos_value > cfg["max_participation"] * adv) & held
    pct = 100 * breaches.sum().sum() / max(1, held.sum().sum())
    ratio = (cfg["max_participation"] * adv).where(held) / book.where(held)   # max AUM per position
    max_aum = ratio.stack().quantile(0.05)   # robust: AUM keeping ~95% of positions within the cap
    print(f"\n=== Capacity @ ₹{cfg['aum_cr']:.0f}cr book, max {cfg['max_participation']:.0%} of ADV/name ===")
    print(f"  positions breaching the participation cap: {pct:.0f}% of held position-days")
    print(f"  book size keeping ~95% of positions within the cap: ≈ ₹{max_aum:.0f} crore")
    if pct > 20:
        print("  ⚠ at this AUM many positions are too big for the names' liquidity -> "
              "lower AUM, raise min_adv_cr, or add a per-name weight cap.")


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


def walk_forward_combine(R, train=756, test=126, min_sharpe=0.5):
    """Rolling walk-forward: the production-grade OOS test. For each test window,
    RE-select strategies and RE-fit allocation weights using ONLY the preceding
    `train` days, then apply them to the next `test` days. Stitch the test-window
    returns into one continuous out-of-sample track per method. The strategy set
    is allowed to change over time (as it must in practice).

    train/test in trading days (756≈3y, 126≈6m). Returns (metrics, oos_series, log)."""
    methods = ["equal", "inverse_vol", "min_variance", "risk_parity", "tangency/kelly", "hrp"]
    oos = {m: [] for m in methods}
    log = []
    start = train
    while start + test <= len(R):
        Rtr, Rte = R.iloc[start - train:start], R.iloc[start:start + test]
        keep = [c for c in Rtr.columns if portfolio._perf(Rtr[c])["sharpe"] >= min_sharpe]
        if len(keep) >= 2:
            _, w, _, _ = portfolio.combine(Rtr[keep])
            for m in methods:
                oos[m].append(Rte[keep] @ w[m])
        else:                                            # nothing qualified -> hold cash
            for m in methods:
                oos[m].append(pd.Series(0.0, index=Rte.index))
        log.append((R.index[start].date(), len(keep)))
        start += test
    if not log:
        return None, None, log
    series = {m: pd.concat(v) for m, v in oos.items()}
    table = pd.DataFrame({m: portfolio._perf(s) for m, s in series.items()}).T[
        ["cagr", "vol", "sharpe", "maxdd", "calmar"]]
    return table, series, log


# ── main ────────────────────────────────────────────────────────────────────────
def main(cfg=CONFIG):
    uni = IndexUniverse(cfg["constituents"])
    print(uni.summary())
    tickers = uni.all_tickers()
    dates = pd.bdate_range(cfg["start"], cfg["end"])

    px, src = load_prices(cfg["price_path"], tickers, dates)
    print(f"Prices: {src}  shape={px.close.shape}")
    matched = coverage_report(px, uni)

    uni_mask = uni.daily_mask(px.close.index, tickers)
    membership = uni_mask & liquidity_mask(px, cfg["min_adv_cr"]).reindex_like(uni_mask).fillna(False)
    kept = membership.sum().sum() / max(1, uni_mask.sum().sum())
    print(f"Liquidity filter (20d ADV >= ₹{cfg['min_adv_cr']:.0f}cr): "
          f"{100*kept:.0f}% of member-days remain tradable")
    ctx = {"membership": membership, "universe": uni}

    print(f"\n=== Backtesting {len(S.REGISTRY)} strategies on {cfg['index']} "
          f"({cfg['cost_bps']:.0f} bps/side) ===")
    table, R = S.run_all(px, ctx, cost_bps=cfg["cost_bps"])
    table.to_csv(os.path.join(cfg["out_dir"], "per_strategy_metrics.csv"))

    print("\n=== FULL-SAMPLE combine (in-sample selection — optimistic) ===")
    Rsel, keep = S.select_by_sharpe(table, R, cfg["min_sharpe"])
    if Rsel.shape[1] >= 2:
        mtab, weights, k, corr = portfolio.combine(Rsel)
        print(mtab.to_string())
        weights.to_csv(os.path.join(cfg["out_dir"], "final_weights.csv"))
        print(f"avg strategy correlation = {corr['avg']:.2f}; "
              f"Kelly leverage (unlevered cap) = {k['leverage_unlevered']:.2f}x")
        # capacity: net the selected strategies (equal-allocated) into a stock-level book
        alloc = pd.Series(1.0 / len(keep), index=keep)
        capacity_report(px, net_book_weights(px, ctx, alloc), cfg)

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

    print("\n=== ROLLING WALK-FORWARD (production-grade OOS — trust THIS) ===")
    wf_tab, wf_series, wf_log = walk_forward_combine(
        R, cfg["wf_train"], cfg["wf_test"], cfg["min_sharpe"])
    if wf_tab is not None:
        print(f"re-fit every {cfg['wf_test']} days on a {cfg['wf_train']}-day trailing window; "
              f"{len(wf_log)} folds")
        print(f"strategies selected per fold: min={min(n for _, n in wf_log)}, "
              f"max={max(n for _, n in wf_log)}, "
              f"avg={np.mean([n for _, n in wf_log]):.1f}")
        print(wf_tab.to_string())
        pd.DataFrame(wf_series).to_csv(os.path.join(cfg["out_dir"], "walkforward_returns.csv"))
        print("\n-> This is the realistic estimate: every allocation decision used ONLY past data.")
    else:
        print(f"Not enough history for a {cfg['wf_train']}+{cfg['wf_test']}-day walk-forward.")

    _plot(R, keep, cfg, wf_series if wf_tab is not None else None)
    print("\nDone. Outputs: per_strategy_metrics.csv, final_weights.csv, "
          "walkforward_returns.csv, equity_curves.png, walkforward_equity.png")


def _plot(R, keep, cfg, wf_series=None):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    if keep:                                             # full-sample (in-sample) curves
        Rsel = R[keep]
        _, weights, _, _ = portfolio.combine(Rsel)
        fig, ax = plt.subplots(figsize=(11, 6))
        for m in ["equal", "hrp", "tangency/kelly", "min_variance"]:
            if m in weights:
                (1 + (Rsel @ weights[m])).cumprod().plot(ax=ax, label=m, lw=1.6)
        (1 + Rsel.mean(axis=1)).cumprod().plot(ax=ax, label="avg of selected", ls="--", c="grey")
        ax.set_yscale("log"); ax.legend()
        ax.set_title(f"Combined portfolio equity (full-sample) — {cfg['index']}")
        ax.set_ylabel("growth of 1 (log)")
        fig.tight_layout(); fig.savefig(os.path.join(cfg["out_dir"], "equity_curves.png"), dpi=110)
        plt.close(fig)
    if wf_series is not None:                            # walk-forward (out-of-sample) curves
        fig, ax = plt.subplots(figsize=(11, 6))
        for m in ["equal", "hrp", "tangency/kelly", "min_variance"]:
            if m in wf_series:
                (1 + wf_series[m]).cumprod().plot(ax=ax, label=m, lw=1.6)
        ax.set_yscale("log"); ax.legend()
        ax.set_title(f"Walk-forward (out-of-sample) equity — {cfg['index']}")
        ax.set_ylabel("growth of 1 (log)")
        fig.tight_layout(); fig.savefig(os.path.join(cfg["out_dir"], "walkforward_equity.png"), dpi=110)
        plt.close(fig)


if __name__ == "__main__":
    main()
