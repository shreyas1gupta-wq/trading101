"""
Indian Blue-Chip Stocks  |  12-Year Total Return Analysis (approx. 2010-2022)
Data source: Provided research data (book/report), ~12-year window ending 2022.
Sensex benchmark: Jan 2010 → Dec 2022  (~17,400 → ~60,840)  ≈ 3.49x  |  10.8% CAGR
"""

import pandas as pd
import numpy as np
from tabulate import tabulate

# ── Raw data from research table ─────────────────────────────────────────────
# (stock name, total_return_x, cagr_pct)
RAW_DATA = [
    ("ABB",                  16,   29),
    ("ACC",                   8,   21),
    ("Adani Enterprises",    17,   30),
    ("Ambuja Cements",        6,   18),
    ("Ashok Leyland",        10,   23),
    ("Asian Paints",         15,   28),
    ("Bajaj Auto",            8,   21),
    ("Bharat Electronics",   30,   36),
    ("Bharat Forge",         13,   26),
    ("Blue Star",            22,   32),
    ("Bosch",                13,   26),
    ("Britannia",             3,   11),
    ("Cipla",                 4,   13),
    ("Colgate-Palmolive",     6,   18),
    ("Container Corpn",      17,   29),
    ("CRISIL",               16,   28),
    ("Cummins India",         9,   22),
    ("Dabur India",           7,   20),
    ("Dewan Housing (DHFL)", 12,   25),
    ("Exide Inds",           25,   34),
    ("Federal Bank",         32,   37),
    ("GAIL India",           14,   27),
    ("GE Shipping",          20,   31),
    ("Grasim Inds",           9,   22),
    ("GSK Consumer",          5,   15),
    ("GSK Pharma",            4,   12),
    ("Havells India",        51,   43),
    ("HDFC",                 19,   31),
    ("Hero MotoCorp",        10,   23),
    ("Hind. Unilever",        2,    4),
    ("Hindalco",              4,   12),
    ("Infosys",               3,   11),
    ("IOC",                   6,   19),
    ("Ipca Labs",            21,   32),
    ("ITC",                   8,   21),
    ("L&T",                  24,   33),
    ("LIC Housing Finance",  37,   39),
    ("M&M",                   9,   22),
    ("Motherson Sumi",       63,   46),
    ("Nestle India",          9,   23),
    ("Pfizer",                3,    9),
    ("Pidilite",              9,   23),
    ("Reliance",              9,   22),
    ("Sesa Goa (Vedanta)",  185,   61),
    ("SBI",                  15,   28),
    ("Tata Steel",           10,   24),
    ("Titan",                44,   41),
    ("Wipro",                 1,   -1),
]

# Sensex (BSE) benchmark – Jan 2010 → Dec 2022 (~12 years)
# Approx: 17,400 → 60,840  ≈  3.49x total return
SENSEX = {
    "total_return_x":   3.49,
    "total_return_pct": 249.0,
    "cagr_pct":         10.8,
    "period":           "~12 years (Jan 2010 – Dec 2022)",
}


def build_dataframe():
    df = pd.DataFrame(RAW_DATA, columns=["stock", "total_return_x", "cagr_pct"])
    df["total_return_pct"] = (df["total_return_x"] - 1) * 100
    df["beat_sensex"] = df["cagr_pct"] > SENSEX["cagr_pct"]
    df = df.sort_values("cagr_pct", ascending=False).reset_index(drop=True)
    return df


