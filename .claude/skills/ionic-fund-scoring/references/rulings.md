# Desk rulings

| Date | Ruling |
|---|---|
| 2026-08-04 | **Originate and veto.** QFRA-1 originates a fund Sell; a QFRA-2 grade of A or B vetoes it. A single-framework Sell needs FM sign-off. This **supersedes** the older "a fund Sell requires BOTH frameworks". |
| 2026-08-31 | **The bottom-third rule.** A scheme in the bottom third of its own category on **both** the three-year and five-year horizon is a Sell. Extended by the Principal to hybrid multi-asset, balanced-advantage / dynamic-asset-allocation and equity-savings categories. Commodity vehicles are held; debt is No View. |
| 2026-08-31 | **Two carve-outs.** Kotak Small Cap and Canara Robeco Large & Mid Cap (formerly Canara Robeco Emerging Equities) are not sold for now. Both trip the bottom-third rule. Recorded as `Hold (watch)` in `desk_calls.csv`. |
| 2026-08-31 | **Rationale wording.** Every client-facing rationale opens `QFRA Framework:` followed by the reason. No rationale for a No View. |
| 2026-09-02 | **Central fixing.** Scores and calls are fixed centrally; method, workflow and data do not go to an advisor or to another Claude. |

## Standing rules

- Never fabricate a score.
- An unscored scheme is `No View`.
- No client Buy is ever issued.
- Fund-name-to-framework mapping never uses string similarity.

## Superseded text still in circulation

"A fund Sell requires BOTH frameworks" still appears in the `Ionic_Portfolio_Review` and
`qfra1-rerun` skills. It was superseded on 2026-08-04 by originate-and-veto. Correct those
skills when they are in reach; until then, treat originate-and-veto as authoritative.
