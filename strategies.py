"""
Strategy library  |  long-only, days-to-weeks, bear/sideways, Nifty universe
================================================================================
Uniform signal->weights framework for the catalogue (STRATEGY_CATALOG.md). Every
strategy has signature  f(px, ctx) -> weights DataFrame  (dates x tickers, long
only, each row sums to the invested fraction; the remainder is cash).

  px  : Prices container (.open/.high/.low/.close/.volume, each dates x tickers)
  ctx : {"membership": daily bool mask from universe.py, "universe": IndexUniverse}

run_all(px, ctx) runs every registered strategy through the backtest engine and
returns (per-strategy metrics, daily-returns matrix R). Feed R to portfolio.combine()
to build the final blended product.

Data coverage: A (mean-reversion), D (cross-sectional), E (price-action) and
index-reconstitution + seasonal are codeable on OHLCV. Event/fundamental
strategies (PEAD, buybacks, revisions, bulk deals, ex-date, sector rotation,
cointegration) are REGISTERED AS STUBS (return cash) until event data is supplied.
"""

import numpy as np
import pandas as pd

from swing_backtest import run_backtest, metrics, compute_rsi, TRADING_DAYS, COST_PER_SIDE_BPS
from universe import IndexUniverse, NIFTY200

# ══════════════════════════════════════════════════════════════════════════════
#  Prices container + synthetic OHLCV (swap for real Kaggle data on Kaggle)
# ══════════════════════════════════════════════════════════════════════════════
class Prices:
    def __init__(self, open, high, low, close, volume):
        self.open, self.high, self.low, self.close, self.volume = open, high, low, close, volume


def make_synthetic_ohlcv(tickers, dates, seed=7):
    """Regime-switching market + idiosyncratic OU deviations -> OHLCV for `tickers`.
    Same engine as swing_backtest's generator, extended to full OHLCV."""
    rng = np.random.default_rng(seed)
    n = len(dates)
    # market regimes across the span (bull, sideways, bear, recovery, sideways)
    segs = [(0.30, 0.0006, 0.010), (0.20, 0.0, 0.012), (0.15, -0.0010, 0.020),
            (0.20, 0.0003, 0.016), (0.15, 0.00005, 0.013)]
    parts = []
    for frac, mu, sig in segs:
        parts.append(rng.normal(mu, sig, max(1, int(round(frac * n)))))
    mkt_lr = np.concatenate(parts)[:n]
    if len(mkt_lr) < n:
        mkt_lr = np.concatenate([mkt_lr, rng.normal(0, 0.012, n - len(mkt_lr))])
    mkt_ll = np.cumsum(mkt_lr)

    kappa, sig_e = 0.10, 0.015
    close = {}
    for tk in tickers:
        beta, start = rng.uniform(0.7, 1.3), rng.uniform(40, 800)
        x, idio = 0.0, np.empty(n)
        for t in range(n):
            x = x * (1 - kappa) + rng.normal(0, sig_e)
            idio[t] = x
        close[tk] = start * np.exp(beta * mkt_ll + idio)
    close = pd.DataFrame(close, index=dates)

    # build OHLC around close with a plausible intraday range; volume ~ lognormal
    rng2 = np.random.default_rng(seed + 1)
    rel = pd.DataFrame(rng2.normal(0, 0.008, close.shape), index=dates, columns=close.columns)
    prev = close.shift(1).fillna(close.iloc[0])
    openp = prev * (1 + rng2.normal(0, 0.004, close.shape))
    rng_day = (close.abs() * (0.005 + np.abs(rel)))
    high = np.maximum(openp, close) + rng_day.abs()
    low = np.minimum(openp, close) - rng_day.abs()
    vol = pd.DataFrame(rng2.lognormal(12, 0.6, close.shape), index=dates, columns=close.columns)
    return Prices(openp, high, low, close, vol), "SYNTHETIC OHLCV (regime-switching; engine validation only)"


# ══════════════════════════════════════════════════════════════════════════════
#  Indicator toolkit (vectorised; DataFrame in -> DataFrame out)
# ══════════════════════════════════════════════════════════════════════════════
def sma(df, n):           return df.rolling(n).mean()
def roll_std(df, n):      return df.rolling(n).std()
def rsi_df(df, n):        return df.apply(lambda s: compute_rsi(s, n))
def hh(df, n):            return df.rolling(n).max()
def ll(df, n):            return df.rolling(n).min()