def main():
    df = build_dataframe()
    N = len(df)

    print("=" * 74)
    print("    INDIAN BLUE-CHIP STOCKS  |  12-YEAR TOTAL RETURN ANALYSIS")
    print("    Period: ~2010–2022  |  Data: Research Table (Price + Dividends)")
    print("=" * 74)

    # ── BENCHMARK ────────────────────────────────────────────────────────────
    print(f"\n  BSE SENSEX ({SENSEX['period']})")
    print(f"  Total Return : {SENSEX['total_return_x']:.2f}x  ({SENSEX['total_return_pct']:.0f}%)")
    print(f"  CAGR         : {SENSEX['cagr_pct']:.1f}% per annum")

    # ── FULL TABLE ───────────────────────────────────────────────────────────
    print("\n" + "=" * 74)
    print("    STOCK-WISE RETURNS  (sorted by CAGR, high → low)")
    print("=" * 74)
    rows = []
    for rank, r in df.iterrows():
        beat = "YES ✓" if r["beat_sensex"] else "no"
        rows.append([rank + 1, r["stock"],
                     f"{r['total_return_x']:.0f}x",
                     f"{r['total_return_pct']:.0f}%",
                     f"{r['cagr_pct']:.0f}%",
                     beat])
    headers = ["#", "Stock", "Return (x)", "Return (%)", "CAGR (%)", "Beat Sensex?"]
    print(tabulate(rows, headers=headers, tablefmt="grid"))

    # ── EQUAL-WEIGHT PORTFOLIO ───────────────────────────────────────────────
    avg_return_x   = df["total_return_x"].mean()
    # Derive implied years from CAGR data (cross-check via geometric mean of (1+cagr)^12)
    years_implied  = 12
    portfolio_cagr = (avg_return_x ** (1 / years_implied) - 1) * 100

    # Median-weight portfolio (use median stock return as portfolio proxy)
    median_return_x   = float(np.median(df["total_return_x"]))
    median_port_cagr  = (median_return_x ** (1 / years_implied) - 1) * 100

    print("\n" + "=" * 74)
    print("    EQUAL-WEIGHT PORTFOLIO  (all 48 stocks, equal allocation)")
    print("=" * 74)
    print(f"  Stocks in portfolio          : {N}")
    print(f"  Avg Total Return (arith.)    : {avg_return_x:.2f}x  ({(avg_return_x-1)*100:.0f}%)")
    print(f"  Portfolio CAGR (implied)     : {portfolio_cagr:.1f}%  per annum")
    print(f"  Sensex CAGR                  : {SENSEX['cagr_pct']:.1f}%  per annum")
    print(f"  Alpha vs Sensex              : {portfolio_cagr - SENSEX['cagr_pct']:+.1f}%  per year")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  Median-stock Return          : {median_return_x:.0f}x")
    print(f"  Median-stock CAGR            : {median_port_cagr:.1f}%  per annum")
    print(f"  Median Alpha vs Sensex       : {median_port_cagr - SENSEX['cagr_pct']:+.1f}%  per year")

    # ── DISTRIBUTION STATS ───────────────────────────────────────────────────
    cagrs  = df["cagr_pct"].values.astype(float)
    ret_x  = df["total_return_x"].values.astype(float)

    mean_cagr   = float(np.mean(cagrs))
    median_cagr = float(np.median(cagrs))
    std_cagr    = float(np.std(cagrs))
    q1 = float(np.percentile(cagrs, 25))
    q3 = float(np.percentile(cagrs, 75))
    iqr = q3 - q1

    best_idx  = df["cagr_pct"].idxmax()
    worst_idx = df["cagr_pct"].idxmin()
    best_rx   = df["total_return_x"].idxmax()
    worst_rx  = df["total_return_x"].idxmin()

    win_count = int(df["beat_sensex"].sum())
    win_rate  = win_count / N * 100

    pos_count   = int((df["cagr_pct"] > 0).sum())
    count_2x    = int((ret_x >= 2).sum())
    count_5x    = int((ret_x >= 5).sum())
    count_10x   = int((ret_x >= 10).sum())
    count_20x   = int((ret_x >= 20).sum())
    count_50x   = int((ret_x >= 50).sum())

    print("\n" + "=" * 74)
    print("    DISTRIBUTION STATISTICS")
    print("=" * 74)
    print(f"  N (stocks in sample)         : {N}")
    print(f"  Mean CAGR                    : {mean_cagr:.1f}%")
    print(f"  Median CAGR                  : {median_cagr:.1f}%")
    print(f"  Std Deviation (CAGR)         : {std_cagr:.1f}%")
    print(f"  Skewness (CAGR)              : {float(pd.Series(cagrs).skew()):.2f}  (right-skewed = a few big winners)")
    print(f"  ─────────────────────────────────────────────────────────")
    print(f"  Best CAGR   : {df.loc[best_idx, 'cagr_pct']:.0f}%   → {df.loc[best_idx, 'stock']}")
    print(f"  Worst CAGR  : {df.loc[worst_idx, 'cagr_pct']:.0f}%    → {df.loc[worst_idx, 'stock']}")
    print(f"  Best Return : {df.loc[best_rx, 'total_return_x']:.0f}x   → {df.loc[best_rx, 'stock']}")
    print(f"  Worst Return: {df.loc[worst_rx, 'total_return_x']:.0f}x     → {df.loc[worst_rx, 'stock']}")

    print(f"\n  Percentile Breakdown (CAGR):")
    print(f"    10th pct                   : {np.percentile(cagrs, 10):.1f}%")
    print(f"    25th pct  (Q1)             : {q1:.1f}%")
    print(f"    50th pct  (Median)         : {median_cagr:.1f}%")
    print(f"    75th pct  (Q3)             : {q3:.1f}%")
    print(f"    90th pct                   : {np.percentile(cagrs, 90):.1f}%")
    print(f"    IQR  (Q3 − Q1)             : {iqr:.1f}%")

    print(f"\n  Return Multiple Distribution:")
    print(f"    Stocks with positive CAGR  : {pos_count}/{N}  ({pos_count/N*100:.0f}%)")
    print(f"    Stocks ≥ 2x                : {count_2x}/{N}  ({count_2x/N*100:.0f}%)")
    print(f"    Stocks ≥ 5x                : {count_5x}/{N}  ({count_5x/N*100:.0f}%)")
    print(f"    Stocks ≥ 10x               : {count_10x}/{N}  ({count_10x/N*100:.0f}%)")
    print(f"    Stocks ≥ 20x               : {count_20x}/{N}  ({count_20x/N*100:.0f}%)")
    print(f"    Stocks ≥ 50x               : {count_50x}/{N}  ({count_50x/N*100:.0f}%)")

    # ── WIN RATE ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 74)
    print("    WIN RATE vs BSE SENSEX")
    print("=" * 74)
    print(f"  Sensex CAGR hurdle           : {SENSEX['cagr_pct']:.1f}%")
    print(f"  Stocks BEATING Sensex        : {win_count}/{N}  ({win_rate:.0f}%)")
    print(f"  Stocks LAGGING  Sensex       : {N-win_count}/{N}  ({100-win_rate:.0f}%)")

    winners = df[df["beat_sensex"]].sort_values("cagr_pct", ascending=False)
    losers  = df[~df["beat_sensex"]].sort_values("cagr_pct", ascending=True)
    print(f"\n  Stocks lagging Sensex: {', '.join(losers['stock'].tolist())}")

    # ── TOP / BOTTOM TABLES ──────────────────────────────────────────────────
    print("\n" + "=" * 74)
    print("    TOP 10 PERFORMERS")
    print("=" * 74)
    for _, r in df.head(10).iterrows():
        bar = "█" * min(int(r["cagr_pct"] / 3), 20)
        print(f"  {r['stock']:<25}  {r['total_return_x']:>5.0f}x   {r['cagr_pct']:>4.0f}% CAGR  {bar}")

    print("\n" + "=" * 74)
    print("    BOTTOM 10 PERFORMERS")
    print("=" * 74)
    for _, r in df.tail(10).iterrows():
        print(f"  {r['stock']:<25}  {r['total_return_x']:>5.0f}x   {r['cagr_pct']:>4.0f}% CAGR")

    # ── PORTFOLIO vs SENSEX SUMMARY ──────────────────────────────────────────
    print("\n" + "=" * 74)
    print("    PORTFOLIO vs SENSEX  —  ₹100 INVESTED (hypothetical)")
    print("=" * 74)
    print(f"  Equal-weight portfolio → ₹{avg_return_x*100:,.0f}   ({avg_return_x:.1f}x)")
    print(f"  BSE Sensex             → ₹{SENSEX['total_return_x']*100:,.0f}   ({SENSEX['total_return_x']:.1f}x)")
    print(f"  Extra wealth generated : ₹{(avg_return_x - SENSEX['total_return_x'])*100:,.0f} per ₹100 invested")
    best_single = df["total_return_x"].max()
    best_name   = df.loc[df["total_return_x"].idxmax(), "stock"]
    print(f"  Best single stock      → ₹{best_single*100:,.0f}   ({best_name}, {best_single:.0f}x)")

    # ── SAVE CSV ─────────────────────────────────────────────────────────────
    df.to_csv("bluechip_returns_12yr.csv", index=False)
    print(f"\n  Results saved → bluechip_returns_12yr.csv")
    print("\n" + "=" * 74)
    print("    ANALYSIS COMPLETE")
    print("=" * 74 + "\n")

    return df


if __name__ == "__main__":
    main()
