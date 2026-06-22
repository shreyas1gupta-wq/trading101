"""
Sub-Period Return Analysis: 2012-2016 and 2016-2020
Data: Approximate estimates from market research + known events.
NOTE: External finance APIs are blocked in this environment.
      Figures are research-informed estimates, not live price data.

Key reference points (Sensex):
  Jan 2012: ~15,900  |  Dec 2016: ~26,625  |  Dec 2020: ~47,750
  2012-2016: 1.67x  (13.5% CAGR)
  2016-2020: 1.79x  (15.7% CAGR)

DHFL note: Went bankrupt in 2019 (IL&FS/NBFC crisis). Stock fell ~95%.
Sesa Goa merged into Vedanta Ltd (2013). Commodity cycle volatile.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from tabulate import tabulate
import os

os.makedirs("charts", exist_ok=True)

# ── Benchmark ─────────────────────────────────────────────────────────────────
SENSEX = {
    "2012_2016": {"return_x": 1.67, "cagr": 13.5},
    "2016_2020": {"return_x": 1.79, "cagr": 15.7},
    "12yr":      {"return_x": 3.49, "cagr": 10.8},   # from prior analysis
}

# ── Sub-period data ───────────────────────────────────────────────────────────
# (stock, 2012-2016 return_x, 2016-2020 return_x, 12yr_return_x from table)
# CAGR = x^(1/4) - 1 for 4-year periods
# Market context:
#   2012-2016: Modi election rally (2014), capex revival, auto boom
#   2016-2020: Demonetization (Nov'16), GST (Jul'17), IL&FS crisis (Sep'18),
#              COVID crash (Mar'20) → V-recovery (Dec'20)
RAW = [
    # stock name,              2012-16x, 2016-20x, 12yr_x
    ("ABB",                      2.5,     1.7,     16),
    ("ACC",                      1.6,     1.4,      8),
    ("Adani Enterprises",        1.8,     2.5,     17),
    ("Ambuja Cements",           1.5,     1.4,      6),
    ("Ashok Leyland",            3.0,     1.4,     10),
    ("Asian Paints",             2.1,     2.0,     15),
    ("Bajaj Auto",               1.9,     1.6,      8),
    ("Bharat Electronics",       3.8,     2.0,     30),
    ("Bharat Forge",             2.8,     1.7,     13),
    ("Blue Star",                2.3,     2.2,     22),
    ("Bosch",                    2.5,     1.7,     13),
    ("Britannia",                1.4,     1.8,      3),
    ("Cipla",                    1.5,     1.4,      4),
    ("Colgate-Palmolive",        1.5,     1.5,      6),
    ("Container Corpn",          2.1,     1.7,     17),
    ("CRISIL",                   2.4,     1.9,     16),
    ("Cummins India",            2.1,     1.5,      9),
    ("Dabur India",              1.7,     1.6,      7),
    ("Dewan Housing (DHFL)",     4.2,     0.08,    12),  # ~92% collapse 2018-19
    ("Exide Inds",               2.6,     2.0,     25),
    ("Federal Bank",             3.2,     1.8,     32),
    ("GAIL India",               2.2,     1.7,     14),
    ("GE Shipping",              2.6,     1.9,     20),
    ("Grasim Inds",              1.8,     1.7,      9),
    ("GSK Consumer",             1.7,     1.4,      5),
    ("GSK Pharma",               1.5,     1.3,      4),
    ("Havells India",            3.8,     3.0,     51),
    ("HDFC",                     2.4,     2.1,     19),
    ("Hero MotoCorp",            2.3,     1.5,     10),
    ("HUL",                      1.3,     2.0,      2),
    ("Hindalco",                 1.2,     1.5,      4),
    ("Infosys",                  1.4,     1.5,      3),
    ("IOC",                      1.9,     1.5,      6),
    ("Ipca Labs",                2.8,     1.8,     21),
    ("ITC",                      1.9,     1.6,      8),
    ("L&T",                      2.7,     2.0,     24),
    ("LIC Housing Finance",      3.6,     1.6,     37),
    ("M&M",                      2.1,     1.5,      9),
    ("Motherson Sumi",           6.5,     2.5,     63),
    ("Nestle India",             1.7,     1.9,      9),
    ("Pfizer",                   1.4,     1.3,      3),
    ("Pidilite",                 2.2,     1.8,      9),
    ("Reliance",                 1.3,     2.8,      9),
    ("Sesa Goa (Vedanta)",       2.0,     3.5,    185),
    ("SBI",                      2.6,     1.4,     15),
    ("Tata Steel",               1.4,     1.9,     10),
    ("Titan",                    2.3,     3.2,     44),
    ("Wipro",                    1.2,     1.1,      1),
]

PERIOD_LABELS = ["2012-2016", "2016-2020"]
SENSEX_X = [SENSEX["2012_2016"]["return_x"], SENSEX["2016_2020"]["return_x"]]
SENSEX_C = [SENSEX["2012_2016"]["cagr"],     SENSEX["2016_2020"]["cagr"]]


def cagr(x, yrs=4):
    return (x ** (1/yrs) - 1) * 100


def build_df():
    cols = ["stock", "ret_12_16", "ret_16_20", "ret_12yr",
            "cagr_12_16", "cagr_16_20", "cagr_12yr",
            "beat_12_16", "beat_16_20",
            "consistent_beater", "reversal"]
    rows = []
    for name, r1, r2, r12 in RAW:
        c1 = cagr(r1)
        c2 = cagr(r2)
        c12 = (r12 ** (1/12) - 1) * 100 if r12 > 0 else -100
        b1 = c1 > SENSEX_C[0]
        b2 = c2 > SENSEX_C[1]
        consistent = b1 and b2
        reversal = (b1 and not b2) or (not b1 and b2)
        rows.append([name, r1, r2, r12, c1, c2, c12, b1, b2, consistent, reversal])
    df = pd.DataFrame(rows, columns=cols)
    return df


# ── colour palette ────────────────────────────────────────────────────────────
BG     = "#0D1117"; PANEL  = "#161B22"; TEXT = "#E6EDF3"; GRID = "#30363D"
GREEN  = "#2EA043"; ORANGE = "#E67E22"; RED  = "#E74C3C"
BLUE   = "#58A6FF"; YELLOW = "#F1C40F"; PURPLE = "#BC8CFF"


def style_ax(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    for sp in ax.spines.values():
        sp.set_edgecolor(GRID)
    ax.grid(color=GRID, linewidth=0.5, alpha=0.5)


def main():
    df = build_df()
    N = len(df)

    print("=" * 78)
    print("    BLUE-CHIP STOCKS  |  SUB-PERIOD RETURN ANALYSIS")
    print("    Period 1: 2012–2016  |  Period 2: 2016–2020")
    print("    [Figures are research-informed estimates — see module docstring]")
    print("=" * 78)

    # ── Benchmark ─────────────────────────────────────────────────────────────
    print(f"""
  BSE SENSEX
    2012–2016 : {SENSEX_X[0]:.2f}x   CAGR {SENSEX_C[0]:.1f}%
    2016–2020 : {SENSEX_X[1]:.2f}x   CAGR {SENSEX_C[1]:.1f}%
