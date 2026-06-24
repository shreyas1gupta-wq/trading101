"""
Portfolio-of-strategies combiner
================================================================================
Given a matrix of per-strategy DAILY RETURNS (dates x strategy), allocate capital
ACROSS the strategies using correlation- and Kelly-based methods, then report the
blended performance. This is the "combine many backtested strategies into one
final portfolio" layer that sits on top of the strategy backtests.

Allocators (each returns long-only weights that sum to 1):
  • equal        - 1/N naive baseline
  • inverse_vol  - weight ∝ 1/σ_i  (ignores correlation)
  • min_variance - w ∝ Σ⁻¹1        (pure risk, ignores returns)
  • risk_parity  - equal risk contribution (ERC; uses correlation)
  • max_sharpe   - tangency, w ∝ Σ⁻¹μ (uses returns + correlation)
  • hrp          - Hierarchical Risk Parity (López de Prado 2016; robust to
                   estimation error via correlation clustering)
  • kelly        - growth-optimal: SAME direction as tangency, but also returns
                   the optimal LEVERAGE. Full Kelly is aggressive; half-Kelly is
                   the practical default. (Reported, not force-applied.)

Note: max_sharpe and Kelly share the same *relative* weights (both ∝ Σ⁻¹μ);
Kelly's extra output is how much total capital to deploy (leverage), which the
others don't address. min_variance / risk_parity / HRP / inverse_vol give
genuinely different mixes.
"""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform
from scipy.optimize import minimize

TRADING_DAYS = 252


# ── helpers ───────────────────────────────────────────────────────────────────
def _clip_norm(w):
    w = w.clip(lower=0)
    s = w.sum()
    return w / s if s > 0 else pd.Series(1.0 / len(w), index=w.index)


def _perf(rets):
    rets = rets.dropna()
    n = len(rets)
    eq = (1 + rets).cumprod()
    cagr = eq.iloc[-1] ** (TRADING_DAYS / n) - 1
    vol = rets.std() * np.sqrt(TRADING_DAYS)
    sharpe = rets.mean() / rets.std() * np.sqrt(TRADING_DAYS) if rets.std() > 0 else 0.0
    maxdd = (eq / eq.cummax() - 1).min()
    calmar = cagr / abs(maxdd) if maxdd < 0 else np.nan
    return dict(cagr=cagr, vol=vol, sharpe=sharpe, maxdd=maxdd, calmar=calmar)


# ── allocators ──────────────────────────────────────────────────────────────
def w_equal(R):
    return pd.Series(1.0 / R.shape[1], index=R.columns)


def w_inverse_vol(R):
    iv = 1.0 / R.std()
    return iv / iv.sum()


def w_min_variance(R):
    cov = R.cov().values
    inv = np.linalg.pinv(cov)
    w = inv @ np.ones(cov.shape[0])
    return _clip_norm(pd.Series(w, index=R.columns))


def w_max_sharpe(R, rf_daily=0.0):
    mu = R.mean().values - rf_daily
    inv = np.linalg.pinv(R.cov().values)
    return _clip_norm(pd.Series(inv @ mu, index=R.columns))


