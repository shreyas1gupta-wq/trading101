"""
Swing-Trading Backtest Harness  |  Long-only, days-to-weeks, bear/sideways regime
================================================================================
Implements the two flagship strategies from the strategy catalogue:

  A. Cross-sectional 5-day reversal  (long-only, regime-gated, vol-weighted)
        Rank the liquid universe by trailing 5-day return; BUY the biggest
        losers (bottom decile); rebalance weekly; scale total exposure by a
        market-regime filter so the book sits in cash during waterfall declines.

  B. Connors RSI(2) oversold bounce  (long-only, 200-DMA filter, time-stop)
        In names trading above their 200-DMA, BUY when 2-period RSI < 10;
        EXIT when RSI(2) > 70 or after `max_hold` days, whichever first.

Both obey the product constraints: LONG-ONLY, no options, holding a few days to
a few weeks (not intraday, not buy-and-hold), Indian liquid large-caps, and
India cash-equity frictions (STT + charges + slippage) and the post-Jul-2024
20% short-term capital-gains tax are modelled.

--------------------------------------------------------------------------------
DATA
--------------------------------------------------------------------------------
This environment's egress policy blocks market-data hosts (Yahoo Finance returns
HTTP 403 at the proxy), so by default the harness runs on a SYNTHETIC, regime-
switching dataset with built-in idiosyncratic mean reversion. That validates the
engine, the regime gate, and the cost/tax model -- it does NOT prove a real-world
edge. To run on real data, drop one CSV per ticker into ./data/ with columns
[Date, Open, High, Low, Close, Volume] (e.g. RELIANCE.csv) and re-run; the loader
auto-detects them and uses real prices with zero code changes.
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
from tabulate import tabulate

# ── Global config ────────────────────────────────────────────────────────────
TRADING_DAYS   = 252
DATA_DIR       = "data"        # drop real OHLCV CSVs here to use live prices
CHART_PATH     = "charts/swing_backtest.png"

# India cash-equity delivery frictions, charged per side on traded notional:
#   STT 0.10% (each side) + exchange/SEBI/stamp ~0.02% + slippage ~0.06%  ≈ 0.18%/side
#   => round-trip ≈ 0.36%.  Tune COST_PER_SIDE_BPS to your broker/liquidity.
COST_PER_SIDE_BPS = 18.0
STCG_TAX          = 0.20       # short-term cap-gains (holding < 1yr) post Jul-2024


# ══════════════════════════════════════════════════════════════════════════════
#  DATA
# ══════════════════════════════════════════════════════════════════════════════
def generate_synthetic(n_tickers=24, seed=7):
    """Regime-switching market + idiosyncratic Ornstein-Uhlenbeck (mean-reverting)
    deviations, so cross-sectional reversal has a *real* (if synthetic) signal."""
    rng = np.random.default_rng(seed)

    # (length_days, daily_drift, daily_vol) -- bull, sideways, bear, recovery, sideways
    segs = [(500, 0.0006, 0.010),
            (500, 0.0000, 0.012),
            (400, -0.0010, 0.020),
            (700, 0.0003, 0.016),
            (500, 0.00005, 0.013)]
    mkt_lr = np.concatenate([rng.normal(mu, sig, n) for (n, mu, sig) in segs])
    n_days = len(mkt_lr)
    mkt_loglevel = np.cumsum(mkt_lr)
    dates = pd.bdate_range(end="2024-12-31", periods=n_days)

    kappa, sig_e = 0.10, 0.015          # OU mean-reversion speed (~7d half-life) & noise
    cols = {}
    for k in range(n_tickers):
        beta  = rng.uniform(0.7, 1.3)
        start = rng.uniform(50, 800)
        x = 0.0
        idio = np.empty(n_days)
        for t in range(n_days):
            x = x * (1 - kappa) + rng.normal(0, sig_e)
            idio[t] = x
        close = start * np.exp(beta * mkt_loglevel + idio)
        cols[f"STK{k+1:02d}"] = close

    close = pd.DataFrame(cols, index=dates)
    return close, "SYNTHETIC (regime-switching, built-in mean reversion)"


def load_data():
    """Real CSVs in ./data/ if present, else synthetic."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    if files:
        frames = {}
        for f in files:
            tk = os.path.splitext(os.path.basename(f))[0]
            d = pd.read_csv(f, parse_dates=["Date"]).set_index("Date").sort_index()
            frames[tk] = d["Close"]
        close = pd.DataFrame(frames).dropna(how="all").ffill()
        return close, f"REAL CSVs from ./{DATA_DIR}/ ({len(files)} tickers)"
    return generate_synthetic()


