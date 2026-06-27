"""
Realistic execution layer  |  costs, slippage, circuit (LC/UC) fills, trade blotter
================================================================================
The base engine (swing_backtest.run_backtest) fills at the next close and charges a
flat per-side bps on turnover. Real Indian cash-equity trading is harsher:

  • Slippage scales with SIZE.  A flat bps understates the cost of pushing size
    through a thin name. We add a square-root market-impact term:
        per_side_bps = cost_bps + impact_coef * daily_vol_bps * sqrt(trade_value / ADV)
    so a trade that is a big fraction of a name's ADV pays much more. Names with no
    volume data (close-only sources) can't be sized, so they pay cost_bps + a fixed
    illiquidity surcharge.

  • Circuit limits (LC/UC).  A stock locked at the UPPER circuit has no sellers — you
    can't BUY it; locked at the LOWER circuit it has no buyers — you can't SELL it.
    We detect locked days (a move >= the daily band, or a real-OHLC day that printed a
    single price) and BLOCK the corresponding trade: the position stays at yesterday's
    weight. So you miss the up-gap you chased and you're stuck wearing the down-gap —
    exactly the asymmetry that flat-cost backtests ignore.

  • Liquidity filter is applied upstream (kaggle_pipeline.liquidity_mask) so strategies
    only ever target names that clear an ADV floor.

trade_blotter() turns the realized weight matrix into a per-trade ledger: entry, exit,
hold, return, and the trail (max favourable / adverse excursion) for every position.
"""

import numpy as np
import pandas as pd


def _adv_crore(px, n=20):
    """20-day average daily traded value, ₹ crore (NaN where volume is absent)."""
    return (px.close * px.volume).rolling(n).mean() / 1e7


# ── circuit (LC/UC) detection + blocked fills ──────────────────────────────────
def circuit_masks(px, band=0.20):
    """(upper_lock, lower_lock) bool frames. A name is upper-locked when it gaps up
    >= band (no sellers) and lower-locked when it gaps down <= -band (no buyers).
    For names that carry real OHLC, a day that printed a single price (high==low) with
    a non-trivial move is also treated as locked; close-only names (always high==low)
    rely on the move threshold alone."""
    close = px.close
    ret = close.pct_change()
    eps = 1e-6
    upper = ret >= band - eps
    lower = ret <= -(band - eps)
    if px.high is not None and px.low is not None:
        flat = (px.high == px.low)
        has_range = (px.high > px.low).mean() > 0.05            # per-column: real intraday range?
        flat_lock = flat & has_range                            # ignore flat for close-only names
        upper = upper | (flat_lock & (ret > 0))
        lower = lower | (flat_lock & (ret < 0))
    return upper.fillna(False), lower.fillna(False)


def apply_circuit(target, upper_lock, lower_lock):
    """Block trades that the circuit prevents: keep yesterday's (intended) weight when
    you wanted to BUY a upper-locked name or SELL a lower-locked one. Vectorised
    approximation (uses intended prior weight; circuit days are rare so the drift from
    the true realized prior is negligible)."""
    prev = target.shift(1).fillna(0.0)
    up = upper_lock.reindex_like(target).fillna(False)
    dn = lower_lock.reindex_like(target).fillna(False)
    blocked = ((target > prev) & up) | ((target < prev) & dn)
    return target.where(~blocked, prev)


# ── liquidity-aware cost ───────────────────────────────────────────────────────
def realistic_cost(realized, px, cfg):
    """Daily total cost (fraction of book) with size-dependent slippage."""
    base = cfg.get("cost_bps", 18.0)
    coef = cfg.get("impact_coef", 1.0)
    surch = cfg.get("illiquid_surcharge_bps", 25.0)
    aum = cfg.get("aum_cr", 50.0)

    turn = (realized - realized.shift(1).fillna(0.0)).abs()
    adv = _adv_crore(px).reindex_like(turn)
    vol_bps = (px.close.pct_change().rolling(20).std() * 1e4).reindex_like(turn)
    participation = (turn * aum) / adv                          # fraction of ADV (NaN if no volume)
    impact = coef * vol_bps * np.sqrt(participation.clip(lower=0))
    per_side = (base + impact).where(adv.notna(), base + surch).fillna(base)
    return (turn * per_side / 1e4).sum(axis=1)


