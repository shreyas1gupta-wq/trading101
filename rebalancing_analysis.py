"""
Rebalancing Analysis: Buy-and-Hold vs Annual vs 3-Year Equal-Weight Rebalancing
Uses the 48 Indian blue-chip stocks (12-year data, ~2010-2022).

Two approaches:
  1. Deterministic  — constant annual return = CAGR (no volatility)
  2. Monte Carlo    — annual return ~ Normal(CAGR, sigma=0.28) × 10,000 paths
     (0.28 is typical annualised vol for Indian large-caps)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from tabulate import tabulate
import os

from analysis import build_dataframe, SENSEX

os.makedirs("charts", exist_ok=True)
np.random.seed(42)

YEARS     = 12
N_SIMS    = 10_000
SIGMA     = 0.28      # annualised vol for Indian large-caps
INITIAL   = 100_000   # ₹1 lakh starting investment

BG     = "#0D1117"
PANEL  = "#161B22"
TEXT   = "#E6EDF3"
GRID   = "#30363D"
GREEN  = "#2EA043"
BLUE   = "#58A6FF"
ORANGE = "#E67E22"
YELLOW = "#F1C40F"
RED    = "#E74C3C"
PURPLE = "#BC8CFF"


# ── helpers ──────────────────────────────────────────────────────────────────

def simulate_portfolio(cagrs, strategy, n_years=YEARS):
    """
    cagrs: array of shape (N,)  — annual returns per stock (fraction)
    strategy: 'bh' | 'annual' | '3yr'
    Returns: final portfolio value starting from 1.0
    """
    n = len(cagrs)
    weights = np.ones(n) / n
    value   = 1.0

    if strategy == "bh":
        for yr in range(n_years):
            weights = weights * (1 + cagrs)
            value   = weights.sum()
            weights = weights / value    # normalise for tracking (not actually rebalanced)
        # simpler: just weighted sum of terminal values
        return (np.ones(n) / n * (1 + cagrs) ** n_years).sum()

    elif strategy == "annual":
        for yr in range(n_years):
            port_return = (weights * (1 + cagrs)).sum()
            value *= port_return
            weights = np.ones(n) / n   # rebalance
        return value

    elif strategy == "3yr":
        for period in range(n_years // 3):
            port_return = (weights * (1 + cagrs) ** 3).sum()
            value *= port_return
            weights = np.ones(n) / n   # rebalance
        return value

    raise ValueError(strategy)


def simulate_stochastic(cagrs, strategy, n_years=YEARS, n_sims=N_SIMS, sigma=SIGMA):
    """Monte Carlo: each year returns are sampled from Normal(cagr, sigma)."""
    n = len(cagrs)
    results = []

    for _ in range(n_sims):
        if strategy == "bh":
            # Annual returns drawn independently per stock per year
            annual_r = np.random.normal(cagrs, sigma, size=(n_years, n))
            # Terminal weights
            terminal = np.prod(1 + annual_r, axis=0) / n
            results.append(terminal.sum())

        elif strategy == "annual":
            value   = 1.0
            weights = np.ones(n) / n
            for yr in range(n_years):
                r = np.random.normal(cagrs, sigma)
                port_ret = (weights * (1 + r)).sum()
                value   *= port_ret
                weights  = np.ones(n) / n
            results.append(value)

        elif strategy == "3yr":
            value   = 1.0
            weights = np.ones(n) / n
            for period in range(n_years // 3):
                r3 = np.random.normal(cagrs * 3, sigma * np.sqrt(3))  # 3-yr compounded
                port_ret = (weights * (1 + r3)).sum()
                value   *= port_ret
                weights  = np.ones(n) / n
            results.append(value)

    return np.array(results)


def stats(arr):
    return {
        "mean":   np.mean(arr),
        "median": np.median(arr),
        "p5":     np.percentile(arr, 5),
        "p25":    np.percentile(arr, 25),
        "p75":    np.percentile(arr, 75),
        "p95":    np.percentile(arr, 95),
        "std":    np.std(arr),
        "cagr":   (np.mean(arr) ** (1/YEARS) - 1) * 100,
        "cagr_med": (np.median(arr) ** (1/YEARS) - 1) * 100,
    }


def style_ax(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=9)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.title.set_color(TEXT)
    for sp in ax.spines.values():
        sp.set_edgecolor(GRID)
    ax.grid(color=GRID, linewidth=0.5, alpha=0.5)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    df_stocks = build_dataframe()
    cagrs = (df_stocks["cagr_pct"].values / 100).astype(float)   # fractions

    print("=" * 74)
    print("    REBALANCING ANALYSIS  |  EQUAL-WEIGHT PORTFOLIO  |  12 YEARS")
    print("=" * 74)

    # ── 1. Deterministic (constant annual return = CAGR) ─────────────────────
    bh_det     = simulate_portfolio(cagrs, "bh")
    annual_det = simulate_portfolio(cagrs, "annual")
    yr3_det    = simulate_portfolio(cagrs, "3yr")
    sensex_det = SENSEX["total_return_x"]

    print("\n── DETERMINISTIC (constant annual return = CAGR) ───────────────────────")
    det_rows = [
        ["Buy-and-Hold (no rebalancing)", f"{bh_det:.2f}x",
         f"{(bh_det-1)*100:.0f}%",
         f"{(bh_det**(1/YEARS)-1)*100:.1f}%",
         f"₹{bh_det*INITIAL:,.0f}",
         f"{bh_det/sensex_det:.1f}x vs Sensex"],
        ["3-Year Rebalancing",            f"{yr3_det:.2f}x",
         f"{(yr3_det-1)*100:.0f}%",
         f"{(yr3_det**(1/YEARS)-1)*100:.1f}%",
         f"₹{yr3_det*INITIAL:,.0f}",
         f"{yr3_det/sensex_det:.1f}x vs Sensex"],
        ["Annual Rebalancing",            f"{annual_det:.2f}x",
         f"{(annual_det-1)*100:.0f}%",
         f"{(annual_det**(1/YEARS)-1)*100:.1f}%",
         f"₹{annual_det*INITIAL:,.0f}",
         f"{annual_det/sensex_det:.1f}x vs Sensex"],
        ["Sensex (benchmark)",            f"{sensex_det:.2f}x",
         f"{(sensex_det-1)*100:.0f}%",
         f"{SENSEX['cagr_pct']:.1f}%",
         f"₹{sensex_det*INITIAL:,.0f}",
         "—"],
    ]
    print(tabulate(det_rows,
                   headers=["Strategy", "Return (x)", "Return (%)", "CAGR", f"₹{INITIAL//1000}K → ", ""],
                   tablefmt="grid"))

    print(f"""
  Note: With CONSTANT returns, rebalancing REDUCES returns.
  You systematically sell the 61% CAGR winner (Sesa Goa) to fund the -1% loser (Wipro).
  Buy-and-hold lets winners compound freely.
  BH advantage over annual rebalancing: {bh_det/annual_det:.2f}x  ({(bh_det/annual_det-1)*100:.0f}% more wealth)