# ══════════════════════════════════════════════════════════════════════════════
#  INDICATORS & REGIME FILTER
# ══════════════════════════════════════════════════════════════════════════════
def compute_rsi(series, n):
    """Wilder's RSI."""
    delta = series.diff()
    up   = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up   = up.ewm(alpha=1 / n, adjust=False).mean()
    roll_down = down.ewm(alpha=1 / n, adjust=False).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def regime_exposure(close, d):
    """Fraction of capital to deploy on date `d`.
       Favour mean-reversion when the market is weak/sideways (its home turf),
       trim in strong uptrends, and slam a 'crash brake' on during waterfalls
       so we don't catch falling knives."""
    mkt   = close.mean(axis=1)                 # equal-weight market proxy
    ma200 = mkt.rolling(200).mean()
    if pd.isna(ma200.loc[d]):
        return 0.5
    m    = mkt.loc[d]
    ma   = ma200.loc[d]
    mom20 = mkt.pct_change(20).loc[d]
    ret10 = mkt.pct_change(10).loc[d]

    expo = 1.0
    if m > ma and mom20 > 0.05:                # strong uptrend -> reversal weaker
        expo = 0.5
    if ret10 < -0.08:                          # crash brake -> mostly cash
        expo = min(expo, 0.3)
    return expo


# ══════════════════════════════════════════════════════════════════════════════
#  STRATEGIES  (each returns a long-only target-weight DataFrame: dates x tickers)
# ══════════════════════════════════════════════════════════════════════════════
def strat_xs_reversal(close, lookback=5, frac=0.20, rebalance=5,
                      vol_weight=True, use_regime=True):
    rets_lb = close.pct_change(lookback)
    vol20   = close.pct_change().rolling(20).std()
    weights = pd.DataFrame(index=close.index, columns=close.columns, dtype=float)

    rebal_days = close.index[::rebalance]
    for d in rebal_days:
        r = rets_lb.loc[d].dropna()
        if len(r) < 5:
            continue
        n_pick = max(1, int(round(len(r) * frac)))
        picks  = r.nsmallest(n_pick).index          # biggest losers -> expect bounce

        if vol_weight:
            inv = 1.0 / vol20.loc[d, picks].replace(0, np.nan)
            w = (inv / inv.sum()).fillna(1.0 / n_pick)
        else:
            w = pd.Series(1.0 / n_pick, index=picks)

        expo = regime_exposure(close, d) if use_regime else 1.0
        row = pd.Series(0.0, index=close.columns)
        row[picks] = (w * expo).values
        weights.loc[d] = row

    return weights.ffill().fillna(0.0)             # hold basket until next rebalance


def strat_rsi2(close, n=2, buy_th=10, exit_th=70, trend_ma=200,
               max_hold=6, max_names=10, use_regime=True):
    ma  = close.rolling(trend_ma).mean()
    rsi = close.apply(lambda s: compute_rsi(s, n))

    # stateful per-ticker holding mask
    hold = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    idx = close.index
    for tk in close.columns:
        c, r, m = close[tk].values, rsi[tk].values, ma[tk].values
        h = np.zeros(len(c)); in_pos = False; days = 0
        for i in range(len(c)):
            if np.isnan(m[i]):
                continue
            if in_pos:
                days += 1
                if r[i] > exit_th or days >= max_hold:
                    in_pos = False; days = 0
                else:
                    h[i] = 1.0
            elif c[i] > m[i] and r[i] < buy_th:
                in_pos = True; days = 1; h[i] = 1.0
        hold[tk] = h

    # convert holdings -> weights using FIXED-size slots (1/max_names each) so a
    # continuing position keeps a stable weight and generates no phantom turnover.
    # The 200-DMA entry filter is RSI(2)'s native regime control, so we don't
    # re-scale by the market gate here (that would churn held names every day).
    slot = 1.0 / max_names
    weights = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for d in idx:
        active = hold.loc[d]
        names = active[active > 0].index
        if len(names) == 0:
            continue
        if len(names) > max_names:                 # keep the most oversold
            names = rsi.loc[d, names].nsmallest(max_names).index
        weights.loc[d, names] = slot
    return weights


# ══════════════════════════════════════════════════════════════════════════════
#  BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════════════
def run_backtest(close, weights, cost_per_side_bps=COST_PER_SIDE_BPS):
    rets   = close.pct_change().fillna(0.0)
    target = weights.fillna(0.0).clip(lower=0.0)            # long-only
    held   = target.shift(1).fillna(0.0)                   # 1-day lag => no look-ahead
    gross  = (held * rets).sum(axis=1)
    turnover = (target - target.shift(1).fillna(0.0)).abs().sum(axis=1)
    cost   = turnover * (cost_per_side_bps / 1e4)
    net    = gross - cost
    equity = (1 + net).cumprod()
    return dict(net=net, equity=equity, turnover=turnover,
                exposure=target.sum(axis=1))


