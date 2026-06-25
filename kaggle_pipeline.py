"""
Kaggle orchestrator  |  end-to-end: constituents -> strategies -> final portfolio
================================================================================
Runs the whole pipeline in one place, designed to execute on a Kaggle notebook
(free compute + internet + datasets) where real NSE price data lives. It runs
immediately on SYNTHETIC prices so you can validate the plumbing, then switches
to REAL data the moment you point CONFIG at a price dataset.

PRICE DATA — a free-data WATERFALL (see data_sources.py)
--------------------------------------------------------
The hard part is sourcing prices for the DELISTED names (the ~233 Nifty-200 / ~503
Nifty-500 tickers that left the index, many because they blew up) without which the
backtest is survivorship-biased on the price side. No single free source has them
all, so CONFIG["sources"] cascades per ticker and takes the first that covers it:

  1. yfinance  -- free/unlimited, split+dividend ADJUSTED -> survivors
  2. local     -- the bundled delisted price panel + any Kaggle EOD dump you add
  3. EODHD     -- adjusted, but free tier ~20 calls/day -> last resort, capped, cached
                  (key read ONLY from the $EODHD_API_KEY env var / Kaggle Secret)

It still runs immediately on SYNTHETIC prices (no sources -> synthetic) so the
plumbing is verifiable offline. The coverage report prints how many constituents
matched and from which source; aim for >90%.

HOW TO RUN ON KAGGLE
--------------------
1. New Notebook (internet ON). Add this repo (incl. data/) as a Dataset/Utility Script,
   and optionally your saved NSE EOD dump as another Input.
2. Point an extra {"type":"local","path":"/kaggle/input/<your-eod>"} entry in
   CONFIG["sources"] at that dump; add your EODHD key as a Kaggle Secret named
   EODHD_API_KEY. (Defaults already use yfinance + the bundled delisted panel.)
3. Run -> per-strategy + combined metrics (in-sample AND out-of-sample), capacity,
   walk-forward, benchmark vs NIFTY index, and saved curves/weights.
"""

import os
import glob
import numpy as np
import pandas as pd

import portfolio
import strategies as S
import data_sources as DS
from universe import IndexUniverse, NIFTY200, NIFTY500

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CONFIG = {
    "index":       "NIFTY200",          # or "NIFTY500"
    "constituents": NIFTY200,           # path to the constituent xlsx
    "price_path":  None,                # back-compat: a single local dir/CSV (added as a 'local' source)
    "sources": [                        # the free-data WATERFALL — first source that has a ticker wins
        {"type": "yfinance", "suffix": ".NS"},                                      # survivors, adjusted, unlimited
        {"type": "local", "path": "data/NIFTY500_delisted_prices_2005_2025.xlsx"},  # bundled delisted panel
        # {"type": "local", "path": "/kaggle/input/<your-nse-eod>"},                # <- add your saved Kaggle EOD here
        {"type": "eodhd", "exchange": "NSE", "max_calls": 20},                      # last resort; key from $EODHD_API_KEY
    ],
    "cache_dir":   "cache",             # per-ticker CSV cache (yfinance/EODHD) so re-runs don't re-fetch
    "benchmarks":  "data/factor_navs_2005_2025.xlsx",   # index NAV series for a buy&hold comparison (optional)
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


# ── price loading: delegate to the data_sources waterfall (synthetic fallback) ──
def load_prices(cfg, tickers, dates):
    """Build the price panel via data_sources.build_panel (yfinance -> local -> EODHD).
    Returns (Prices, source_str, provenance, notes). Falls back to SYNTHETIC when no
    sources are configured or the cascade resolves nothing, so the plumbing still
    runs end-to-end offline."""
    sources = cfg.get("sources")
    if not sources and cfg.get("price_path"):                 # back-compat single path
        sources = [{"type": "local", "path": cfg["price_path"]}]
    if not sources:
        px, src = S.make_synthetic_ohlcv(tickers, dates)
        return px, src + "  [no sources configured -> SYNTHETIC]", {}, []

    px, prov, notes = DS.build_panel({**cfg, "sources": sources}, tickers, dates)
    if px.close.shape[1] == 0 or not px.close.notna().any().any():
        px, src = S.make_synthetic_ohlcv(tickers, dates)
        return px, src + "  [sources resolved 0 tickers -> SYNTHETIC]", prov, notes
    want = [DS._norm(t) for t in tickers]
    return px, "REAL prices (" + DS.provenance_summary(prov, want) + ")", prov, notes


def adv_crore(px, n=20):
    """20-day average daily traded value in ₹ crore (1 cr = 1e7)."""
    return (px.close * px.volume).rolling(n).mean() / 1e7


def liquidity_mask(px, min_adv_cr):
    """Tradable only where 20d ADV >= floor. Filtering out illiquids is more honest
    than modelling huge slippage on names you could never fill at swing size.
    Names with NO volume data at all (close-only sources, e.g. the delisted panel)
    can't be assessed -> we DON'T exclude them on liquidity (unknown != illiquid);
    their capacity simply isn't modelled."""
    mask = adv_crore(px) >= min_adv_cr
    novol = px.volume.columns[~px.volume.notna().any()]
    if len(novol):
        mask[novol] = True
    return mask


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
    if adv.notna().sum().sum() == 0:                          # close-only source: no volume to assess
        print("\n=== Capacity ===  volume unavailable for held names -> not assessed "
              "(close-only price source; add a volume-bearing source to enable).")
        return
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

    px, src, prov, notes = load_prices(cfg, tickers, dates)
    print(f"Prices: {src}  shape={px.close.shape}")
    for n in notes:
        print(f"   {n}")
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

    benchmark_report(cfg, px.close.index, wf_series if wf_tab is not None else None)

    _plot(R, keep, cfg, wf_series if wf_tab is not None else None)
    print("\nDone. Outputs: per_strategy_metrics.csv, final_weights.csv, "
          "walkforward_returns.csv, equity_curves.png, walkforward_equity.png")


def benchmark_report(cfg, dates, wf_series=None):
    """Compare the strategy's walk-forward (equal-weight) return to simply buying and
    holding the index — the bar any active strategy has to clear after costs."""
    bm = DS.load_benchmarks(cfg.get("benchmarks"))
    if bm is None or bm.empty:
        return
    dates = pd.DatetimeIndex(dates)
    bm = bm.reindex(bm.index.union(dates)).ffill().reindex(dates).dropna(how="all")
    if len(bm) < 2:
        return
    yrs = max((bm.index[-1] - bm.index[0]).days / 365.25, 1e-9)
    print("\n=== Benchmark: buy & hold the index (same window) ===")
    for col in bm.columns:
        s = bm[col].dropna()
        if len(s) < 2:
            continue
        cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1
        print(f"  {col:12s} CAGR {cagr:6.1%}   (total {s.iloc[-1]/s.iloc[0]-1:6.0%})")
    if wf_series is not None and "equal" in wf_series:
        eq = (1 + wf_series["equal"]).cumprod()
        wf_cagr = eq.iloc[-1] ** (252 / len(eq)) - 1
        print(f"  -> strategy walk-forward (equal): CAGR {wf_cagr:.1%}. "
              f"Beating buy&hold AFTER costs is the real test.")


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