""")

    # ── 2. Monte Carlo (realistic annual volatility = {SIGMA:.0%}) ────────────
    print(f"── MONTE CARLO  (σ = {SIGMA:.0%}/yr, N = {N_SIMS:,} simulations) ─────────────────")
    print("   Running simulations...", end="", flush=True)

    bh_mc     = simulate_stochastic(cagrs, "bh")
    annual_mc = simulate_stochastic(cagrs, "annual")
    yr3_mc    = simulate_stochastic(cagrs, "3yr")
    print(" done.\n")

    s_bh  = stats(bh_mc)
    s_ann = stats(annual_mc)
    s_3yr = stats(yr3_mc)

    mc_rows = [
        ["Buy-and-Hold",
         f"{s_bh['mean']:.1f}x",    f"{s_bh['cagr']:.1f}%",
         f"{s_bh['median']:.1f}x",  f"{s_bh['cagr_med']:.1f}%",
         f"{s_bh['p5']:.1f}x",      f"{s_bh['p95']:.1f}x"],
        ["3-Year Rebalancing",
         f"{s_3yr['mean']:.1f}x",   f"{s_3yr['cagr']:.1f}%",
         f"{s_3yr['median']:.1f}x", f"{s_3yr['cagr_med']:.1f}%",
         f"{s_3yr['p5']:.1f}x",     f"{s_3yr['p95']:.1f}x"],
        ["Annual Rebalancing",
         f"{s_ann['mean']:.1f}x",   f"{s_ann['cagr']:.1f}%",
         f"{s_ann['median']:.1f}x", f"{s_ann['cagr_med']:.1f}%",
         f"{s_ann['p5']:.1f}x",     f"{s_ann['p95']:.1f}x"],
        ["Sensex",
         f"{sensex_det:.1f}x",      f"{SENSEX['cagr_pct']:.1f}%",
         f"{sensex_det:.1f}x",      f"—",
         "—",                        "—"],
    ]
    print(tabulate(mc_rows,
                   headers=["Strategy", "Mean (x)", "CAGR(mean)", "Median (x)",
                             "CAGR(med)", "5th pct", "95th pct"],
                   tablefmt="grid"))

    # Win probability analysis
    win_ann_over_bh  = (annual_mc > bh_mc).mean() * 100
    win_3yr_over_bh  = (yr3_mc   > bh_mc).mean() * 100
    win_ann_over_3yr = (annual_mc > yr3_mc).mean()  * 100

    print(f"""
  Probability that Annual Rebalancing beats Buy-and-Hold : {win_ann_over_bh:.1f}%
  Probability that 3-Year Rebalancing beats Buy-and-Hold : {win_3yr_over_bh:.1f}%
  Probability that Annual beats 3-Year Rebalancing       : {win_ann_over_3yr:.1f}%