def true_range(px):
    pc = px.close.shift(1)
    return pd.concat([(px.high - px.low), (px.high - pc).abs(), (px.low - pc).abs()]
                     ).groupby(level=0).max()


def atr(px, n=14):        return true_range(px).rolling(n).mean()
def ibs(px):              return ((px.close - px.low) / (px.high - px.low).replace(0, np.nan)).clip(0, 1)


def pct_b(px, n=20, k=2):
    m, s = sma(px.close, n), roll_std(px.close, n)
    upper, lower = m + k * s, m - k * s
    return (px.close - lower) / (upper - lower).replace(0, np.nan)


def williams_r(px, n=10):
    high_n, low_n = hh(px.high, n), ll(px.low, n)
    return -100 * (high_n - px.close) / (high_n - low_n).replace(0, np.nan)


def cci(px, n=20):
    tp = (px.high + px.low + px.close) / 3.0
    md = (tp - tp.rolling(n).mean()).abs().rolling(n).mean()
    return (tp - tp.rolling(n).mean()) / (0.015 * md.replace(0, np.nan))


def zscore(df, n):        return (df - df.rolling(n).mean()) / df.rolling(n).std().replace(0, np.nan)
def rolling_vwap(px, n):  return (((px.high + px.low + px.close) / 3) * px.volume).rolling(n).sum() / px.volume.rolling(n).sum()


# ══════════════════════════════════════════════════════════════════════════════
#  Signal -> weights machinery + overlays (the B-family, embedded)
# ══════════════════════════════════════════════════════════════════════════════
def _market_proxy(px):    return px.close.mean(axis=1)


def _regime_scalar(px):
    """Invested fraction per day: full in sideways/weak tape, 0.5 in strong uptrend,
    0.3 crash-brake during waterfalls. (Catalogue B #17/#25.)"""
    mkt = _market_proxy(px)
    ma200 = mkt.rolling(200).mean()
    mom20, ret10 = mkt.pct_change(20), mkt.pct_change(10)
    expo = pd.Series(1.0, index=mkt.index)
    expo[(mkt > ma200) & (mom20 > 0.05)] = 0.5
    expo[ret10 < -0.08] = 0.3
    expo[ma200.isna()] = 0.5
    return expo