def realistic_backtest(px, weights, cfg):
    """Next-close fills with circuit blocking + size-dependent slippage. Same return
    dict shape as swing_backtest.run_backtest, plus 'realized' (post-circuit weights)."""
    close = px.close
    rets = close.pct_change().fillna(0.0)
    target = weights.reindex_like(close).fillna(0.0).clip(lower=0.0)        # long-only
    up, dn = circuit_masks(px, cfg.get("circuit_band", 0.20))
    realized = apply_circuit(target, up, dn)
    held = realized.shift(1).fillna(0.0)                                    # 1-day lag => no look-ahead
    gross = (held * rets).sum(axis=1)
    cost = realistic_cost(realized, px, cfg)
    net = gross - cost
    turnover = (realized - realized.shift(1).fillna(0.0)).abs().sum(axis=1)
    return dict(net=net, equity=(1 + net).cumprod(), turnover=turnover,
                exposure=realized.sum(axis=1), realized=realized, gross=gross, cost=cost)


# ── trade blotter (entry / exit / trail) ───────────────────────────────────────
def trade_blotter(realized, px, min_w=1e-6):
    """Per-trade ledger from the realized weight matrix: for each name, every contiguous
    held span becomes one row with entry/exit dates+prices, hold length, gross return,
    and the trail — max favourable (MFE) and max adverse (MAE) excursion over the hold."""
    close = px.close
    held = realized > min_w
    rows = []
    for tk in held.columns[held.any()]:
        h = held[tk]
        c = close[tk]
        entries = h.index[h & ~h.shift(1, fill_value=False)]
        exits = h.index[(~h) & h.shift(1, fill_value=False)]
        for e in entries:
            later = exits[exits > e]
            xd = later[0] if len(later) else h.index[-1]
            open_end = len(later) == 0
            seg = c.loc[e:xd].dropna()
            if len(seg) < 1 or pd.isna(seg.iloc[0]) or seg.iloc[0] == 0:
                continue
            ep, xp = seg.iloc[0], seg.iloc[-1]
            w_seg = realized[tk].loc[e:xd]
            rows.append({
                "ticker": tk,
                "entry_date": e.date(), "exit_date": xd.date(),
                "hold_days": int(len(seg)),
                "entry_px": round(float(ep), 2), "exit_px": round(float(xp), 2),
                "ret_pct": round(100 * (xp / ep - 1), 2),
                "mfe_pct": round(100 * (seg.max() / ep - 1), 2),     # trail: best unrealized
                "mae_pct": round(100 * (seg.min() / ep - 1), 2),     # trail: worst unrealized
                "avg_weight": round(float(w_seg.mean()), 4),
                "open_at_end": open_end,
            })
    cols = ["ticker", "entry_date", "exit_date", "hold_days", "entry_px", "exit_px",
            "ret_pct", "mfe_pct", "mae_pct", "avg_weight", "open_at_end"]
    bl = pd.DataFrame(rows, columns=cols)
    return bl.sort_values(["entry_date", "ticker"]).reset_index(drop=True) if len(bl) else bl


def trade_stats(bl):
    """Trade-level statistics from one blotter: win rate, average win/loss, payoff
    ratio, and per-trade EXPECTANCY (= mean trade return, i.e. win%·avgWin + loss%·avgLoss).
    Expectancy is the bottom line — a strategy can win often yet bleed if the losers are
    big, or win rarely yet profit if the winners run."""
    if bl is None or len(bl) == 0:
        return {"n_trades": 0, "win_rate": np.nan, "avg_win_pct": np.nan,
                "avg_loss_pct": np.nan, "payoff": np.nan, "expectancy_pct": np.nan,
                "avg_hold_d": np.nan, "avg_mfe_pct": np.nan, "avg_mae_pct": np.nan,
                "best_pct": np.nan, "worst_pct": np.nan, "open_at_end": 0}
    r = bl["ret_pct"].astype(float)
    wins, losses = r[r > 0], r[r <= 0]
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = losses.mean() if len(losses) else 0.0                  # <= 0
    return {
        "n_trades": int(len(r)),
        "win_rate": round(len(wins) / len(r), 4),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "payoff": round(avg_win / abs(avg_loss), 2) if avg_loss < 0 else np.nan,
        "expectancy_pct": round(r.mean(), 3),                        # per-trade edge
        "avg_hold_d": round(bl["hold_days"].mean(), 1),
        "avg_mfe_pct": round(bl["mfe_pct"].mean(), 2),
        "avg_mae_pct": round(bl["mae_pct"].mean(), 2),
        "best_pct": round(r.max(), 1),
        "worst_pct": round(r.min(), 1),
        "open_at_end": int(bl["open_at_end"].sum()) if "open_at_end" in bl else 0,
    }
