"""
Generates 4-panel chart of Indian blue-chip 12-year returns.
Saves to charts/bluechip_analysis.png
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import os

from analysis import build_dataframe, SENSEX

os.makedirs("charts", exist_ok=True)

# ── Color palette ─────────────────────────────────────────────────────────────
BG       = "#0D1117"
PANEL    = "#161B22"
TEXT     = "#E6EDF3"
GRID     = "#30363D"
GREEN    = "#2EA043"
ORANGE   = "#E67E22"
RED      = "#E74C3C"
BLUE     = "#58A6FF"
YELLOW   = "#F1C40F"
PURPLE   = "#BC8CFF"


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
    df = build_dataframe()
    sensex_cagr = SENSEX["cagr_pct"]
    sensex_x    = SENSEX["total_return_x"]

    colors = [GREEN if b else ORANGE for b in df["beat_sensex"]]

    fig = plt.figure(figsize=(22, 26), facecolor=BG)
    fig.suptitle(
        "Indian Blue-Chip Stocks  |  12-Year Total Return Analysis  (~2010–2022)",
        fontsize=18, fontweight="bold", color=TEXT, y=0.99
    )

    gs = gridspec.GridSpec(3, 2, figure=fig,
                           hspace=0.50, wspace=0.32,
                           left=0.06, right=0.98, top=0.97, bottom=0.03)

    ax1 = fig.add_subplot(gs[0, :])   # wide: horizontal bar of CAGR
    ax2 = fig.add_subplot(gs[1, 0])   # histogram
    ax3 = fig.add_subplot(gs[1, 1])   # scatter
    ax4 = fig.add_subplot(gs[2, :])   # bubble / return ranking

    for ax in [ax1, ax2, ax3, ax4]:
        style_ax(ax)

    # ── Panel 1: Horizontal bar chart – CAGR ─────────────────────────────────
    bars = ax1.barh(df["stock"], df["cagr_pct"], color=colors, edgecolor="none", height=0.75)
    ax1.axvline(sensex_cagr, color=RED, linewidth=2.5, linestyle="--", zorder=5,
                label=f"Sensex CAGR  {sensex_cagr:.1f}%")
    ax1.axvline(float(np.mean(df["cagr_pct"])), color=BLUE, linewidth=1.8, linestyle="-.",
                label=f"Mean CAGR  {np.mean(df['cagr_pct']):.1f}%")
    ax1.axvline(float(np.median(df["cagr_pct"])), color=YELLOW, linewidth=1.8, linestyle=":",
                label=f"Median CAGR  {np.median(df['cagr_pct']):.1f}%")

    for bar, val in zip(bars, df["cagr_pct"]):
        ax1.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                 f"{val:.0f}%", va="center", ha="left", fontsize=7, color=TEXT)

    beat_n = int(df["beat_sensex"].sum())
    lag_n  = len(df) - beat_n
    ax1.legend(handles=[
        mpatches.Patch(color=GREEN,  label=f"Beat Sensex  ({beat_n} stocks)"),
        mpatches.Patch(color=ORANGE, label=f"Lag Sensex   ({lag_n} stocks)"),
        mpatches.Patch(color=RED,    label=f"Sensex CAGR  {sensex_cagr:.1f}%"),
        mpatches.Patch(color=BLUE,   label=f"Mean CAGR  {np.mean(df['cagr_pct']):.1f}%"),
        mpatches.Patch(color=YELLOW, label=f"Median CAGR  {np.median(df['cagr_pct']):.1f}%"),
    ], loc="lower right", facecolor=PANEL, labelcolor=TEXT, fontsize=8, framealpha=0.9)

    ax1.set_xlabel("CAGR  (%)", fontsize=11)
    ax1.set_title("12-Year CAGR by Stock  (sorted high → low)", fontsize=13, fontweight="bold")
    ax1.tick_params(axis="y", labelsize=8)
    ax1.invert_yaxis()
    ax1.set_xlim(-5, df["cagr_pct"].max() + 10)

    # ── Panel 2: CAGR Histogram ───────────────────────────────────────────────
    cagrs = df["cagr_pct"].values.astype(float)
    ax2.hist(cagrs, bins=12, color=GREEN, edgecolor=BG, alpha=0.85, rwidth=0.88)
    ax2.axvline(float(np.median(cagrs)), color=YELLOW, lw=2, ls="--",
                label=f"Median  {np.median(cagrs):.1f}%")
    ax2.axvline(float(np.mean(cagrs)),   color=BLUE,   lw=2, ls="-.",
                label=f"Mean  {np.mean(cagrs):.1f}%")
    ax2.axvline(sensex_cagr,             color=RED,    lw=2, ls=":",
                label=f"Sensex  {sensex_cagr:.1f}%")
    ax2.set_xlabel("CAGR  (%)", fontsize=11)
    ax2.set_ylabel("No. of Stocks", fontsize=11)
    ax2.set_title("CAGR Distribution", fontsize=13, fontweight="bold")
    ax2.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    # annotation box
    stats_text = (
        f"N = {len(df)}\n"
        f"Mean  = {np.mean(cagrs):.1f}%\n"
        f"Median= {np.median(cagrs):.1f}%\n"
        f"Std   = {np.std(cagrs):.1f}%\n"
        f"Q1    = {np.percentile(cagrs, 25):.1f}%\n"
        f"Q3    = {np.percentile(cagrs, 75):.1f}%"
    )
    ax2.text(0.97, 0.97, stats_text, transform=ax2.transAxes,
             va="top", ha="right", fontsize=8, color=TEXT,
             bbox=dict(boxstyle="round", facecolor=BG, alpha=0.8))

    # ── Panel 3: Scatter – CAGR vs Return (x) ────────────────────────────────
    sc_colors = [GREEN if b else ORANGE for b in df["beat_sensex"]]
    ax3.scatter(df["cagr_pct"], df["total_return_x"],
                c=sc_colors, s=70, edgecolors="white", linewidths=0.4, zorder=3)
    ax3.axvline(sensex_cagr, color=RED, lw=1.5, ls="--", alpha=0.8, label=f"Sensex {sensex_cagr:.1f}%")
    ax3.axhline(sensex_x,    color=RED, lw=1.5, ls=":",  alpha=0.8, label=f"Sensex {sensex_x:.1f}x")

    for _, r in df.iterrows():
        if r["total_return_x"] >= 20 or r["cagr_pct"] >= 35:
            ax3.annotate(r["stock"],
                         (r["cagr_pct"], r["total_return_x"]),
                         textcoords="offset points", xytext=(5, 3),
                         fontsize=7, color=TEXT)

    ax3.set_xlabel("CAGR  (%)", fontsize=11)
    ax3.set_ylabel("Total Return  (x)", fontsize=11)
    ax3.set_title("Total Return  vs  CAGR", fontsize=13, fontweight="bold")
    ax3.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=8)

    # ── Panel 4: Bubble chart – total return ranking ─────────────────────────
    df_sorted = df.sort_values("total_return_x", ascending=False).reset_index(drop=True)
    bc = [GREEN if b else ORANGE for b in df_sorted["beat_sensex"]]
    sizes = np.sqrt(df_sorted["total_return_x"]) * 80
    ax4.scatter(df_sorted.index, df_sorted["total_return_x"],
                s=sizes, c=bc, alpha=0.75, edgecolors="white", linewidths=0.5, zorder=3)
    ax4.axhline(sensex_x, color=RED, lw=2, ls="--",
                label=f"Sensex  {sensex_x:.1f}x  ({SENSEX['cagr_pct']:.1f}% CAGR)")

    max_ret = df_sorted["total_return_x"].max()
    for i, r in df_sorted.iterrows():
        offset = max_ret * 0.02
        ax4.text(i, r["total_return_x"] + offset, r["stock"],
                 ha="center", va="bottom", fontsize=6, color=TEXT, rotation=60)

    ax4.set_xlabel("Rank  (by Total Return, left = best)", fontsize=11)
    ax4.set_ylabel("Total Return  (x)", fontsize=11)
    ax4.set_title("Total Return Ranking  (bubble size ∝ √return)", fontsize=13, fontweight="bold")
    ax4.set_xticks([])
    ax4.legend(facecolor=PANEL, labelcolor=TEXT, fontsize=9)

    # ── Save ─────────────────────────────────────────────────────────────────
    out = "charts/bluechip_analysis.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"Chart saved → {out}")
    plt.close()


if __name__ == "__main__":
    main()
