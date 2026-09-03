# The method as implemented

## The score

For each horizon independently, the score is **the share of the scheme's own peer group it
has beaten**.

Peer group construction:
- the same SEBI category,
- the same plan,
- growth option only,
- peers must themselves hold that horizon,
- minimum **eight** peers, or the scheme is unscored.

The score is the mean of the available horizons, rounded.

## Why the benchmark is the peer median, not an index

This is the choice that makes the score work at all for multi-asset and
balanced-advantage funds, where every AMC picks its own composite and no index is
comparable across the category. It is the reason coverage reaches the hybrid block that
neither QFRA framework can touch.

## Horizons are computed independently

Three-year and five-year are computed separately, so a scheme with only a three-year
record is scored on three years and *says so*, rather than being dropped. HSBC Value is
the live case.

The two horizons largely agree — rank correlation +0.812 across 577 funds in 14 categories
— which is exactly why requiring **both** to fail is a meaningful filter rather than one
test counted twice. When they were accidentally collapsed onto the same month, the
"bottom third on BOTH horizons" rule silently became a single test (defect 5). That path
now hard-aborts.

## One score per scheme

Taken from the **Direct** plan, falling back to Regular only where a scheme has no Direct
plan. Never averaged across the share classes a particular client happens to hold — that
made the same fund score differently in two clients' decks (defect 15).

## Keying

Schemes are keyed on `(category, base_name)`, not on the normalised name alone. The name
alone is not injective: "DSP **Regular** Savings Fund" (conservative hybrid) and "DSP
Savings Fund" (money market) both reduce to `DSP SAVINGS FUND`, because REGULAR is part of
the first fund's actual name. A gate aborts the export if any scheme carries more than one
call or score (defect 13).

IDCW phrases are stripped as whole units, not word by word, and anything still ending on a
connective aborts the export (defect 14).

## Redemption mechanics that matter for the tax column

- **FIFO ordering** means a partial trim sells the *oldest* units, which are long-term: no
  exit load, and 12.5% above the ₹1.25L per-assessee exemption.
- Equity-oriented: **LTCG 12.5%, STCG 20%**.
- Debt, gold and ULIP sit outside that regime.
- **Section 112A grandfathering** applies to units held before 31-Jan-2018.
