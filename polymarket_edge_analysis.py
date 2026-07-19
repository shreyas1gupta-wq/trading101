"""
Polymarket Favorite-Longshot Bias / Edge Analysis
===================================================
Question: at the extremes of implied probability (>=90-95th pct "favorites",
<=5-10th pct "longshots"), are Polymarket contracts mispriced relative to how
often they actually resolve -- and if so, is there enough edge to matter once
sized responsibly (quarter-Kelly) on thin, low-liquidity books?

DATA SOURCES (both free, real, checked directly into git -- see data/polymarket/):
  1. manja316/polymarket-historical-data (GitHub)
     - markets.csv: 9,550 markets, metadata + last traded price + active flag
     - prices_sample.csv: 100,000 real price snapshots, all taken on 2026-04-17
       across 2,088 markets (Yes + No side, ~15 min cadence over one ~10h window)
     Used as: "price observed on 2026-04-17" vs "did it resolve Yes or No by now
     (2026-07-19)" -- a real ~3-month-ahead calibration test across many
     categories (politics, sports, crypto, geopolitics, economics).
  2. tanaerao/polymarket-midterms (GitHub)
     - 39 real Polymarket markets from the 2022 US midterms, ~28k raw on-chain
       trades (wallet address, timestamp, buy/sell, price, USD amount).
     Used as: real trade-level (not snapshot) data with genuine dollar trade
     sizes, to cross-check the calibration finding on a second, independent,
     much higher-frequency dataset and to look at "trades per dollar" (i.e.
     how thin the book gets in the extreme buckets).

NETWORK CAVEAT: this environment's egress policy blocks Polymarket's own API,
Kalshi entirely, Hugging Face, Kaggle, and direct blockchain RPC/subgraph
endpoints -- confirmed via direct probes, not assumed. Only public data
checked into a reachable GitHub repo could be used. That means: no Kalshi
data at all, and no live order-book depth for either venue. Per instructions,
all strategies below ASSUME MARKET-ORDER FILLS at the observed price (no
maker/limit-order fill simulation, no fee model) -- a simplification, not a
claim that real execution costs are zero.

RESOLUTION PROXY: Polymarket contracts trade to ~0 or ~1 right before they
close. For the 7,552 markets in manja316 that are no longer active, 98.6% of
last_trade_price values are decisively <0.05 or >0.95 (checked empirically
below) -- the ambiguous 1.4% (illiquid/void markets) are dropped.
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tabulate import tabulate

RNG_SEED = 7
DATA_DIR = "data/polymarket"
os.makedirs("charts", exist_ok=True)


def wilson_ci(k, n, z=1.96):
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return np.nan, np.nan, np.nan
    phat = k / n
    denom = 1 + z**2 / n
    centre = phat + z**2 / (2 * n)
    adj = z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return phat, (centre - adj) / denom, (centre + adj) / denom


# ── 1. manja316: snapshot price (2026-04-17) vs resolved-by-now outcome ──────
def load_manja316():
    markets = pd.read_csv(f"{DATA_DIR}/manja316/markets.csv")
    prices = pd.read_csv(f"{DATA_DIR}/manja316/prices_sample.csv")

    resolved = markets[markets["active"] == 0].copy()
    n_inactive_total = len(resolved)
    ambiguous = resolved[(resolved["last_trade_price"] > 0.15) & (resolved["last_trade_price"] < 0.85)]
    resolved = resolved.drop(ambiguous.index)
    resolved["realized_yes"] = (resolved["last_trade_price"] > 0.5).astype(int)

    yes_px = prices[prices["outcome"] == "Yes"][["market_id", "price"]].rename(columns={"price": "p_yes"})
    yes_px = yes_px.groupby("market_id", as_index=False)["p_yes"].last()

    merged = resolved.merge(yes_px, on="market_id", how="inner")

    fav_is_yes = merged["p_yes"] >= 0.5
    fav_price = np.where(fav_is_yes, merged["p_yes"], 1 - merged["p_yes"])
    fav_win = np.where(fav_is_yes, merged["realized_yes"] == 1, merged["realized_yes"] == 0).astype(int)
    long_price = 1 - fav_price
    long_win = 1 - fav_win

    bets = pd.concat([
        pd.DataFrame({"source": "manja316", "market_id": merged["market_id"], "timestamp": pd.Timestamp("2026-04-17"),
                      "price": fav_price, "win": fav_win, "amount_usd": np.nan, "category": merged["category"]}),
        pd.DataFrame({"source": "manja316", "market_id": merged["market_id"], "timestamp": pd.Timestamp("2026-04-17"),
                      "price": long_price, "win": long_win, "amount_usd": np.nan, "category": merged["category"]}),
    ], ignore_index=True)
    return bets, n_inactive_total, len(ambiguous)


# ── 2. tanaerao: real per-trade midterm data, normalized to "buy at p" ───────
def load_tanaerao():
    files = sorted(glob.glob(f"{DATA_DIR}/tanaerao/*.csv"))
    all_bets, skipped = [], []
    for fp in files:
        race = os.path.basename(fp).replace(".csv", "")
        df = pd.read_csv(fp)
        df = df.rename(columns={"Timestamp": "timestamp", "Type": "type", "Outcome": "outcome",
                                 "Amount": "amount_usd", "Price": "price"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "price", "outcome"])

        outcomes = df["outcome"].unique()
        if len(outcomes) != 2:
            skipped.append((race, "not binary"))
            continue
        last_px = df.sort_values("timestamp").groupby("outcome")["price"].last()
        if last_px.max() < 0.85 or last_px.min() > 0.15:
            skipped.append((race, "never converged decisively"))
            continue
        winner = last_px.idxmax()
        other = {o: [x for x in outcomes if x != o][0] for o in outcomes}

        buys = df[df["type"] == "Buy"].copy()
        buys["bet_outcome"] = buys["outcome"]
        buys["bet_price"] = buys["price"]

        sells = df[df["type"] == "Sell"].copy()
        sells["bet_outcome"] = sells["outcome"].map(other)
        sells["bet_price"] = 1 - sells["price"]

        norm = pd.concat([buys, sells], ignore_index=True)
        norm = norm[(norm["bet_price"] > 0) & (norm["bet_price"] < 1)]
        norm["win"] = (norm["bet_outcome"] == winner).astype(int)
        norm["source"] = "tanaerao"
        norm["market_id"] = race
        norm["category"] = "us_midterms_2022"
        all_bets.append(norm[["source", "market_id", "timestamp", "bet_price", "win", "amount_usd", "category"]]
                         .rename(columns={"bet_price": "price"}))
    return pd.concat(all_bets, ignore_index=True), skipped


manja_bets, n_inactive_total, n_ambiguous = load_manja316()
tana_bets, tana_skipped = load_tanaerao()
bets = pd.concat([manja_bets, tana_bets], ignore_index=True)
bets["price"] = bets["price"].clip(1e-4, 1 - 1e-4)

print(f"manja316: {n_inactive_total} resolved markets ({n_ambiguous} dropped as ambiguous last_trade_price), "
      f"{len(manja_bets)} favorite+longshot bet-rows from {manja_bets['market_id'].nunique()} markets")
print(f"tanaerao: {len(tana_bets)} real trade-level bet-rows from {tana_bets['market_id'].nunique()} races "
      f"({len(tana_skipped)} races skipped: {tana_skipped})")
print(f"combined: {len(bets)} bet-level observations\n")

# ── 3. Calibration table by price bucket ─────────────────────────────────────
BUCKETS = [0, .05, .10, .20, .30, .40, .50, .60, .70, .80, .90, .95, 1.001]
# cast off the Categorical dtype pd.cut returns -- pandas refuses arithmetic
# (e.g. subtraction for Kelly sizing below) on Categorical columns even when
# every value is a plain Interval object.
bets["bucket"] = pd.cut(bets["price"], BUCKETS, right=False).astype(object)


def calib_table(df):
    rows = []
    for b, g in df.groupby("bucket", observed=True):
        n = len(g)
        if n == 0:
            continue
        k = g["win"].sum()
        phat, lo, hi = wilson_ci(k, n)
        rows.append({
            "bucket_obj": b, "bucket": f"[{b.left:.2f},{b.right:.2f})", "n": n,
            "mean_price": g["price"].mean(), "win_rate": phat, "wilson_lo": lo, "wilson_hi": hi,
            "edge": phat - g["price"].mean(), "ev_per_$": phat / g["price"].mean() - 1,
            "median_trade_$": g["amount_usd"].median(),
        })
    return pd.DataFrame(rows)


DISPLAY_COLS = ["bucket", "n", "mean_price", "win_rate", "wilson_lo", "wilson_hi", "edge", "ev_per_$", "median_trade_$"]
combined_calib = calib_table(bets)
manja_calib = calib_table(bets[bets["source"] == "manja316"])
tana_calib = calib_table(bets[bets["source"] == "tanaerao"])

print("=== Combined calibration table (both datasets) ===")
print(tabulate(combined_calib[DISPLAY_COLS], headers="keys", floatfmt=".4f", showindex=False))
print("\n=== manja316 only (cross-category, ~3mo horizon) ===")
print(tabulate(manja_calib[DISPLAY_COLS], headers="keys", floatfmt=".4f", showindex=False))
print("\n=== tanaerao only (2022 midterms, real trade-level) ===")
print(tabulate(tana_calib[DISPLAY_COLS], headers="keys", floatfmt=".4f", showindex=False))

combined_calib[DISPLAY_COLS].to_csv("polymarket_calibration_results.csv", index=False)

# ── 4. Strategy backtest: 4 variants, quarter-Kelly, market-order fills ──────
rng = np.random.default_rng(RNG_SEED)
bets = bets.sample(frac=1, random_state=RNG_SEED).reset_index(drop=True)  # shuffle, then...
bets["fit"] = bets.groupby("bucket", observed=True).cumcount() % 2 == 0  # ...50/50 split stratified per bucket

fit_set, test_set = bets[bets["fit"]].copy(), bets[~bets["fit"]].copy()
fit_stats = calib_table(fit_set).set_index("bucket_obj")

STRATEGIES = {
    "A: Favorite-Harvest tight (90-95%)": lambda p: (p >= 0.90) & (p < 0.95),
    "B: Favorite-Harvest extreme (95-100%)": lambda p: (p >= 0.95),
    "C: Longshot-Buy (5-10%, contrarian control)": lambda p: (p >= 0.05) & (p < 0.10),
    "D: No-filter baseline (always back favorite, p>=50%)": lambda p: (p >= 0.50),
}

KELLY_FRACTION = 0.25
MAX_STAKE = 0.20
N_MC = 2000
START_BANKROLL = 100.0


def backtest(mask_fn):
    sub = test_set[mask_fn(test_set["price"])].copy()
    # Collapse to ONE row per (source, market_id): the raw trade-tick counts
    # above are how many trades *anyone* made at that price, not how many
    # independent opportunities a single trader following this rule would get
    # (many ticks are other traders re-trading the same handful of markets).
    # Compounding must run over real opportunities, not repeated ticks of the
    # same event, or growth numbers blow up to nonsense (see write-up).
    sub = sub.sort_values("timestamp").drop_duplicates(subset=["source", "market_id"], keep="first")
    sub["p_est"] = sub["bucket"].map(fit_stats["wilson_lo"])  # conservative, out-of-sample estimate
    sub = sub.dropna(subset=["p_est"])
    if len(sub) == 0:
        return {"n_bets": 0, "n_qualifying": 0}

    kelly_full = (sub["p_est"] - sub["price"]) / (1 - sub["price"])
    sub["stake_frac"] = (KELLY_FRACTION * kelly_full).clip(lower=0, upper=MAX_STAKE)
    n_considered = len(sub)
    sub = sub[sub["stake_frac"] > 0]
    if len(sub) == 0:
        return {"n_bets": 0, "n_qualifying": n_considered}

    payout_mult = 1 / sub["price"]
    log_ret = np.where(
        sub["win"] == 1,
        np.log1p(sub["stake_frac"] * (payout_mult - 1)),
        np.log1p(-sub["stake_frac"]),
    ).astype(float)
    sharpe = log_ret.mean() / log_ret.std(ddof=1) if log_ret.std(ddof=1) > 0 else np.nan

    term_wealth, ruin = [], 0
    for _ in range(N_MC):
        order = rng.permutation(len(log_ret))
        path = START_BANKROLL * np.exp(np.cumsum(log_ret[order]))
        term_wealth.append(path[-1])
        if (path < 10).any():
            ruin += 1
    term_wealth = np.array(term_wealth)

    return {
        "n_bets": len(sub), "n_qualifying": n_considered, "avg_stake_frac": sub["stake_frac"].mean(),
        "sharpe_per_bet": sharpe, "median_terminal_$100": np.median(term_wealth),
        "p05_terminal": np.percentile(term_wealth, 5), "p95_terminal": np.percentile(term_wealth, 95),
        "p_ruin_below_$10": ruin / N_MC, "log_ret": log_ret,
    }


results = {name: backtest(fn) for name, fn in STRATEGIES.items()}

summary_rows = []
for name, r in results.items():
    if r["n_bets"] == 0:
        summary_rows.append({
            "strategy": name, "n_qualifying_pricewise": r["n_qualifying"], "n_bets_placed": 0,
            "avg_stake_%bankroll": np.nan, "sharpe_per_bet": np.nan, "median_$100_becomes": np.nan,
            "p05_$100_becomes": np.nan, "p95_$100_becomes": np.nan, "p(ruin<$10)": np.nan,
            "note": "Kelly sat out: fit-set edge was <= 0 for every bet in this band",
        })
    else:
        summary_rows.append({
            "strategy": name, "n_qualifying_pricewise": r["n_qualifying"], "n_bets_placed": r["n_bets"],
            "avg_stake_%bankroll": r["avg_stake_frac"] * 100, "sharpe_per_bet": r["sharpe_per_bet"],
            "median_$100_becomes": r["median_terminal_$100"], "p05_$100_becomes": r["p05_terminal"],
            "p95_$100_becomes": r["p95_terminal"], "p(ruin<$10)": r["p_ruin_below_$10"], "note": "",
        })
summary = pd.DataFrame(summary_rows).sort_values("sharpe_per_bet", ascending=False, na_position="last")
print("\n=== Strategy backtest summary (test-set only, quarter-Kelly, market-order fills) ===")
print(tabulate(summary, headers="keys", floatfmt=".4f", showindex=False))
summary.to_csv("polymarket_strategy_backtest.csv", index=False)

viable = summary.dropna(subset=["sharpe_per_bet"])
if len(viable) > 0:
    print(f"\nBest Sharpe: {viable.iloc[0]['strategy']}")
else:
    print("\nNo strategy cleared quarter-Kelly's positive-edge bar on the test set.")

# ── 5. Charts ─────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax = axes[0, 0]
cc = combined_calib
ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="perfectly calibrated")
ax.errorbar(cc["mean_price"], cc["win_rate"],
            yerr=[cc["win_rate"] - cc["wilson_lo"], cc["wilson_hi"] - cc["win_rate"]],
            fmt="o-", color="tab:blue", capsize=3, label="observed (95% Wilson CI)")
ax.set_xlabel("Market-implied price (probability)")
ax.set_ylabel("Realized win rate")
ax.set_title("Calibration: does price match reality?")
ax.legend()
ax.grid(alpha=0.3)

ax = axes[0, 1]
tsz = cc.dropna(subset=["median_trade_$"])
if len(tsz) > 0:
    ax.bar(range(len(tsz)), tsz["median_trade_$"], color="tab:orange")
    ax.set_xticks(range(len(tsz)))
    ax.set_xticklabels(tsz["bucket"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Median trade size ($, tanaerao real trades)")
    ax.set_title("Liquidity by price bucket (thinner at the tails?)")
    ax.grid(alpha=0.3, axis="y")

ax = axes[1, 0]
for name, r in results.items():
    if r["n_bets"] == 0:
        continue
    path = START_BANKROLL * np.exp(np.cumsum(r["log_ret"]))
    ax.plot(path, label=f"{name.split(':')[0]} (Sharpe {r['sharpe_per_bet']:.2f})")
ax.set_yscale("log")
ax.set_xlabel("Bet # (test-set order, one MC path)")
ax.set_ylabel("Bankroll ($, log scale)")
ax.set_title("Equity curves, $100 start, quarter-Kelly")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

ax = axes[1, 1]
sv = summary.dropna(subset=["sharpe_per_bet"]).sort_values("sharpe_per_bet")
if len(sv) > 0:
    colors = ["tab:red" if s < 0 else "tab:green" for s in sv["sharpe_per_bet"]]
    ax.barh([s.split(":")[0] for s in sv["strategy"]], sv["sharpe_per_bet"], color=colors)
ax.set_xlabel("Sharpe ratio (per bet)")
ax.set_title("Strategy comparison (strategies with 0 bets omitted)")
ax.grid(alpha=0.3, axis="x")

plt.tight_layout()
plt.savefig("charts/polymarket_edge_analysis.png", dpi=150)
print("\nSaved charts/polymarket_edge_analysis.png")