""")

    # ── Full comparison table ─────────────────────────────────────────────────
    print("=" * 78)
    print("    STOCK RETURNS BY PERIOD")
    print("=" * 78)

    table_rows = []
    for _, r in df.sort_values("cagr_12_16", ascending=False).iterrows():
        b1 = "YES" if r["beat_12_16"] else "no"
        b2 = "YES" if r["beat_16_20"] else "no"
        momentum = ("↑ both"   if r["consistent_beater"] else
                    "↓ both"   if not r["beat_12_16"] and not r["beat_16_20"] else
                    "→ faded"  if r["beat_12_16"] and not r["beat_16_20"] else
                    "→ caught up")
        table_rows.append([
            r["stock"],
            f"{r['ret_12_16']:.1f}x", f"{r['cagr_12_16']:.1f}%", b1,
            f"{r['ret_16_20']:.1f}x", f"{r['cagr_16_20']:.1f}%", b2,
            momentum,
        ])
    headers = [
        "Stock",
        "2012-16(x)", "CAGR", "Beat?",
        "2016-20(x)", "CAGR", "Beat?",
        "Pattern"
    ]
    print(tabulate(table_rows, headers=headers, tablefmt="grid"))

    # ── Period-level portfolio stats ──────────────────────────────────────────
    for period, col_x, col_c, beat_col, s_x, s_c in [
        ("2012–2016", "ret_12_16", "cagr_12_16", "beat_12_16", SENSEX_X[0], SENSEX_C[0]),
        ("2016–2020", "ret_16_20", "cagr_16_20", "beat_16_20", SENSEX_X[1], SENSEX_C[1]),
    ]:
        cagrs = df[col_c].values
        ret_x = df[col_x].values
        wins  = df[beat_col].sum()

        avg_x  = ret_x.mean()
        port_c = cagr(avg_x)

        print(f"\n{'='*78}")
        print(f"    {period} — PORTFOLIO STATS")
        print(f"{'='*78}")
        print(f"  Equal-Weight Avg Return  : {avg_x:.2f}x  ({(avg_x-1)*100:.0f}%)")
        print(f"  Portfolio CAGR           : {port_c:.1f}%")
        print(f"  Sensex CAGR              : {s_c:.1f}%")
        print(f"  Portfolio Alpha          : {port_c - s_c:+.1f}%/yr")
        print(f"  Win Rate vs Sensex       : {wins}/{N}  ({wins/N*100:.0f}%)")
        print(f"  Median CAGR              : {np.median(cagrs):.1f}%")
        print(f"  Mean CAGR                : {np.mean(cagrs):.1f}%")
        print(f"  Std Dev CAGR             : {np.std(cagrs):.1f}%")
        print(f"  Best  : {df.loc[df[col_c].idxmax(), 'stock']}  {df[col_c].max():.1f}%")
        print(f"  Worst : {df.loc[df[col_c].idxmin(), 'stock']}  {df[col_c].min():.1f}%")
        print(f"  Stocks ≥ 2x  : {(ret_x>=2).sum()}/{N}   Stocks ≥ 3x: {(ret_x>=3).sum()}/{N}")

    # ── Pattern analysis ──────────────────────────────────────────────────────
    consistent_beat = df[df["consistent_beater"]]
    faded           = df[df["beat_12_16"] & ~df["beat_16_20"]]
    caught_up       = df[~df["beat_12_16"] & df["beat_16_20"]]
    laggards        = df[~df["beat_12_16"] & ~df["beat_16_20"]]

    print(f"\n{'='*78}")
    print(f"    PERFORMANCE PATTERNS")
    print(f"{'='*78}")
    print(f"\n  CONSISTENT BEATERS (beat Sensex in BOTH periods)  [{len(consistent_beat)}/{N}]:")
    for _, r in consistent_beat.sort_values("cagr_12_16", ascending=False).iterrows():
        print(f"    {r['stock']:<25}  {r['ret_12_16']:.1f}x ({r['cagr_12_16']:.0f}%)  →  {r['ret_16_20']:.1f}x ({r['cagr_16_20']:.0f}%)")

    print(f"\n  FADED (beat 2012-16, lagged 2016-20)  [{len(faded)}/{N}]:")
    for _, r in faded.sort_values("cagr_12_16", ascending=False).iterrows():
        print(f"    {r['stock']:<25}  {r['ret_12_16']:.1f}x ({r['cagr_12_16']:.0f}%)  →  {r['ret_16_20']:.1f}x ({r['cagr_16_20']:.0f}%)")

    print(f"\n  CAUGHT UP (lagged 2012-16, beat 2016-20)  [{len(caught_up)}/{N}]:")
    for _, r in caught_up.sort_values("cagr_16_20", ascending=False).iterrows():
        print(f"    {r['stock']:<25}  {r['ret_12_16']:.1f}x ({r['cagr_12_16']:.0f}%)  →  {r['ret_16_20']:.1f}x ({r['cagr_16_20']:.0f}%)")

    print(f"\n  CONSISTENT LAGGARDS (lagged Sensex both periods)  [{len(laggards)}/{N}]:")
    for _, r in laggards.iterrows():
        print(f"    {r['stock']:<25}  {r['ret_12_16']:.1f}x ({r['cagr_12_16']:.0f}%)  →  {r['ret_16_20']:.1f}x ({r['cagr_16_20']:.0f}%)")

    # ── Top/bottom per period ─────────────────────────────────────────────────
    for period, col_c, col_x in [
        ("2012–2016", "cagr_12_16", "ret_12_16"),
        ("2016–2020", "cagr_16_20", "ret_16_20"),
    ]:
        print(f"\n  TOP 5  {period}")
        for _, r in df.nlargest(5, col_c).iterrows():
            print(f"    {r['stock']:<25}  {r[col_x]:.1f}x   {r[col_c]:.1f}% CAGR")
        print(f"\n  BOTTOM 5  {period}")
        for _, r in df.nsmallest(5, col_c).iterrows():
            print(f"    {r['stock']:<25}  {r[col_x]:.1f}x   {r[col_c]:.1f}% CAGR")

    # ── DHFL spotlight ────────────────────────────────────────────────────────
    dhfl = df[df["stock"] == "Dewan Housing (DHFL)"].iloc[0]
    print(f"""
{'='*78}
    SPOTLIGHT: DEWAN HOUSING (DHFL) — THE CAUTIONARY TALE
{'='*78}
  2012–2016  :  {dhfl['ret_12_16']:.1f}x  ({dhfl['cagr_12_16']:.1f}% CAGR)  ← Housing boom, fastest growing HFC
  2016–2020  :  {dhfl['ret_16_20']:.2f}x  ({dhfl['cagr_16_20']:.1f}% CAGR)  ← CATASTROPHIC
               IL&FS crisis (Sep 2018) triggered NBFC/HFC credit crunch.
               DHFL admitted payment defaults (Jun 2019).
               RBI superseded board (Nov 2019).
               Stock collapsed from ~₹600 (peak) to ~₹5-20 by 2020.
               Acquired by Piramal Capital via NCLT (Sep 2021).
  Lesson    :  A 4x return in one period can be wiped out in the next.
               Leverage + governance risk = permanent capital loss.