def w_risk_parity(R):
    """Equal-risk-contribution (long-only). Minimizes the dispersion of risk
    contributions via SLSQP -- robust when strategies are negatively correlated
    (the fixed-point form NaNs there because a risk contribution can go negative)."""
    cov = R.cov().values
    n = cov.shape[0]

    def obj(w):
        rc = w * (cov @ w)                      # risk contribution of each strategy
        return np.sum((rc - rc.mean()) ** 2)    # equalize them

    w0 = 1.0 / np.sqrt(np.diag(cov)); w0 /= w0.sum()
    res = minimize(obj, w0, method="SLSQP", bounds=[(0.0, 1.0)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
                   options={"maxiter": 500, "ftol": 1e-12})
    w = np.clip(res.x, 0, None); w /= w.sum()
    return pd.Series(w, index=R.columns)


def kelly(R, rf_daily=0.0):
    """Growth-optimal. Returns relative weights (= tangency) AND the leverage."""
    mu = R.mean().values - rf_daily
    cov = R.cov().values
    f = np.linalg.pinv(cov) @ mu                        # raw Kelly fractions (per day)
    w = _clip_norm(pd.Series(f, index=R.columns))       # long-only relative mix
    # optimal leverage of the tangency portfolio: k* = μ_p / σ_p²  (in daily units)
    mu_p = float(w.values @ mu)
    var_p = float(w.values @ cov @ w.values)
    k_full = mu_p / var_p if var_p > 0 else 0.0
    return dict(weights=w, leverage_full=k_full, leverage_half=k_full / 2.0,
                # for an UNLEVERED long-only book you cap deployment at 100%:
                leverage_unlevered=min(k_full / 2.0, 1.0))


# ── HRP (López de Prado) ──────────────────────────────────────────────────────
def _ivp(cov):
    ivp = 1.0 / np.diag(cov); return ivp / ivp.sum()


def _cluster_var(cov, items):
    c = cov.loc[items, items]
    w = _ivp(c.values).reshape(-1, 1)
    return float((w.T @ c.values @ w).item())


def _quasi_diag(link):
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    n = link[-1, 3]
    while sort_ix.max() >= n:
        sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
        df0 = sort_ix[sort_ix >= n]
        i, j = df0.index, df0.values - n
        sort_ix[i] = link[j, 0]
        sort_ix = pd.concat([sort_ix, pd.Series(link[j, 1], index=i + 1)]).sort_index()
        sort_ix.index = range(sort_ix.shape[0])
    return sort_ix.tolist()


def w_hrp(R):
    cov, corr = R.cov(), R.corr()
    dist = np.sqrt(np.clip((1 - corr) / 2.0, 0, 1))
    link = linkage(squareform(dist.values, checks=False), method="single")
    order = [corr.columns[i] for i in _quasi_diag(link)]
    w = pd.Series(1.0, index=order)
    clusters = [order]
    while clusters:
        clusters = [c[j:k] for c in clusters
                    for j, k in ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for i in range(0, len(clusters), 2):
            c0, c1 = clusters[i], clusters[i + 1]
            v0, v1 = _cluster_var(cov, c0), _cluster_var(cov, c1)
            alpha = 1 - v0 / (v0 + v1)
            w[c0] *= alpha; w[c1] *= 1 - alpha
    return w.reindex(R.columns)


# ── correlation diagnostics ───────────────────────────────────────────────────
def correlation_report(R):
    c = R.corr()
    off = c.where(~np.eye(len(c), dtype=bool))
    pairs = (off.stack().sort_values(ascending=False))
    return dict(avg=off.stack().mean(), min=off.min().min(), max=off.max().max(),
                most_correlated=pairs.head(3), least_correlated=pairs.tail(3))


# ── driver ────────────────────────────────────────────────────────────────────
def combine(R, rf_daily=0.0):
    """Run every allocator; return (metrics_table_df, weights_df, kelly_info, corr_report)."""
    R = R.dropna(how="all").fillna(0.0)
    methods = {
        "equal":         w_equal(R),
        "inverse_vol":   w_inverse_vol(R),
        "min_variance":  w_min_variance(R),
        "risk_parity":   w_risk_parity(R),
        "tangency/kelly": w_max_sharpe(R, rf_daily),  # Kelly shares this relative mix
        "hrp":           w_hrp(R),
    }
    k = kelly(R, rf_daily)                       # leverage reported separately (below)

    weights = pd.DataFrame(methods)
    rows = {m: _perf(R @ w) for m, w in methods.items()}
    # also the best single strategy, for reference
    best = max(R.columns, key=lambda c: _perf(R[c])["sharpe"])
    rows[f"[best single: {best}]"] = _perf(R[best])
    metrics = pd.DataFrame(rows).T[["cagr", "vol", "sharpe", "maxdd", "calmar"]]
    return metrics, weights, k, correlation_report(R)


# ── demo on synthetic strategy return streams ─────────────────────────────────
def _demo():
    rng = np.random.default_rng(11)
    n_days, n_strat = 252 * 8, 8
    # 3 latent factors -> realistic correlation clusters across strategies
    F = rng.normal(0, 0.01, (n_days, 3))
    load = rng.uniform(-1, 1, (n_strat, 3))
    idio = rng.normal(0, 0.012, (n_days, n_strat))
    drift = rng.uniform(0.0001, 0.0006, n_strat)        # varying edge/Sharpe
    R = (F @ load.T) + idio + drift
    cols = [f"strat_{i+1:02d}" for i in range(n_strat)]
    R = pd.DataFrame(R, columns=cols,
                     index=pd.bdate_range("2016-01-01", periods=n_days))

    metrics, weights, k, corr = combine(R)
    pd.set_option("display.width", 120, "display.float_format", lambda x: f"{x:7.3f}")
    print("=== Combined-portfolio performance by allocation method ===")
    print(metrics.to_string())
    print("\n=== Weights per method ===")
    print(weights.round(3).to_string())
    print(f"\n=== Kelly leverage (tangency mix) ===")
    print(f"   full={k['leverage_full']:.1f}x  half={k['leverage_half']:.1f}x  "
          f"unlevered-cap={k['leverage_unlevered']:.2f}x")
    print("   NB: full-Kelly leverage is famously over-aggressive & hyper-sensitive to")
    print("   return estimates. For a no-leverage long-only product, deploy the tangency")
    print("   MIX at <=100% (the 'unlevered-cap'), holding the remainder in cash/liquid debt.")
    print(f"\n=== Strategy correlations === avg={corr['avg']:.2f} "
          f"min={corr['min']:.2f} max={corr['max']:.2f}")
    print("Most correlated pairs:\n", corr["most_correlated"].to_string())
    print("\nTakeaway: combining lifts Sharpe above the best single strategy when "
          "strategies are imperfectly correlated; HRP/risk-parity trade a little\n"
          "return for materially lower drawdown vs concentrated max-Sharpe/Kelly.")


if __name__ == "__main__":
    _demo()
