"""
S&P 500 weekly bull-flag / tight-consolidation-at-highs study.

Detects historical weekly setups that match the mid-2026 chart:
  - POLE : market is up strongly off its 52-week low (>= +20%)
  - FLAG : last 10 weeks of closes sit in a tight horizontal band
           (max/min close span <= 6%, net drift <= 4%)
  - AT HIGHS : close within 2% of the 52-week closing high

For every non-overlapping historical instance, computes forward
price returns 3m / 6m / 1y / 3y / 5y and compares against the
unconditional baseline of all weeks.

Data: tries yfinance (^GSPC, full history) first; if the network is
unavailable it falls back to the S&P 500 daily series bundled with
the `skfolio` package (1990-2022). Price returns only, no dividends.
"""

import numpy as np
import pandas as pd

POLE_MIN_GAIN_OFF_LOW = 0.20   # >= +20% above 52w low (July 2026: +21.6%)
FLAG_WEEKS = 10                # consolidation lookback
FLAG_MAX_RANGE = 0.06          # close-to-close span of flag <= 6%
FLAG_MAX_DRIFT = 0.04          # |net change| across flag <= 4% (horizontal)
NEAR_HIGH_PCT = 0.02           # close within 2% of 52w high (July 2026: 0.94%)
COOLDOWN_WEEKS = 26            # de-duplicate signals within 6 months

HORIZONS = {"3m": 13, "6m": 26, "1y": 52, "3y": 156, "5y": 260}


def load_weekly_close():
    try:
        import yfinance as yf
        df = yf.download("^GSPC", start="1927-01-01", interval="1d",
                         auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        close = df["Close"].dropna()
        if len(close) == 0:
            raise RuntimeError("empty yfinance response")
        src = "yfinance ^GSPC"
    except Exception:
        from skfolio.datasets import load_sp500_index
        close = load_sp500_index()["SP500"].dropna()
        src = "skfolio bundled S&P 500 (1990-2022)"
    weekly = close.resample("W-FRI").last().dropna()
    return weekly, src


def detect_signals(close):
    hi52 = close.rolling(52).max()
    lo52 = close.rolling(52).min()
    flag_hi = close.rolling(FLAG_WEEKS).max()
    flag_lo = close.rolling(FLAG_WEEKS).min()
    drift = close / close.shift(FLAG_WEEKS) - 1

    cond = (
        (close >= hi52 * (1 - NEAR_HIGH_PCT))
        & (close / lo52 - 1 >= POLE_MIN_GAIN_OFF_LOW)
        & (flag_hi / flag_lo - 1 <= FLAG_MAX_RANGE)
        & (drift.abs() <= FLAG_MAX_DRIFT)
    ).fillna(False)

    signals, last = [], None
    for dt in close.index[cond]:
        if last is None or (dt - last).days > COOLDOWN_WEEKS * 7:
            signals.append(dt)
        last = dt
    return signals


def forward_returns(close, signals):
    rows = []
    for dt in signals:
        i = close.index.get_loc(dt)
        row = {"signal_date": dt.date(), "close": round(float(close.iloc[i]), 2)}
        for name, k in HORIZONS.items():
            row[name] = (
                round(float(close.iloc[i + k] / close.iloc[i] - 1) * 100, 1)
                if i + k < len(close) else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def baseline(close):
    out = {}
    for name, k in HORIZONS.items():
        r = (close.shift(-k) / close - 1).dropna() * 100
        out[name] = {"median": r.median(), "pct_positive": (r > 0).mean() * 100}
    return out


def main():
    close, src = load_weekly_close()
    print(f"Source: {src}")
    print(f"Weekly bars: {len(close)}  ({close.index[0].date()} -> {close.index[-1].date()})")

    signals = detect_signals(close)
    res = forward_returns(close, signals)
    print(f"\nHistorical instances (first week of each episode): {len(res)}\n")
    print(res.to_string(index=False))

    base = baseline(close)
    print("\nSummary of forward returns after signal (%):")
    summary = []
    for name in HORIZONS:
        r = res[name].dropna()
        if len(r) == 0:
            continue
        summary.append({
            "horizon": name, "n": len(r),
            "median": round(r.median(), 1), "mean": round(r.mean(), 1),
            "min": round(r.min(), 1), "max": round(r.max(), 1),
            "pct_positive": round((r > 0).mean() * 100, 0),
            "baseline_median": round(base[name]["median"], 1),
            "baseline_pct_pos": round(base[name]["pct_positive"], 0),
        })
    print(pd.DataFrame(summary).to_string(index=False))

    res.to_csv("sp500_flag_signals.csv", index=False)
    print("\nSaved sp500_flag_signals.csv")


if __name__ == "__main__":
    main()