""")

    # ── Wealth path ₹1L ──────────────────────────────────────────────────────
    port1_val = df["ret_12_16"].mean()
    port2_val = df["ret_16_20"].mean()
    overall_8yr = port1_val * port2_val
    sensex_8yr  = SENSEX_X[0] * SENSEX_X[1]

    print(f"{'='*78}")
    print(f"    ₹1 LAKH INVESTED — 8-YEAR JOURNEY  (2012 → 2020)")
    print(f"{'='*78}")
    print(f"  Start (2012)  : ₹1,00,000")
    print(f"  After 2016    : Portfolio ₹{port1_val*1e5:,.0f}   vs   Sensex ₹{SENSEX_X[0]*1e5:,.0f}")
    print(f"  After 2020    : Portfolio ₹{overall_8yr*1e5:,.0f}  vs   Sensex ₹{sensex_8yr*1e5:,.0f}")
    print(f"  8-yr Alpha    : +₹{(overall_8yr - sensex_8yr)*1e5:,.0f} extra per ₹1L invested")
    print(f"  Portfolio 8yr : {overall_8yr:.2f}x  ({cagr(overall_8yr, 8):.1f}% CAGR)")
    print(f"  Sensex 8yr    : {sensex_8yr:.2f}x  ({cagr(sensex_8yr, 8):.1f}% CAGR)")

    df.to_csv("subperiod_returns.csv", index=False)
    print(f"\n  Saved → subperiod_returns.csv\n")

    return df


# ── CHARTS ────────────────────────────────────────────────────────────────────

def make_charts(df):
    fig = plt.figure(figsize=(22, 28), facecolor=BG)
    fig.suptitle(
        "Blue-Chip Stocks  |  Sub-Period Analysis  |  2012–2016  vs  2016–2020",
        fontsize=17, fontweight="bold", color=TEXT, y=0.995
    )
    gs = gridspec.GridSpec(4, 2, figure=fig,
                           hspace=0.50, wspace=0.30,
                           left=0.06, right=0.98, top=0.98, bottom=0.02)

    ax1 = fig.add_subplot(gs[0, :])  # Grouped bar – CAGR comparison per stock
    ax2 = fig.add_subplot(gs[1, 0])  # Scatter: period1 vs period2 CAGR
    ax3 = fig.add_subplot(gs[1, 1])  # Win rate bars
    ax4 = fig.add_subplot(gs[2, :])  # Horizontal bar sorted by 2012-16 CAGR
    ax5 = fig.add_subplot(gs[3, :])  # Horizontal bar sorted by 2016-20 CAGR

    for ax in [ax1, ax2, ax3, ax4, ax5]:
        style_ax(ax)

    df_s1 = df.sort_values("cagr_12_16", ascending=False).reset_index(drop=True)
    df_s2 = df.sort_values("cagr_16_20", ascending=False).reset_index(drop=True)

    # ── Panel 1: Grouped bar – top 20 by either period ────────────────────────
    top_stocks = pd.concat([
        df.nlargest(10, "cagr_12_16"),
        df.nlargest(10, "cagr_16_20"),
    ]).drop_duplicates("stock").sort_values("cagr_12_16", ascending=False).head(20)

    x = np.arange(len(top_stocks))
    w = 0.38
    ax1.bar(x - w/2, top_stocks["cagr_12_16"], w, color=GREEN,  alpha=0.85,
            label="2012–2016", edgecolor=BG, linewidth=0.4)
    ax1.bar(x + w/2, top_stocks["cagr_16_20"], w, color=BLUE,   alpha=0.85,
            label="2016–2020", edgecolor=BG, linewidth=0.4)
    ax1.axhline(SENSEX_C[0], color=GREEN,  lw=1.5, ls="--", alpha=0.7,
                label=f"Sensex 2012-16: {SENSEX_C[0]:.1f}%")
    ax1.axhline(SENSEX_C[1], color=BLUE,   lw=1.5, ls=":",  alpha=0.7,
                label=f"Sensex 2016-20: {SENSEX_C[1]:.1f}%")
    ax1.set_xticks(x)
    ax1.set_xticklabels(top_stocks["stock"], rotation=40, ha="right", fontsize=7.5)
    ax1.set_ylabel("CAGR (%)", fontsize=10)
    ax1.set_title("Top Performers by CAGR — Both Periods Side-by-Side", fontsize=12, fontweight="bold")
    ax1.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    # ── Panel 2: Scatter – 2012-16 CAGR vs 2016-20 CAGR ─────────────────────
    colors_sc = []
    for _, r in df.iterrows():
        if r["consistent_beater"]: colors_sc.append(GREEN)
        elif r["beat_12_16"] and not r["beat_16_20"]: colors_sc.append(ORANGE)
        elif not r["beat_12_16"] and r["beat_16_20"]: colors_sc.append(BLUE)
        else: colors_sc.append(RED)

    ax2.scatter(df["cagr_12_16"], df["cagr_16_20"], c=colors_sc,
                s=60, edgecolors="white", linewidths=0.4, zorder=3)
    ax2.axvline(SENSEX_C[0], color=GREEN, lw=1.5, ls="--", alpha=0.8)
    ax2.axhline(SENSEX_C[1], color=BLUE,  lw=1.5, ls="--", alpha=0.8)

    # Quadrant labels
    ax2.text(0.02, 0.98, "Lagged both", transform=ax2.transAxes,
             color=RED, fontsize=8, va="top")
    ax2.text(0.98, 0.98, "Beat both\n(consistent)", transform=ax2.transAxes,
             color=GREEN, fontsize=8, va="top", ha="right")
    ax2.text(0.98, 0.02, "Faded", transform=ax2.transAxes,
             color=ORANGE, fontsize=8, ha="right")
    ax2.text(0.02, 0.02, "Caught up", transform=ax2.transAxes,
             color=BLUE, fontsize=8)

    for _, r in df.iterrows():
        if abs(r["cagr_12_16"]) > 40 or abs(r["cagr_16_20"]) > 30 or r["cagr_16_20"] < -10:
            ax2.annotate(r["stock"].split(" ")[0],
                         (r["cagr_12_16"], r["cagr_16_20"]),
                         textcoords="offset points", xytext=(4, 3),
                         fontsize=6.5, color=TEXT)

    ax2.set_xlabel("CAGR 2012–2016 (%)", fontsize=10)
    ax2.set_ylabel("CAGR 2016–2020 (%)", fontsize=10)
    ax2.set_title("Period Consistency Scatter", fontsize=11, fontweight="bold")
    legend_patches = [
        mpatches.Patch(color=GREEN,  label="Beat both"),
        mpatches.Patch(color=ORANGE, label="Faded"),
        mpatches.Patch(color=BLUE,   label="Caught up"),
        mpatches.Patch(color=RED,    label="Lagged both"),
    ]
    ax2.legend(handles=legend_patches, facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    # ── Panel 3: Win rate + stats bars ────────────────────────────────────────
    metrics = ["Win Rate\n(%)", "Median CAGR\n(%)", "Mean CAGR\n(%)", "Portfolio\nCAGR (%)"]
    p1_vals = [
        df["beat_12_16"].mean() * 100,
        df["cagr_12_16"].median(),
        df["cagr_12_16"].mean(),
        cagr(df["ret_12_16"].mean()),
    ]
    p2_vals = [
        df["beat_16_20"].mean() * 100,
        df["cagr_16_20"].median(),
        df["cagr_16_20"].mean(),
        cagr(df["ret_16_20"].mean()),
    ]
    sensex_vals = [100, SENSEX_C[0], SENSEX_C[0], SENSEX_C[0]]  # win rate: Sensex beats itself 100%

    x3 = np.arange(len(metrics))
    w3 = 0.30
    b1 = ax3.bar(x3 - w3, p1_vals, w3, color=GREEN, alpha=0.85, label="2012–2016")
    b2 = ax3.bar(x3,      p2_vals, w3, color=BLUE,  alpha=0.85, label="2016–2020")

    for bar, val in zip(list(b1) + list(b2), p1_vals + p2_vals):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                 f"{val:.1f}", ha="center", fontsize=8, color=TEXT, fontweight="bold")

    ax3.set_xticks(x3 - w3/2)
    ax3.set_xticklabels(metrics, fontsize=8)
    ax3.set_ylabel("%", fontsize=10)
    ax3.set_title("Period-Level Portfolio Metrics", fontsize=11, fontweight="bold")
    ax3.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    # ── Panel 4: Horizontal bar – sorted by 2012-16 ───────────────────────────
    colors4 = [GREEN if b else ORANGE for b in df_s1["beat_12_16"]]
    ax4.barh(df_s1["stock"], df_s1["cagr_12_16"], color=colors4, edgecolor="none", height=0.72)
    ax4.axvline(SENSEX_C[0], color=RED, lw=2, ls="--",
                label=f"Sensex {SENSEX_C[0]:.1f}%")
    ax4.axvline(0, color=TEXT, lw=0.8, alpha=0.3)
    ax4.set_xlabel("CAGR (%)", fontsize=10)
    ax4.set_title("2012–2016 CAGR  (sorted high→low)", fontsize=12, fontweight="bold")
    ax4.tick_params(axis="y", labelsize=7.5)
    ax4.invert_yaxis()
    ax4.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    # ── Panel 5: Horizontal bar – sorted by 2016-20 ───────────────────────────
    colors5 = [BLUE if b else RED for b in df_s2["beat_16_20"]]
    ax5.barh(df_s2["stock"], df_s2["cagr_16_20"], color=colors5, edgecolor="none", height=0.72)
    ax5.axvline(SENSEX_C[1], color=ORANGE, lw=2, ls="--",
                label=f"Sensex {SENSEX_C[1]:.1f}%")
    ax5.axvline(0, color=TEXT, lw=0.8, alpha=0.3)
    ax5.set_xlabel("CAGR (%)", fontsize=10)
    ax5.set_title("2016–2020 CAGR  (sorted high→low)  ← DHFL collapse visible",
                  fontsize=12, fontweight="bold")
    ax5.tick_params(axis="y", labelsize=7.5)
    ax5.invert_yaxis()
    ax5.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    out = "charts/subperiod_analysis.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"Chart saved → {out}")
    plt.close()


if __name__ == "__main__":
    df = main()
    make_charts(df)
