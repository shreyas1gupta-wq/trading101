"""
Kaggle orchestrator  |  end-to-end: constituents -> strategies -> final portfolio
================================================================================
Runs the whole pipeline in one place, designed to execute on a Kaggle notebook
(free compute + internet + datasets) where real NSE price data lives. It runs
immediately on SYNTHETIC prices so you can validate the plumbing, then switches
to REAL data the moment you point CONFIG at a price dataset.

UNIVERSE: the main test universe is Nifty500; the mean-reversion family is restricted
to the more-liquid Nifty200 (mean-reversion in illiquid small-caps isn't tradable).
Configurable via CONFIG["mr_constituents"]/["mr_families"]; prices are fetched for the
union of both universes.

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
import json
import numpy as np
import pandas as pd

import portfolio
import strategies as S
import data_sources as DS
import execution as EX
from universe import IndexUniverse, NIFTY200, NIFTY500

# ── CONFIG ─────────────────────────────────────────────────────────────────────
CONFIG = {
    "index":       "NIFTY500",          # MAIN test universe (broad)
    "constituents": NIFTY500,           # path to the constituent xlsx
    "mr_index":    "NIFTY200",          # mean-reversion runs on the more LIQUID Nifty200
    "mr_constituents": NIFTY200,        #   (falling-knife reversion in illiquid small-caps is untradeable)
    "mr_families": ["mean-reversion"],  # strategy families restricted to the MR universe
    "price_path":  None,                # back-compat: a single local dir/CSV (added as a 'local' source)
    "sources": [                        # the free-data WATERFALL — first source that has a ticker wins
        {"type": "local", "path": "data/NIFTY500_master_prices_2015_2025.xlsx"},    # bundled REAL panel: 976 tickers,
                                                                                     #   2015-2025, confirmed split/bonus-adjusted
        {"type": "local", "path": "data/NIFTY500_delisted_prices_2005_2025.xlsx"},  # bundled delisted panel (extra names + pre-2015)
        {"type": "yfinance", "suffix": ".NS"},                                      # extends past the bundled window; unlimited
        # {"type": "local", "path": "/kaggle/input/<your-nse-eod>"},                # <- add your saved Kaggle EOD here
        {"type": "eodhd", "exchange": "NSE", "max_calls": 20},                      # last resort; key from $EODHD_API_KEY
    ],
    "cache_dir":   "cache",             # per-ticker CSV cache (yfinance/EODHD) so re-runs don't re-fetch
    "benchmarks":  "data/factor_navs_2005_2025.xlsx",   # index NAV series for a buy&hold comparison (optional)
    "start":       "2015-01-01",        # matches the bundled master panel's real coverage (extend "end" on Kaggle w/ yfinance)
    "end":         "2025-12-05",
    "min_sharpe":  0.5,                 # selection bar (applied on the TRAIN window only)
    "holdout":     0.5,                 # fraction of time used for in-sample selection; rest is OOS
    "wf_train":    756,                 # walk-forward train window (~3y of trading days)
    "wf_test":     126,                 # walk-forward test window  (~6m); also the re-fit step
    "cost_bps":    18.0,                # per-side slippage+cost in bps (round-trip ~2x); stress-test small-caps higher
    "min_adv_cr":  5.0,                 # liquidity floor: drop names with 20d avg daily value < this (₹ crore)
    "aum_cr":      50.0,                # assumed book size for the capacity report (₹ crore)
    "max_participation": 0.10,          # a position may be at most this fraction of a name's ADV
    "out_dir":     ".",
    "per_strategy": True,               # save each strategy's result individually (resumable)
    "batch_size":  5,                   # process strategies this many at a time, saving after each
    "backtest":    "realistic",         # "realistic" (LC/UC circuit + size-aware slippage) or "simple"
    "save_trades": True,                # write a per-strategy trade blotter (entry/exit/trail) to trades/
    "impact_coef": 1.0,                 # sqrt market impact: +bps ≈ coef × daily_vol_bps × sqrt(trade/ADV)
    "illiquid_surcharge_bps": 25.0,     # per-side add when ADV is unknown (close-only names)
    "circuit_band": 0.20,               # LC/UC daily band: block buys at UC, sells at LC
    "force":       False,               # True -> recompute even if a saved result exists
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


def net_book_weights(px, ctx, strat_alloc, masks_by_family=None):
    """Net STOCK-level book = Σ_strategy (allocation × that strategy's stock weights).
    portfolio.combine() gives weights ACROSS strategies; this turns them back into
    actual per-name positions over time, which is what capacity is about. Uses the
    same per-family universe override as run_all so the book matches what was traded."""
    net = None
    for name, a in strat_alloc.items():
        family, fn = S.REGISTRY[name]
        ctx_i = ({**ctx, "membership": masks_by_family[family]}
                 if masks_by_family and family in masks_by_family else ctx)
        w = fn(px, ctx_i) * a
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


def run_strategies(px, ctx, cfg, masks_by_family=None):
    """Backtest every registered strategy in BATCHES (cfg['batch_size'], default 5),
    saving after each: for each strategy SAVE its returns to per_strategy/<name>.csv,
    a full trade blotter (entry/exit/trail) to trades/<name>_trades.csv, and append to
    a running per_strategy_metrics.csv; SHOW the result; then move on. Loops batch by
    batch until ALL are finished. Resumable — a strategy whose returns file exists is
    loaded, not recomputed (cfg['force']=True to recompute). cfg['backtest']=='realistic'
    uses the LC/UC + size-aware-slippage engine; 'simple' uses the flat-cost engine."""
    outdir = os.path.join(cfg["out_dir"], "per_strategy")
    tradesdir = os.path.join(cfg["out_dir"], "trades")
    os.makedirs(outdir, exist_ok=True)
    save_trades = cfg.get("save_trades", True)
    if save_trades:
        os.makedirs(tradesdir, exist_ok=True)
    realistic = cfg.get("backtest", "realistic") == "realistic"
    items = list(S.REGISTRY.items())
    bs = max(1, int(cfg.get("batch_size", 5)))
    nb = (len(items) + bs - 1) // bs
    keys = ("cagr", "vol", "sharpe", "maxdd", "calmar")
    rows, R = {}, {}
    eng = "realistic (LC/UC + size-aware slippage)" if realistic else "simple (flat cost)"
    print(f"\n=== Backtesting {len(items)} strategies, {bs} at a time, until done  "
          f"[{eng}; main {cfg['index']}{'; MR '+cfg['mr_index'] if masks_by_family else ''}] ===")
    for b in range(nb):
        batch = items[b * bs:(b + 1) * bs]
        print(f"\n── batch {b+1}/{nb}: {', '.join(n for n, _ in batch)}")
        for name, (family, fn) in batch:
            fp = os.path.join(outdir, f"{name}.csv")
            if os.path.exists(fp) and not cfg.get("force"):                       # resume
                net = pd.read_csv(fp, index_col=0, parse_dates=True).squeeze("columns")
                p = portfolio._perf(net)
                row = {"family": family, **{k: p[k] for k in keys}}
                bf = os.path.join(tradesdir, f"{name}_trades.csv")
                if save_trades and os.path.exists(bf):
                    row["trades"] = max(0, sum(1 for _ in open(bf)) - 1)           # recover count from blotter
                rows[name] = row
                R[name] = net
                print(f"   {name:28s} Sharpe {p['sharpe']:5.2f}  (cached)")
                continue
            ctx_i = ({**ctx, "membership": masks_by_family[family]}
                     if masks_by_family and family in masks_by_family else ctx)
            try:
                w = fn(px, ctx_i)
                if realistic:
                    res = EX.realistic_backtest(px, w, cfg)
                    realized = res["realized"]
                else:
                    res = S.run_backtest(px.close, w, cfg["cost_bps"])
                    realized = w.reindex_like(px.close).fillna(0.0).clip(lower=0.0)
                if res["exposure"].abs().sum() < 1e-9:
                    print(f"   {name:28s} (no trades — skipped)")
                    continue
                net = res["net"]
                p = portfolio._perf(net)
                R[name] = net
                net.rename("net").to_frame().to_csv(fp)                            # 1) returns
                ntr = -1
                if save_trades:                                                   # 2) trade blotter
                    bl = EX.trade_blotter(realized, px)
                    bl.to_csv(os.path.join(tradesdir, f"{name}_trades.csv"), index=False)
                    ntr = len(bl)
                yrs = max(len(net) / 252, 1e-9)
                rows[name] = {"family": family, **{k: p[k] for k in keys},
                              "trades": ntr, "ann_turn": res["turnover"].sum() / yrs}
                pd.DataFrame(rows).T.to_csv(os.path.join(cfg["out_dir"], "per_strategy_metrics.csv"))  # 3) append
                print(f"   {name:28s} CAGR {p['cagr']*100:6.1f}%  Sharpe {p['sharpe']:5.2f}  "  # show
                      f"MaxDD {p['maxdd']*100:6.1f}%  trades {ntr:4d}  -> saved")
            except Exception as ex:                                               # then move on
                print(f"   {name:28s} ERROR: {ex}")
        print(f"   -- batch {b+1}/{nb} done ({len(rows)}/{len(items)} cumulative)")
    print(f"=== Finished: {len(rows)} strategies saved -> per_strategy_metrics.csv"
          f"{'; blotters -> trades/' if save_trades else ''} ===")
    return pd.DataFrame(rows).T, pd.DataFrame(R)


_FAM_ORDER = ["mean-reversion", "cross-sectional", "price-action", "event", "seasonal"]


def _specs_markdown(cfg):
    mr = set(cfg.get("mr_families", []))
    uni = lambda f: cfg.get("mr_index", "NIFTY200") if f in mr else cfg.get("index", "NIFTY500")
    L = ["# Strategy specifications", "",
         "Auto-generated from `strategies.SPECS` (kept beside the code). Shared controls:", "",
         "- **Universe** — Nifty200 for mean-reversion, Nifty500 otherwise; 20-day ADV liquidity floor.",
         "- **Regime gate** — exposure × {1.0 weak/sideways · 0.5 strong uptrend · 0.3 crash-brake "
         "when 10-day market return < −8%}; seasonal strategies excepted.",
         "- **Execution** — next-close fill, LC/UC circuit blocking, size-aware slippage.",
         "- **Stops** — NO hard price stop-loss and NO trailing stop anywhere; exits are signal + "
         "time-stop. Add an SL/trailing overlay if you want hard stops.", ""]
    by = {}
    for name, (fam, _) in S.REGISTRY.items():
        by.setdefault(fam, []).append(name)
    for fam in _FAM_ORDER:
        if fam not in by:
            continue
        L.append(f"## {fam.title()}  ·  {uni(fam)}")
        for name in by[fam]:
            sp = S.SPECS.get(name, {})
            L += [f"### {name}",
                  f"- **entry** — {sp.get('entry', '?')}",
                  f"- **exit** — {sp.get('exit', '?')}",
                  f"- **stop / trail** — {sp.get('stop', '?')} / {sp.get('trail', '?')}",
                  f"- **filters** — {sp.get('filters', '?')}",
                  f"- **sizing** — {sp.get('sizing', '?')}  ·  **hold** — {sp.get('hold', '?')}"
                  f"  ·  **data** — {sp.get('needs', '?')}", ""]
    if S.STUBS:
        L += ["## Stubs (registered, need extra data)"]
        L += [f"- **{n}** ({fam}) — {why}" for n, (fam, why) in S.STUBS.items()] + [""]
    return "\n".join(L)


def save_specs(cfg):
    """Save the strategy LOGIC (entry/exit/stop/trail/filters) — human-readable
    STRATEGY_SPECS.md + machine-readable strategy_specs.json — before any results."""
    mr = set(cfg.get("mr_families", []))
    with open(os.path.join(cfg["out_dir"], "STRATEGY_SPECS.md"), "w") as fh:
        fh.write(_specs_markdown(cfg))
    cards = {n: {**S.spec_card(n),
                 "universe": cfg.get("mr_index") if f in mr else cfg.get("index")}
             for n, (f, _) in S.REGISTRY.items()}
    with open(os.path.join(cfg["out_dir"], "strategy_specs.json"), "w") as fh:
        json.dump(cards, fh, indent=2)


def strategy_cards(cfg):
    """Combine each strategy's LOGIC with its latest RESULTS into one note per strategy
    (strategy_cards.md) — the 'save the logic, then keep adding results' artifact."""
    mp = os.path.join(cfg["out_dir"], "per_strategy_metrics.csv")
    if not os.path.exists(mp):
        return None
    m = pd.read_csv(mp, index_col=0)
    tp = os.path.join(cfg["out_dir"], "trades_summary.csv")
    ts = pd.read_csv(tp, index_col=0) if os.path.exists(tp) else None
    mr = set(cfg.get("mr_families", []))
    order = m.sort_values("sharpe", ascending=False).index if "sharpe" in m.columns else m.index
    L = ["# Strategy cards — logic + latest results", "",
         f"_main {cfg['index']} · mean-reversion {cfg.get('mr_index')} · sorted by Sharpe_", ""]
    for name in order:
        sp = S.SPECS.get(name, {})
        fam = S.REGISTRY.get(name, (None,))[0]
        u = cfg.get("mr_index") if fam in mr else cfg.get("index")
        r = m.loc[name]
        L += [f"## {name}  ·  {fam} · {u}",
              f"- **entry** — {sp.get('entry', '?')}",
              f"- **exit** — {sp.get('exit', '?')}  |  **stop** — {sp.get('stop', '?')}  |  **trail** — {sp.get('trail', '?')}",
              f"- **filters** — {sp.get('filters', '?')}  |  **sizing** — {sp.get('sizing', '?')}  |  **hold** — {sp.get('hold', '?')}"]
        res = (f"- **results** — CAGR {r['cagr']*100:.1f}% · Sharpe {r['sharpe']:.2f} · "
               f"MaxDD {r['maxdd']*100:.1f}% · Calmar {r['calmar']:.2f}")
        if "trades" in m.columns and pd.notna(r.get("trades")):
            res += f" · {int(r['trades'])} trades"
        L.append(res)
        if ts is not None and name in ts.index:
            t = ts.loc[name]
            L.append(f"- **trade-stats** — win {t['win_rate']*100:.0f}% · payoff {t['payoff']:.2f} · "
                     f"expectancy {t['expectancy_pct']:.2f}%/trade · avg hold {t['avg_hold_d']:.1f}d")
        L.append("")
    txt = "\n".join(L)
    with open(os.path.join(cfg["out_dir"], "strategy_cards.md"), "w") as fh:
        fh.write(txt)
    return txt


def trades_summary(cfg):
    """Roll every saved blotter (trades/<name>_trades.csv) up into one trade-stats
    table (win rate / payoff / expectancy / hold), saved to trades_summary.csv."""
    files = sorted(glob.glob(os.path.join(cfg["out_dir"], "trades", "*_trades.csv")))
    if not files:
        return None
    rows = {}
    for f in files:
        name = os.path.basename(f)[:-len("_trades.csv")]
        rows[name] = EX.trade_stats(pd.read_csv(f))
    tab = pd.DataFrame(rows).T
    tab.to_csv(os.path.join(cfg["out_dir"], "trades_summary.csv"))
    return tab


# ── main ────────────────────────────────────────────────────────────────────────
def main(cfg=CONFIG):
    uni = IndexUniverse(cfg["constituents"])              # main test universe (Nifty500)
    print(uni.summary())
    tickers = set(uni.all_tickers())

    # Mean-reversion runs on the more-liquid Nifty200 subset (catching falling knives in
    # illiquid small-caps isn't tradable); every other family uses the full Nifty500.
    uni_mr = None
    if cfg.get("mr_constituents") and cfg.get("mr_families"):
        uni_mr = IndexUniverse(cfg["mr_constituents"])
        print("MR universe:", uni_mr.summary())
        tickers |= set(uni_mr.all_tickers())              # fetch prices for the UNION of both
    tickers = sorted(tickers)
    dates = pd.bdate_range(cfg["start"], cfg["end"])

    px, src, prov, notes = load_prices(cfg, tickers, dates)
    print(f"Prices: {src}  shape={px.close.shape}")
    for n in notes:
        print(f"   {n}")
    matched = coverage_report(px, uni)

    liq = liquidity_mask(px, cfg["min_adv_cr"])
    uni_mask = uni.daily_mask(px.close.index, tickers)
    membership = uni_mask & liq.reindex_like(uni_mask).fillna(False)
    kept = membership.sum().sum() / max(1, uni_mask.sum().sum())
    print(f"Liquidity filter (20d ADV >= ₹{cfg['min_adv_cr']:.0f}cr): "
          f"{100*kept:.0f}% of member-days remain tradable")
    ctx = {"membership": membership, "universe": uni}

    masks_by_family = None
    if uni_mr is not None:
        mr_mask = uni_mr.daily_mask(px.close.index, tickers) & liq.reindex_like(uni_mask).fillna(False)
        masks_by_family = {fam: mr_mask for fam in cfg["mr_families"]}

    save_specs(cfg)                                          # FIRST: save the strategy logic notes
    fam_note = f"; {'/'.join(cfg.get('mr_families', []))} on {cfg.get('mr_index')}" if masks_by_family else ""
    print(f"\n=== Backtesting {len(S.REGISTRY)} strategies on {cfg['index']}{fam_note} "
          f"({cfg['cost_bps']:.0f} bps/side) ===")
    if cfg.get("per_strategy"):
        table, R = run_strategies(px, ctx, cfg, masks_by_family)
    else:
        table, R = S.run_all(px, ctx, cost_bps=cfg["cost_bps"], masks_by_family=masks_by_family)
    table.to_csv(os.path.join(cfg["out_dir"], "per_strategy_metrics.csv"))

    if cfg.get("per_strategy") and cfg.get("save_trades", True):
        ts = trades_summary(cfg)
        if ts is not None:
            cols = ["n_trades", "win_rate", "avg_win_pct", "avg_loss_pct", "payoff",
                    "expectancy_pct", "avg_hold_d"]
            print("\n=== Trade stats per strategy (from blotters; sorted by expectancy) ===")
            print(ts.sort_values("expectancy_pct", ascending=False)[cols].head(15).to_string())
            print("   expectancy_pct = average return PER TRADE (the per-trade edge after costs)")
        strategy_cards(cfg)                                  # THEN: logic + results, one note per strategy

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
        capacity_report(px, net_book_weights(px, ctx, alloc, masks_by_family), cfg)

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