def mask_to_weights(px, mask, ctx, vol_weight=True, regime=True):
    """Equal- or inverse-vol weight across signalled+member names; scale by regime."""
    member = ctx.get("membership")
    m = mask.fillna(False)
    if member is not None:
        m = m & member.reindex_like(m).fillna(False)
    if vol_weight:
        inv = 1.0 / px.close.pct_change().rolling(20).std()
        raw = m * inv.reindex_like(m)
    else:
        raw = m.astype(float)
    w = raw.div(raw.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    if regime:
        w = w.mul(_regime_scalar(px), axis=0)
    return w


def rank_to_weights(px, score, ctx, frac=0.1, long_low=True, rebalance=5, regime=True):
    """Cross-sectional: pick the bottom (or top) `frac` by score among members; hold
    until next rebalance."""
    member = ctx.get("membership")
    weights = pd.DataFrame(index=px.close.index, columns=px.close.columns, dtype=float)
    rebal = px.close.index[::rebalance]
    for d in rebal:
        s = score.loc[d].dropna()
        if member is not None:
            s = s[member.loc[d].reindex(s.index).fillna(False)]
        if len(s) < 10:
            continue
        k = max(1, int(round(len(s) * frac)))
        picks = (s.nsmallest(k) if long_low else s.nlargest(k)).index
        row = pd.Series(0.0, index=px.close.columns)
        row[picks] = 1.0 / k
        weights.loc[d] = row
    w = weights.ffill().fillna(0.0)
    if regime:
        w = w.mul(_regime_scalar(px), axis=0)
    return w


def stateful_mask(entry, exit_, max_hold=None):
    """enter when `entry`, stay until `exit_` or `max_hold` bars, per ticker."""
    e = entry.fillna(False).values
    x = exit_.fillna(False).values
    out = np.zeros(e.shape, dtype=bool)
    T, N = e.shape
    for j in range(N):
        ej, xj = e[:, j], x[:, j]
        if not ej.any():
            continue
        inpos, days = False, 0
        for i in range(T):
            if inpos:
                days += 1
                if xj[i] or (max_hold is not None and days >= max_hold):
                    inpos = False; days = 0
                else:
                    out[i, j] = True
            elif ej[i]:
                inpos, days = True, 1
                out[i, j] = True
    return pd.DataFrame(out, index=entry.index, columns=entry.columns)


# ══════════════════════════════════════════════════════════════════════════════
#  Strategy registry
# ══════════════════════════════════════════════════════════════════════════════
REGISTRY = {}    # name -> (family, fn)
STUBS = {}       # name -> reason


def strategy(name, family):
    def deco(fn):
        REGISTRY[name] = (family, fn)
        return fn
    return deco


def stub(name, family, reason):
    STUBS[name] = (family, reason)


# ── A. Mean-reversion ─────────────────────────────────────────────────────────
@strategy("A_rsi2", "mean-reversion")
def rsi2(px, ctx):
    r = rsi_df(px.close, 2); trend = px.close > sma(px.close, 200)
    return mask_to_weights(px, stateful_mask((r < 10) & trend, r > 70, 6), ctx)

@strategy("A_connors_rsi", "mean-reversion")
def connors_rsi(px, ctx):
    # 2-component ConnorsRSI approximation: RSI(3) of price + RSI(2) of up/down streak
    up = (px.close.diff() > 0).astype(int) - (px.close.diff() < 0).astype(int)
    streak = up.apply(lambda s: s.groupby((s != s.shift()).cumsum()).cumsum())
    crsi = (rsi_df(px.close, 3) + rsi_df(streak.astype(float), 2)) / 2
    return mask_to_weights(px, stateful_mask(crsi < 15, crsi > 65, 6), ctx)

@strategy("A_cumulative_rsi", "mean-reversion")
def cumulative_rsi(px, ctx):
    r = rsi_df(px.close, 2); cum = r.rolling(2).sum(); trend = px.close > sma(px.close, 200)
    return mask_to_weights(px, stateful_mask((cum < 35) & trend, r > 65, 6), ctx)

@strategy("A_ibs", "mean-reversion")
def ibs_bounce(px, ctx):
    b = ibs(px)
    return mask_to_weights(px, stateful_mask(b < 0.2, b > 0.7, 5), ctx)

@strategy("A_bollinger_pctb", "mean-reversion")
def bollinger_pctb(px, ctx):
    b = pct_b(px); above = px.close > sma(px.close, 20)
    return mask_to_weights(px, stateful_mask(b < 0, above, 8), ctx)

@strategy("A_dist_ma_z", "mean-reversion")
def dist_ma_z(px, ctx):
    z = (px.close - sma(px.close, 50)) / atr(px, 14)
    return mask_to_weights(px, stateful_mask(z < -2.5, z > -0.2, 10), ctx)

@strategy("A_ou_reversion", "mean-reversion")
def ou_reversion(px, ctx):
    z = zscore(px.close, 10)                       # OU-style; lookback ~ half-life
    return mask_to_weights(px, stateful_mask(z < -1.5, z > 0, 12), ctx)

@strategy("A_williams_r", "mean-reversion")
def williams_bounce(px, ctx):
    w = williams_r(px, 10)
    return mask_to_weights(px, stateful_mask(w < -90, w > -30, 6), ctx)

@strategy("A_cci", "mean-reversion")
def cci_reversion(px, ctx):
    c = cci(px, 20)
    return mask_to_weights(px, stateful_mask(c < -150, c > 0, 8), ctx)

@strategy("A_double7s", "mean-reversion")
def double7s(px, ctx):
    trend = px.close > sma(px.close, 200)
    entry = (px.close <= ll(px.close, 7)) & trend
    exit_ = px.close >= hh(px.close, 7)
    return mask_to_weights(px, stateful_mask(entry, exit_, 10), ctx)

@strategy("A_rsi2_divergence", "mean-reversion")
def rsi2_divergence(px, ctx):
    r2, r14 = rsi_df(px.close, 2), rsi_df(px.close, 14)
    entry = (r2 < 10) & (r14 > r14.shift(5))       # momentum of RSI turning up
    return mask_to_weights(px, stateful_mask(entry, r14 > 60, 8), ctx)

@strategy("A_ensemble_mr", "mean-reversion")
def ensemble_mr(px, ctx):
    votes = ((rsi_df(px.close, 2) < 10).astype(int) + (ibs(px) < 0.2).astype(int)
             + (pct_b(px) < 0).astype(int) + (zscore(px.close, 10) < -2).astype(int))
    entry = votes >= 2
    return mask_to_weights(px, stateful_mask(entry, votes == 0, 6), ctx)


# ── D. Cross-sectional / relative-strength ────────────────────────────────────
@strategy("D_xs_reversal_5d", "cross-sectional")
def xs_reversal_5d(px, ctx):
    return rank_to_weights(px, px.close.pct_change(5), ctx, frac=0.1, long_low=True, rebalance=5)

@strategy("D_reversal_1m", "cross-sectional")
def reversal_1m(px, ctx):
    return rank_to_weights(px, px.close.pct_change(21), ctx, frac=0.1, long_low=True, rebalance=21)

@strategy("D_rel_strength_4w", "cross-sectional")
def rel_strength_4w(px, ctx):
    return rank_to_weights(px, px.close.pct_change(21), ctx, frac=0.1, long_low=False, rebalance=5)

@strategy("D_residual_momentum", "cross-sectional")
def residual_momentum(px, ctx):
    mkt = _market_proxy(px).pct_change()
    rets = px.close.pct_change()
    beta = rets.rolling(60).cov(mkt).div(mkt.rolling(60).var(), axis=0)
    resid = rets.sub(beta.mul(mkt, axis=0))
    score = resid.rolling(21).sum()
    return rank_to_weights(px, score, ctx, frac=0.1, long_low=False, rebalance=21)

@strategy("D_low_vol_tilt", "cross-sectional")
def low_vol_tilt(px, ctx):
    vol = px.close.pct_change().rolling(20).std()
    return rank_to_weights(px, vol, ctx, frac=0.1, long_low=True, rebalance=21)

@strategy("D_beta_rotation", "cross-sectional")
def beta_rotation(px, ctx):
    mkt = _market_proxy(px).pct_change(); rets = px.close.pct_change()
    beta = rets.rolling(60).cov(mkt).div(mkt.rolling(60).var(), axis=0)
    return rank_to_weights(px, beta, ctx, frac=0.1, long_low=True, rebalance=21)

@strategy("D_dispersion_gated_reversal", "cross-sectional")
def dispersion_gated_reversal(px, ctx):
    w = rank_to_weights(px, px.close.pct_change(5), ctx, frac=0.1, long_low=True, rebalance=5, regime=False)
    disp = px.close.pct_change(5).std(axis=1)
    gate = (disp > disp.rolling(120).median()).astype(float)
    return w.mul(gate * _regime_scalar(px), axis=0)


# ── E. Price-action / microstructure ──────────────────────────────────────────
@strategy("E_gap_down_fade", "price-action")
def gap_down_fade(px, ctx):
    entry = px.open < px.close.shift(1) * 0.97
    exit_ = px.close >= px.close.shift(1)          # gap fill
    return mask_to_weights(px, stateful_mask(entry, exit_, 5), ctx)

@strategy("E_failed_breakdown", "price-action")
def failed_breakdown(px, ctx):
    prior_low = ll(px.low, 20).shift(1)
    entry = (px.low < prior_low) & (px.close > prior_low)   # broke then reclaimed
    return mask_to_weights(px, stateful_mask(entry, px.close > sma(px.close, 20), 8), ctx)

@strategy("E_selling_climax", "price-action")
def selling_climax(px, ctx):
    big_vol = px.volume > 2 * sma(px.volume, 20)
    lower_wick = (px.close - px.low) / (px.high - px.low).replace(0, np.nan) > 0.66
    entry = big_vol & lower_wick & (px.close.pct_change() < 0)
    return mask_to_weights(px, stateful_mask(entry, px.close > sma(px.close, 5), 5), ctx)

@strategy("E_vwap_reversion", "price-action")
def vwap_reversion(px, ctx):
    vw = rolling_vwap(px, 20)
    return mask_to_weights(px, stateful_mask(px.close < vw * 0.95, px.close >= vw, 8), ctx)

@strategy("E_pullback_to_ma", "price-action")
def pullback_to_ma(px, ctx):
    up = (px.close > sma(px.close, 50)) & (sma(px.close, 20) > sma(px.close, 20).shift(5))
    entry = up & (px.low <= sma(px.close, 20)) & (px.close > sma(px.close, 20))
    return mask_to_weights(px, stateful_mask(entry, px.close >= hh(px.close, 10), 8), ctx)

@strategy("E_n_down_days", "price-action")
def n_down_days(px, ctx):
    down = px.close.diff() < 0
    four = down & down.shift(1) & down.shift(2) & down.shift(3)
    entry = four & (px.close > sma(px.close, 50))
    return mask_to_weights(px, stateful_mask(entry, px.close.diff() > 0, 5), ctx)

@strategy("E_nr7_breakout", "price-action")
def nr7_breakout(px, ctx):
    rng = px.high - px.low
    nr7 = rng == rng.rolling(7).min()
    entry = nr7.shift(1).fillna(False) & (px.close > px.high.shift(1))
    return mask_to_weights(px, stateful_mask(entry, px.close < sma(px.close, 5), 5), ctx)

@strategy("E_bollinger_squeeze", "price-action")
def bollinger_squeeze(px, ctx):
    bw = (roll_std(px.close, 20) * 4) / sma(px.close, 20)      # bandwidth
    squeeze = bw == bw.rolling(126).min()
    entry = squeeze.shift(1).fillna(False) & (px.close > px.close.shift(1))
    return mask_to_weights(px, stateful_mask(entry, px.close < sma(px.close, 10), 10), ctx)


# ── Event codeable from the constituent files: index reconstitution ───────────
@strategy("C_index_reconstitution", "event")
def index_reconstitution(px, ctx):
    uni = ctx.get("universe")
    if uni is None:
        return pd.DataFrame(0.0, index=px.close.index, columns=px.close.columns)
    weights = pd.DataFrame(index=px.close.index, columns=px.close.columns, dtype=float)
    snaps = uni.snapshots.tolist()
    for i in range(1, len(snaps)):
        added = uni.members_asof(snaps[i]) - uni.members_asof(snaps[i - 1])
        added = [t for t in added if t in px.close.columns]
        if not added:
            continue
        d0 = px.close.index[px.close.index >= snaps[i]]
        if len(d0) == 0:
            continue
        window = d0[:20]                                  # hold ~20 trading days
        weights.loc[window, added] = 1.0 / len(added)
    return weights.fillna(0.0).mul(_regime_scalar(px), axis=0)


# ── Seasonal (calendar) ───────────────────────────────────────────────────────
def _members_equal_weight(px, ctx, day_mask):
    member = ctx.get("membership")
    base = member.reindex_like(px.close).fillna(False) if member is not None \
        else pd.DataFrame(True, index=px.close.index, columns=px.close.columns)
    w = base.astype(float)
    w = w.div(w.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return w.mul(day_mask.astype(float), axis=0)

@strategy("C_turn_of_month", "seasonal")
def turn_of_month(px, ctx):
    idx = px.close.index
    g = pd.Series(idx, index=idx).groupby([idx.year, idx.month])
    last = g.transform("max"); rank_in_month = g.cumcount()
    day_mask = (pd.Series(idx, index=idx) == last) | (rank_in_month < 3)
    return _members_equal_weight(px, ctx, day_mask)

@strategy("C_expiry_week", "seasonal")
def expiry_week(px, ctx):
    idx = px.close.index
    # approximate monthly F&O expiry week as the last 5 trading days of each month
    rank_from_end = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).cumcount(ascending=False)
    return _members_equal_weight(px, ctx, rank_from_end < 5)


# ── Stubs: need event / fundamental / sector data (registered for completeness) ─
for _n, _f, _why in [
    ("C_pead", "event", "needs earnings-surprise data"),
    ("C_earnings_gap_reversal", "event", "needs earnings dates"),
    ("C_pre_earnings_drift", "event", "needs earnings calendar"),
    ("C_estimate_revision", "event", "needs analyst estimates"),
    ("C_buyback_insider", "event", "needs buyback/insider filings"),
    ("C_bulk_block_deal", "event", "needs bulk/block-deal feed"),
    ("C_ex_date_reversion", "event", "needs dividend/ex-dates"),
    ("C_demerger_drift", "event", "needs corporate-action data"),
    ("D_quality_minus_junk", "cross-sectional", "needs fundamentals"),
    ("D_defensive_sector_rotation", "cross-sectional", "needs sector map"),
    ("D_cointegration_pairs", "cross-sectional", "needs pair-selection step"),
]:
    stub(_n, _f, _why)


# ══════════════════════════════════════════════════════════════════════════════
#  Run all strategies -> returns matrix (feed to portfolio.combine)
# ══════════════════════════════════════════════════════════════════════════════
def run_all(px, ctx, verbose=True, cost_bps=COST_PER_SIDE_BPS, masks_by_family=None):
    """masks_by_family: optional {family -> membership mask} to run a family on a
    different universe (e.g. mean-reversion on the more-liquid Nifty200 while the
    rest trade the full Nifty500). Families not listed use ctx['membership']."""
    rows, R = {}, {}
    for name, (family, fn) in REGISTRY.items():
        ctx_i = ({**ctx, "membership": masks_by_family[family]}
                 if masks_by_family and family in masks_by_family else ctx)
        try:
            w = fn(px, ctx_i)
            res = run_backtest(px.close, w, cost_bps)
            if res["exposure"].abs().sum() < 1e-9:
                if verbose: print(f"  skip {name:28s} (no trades)")
                continue
            m = metrics(res, name)
            rows[name] = {"family": family, "cagr": m["cagr"], "sharpe": m["sharpe"],
                          "maxdd": m["maxdd"], "avg_expo": res["exposure"].mean()}
            R[name] = res["net"]
            if verbose:
                print(f"  {name:28s} {family:16s} CAGR {m['cagr']*100:6.1f}%  "
                      f"Sharpe {m['sharpe']:5.2f}  MaxDD {m['maxdd']*100:6.1f}%")
        except Exception as ex:
            if verbose: print(f"  ERROR {name}: {ex}")
    return pd.DataFrame(rows).T, pd.DataFrame(R)


def select_by_sharpe(table, R, min_sharpe=0.5):
    """Keep only strategies that cleared a Sharpe bar. Risk-only allocators
    (HRP/risk-parity/min-var) are return-AGNOSTIC and will fund losers, so the
    pool must be pre-filtered to positive-edge strategies first.

    IMPORTANT: here we filter in-sample for illustration. In production this
    selection MUST be out-of-sample / walk-forward (select on a training window,
    allocate on the next window) or you bake look-ahead overfitting into results."""
    keep = [s for s in R.columns if s in table.index and table.loc[s, "sharpe"] >= min_sharpe]
    return R[keep], keep


def _demo():
    import portfolio
    uni = IndexUniverse(NIFTY200)
    tickers = uni.all_tickers()
    dates = pd.bdate_range("2012-01-01", "2021-12-31")
    print(f"Universe {len(tickers)} tickers, {len(dates)} days. Generating synthetic OHLCV...")
    px, src = make_synthetic_ohlcv(tickers, dates)
    ctx = {"membership": uni.daily_mask(dates, tickers), "universe": uni}

    print(f"\n=== Per-strategy backtest ({src}) ===")
    print(f"Registered: {len(REGISTRY)} functioning + {len(STUBS)} stubs "
          f"(need event/fundamental data)\n")
    table, R = run_all(px, ctx)

    Rsel, keep = select_by_sharpe(table, R, min_sharpe=0.5)
    print(f"\n=== Selecting positive-edge strategies (Sharpe>=0.5, IN-SAMPLE demo) ===")
    print(f"Kept {len(keep)}/{R.shape[1]}: {keep}")

    print(f"\n=== Combining the {Rsel.shape[1]} selected strategies into one portfolio ===")
    mtab, weights, k, corr = portfolio.combine(Rsel)
    pd.set_option("display.width", 130, "display.float_format", lambda x: f"{x:7.3f}")
    print(mtab.to_string())
    print(f"\nStrategy-return correlations: avg={corr['avg']:.2f}.")
    if corr["avg"] > 0.5:
        print("  -> HIGH here: synthetic strategies all key off the same OU reversion, so")
        print("     they're near-duplicates and the blend can't beat the best single one.")
        print("     On REAL data the families (MR / cross-sectional / price-action / event)")
        print("     are far less correlated, so the combo should EXCEED the best single while")
        print("     cutting its single-strategy drawdown risk.")
    print(f"Kelly leverage (capped, unlevered): {k['leverage_unlevered']:.2f}x")
    print("\nNOTE: synthetic prices validate the full pipeline end-to-end. Swap in real "
          "delisted-inclusive adjusted OHLCV on Kaggle for live results.")


if __name__ == "__main__":
    _demo()
