"""
Polymarket "Smart Money" Wallet-Follow Backtest
=================================================
Idea: instead of trading the raw price-percentile signal from
polymarket_edge_analysis.py, identify real wallets (on-chain addresses) with
a credible track record, treat their trades as directional SIGNALS only
(ignore their stake size), and size our own positions with our own model
(quarter-Kelly, blended with a running per-wallet credibility score that
updates online as we see more of that wallet's resolved calls).

DATA: only tanaerao/polymarket-midterms has wallet identities (Account column,
real Polygon addresses) -- the manja316 snapshot data is anonymous, so this
analysis runs on the 2022 US-midterms dataset only: 39 races, ~28k trades,
2,425 unique wallets, 37 races usable after dropping 2 non-binary/unresolved
ones (same filter as polymarket_edge_analysis.py).

WALLET UNIVERSE, BEFORE any ranking (see explore step in chat): of 2,425
wallets, 1,985 (82%) made just a single trade ever -- no track record to
credit. Requiring >=3 trades and >=2 distinct races leaves 401 candidates.

RED FLAGS (excluded from the candidate pool before ranking):
  - n_trades < 3, or n_races < 2               -> not enough evidence
  - net directional exposure ratio < 0.3       -> mostly round-tripping
    (buys and sells on the same outcome that largely cancel out -- looks
    like liquidity provision / hedging, not a directional call worth
    following). ratio = sum(|net notional per position|) / gross notional.
  - n_trades >= 50                             -> likely automated /
    market-making activity, out of scope for both frequency tiers asked for

FREQUENCY TIERS (by total trade count, not trades/day -- trades/day breaks
down for low-count wallets whose whole history spans under an hour):
  low-frequency:    3 <= n_trades < 10
  medium-frequency: 10 <= n_trades < 50

CREDIBILITY SCORE (for choosing who's "top 10/20" -- necessarily a
retrospective, full-sample ranking; a live system would need a rolling
wallet-discovery process, this is disclosed, not solved here):
  per-trade edge = win - price (did they beat the fair/implied price)
  score = mean(edge) - 1.0 * stderr(edge)   [a shrinkage lower-bound so a
  wallet with 3 lucky trades doesn't outrank one with 40 consistently good
  ones]

POSITION SIZING (the part that's genuinely ours, not copied from the wallet):
  base Kelly uses the SAME price-bucket calibration as polymarket_edge_analysis.py
  (full combined-dataset Wilson-lower-bound win rate for that price bucket),
  scaled by a per-wallet credibility MULTIPLIER that updates online: a
  Beta(1,1) posterior on "does this wallet's next call win", updated only
  with that wallet's OWN trades strictly before the current one (no lookahead
  in the sizing, even though wallet selection itself is in-sample).
  stake_frac = quarter_kelly(bucket_p_est, price) * clip(2 * posterior_mean, 0, 2)
  We follow every trade the cohort's wallets make (not just their best ones)
  -- the wallet is the signal source, we decide size, exactly as asked.
"""

import glob
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tabulate import tabulate

RNG_SEED = 7
DATA_DIR = "data/polymarket/tanaerao"
os.makedirs("charts", exist_ok=True)
rng = np.random.default_rng(RNG_SEED)


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan, np.nan
    phat = k / n
    denom = 1 + z**2 / n
    centre = phat + z**2 / (2 * n)
    adj = z * np.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return phat, (centre - adj) / denom, (centre + adj) / denom