""")

    # ── 3. Year-by-year wealth path (deterministic) ──────────────────────────
    print("── YEAR-BY-YEAR WEALTH PATH (deterministic, ₹1 lakh invested) ─────────")
    n = len(cagrs)
    paths = {"Buy-and-Hold": [], "Annual Rebalancing": [], "3-Year Rebalancing": [], "Sensex": []}

    bh_w     = np.ones(n) / n
    bh_val   = 1.0
    ann_val  = 1.0
    yr3_val  = 1.0
    yr3_w    = np.ones(n) / n
    sensex_annual_cagr = (1 + SENSEX["cagr_pct"] / 100)

    for yr in range(1, YEARS + 1):
        # BH
        bh_w = bh_w * (1 + cagrs)
        bh_val = bh_w.sum()
        paths["Buy-and-Hold"].append(bh_val * INITIAL)

        # Annual
        ann_val *= (np.ones(n) / n * (1 + cagrs)).sum()
        paths["Annual Rebalancing"].append(ann_val * INITIAL)

        # 3-yr
        if yr % 3 == 0:
            yr3_val *= (yr3_w * (1 + cagrs) ** 3).sum()
            yr3_w = np.ones(n) / n
            paths["3-Year Rebalancing"].append(yr3_val * INITIAL)
        else:
            # interpolate between rebalance points
            period_start = (yr - 1) // 3 * 3
            base = paths["3-Year Rebalancing"][period_start - 1] if period_start > 0 else INITIAL
            yrs_in = yr - period_start
            interim = (yr3_w * (1 + cagrs) ** yrs_in).sum()
            if period_start > 0:
                paths["3-Year Rebalancing"].append(
                    paths["3-Year Rebalancing"][period_start - 1] * interim)
            else:
                paths["3-Year Rebalancing"].append(INITIAL * interim)

        paths["Sensex"].append(INITIAL * sensex_annual_cagr ** yr)

    yr_rows = [["Year"]]
    yr_rows[0].extend(list(paths.keys()))
    for yr in range(YEARS):
        row = [f"20{10+yr}"]
        for k in paths:
            row.append(f"₹{paths[k][yr]:,.0f}")
        yr_rows.append(row)
    print(tabulate(yr_rows[1:], headers=["Year"] + list(paths.keys()), tablefmt="simple"))

    # ── 4. Key insight summary ────────────────────────────────────────────────
    print("\n" + "=" * 74)
    print("    KEY INSIGHTS")
    print("=" * 74)
    print(f"""
  DETERMINISTIC (no volatility):
  ┌─────────────────────────────┬──────────┬──────────┬──────────┐
  │ Strategy                    │ Return   │ CAGR     │ ₹1L → ?  │
  ├─────────────────────────────┼──────────┼──────────┼──────────┤
  │ Buy-and-Hold                │ {bh_det:6.1f}x  │ {(bh_det**(1/YEARS)-1)*100:5.1f}%  │ ₹{bh_det*INITIAL/1e5:.0f}L     │
  │ 3-Year Rebalancing          │ {yr3_det:6.1f}x  │ {(yr3_det**(1/YEARS)-1)*100:5.1f}%  │ ₹{yr3_det*INITIAL/1e5:.0f}L     │
  │ Annual Rebalancing          │ {annual_det:6.1f}x  │ {(annual_det**(1/YEARS)-1)*100:5.1f}%  │ ₹{annual_det*INITIAL/1e5:.0f}L     │
  │ Sensex                      │ {sensex_det:6.1f}x  │ {SENSEX['cagr_pct']:5.1f}%  │ ₹{sensex_det*INITIAL/1e5:.1f}L     │
  └─────────────────────────────┴──────────┴──────────┴──────────┘

  MONTE CARLO (σ={SIGMA:.0%}/yr, median outcomes):
  ┌─────────────────────────────┬──────────┬──────────┬──────────────────────┐
  │ Strategy                    │ Median   │ CAGR     │ Range (5th–95th pct) │
  ├─────────────────────────────┼──────────┼──────────┼──────────────────────┤
  │ Buy-and-Hold                │ {s_bh['median']:6.1f}x  │ {s_bh['cagr_med']:5.1f}%  │ {s_bh['p5']:.1f}x  –  {s_bh['p95']:.1f}x          │
  │ 3-Year Rebalancing          │ {s_3yr['median']:6.1f}x  │ {s_3yr['cagr_med']:5.1f}%  │ {s_3yr['p5']:.1f}x  –  {s_3yr['p95']:.1f}x          │
  │ Annual Rebalancing          │ {s_ann['median']:6.1f}x  │ {s_ann['cagr_med']:5.1f}%  │ {s_ann['p5']:.1f}x  –  {s_ann['p95']:.1f}x          │
  └─────────────────────────────┴──────────┴──────────┴──────────────────────┘

  WHY:
  • With constant returns, BH wins — compounding lets the best stocks
    (Sesa Goa 61%, Motherson 46%) dominate the portfolio over time.
  • Rebalancing cuts the winners and funds the losers. This HURTS when
    there is no volatility to harvest.
  • With realistic volatility, rebalancing harvests "variance drag":
    the annual strategy narrows the outcome range (lower risk),
    but the median return is still below BH.
  • The volatility-harvesting benefit is real but SMALLER than the
    "sell-the-winner" cost when the dispersion of CAGRs is wide (−1% to 61%).
  • BOTTOM LINE: For a high-dispersion alpha portfolio like these blue chips,
    buy-and-hold beats both rebalancing frequencies in expected return,
    but rebalancing substantially reduces downside risk.
