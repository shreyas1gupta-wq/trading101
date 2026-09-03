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