# ── 1. Load every real trade, keep wallet identity, normalize Buy/Sell ───────
def load_trades():
    rows, skipped = [], []
    for fp in sorted(glob.glob(f"{DATA_DIR}/*.csv")):
        race = os.path.basename(fp).replace(".csv", "")
        df = pd.read_csv(fp)
        df = df.rename(columns={"Timestamp": "timestamp", "Account": "wallet", "Type": "type",
                                 "Outcome": "outcome", "Amount": "amount_usd", "Price": "price"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp", "price", "outcome", "wallet"])

        outcomes = df["outcome"].unique()
        if len(outcomes) != 2:
            skipped.append(race)
            continue
        last_px = df.sort_values("timestamp").groupby("outcome")["price"].last()
        if last_px.max() < 0.85 or last_px.min() > 0.15:
            skipped.append(race)
            continue
        winner = last_px.idxmax()
        other = {o: [x for x in outcomes if x != o][0] for o in outcomes}

        df["raw_outcome"] = df["outcome"]  # keep pre-normalization side for wash-trade detection
        buys = df[df["type"] == "Buy"].copy()
        buys["bet_outcome"], buys["bet_price"] = buys["outcome"], buys["price"]
        sells = df[df["type"] == "Sell"].copy()
        sells["bet_outcome"] = sells["outcome"].map(other)
        sells["bet_price"] = 1 - sells["price"]

        norm = pd.concat([buys, sells], ignore_index=True)
        norm = norm[(norm["bet_price"] > 0) & (norm["bet_price"] < 1)]
        norm["win"] = (norm["bet_outcome"] == winner).astype(int)
        norm["market_id"] = race
        rows.append(norm[["timestamp", "wallet", "market_id", "raw_outcome", "type",
                           "bet_price", "win", "amount_usd"]].rename(columns={"bet_price": "price"}))
    return pd.concat(rows, ignore_index=True), skipped


trades, skipped_races = load_trades()
print(f"loaded {len(trades)} normalized trades from {trades['market_id'].nunique()} races "
      f"({len(skipped_races)} skipped: {skipped_races}), {trades['wallet'].nunique()} unique wallets\n")

# ── 2. Wallet-level track record + red-flag screen ───────────────────────────
def net_exposure_ratio(sub):
    net = sub.groupby(["market_id", "raw_outcome"]).apply(
        lambda s: s.loc[s["type"] == "Buy", "amount_usd"].sum() - s.loc[s["type"] == "Sell", "amount_usd"].sum()
    )
    gross = sub["amount_usd"].sum()
    return abs(net).sum() / gross if gross > 0 else 0.0


wallet_rows = []
for w, sub in trades.groupby("wallet"):
    n_trades, n_races = len(sub), sub["market_id"].nunique()
    edge = sub["win"] - sub["price"]
    wallet_rows.append({
        "wallet": w, "n_trades": n_trades, "n_races": n_races,
        "total_notional": sub["amount_usd"].sum(),
        "net_exposure_ratio": net_exposure_ratio(sub),
        "win_rate": sub["win"].mean(), "mean_edge": edge.mean(),
        "edge_stderr": edge.std(ddof=1) / np.sqrt(n_trades) if n_trades > 1 else np.inf,
    })
wallets = pd.DataFrame(wallet_rows)
wallets["credibility_score"] = wallets["mean_edge"] - 1.0 * wallets["edge_stderr"]

red_flag_insufficient = (wallets["n_trades"] < 3) | (wallets["n_races"] < 2)
red_flag_washy = wallets["net_exposure_ratio"] < 0.3
red_flag_bot = wallets["n_trades"] >= 50
clean = wallets[~(red_flag_insufficient | red_flag_washy | red_flag_bot)].copy()

print(f"wallet screen: {len(wallets)} total -> {red_flag_insufficient.sum()} dropped (insufficient evidence), "
      f"{(red_flag_washy & ~red_flag_insufficient).sum()} dropped (wash-trade-like, net_exposure_ratio<0.3), "
      f"{(red_flag_bot & ~red_flag_insufficient & ~red_flag_washy).sum()} dropped (>=50 trades, likely automated)")
print(f"{len(clean)} candidate wallets remain\n")

clean["tier"] = np.select([clean["n_trades"] < 10, clean["n_trades"] < 50], ["low", "medium"], default="other")
low_ranked = clean[clean["tier"] == "low"].sort_values("credibility_score", ascending=False)
med_ranked = clean[clean["tier"] == "medium"].sort_values("credibility_score", ascending=False)

print(f"low-frequency tier (3-9 trades): {len(low_ranked)} candidates")
print(f"medium-frequency tier (10-49 trades): {len(med_ranked)} candidates\n")

COHORTS = {
    "Low-freq top 10": low_ranked.head(10),
    "Low-freq top 20": low_ranked.head(20),
    "Medium-freq top 10": med_ranked.head(10),
    "Medium-freq top 20": med_ranked.head(20),
}
for name, coh in COHORTS.items():
    print(f"=== {name} ===")
    print(tabulate(coh[["wallet", "n_trades", "n_races", "win_rate", "mean_edge", "credibility_score",
                         "net_exposure_ratio", "total_notional"]],
                    headers="keys", floatfmt=".4f", showindex=False))
    print()

# ── 3. Base price-bucket calibration (same recipe as polymarket_edge_analysis.py) ─
manja = pd.read_csv("data/polymarket/manja316/markets.csv")
manja_prices = pd.read_csv("data/polymarket/manja316/prices_sample.csv")
resolved = manja[manja["active"] == 0].copy()
ambiguous = resolved[(resolved["last_trade_price"] > 0.15) & (resolved["last_trade_price"] < 0.85)]
resolved = resolved.drop(ambiguous.index)
resolved["realized_yes"] = (resolved["last_trade_price"] > 0.5).astype(int)
yes_px = manja_prices[manja_prices["outcome"] == "Yes"][["market_id", "price"]].rename(columns={"price": "p_yes"})
yes_px = yes_px.groupby("market_id", as_index=False)["p_yes"].last()
mmerged = resolved.merge(yes_px, on="market_id", how="inner")
fav_is_yes = mmerged["p_yes"] >= 0.5
fav_price = np.where(fav_is_yes, mmerged["p_yes"], 1 - mmerged["p_yes"])
fav_win = np.where(fav_is_yes, mmerged["realized_yes"] == 1, mmerged["realized_yes"] == 0).astype(int)
manja_bets = pd.concat([
    pd.DataFrame({"price": fav_price, "win": fav_win}),
    pd.DataFrame({"price": 1 - fav_price, "win": 1 - fav_win}),
], ignore_index=True)

BUCKETS = [0, .05, .10, .20, .30, .40, .50, .60, .70, .80, .90, .95, 1.001]
all_bets_for_calib = pd.concat([
    manja_bets[["price", "win"]],
    trades[["price", "win"]],
], ignore_index=True)
all_bets_for_calib["bucket"] = pd.cut(all_bets_for_calib["price"], BUCKETS, right=False).astype(object)

bucket_p_est = {}
for b, g in all_bets_for_calib.groupby("bucket"):
    _, lo, _ = wilson_ci(g["win"].sum(), len(g))
    bucket_p_est[b] = lo

trades["bucket"] = pd.cut(trades["price"], BUCKETS, right=False).astype(object)
trades["bucket_p_est"] = trades["bucket"].map(bucket_p_est)

# ── 4. Backtest: follow the cohort's trades, size with our own model ────────
KELLY_FRACTION = 0.25
MAX_STAKE = 0.20
N_MC = 2000
START_BANKROLL = 100.0


def backtest_cohort(cohort_wallets):
    sub = trades[trades["wallet"].isin(cohort_wallets)].sort_values("timestamp").copy()
    # One entry per (wallet, market): a followed wallet often scales in/out of
    # the same still-open race several times before it resolves. Treating
    # each of those as its own sequential, fully-realized bet double- (or
    # 10x-) counts overlapping-in-time exposure and inflates compounding --
    # the same fix applied to Strategy D in polymarket_edge_analysis.py.
    # Different wallets calling the same race ARE kept as separate signals
    # (that's a real, if correlated, second opinion) -- only repeat entries
    # by the SAME wallet on the SAME market are collapsed.
    sub = sub.drop_duplicates(subset=["wallet", "market_id"], keep="first")
    sub = sub.dropna(subset=["bucket_p_est"])
    if len(sub) == 0:
        return None

    # Online, per-wallet, causal credibility (Beta(1,1) posterior using only
    # that wallet's own PRIOR trades -- no lookahead in the sizing decision).
    wallet_wins = {w: 0 for w in cohort_wallets}
    wallet_seen = {w: 0 for w in cohort_wallets}
    cred_scale = np.empty(len(sub))
    for i, (_, row) in enumerate(sub.iterrows()):
        w = row["wallet"]
        post_mean = (1 + wallet_wins[w]) / (2 + wallet_seen[w])  # Beta(1,1) prior
        cred_scale[i] = np.clip(2 * post_mean, 0, 2)
        wallet_seen[w] += 1
        wallet_wins[w] += row["win"]
    sub["cred_scale"] = cred_scale

    kelly_full = (sub["bucket_p_est"] - sub["price"]) / (1 - sub["price"])
    sub["stake_frac"] = (KELLY_FRACTION * kelly_full * sub["cred_scale"]).clip(lower=0, upper=MAX_STAKE)
    n_signals = len(sub)
    sub = sub[sub["stake_frac"] > 0]
    if len(sub) == 0:
        return {"n_signals": n_signals, "n_bets": 0}

    payout_mult = 1 / sub["price"]
    log_ret = np.where(sub["win"] == 1, np.log1p(sub["stake_frac"] * (payout_mult - 1)),
                        np.log1p(-sub["stake_frac"])).astype(float)
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
        "n_signals": n_signals, "n_bets": len(sub), "avg_stake_frac": sub["stake_frac"].mean(),
        "sharpe_per_bet": sharpe, "median_terminal_$100": np.median(term_wealth),
        "p05_terminal": np.percentile(term_wealth, 5), "p95_terminal": np.percentile(term_wealth, 95),
        "p_ruin_below_$10": ruin / N_MC, "log_ret": log_ret,
    }


results = {name: backtest_cohort(set(coh["wallet"])) for name, coh in COHORTS.items()}

summary_rows = []
for name, r in results.items():
    if r is None or r["n_bets"] == 0:
        summary_rows.append({"cohort": name, "n_signals": 0 if r is None else r["n_signals"],
                              "n_bets_placed": 0, "sharpe_per_bet": np.nan, "median_$100_becomes": np.nan,
                              "p(ruin<$10)": np.nan})
    else:
        summary_rows.append({"cohort": name, "n_signals": r["n_signals"], "n_bets_placed": r["n_bets"],
                              "sharpe_per_bet": r["sharpe_per_bet"], "median_$100_becomes": r["median_terminal_$100"],
                              "p(ruin<$10)": r["p_ruin_below_$10"]})
summary = pd.DataFrame(summary_rows).sort_values("sharpe_per_bet", ascending=False, na_position="last")
print("=== Wallet-follow backtest summary (our own quarter-Kelly sizing, credibility-scaled) ===")
print(tabulate(summary, headers="keys", floatfmt=".4f", showindex=False))
summary.to_csv("polymarket_wallet_follow_backtest.csv", index=False)
wallets.to_csv("polymarket_wallet_scores.csv", index=False)

viable = summary.dropna(subset=["sharpe_per_bet"])
print(f"\nBest Sharpe: {viable.iloc[0]['cohort']}" if len(viable) else "\nNo cohort produced a positive-Kelly bet.")

# ── 5. Chart ──────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
ax = axes[0]
for name, r in results.items():
    if r is None or r["n_bets"] == 0:
        continue
    path = START_BANKROLL * np.exp(np.cumsum(r["log_ret"]))
    ax.plot(path, label=f"{name} (Sharpe {r['sharpe_per_bet']:.2f}, n={r['n_bets']})")
ax.set_yscale("log")
ax.set_xlabel("Bet # (chronological)")
ax.set_ylabel("Bankroll ($, log scale)")
ax.set_title("Wallet-follow equity curves, $100 start")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

ax = axes[1]
sv = summary.dropna(subset=["sharpe_per_bet"]).sort_values("sharpe_per_bet")
if len(sv) > 0:
    colors = ["tab:red" if s < 0 else "tab:green" for s in sv["sharpe_per_bet"]]
    ax.barh(sv["cohort"], sv["sharpe_per_bet"], color=colors)
ax.set_xlabel("Sharpe ratio (per bet)")
ax.set_title("Cohort comparison")
ax.grid(alpha=0.3, axis="x")

plt.tight_layout()
plt.savefig("charts/polymarket_wallet_follow_backtest.png", dpi=150)
print("\nSaved charts/polymarket_wallet_follow_backtest.png")