""")

    return bh_mc, annual_mc, yr3_mc, paths, bh_det, annual_det, yr3_det, s_bh, s_ann, s_3yr


# ── charts ────────────────────────────────────────────────────────────────────

def make_charts(bh_mc, annual_mc, yr3_mc, paths, bh_det, annual_det, yr3_det, s_bh, s_ann, s_3yr):
    fig = plt.figure(figsize=(20, 22), facecolor=BG)
    fig.suptitle(
        "Rebalancing Analysis  |  48 Blue-Chip Stocks  |  12-Year Equal-Weight Portfolio",
        fontsize=16, fontweight="bold", color=TEXT, y=0.99
    )
    gs = gridspec.GridSpec(3, 2, figure=fig,
                           hspace=0.45, wspace=0.32,
                           left=0.07, right=0.97, top=0.96, bottom=0.04)

    ax1 = fig.add_subplot(gs[0, :])   # Wealth path
    ax2 = fig.add_subplot(gs[1, 0])   # MC distributions
    ax3 = fig.add_subplot(gs[1, 1])   # Box plot
    ax4 = fig.add_subplot(gs[2, :])   # Bar comparison

    for ax in [ax1, ax2, ax3, ax4]:
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=TEXT, labelsize=9)
        ax.xaxis.label.set_color(TEXT)
        ax.yaxis.label.set_color(TEXT)
        ax.title.set_color(TEXT)
        for sp in ax.spines.values():
            sp.set_edgecolor(GRID)
        ax.grid(color=GRID, linewidth=0.5, alpha=0.5)

    years_x = list(range(2010, 2010 + YEARS))

    # ── Panel 1: Wealth path ──────────────────────────────────────────────────
    ax1.plot(years_x, [v/1e5 for v in paths["Buy-and-Hold"]],
             color=GREEN, lw=2.5, label=f"Buy-and-Hold  →  {bh_det:.1f}x")
    ax1.plot(years_x, [v/1e5 for v in paths["3-Year Rebalancing"]],
             color=BLUE, lw=2, ls="--", label=f"3-Year Rebalancing  →  {yr3_det:.1f}x")
    ax1.plot(years_x, [v/1e5 for v in paths["Annual Rebalancing"]],
             color=ORANGE, lw=2, ls="-.", label=f"Annual Rebalancing  →  {annual_det:.1f}x")
    ax1.plot(years_x, [v/1e5 for v in paths["Sensex"]],
             color=RED, lw=1.8, ls=":", label=f"Sensex  →  {SENSEX['total_return_x']:.1f}x")

    # Rebalance markers
    for yr in [2013, 2016, 2019, 2022]:
        ax1.axvline(yr, color=BLUE, linewidth=0.8, linestyle="--", alpha=0.4)
    ax1.text(2013.1, ax1.get_ylim()[1] if ax1.get_ylim()[1] > 0 else 1,
             "↕ rebalance", color=BLUE, fontsize=7, alpha=0.7)

    ax1.set_xlabel("Year", fontsize=11)
    ax1.set_ylabel("Portfolio Value (₹ Lakh)", fontsize=11)
    ax1.set_title("Wealth Path  —  ₹1 Lakh Invested  (Deterministic: annual return = CAGR)", fontsize=12, fontweight="bold")
    ax1.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=9)
    ax1.set_xticks(years_x)
    ax1.tick_params(axis="x", rotation=45)

    # ── Panel 2: Monte Carlo outcome distributions ────────────────────────────
    bins = np.linspace(0, max(bh_mc.max(), annual_mc.max(), yr3_mc.max()), 80)
    ax2.hist(bh_mc,     bins=bins, color=GREEN,  alpha=0.55, label="Buy-and-Hold",      density=True)
    ax2.hist(yr3_mc,    bins=bins, color=BLUE,   alpha=0.55, label="3-Year Rebalance",  density=True)
    ax2.hist(annual_mc, bins=bins, color=ORANGE, alpha=0.55, label="Annual Rebalance",  density=True)
    ax2.axvline(np.median(bh_mc),     color=GREEN,  lw=2,   ls="--")
    ax2.axvline(np.median(yr3_mc),    color=BLUE,   lw=2,   ls="--")
    ax2.axvline(np.median(annual_mc), color=ORANGE, lw=2,   ls="--")
    ax2.axvline(SENSEX["total_return_x"], color=RED, lw=2, ls=":", label="Sensex")
    ax2.set_xlabel("12-Year Portfolio Return (x)", fontsize=10)
    ax2.set_ylabel("Density", fontsize=10)
    ax2.set_title(f"Monte Carlo Outcome Distribution  (σ={SIGMA:.0%}/yr, N={N_SIMS:,})", fontsize=11, fontweight="bold")
    ax2.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)
    ax2.set_xlim(0, np.percentile(bh_mc, 97))

    # ── Panel 3: Box plot ─────────────────────────────────────────────────────
    bp_data = [bh_mc, yr3_mc, annual_mc]
    labels  = ["Buy-and-Hold", "3-Year\nRebalancing", "Annual\nRebalancing"]
    bp = ax3.boxplot(bp_data, tick_labels=labels, patch_artist=True,
                     medianprops=dict(color=YELLOW, linewidth=2),
                     flierprops=dict(marker=".", color=TEXT, alpha=0.3, markersize=2),
                     whiskerprops=dict(color=TEXT, linewidth=1.2),
                     capprops=dict(color=TEXT, linewidth=1.5))
    for patch, color in zip(bp["boxes"], [GREEN, BLUE, ORANGE]):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    ax3.axhline(SENSEX["total_return_x"], color=RED, lw=2, ls=":", label=f"Sensex {SENSEX['total_return_x']:.1f}x")
    ax3.set_ylabel("12-Year Return (x)", fontsize=10)
    ax3.set_title("Return Distribution  (Box = 25–75th pct, line = median)", fontsize=11, fontweight="bold")
    ax3.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    # ── Panel 4: Bar comparison – deterministic vs MC median ─────────────────
    x     = np.arange(4)
    width = 0.32
    det_vals = [bh_det, yr3_det, annual_det, SENSEX["total_return_x"]]
    mc_meds  = [s_bh["median"], s_3yr["median"], s_ann["median"], SENSEX["total_return_x"]]
    bar_colors = [GREEN, BLUE, ORANGE, RED]
    bar_labels = ["Buy-and-Hold", "3-Year Rebalance", "Annual Rebalance", "Sensex"]

    b1 = ax4.bar(x - width/2, det_vals, width, color=bar_colors, alpha=0.85,
                 label="Deterministic", edgecolor="white", linewidth=0.5)
    b2 = ax4.bar(x + width/2, mc_meds,  width, color=bar_colors, alpha=0.45,
                 hatch="///", edgecolor="white", linewidth=0.5,
                 label="MC Median")

    for bar, val in zip(b1, det_vals):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                 f"{val:.1f}x", ha="center", fontsize=9, color=TEXT, fontweight="bold")
    for bar, val in zip(b2, mc_meds):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                 f"{val:.1f}x", ha="center", fontsize=9, color=TEXT)

    ax4.set_xticks(x)
    ax4.set_xticklabels(bar_labels, fontsize=10)
    ax4.set_ylabel("12-Year Portfolio Return (x)", fontsize=11)
    ax4.set_title("Strategy Comparison  |  Solid = Deterministic  |  Hatched = MC Median", fontsize=12, fontweight="bold")
    ax4.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=9)

    out = "charts/rebalancing_analysis.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"\nChart saved → {out}")
    plt.close()


if __name__ == "__main__":
    results = main()
    make_charts(*results)
