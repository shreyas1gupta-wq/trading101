# Advisor deck automation

Two scripts that sit on top of `ionic-deck-kit` and turn "run four commands and read three lines of
output carefully" into one command with a yes/no answer.

They add no scoring method — no thresholds, no percentile arithmetic, no peer construction — so they
are safe to live in the public advisor kit alongside the rest of the kit.

## Install

Drop both files into `ionic-scorecard/ionic-deck-kit/build/`, or keep them anywhere and point at the
kit with `--kit` / `$IONIC_KIT`. Needs `pandas`, `openpyxl`, `python-pptx`, `matplotlib` — the same
dependencies the kit already needs.

The score file and `VERSION.json` go in `ionic-deck-kit/scores/` as always, as a pair.

## Use

```bash
# one client
python run_review.py statement.xlsx --client "Family Name"

# a folder of statements; the client name comes from each filename
python run_review.py --batch ./statements --out ./to_send --log run.json

# just audit the score file, without building anything
python preflight_scores.py --scores ionic-deck-kit/scores
```

`--tier` is `HNI_DEEP` (default), `STANDARD` or `RM_SIMPLE`. Exit code is 0 when every deck in the
run is sendable, 1 when any is blocked, 2 when it could not run at all.

## What it actually does

1. **Audits the score/VERSION pair** before building anything: the dates agree, the row and scored
   counts match what VERSION claims, every ISIN appears once, the call vocabulary holds, no Buy,
   every actioned call carries a `QFRA Framework:` rationale and no No View does, the cap is present
   and numeric, and the pair is not older than `--max-age-days` (default 60).
2. **Refuses to build on demo scores.** A demo-only `scores/` directory is a hard block.
3. **Checks the pair is self-consistent across share classes** — see below.
4. **Builds**, then runs **all three QA gates** (both geometry checks and tellscan) even after one
   fails, because one finding is usually a symptom and the other two tell you what kind.
5. **Says SENDABLE or BLOCKED per statement**, with the reason, and writes the whole run to JSON.

## The share-class check, and why it blocks what it blocks

A client holds *one* share class. If a scheme's Growth class carries a real call while its IDCW
class came out `No View`, then whichever class the client happens to hold decides whether they are
told the truth. That is not hypothetical — it is the failure that shipped before, and it is silent,
because `No View` is also the correct answer for thousands of legitimate rows.

So the check separates two cases that a naive "these disagree" test would lump together:

| Case | Verdict | Why |
|---|---|---|
| Holding is `No View`, a sibling class carries a real call | **BLOCK** | The deck would say the desk has no view on a fund it has called. |
| Holding carries the real call, siblings disagree | note only | This client's own call is well formed. |
| Holding's score differs from its scheme's modal score | note only | The printed number may come from the wrong pool. |

Blocking the second case too would fire on most books and train people to pass `--force` by reflex,
which is how a gate stops being read.

**It never repairs anything.** Picking which of two calls was meant would be the kit deciding a
call, which is the one thing it must not do. It names the ISINs; the desk fixes the exporter's
share-class key and re-issues the pair.

`--force` builds anyway. The conflict is still real, the deck still understates a call, and the
override is recorded in the run log.

## Combined decks (central only)

`build_combined_review.py` handles a book holding both direct equity and funds. `build_review.py`
is fund-only by design — it is the advisor-side kit, and a holding statement never carries the
quantitative and analyst material the equity pages need, so it switches them off. A 60%-equity book
therefore renders with 60% of itself missing. This runs centrally, where the stock scorecard is in
reach, and turns those pages back on.

```bash
python build_combined_review.py --repo <ionic-scorecard clone> \
       --holdings holdings.json --client "Family Name"
```

`holdings.json` is `{grand_inr, stocks: [[symbol, name, weight_pct]], funds: [[isin, name, weight_pct]]}`.
Funds are given by **ISIN**, never by name — names collide (defects 13, 14) and the desk does not
map them by similarity.

Each half keeps its own source of truth and neither infers the other:

| Half | Numbers | Call |
|---|---|---|
| Funds | `ionic_scores_<date>.csv` + `VERSION.json` | the score file, keyed on ISIN |
| Stocks | `full750_scored_v3.csv` | `pf_qual_<SYM>.json` → `your_recommendation` |

Two things it refuses to do quietly:

- **No defaulted scores.** The demo builder reads `portfolio_quant.csv` and falls back to 50.0 for a
  missing symbol. That is fine for a demo and not fine for a client — a defaulted 50 looks exactly
  like a real one on the page. The quantitative source here is the v3 freeze, which covers the whole
  750, and an unscored symbol is reported and left out rather than filled in.
- **No spread residual.** Weights are of the whole book, never of a sleeve — running the
  single-scheme cap against the fund sleeve alone would read a 6%-of-book fund as 15% and trim it
  for breaching a cap it is nowhere near. Whatever the named rows do not account for is shown as
  unallocated and flagged, because a book whose rows do not sum to its own total has an error in it
  and hiding the gap is how it reaches the client.

The analyst call governs where it differs from the mechanical `recommendation_v3` — Asian Paints
scores 40.2, mechanically a Hold, and is an analyst Sell.