def metrics(res, label):
    net, eq = res["net"], res["equity"]
    n = len(net)
    years = n / TRADING_DAYS
    cagr = eq.iloc[-1] ** (TRADING_DAYS / n) - 1
    vol  = net.std() * np.sqrt(TRADING_DAYS)
    sharpe = (net.mean() / net.std() * np.sqrt(TRADING_DAYS)) if net.std() > 0 else 0.0
    dd = eq / eq.cummax() - 1
    maxdd = dd.min()
    calmar = cagr / abs(maxdd) if maxdd < 0 else np.nan
    active = res["exposure"] > 1e-9
    winrate = (net[active] > 0).mean() if active.sum() else 0.0
    avg_expo = res["exposure"].mean()
    ann_turn = res["turnover"].sum() / years
    pretax_mult = eq.iloc[-1]
    posttax_mult = 1 + (pretax_mult - 1) * (1 - STCG_TAX) if pretax_mult > 1 else pretax_mult
    posttax_cagr = posttax_mult ** (TRADING_DAYS / n) - 1
    return dict(label=label, cagr=cagr, posttax_cagr=posttax_cagr, vol=vol,
                sharpe=sharpe, maxdd=maxdd, calmar=calmar, winrate=winrate,
                avg_expo=avg_expo, ann_turn=ann_turn, mult=pretax_mult)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    close, source = load_data()

    print("=" * 78)
    print("   SWING-TRADING BACKTEST  |  long-only, days-to-weeks, bear/sideways")
    print("=" * 78)
    print(f"   Data source : {source}")
    print(f"   Universe    : {close.shape[1]} tickers")
    print(f"   Period      : {close.index[0].date()} -> {close.index[-1].date()}"
          f"  ({len(close)} trading days)")
    print(f"   Frictions   : {COST_PER_SIDE_BPS:.0f} bps/side round-trip + {STCG_TAX:.0%} STCG")
    if source.startswith("SYNTHETIC"):
        print("   NOTE        : synthetic data validates the ENGINE, not a real edge.")
    print("=" * 78)

    # ── Strategies ────────────────────────────────────────────────────────────
    w_xs   = strat_xs_reversal(close)
    w_rsi  = strat_rsi2(close)

    res_xs  = run_backtest(close, w_xs)
    res_rsi = run_backtest(close, w_rsi)

    # Buy & hold equal-weight benchmark
    bh_net = close.pct_change().fillna(0.0).mean(axis=1)
    res_bh = dict(net=bh_net, equity=(1 + bh_net).cumprod(),
                  turnover=pd.Series(0.0, index=close.index),
                  exposure=pd.Series(1.0, index=close.index))

    m_xs  = metrics(res_xs,  "A: XS 5-day reversal (regime-gated)")
    m_rsi = metrics(res_rsi, "B: Connors RSI(2) bounce")
    m_bh  = metrics(res_bh,  "Benchmark: equal-weight buy & hold")

    # ── Results table ─────────────────────────────────────────────────────────
    rows = []
    for m in (m_xs, m_rsi, m_bh):
        rows.append([m["label"],
                     f"{m['cagr']*100:6.1f}%",
                     f"{m['posttax_cagr']*100:6.1f}%",
                     f"{m['vol']*100:5.1f}%",
                     f"{m['sharpe']:5.2f}",
                     f"{m['maxdd']*100:6.1f}%",
                     f"{m['calmar']:5.2f}" if not np.isnan(m['calmar']) else "  n/a",
                     f"{m['winrate']*100:4.0f}%",
                     f"{m['avg_expo']*100:4.0f}%",
                     f"{m['ann_turn']:4.1f}x"])
    headers = ["Strategy", "CAGR", "CAGR\n(post-tax)", "Vol", "Sharpe",
               "MaxDD", "Calmar", "Win%", "AvgExp", "Turn/yr"]
    print("\n" + tabulate(rows, headers=headers, tablefmt="grid"))

    print("\n  Reading the table:")
    print("  • Sharpe / MaxDD / Calmar are the consistency metrics that matter for")
    print("    a 'bear-market product' -- not raw CAGR.")
    print("  • 'AvgExp' shows how often the regime gate parks the book in cash.")
    print("  • 'Turn/yr' x post-tax-vs-pretax CAGR gap = how much frictions eat.")

    # ── Chart ─────────────────────────────────────────────────────────────────
    os.makedirs("charts", exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9),
                                   gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(res_xs["equity"],  label=m_xs["label"],  lw=1.8)
    ax1.plot(res_rsi["equity"], label=m_rsi["label"], lw=1.8)
    ax1.plot(res_bh["equity"],  label=m_bh["label"], lw=1.4, ls="--", color="grey")
    ax1.set_yscale("log")
    ax1.set_title("Equity curves (log scale)  —  growth of 1 unit, net of costs")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(alpha=0.3)

    ax2.fill_between(res_xs["exposure"].index, res_xs["exposure"].values,
                     step="pre", alpha=0.5, label="Strategy A invested fraction")
    ax2.set_ylim(0, 1.05)
    ax2.set_title("Regime gate: Strategy A exposure (1.0 = fully invested, 0 = cash)")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(CHART_PATH, dpi=110)
    print(f"\n  Chart saved -> {CHART_PATH}")
    print("=" * 78)
    print("  To run on REAL data: put CSVs in ./data/ (Date,Open,High,Low,Close,Volume)")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()
