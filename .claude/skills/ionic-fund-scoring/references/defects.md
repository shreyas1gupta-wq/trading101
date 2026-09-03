# Defect register

Every entry cost real diagnosis. Reintroducing one is a regression, not a fresh bug. Read
the rows relevant to the area you are about to change.

## Data and scoring pipeline

| # | Defect | What it did |
|---|---|---|
| 1 | QFRA-1 verdicts quoted 18.6 months stale | Two Sell calls issued without checking the anchor. The MF Dashboard's daily NAV physically ends 2025-01-31 for five of six categories. |
| 2 | `mf_nav_backfill.py` parser dead | AMFI inserted `Plan`/`Option` columns, NAV moved from field 4 to 6, `float(ISIN)` raised, and `except ValueError: continue` swallowed every row. Fixed by mapping on header names. Verified: PPFCF Direct 57.32 at 31-Jul-2023. |
| 3 | Health gate self-approving junk | Compared each month against the store's own median, which legacy 2-to-41-scheme months dragged down. Re-anchored on the 90th percentile; 19 further months recovered. |
| 4 | Peer-set option filter biased | Matching only `GROWTH` excluded 852 schemes that spell the growth option `Cumulative` (ICICI throughout) while admitting `Income Distribution cum Capital Withdrawal` payouts. Every median in those categories was wrong. |
| 5 | 3y and 5y collapsed to one test | A month filter using the all-time column count left 12 of 67 months, so `END-36` and `END-60` resolved to the same month. "Bottom third on BOTH horizons" was one test counted twice. Now a hard abort. |
| 15 | Score depended on which plans a client held | The shipped scores averaged the percentiles of the share classes **in that portfolio**: SBI Small Cap averaged two plans, Axis ELSS one. The same fund scored differently in two clients' decks. Now the Direct plan's percentile, one consistent pool. |

## Keying and identity

| # | Defect | What it did |
|---|---|---|
| 13 | Score-file over-merge on the base key | Keying on the normalised name alone is not injective: "DSP **Regular** Savings Fund" (conservative hybrid) and "DSP Savings Fund" (money market) both reduce to `DSP SAVINGS FUND`, because REGULAR is part of the first fund's actual name. A Hold and a No View landed on one key. Now keyed on `(category, base)`, with a gate that aborts if any scheme carries more than one call or score. |
| 20 | IDCW share classes never received their scheme's call | Found 2026-09-03 in the production pair of 2026-07-26. The exporter's IDCW stripping does not cover `IDCW Payout/Reinvestment` (slash) or `IDCW - Payout & Re-investment of Income Distribution...`, so those share classes formed keys of their own and came out `No View` while the Growth classes of the same scheme carried a real call. 7 schemes, 40 ISINs, 26 of them `No View` against a sibling with a live call — including **Groww Aggressive Hybrid, where 2 ISINs say Sell and 2 say No View**. A client holding the IDCW class is told the desk has no view on a fund it has called. Same family as defect 14, and the gate that is supposed to abort when a scheme carries more than one call did not fire. |
| 21 | One scheme carried two scores | Kotak Focused Fund: `INF174KA1EK3` scored 73.0 against 78.0 on its five siblings, because that row spells the plan `Regular plan _ Growth Option` with an underscore where every other row uses a hyphen. Defect 15's failure mode surviving in a single row, and again the multi-score abort did not fire. |
| 14 | Base-key leak stranded a connective | "Payout **of** Income Distribution cum capital withdrawal option" lost the words one at a time and left a bare `OF`, so `INF174K01229` became `KOTAK SMALL CAP FUND OF` — a key of its own. The desk's ruling on Kotak Small Cap could not reach the share class the client actually held. IDCW phrases are now stripped as units, trailing debris stripped, and anything still ending on a connective aborts the export. |

## Statement parsing

| # | Defect | What it did |
|---|---|---|
| 9 | Parser picked the wrong column | `_pick` looped columns-outer, so "Amount Invested" matched the generic word "amount". Parsed total came out at half the real figure with no error. Fixed to words-outer, plus reconciliation against the statement's own TOTAL row. |
| 10 | Reconciliation silently disabled itself | `_num("nan")` returned `float('nan')`, `max()` over a NaN-leading list returned 0, so `if stated:` was falsy and the check never ran. `_num` now never returns NaN. |

## Deck rendering and wording

| # | Defect | What it did |
|---|---|---|
| 6 | `funds_equity` never paginated | 28 rows laid to 12.33in on a 7.5in page. 75 shapes rendered invisibly below the trim. |
| 7 | `fund_actions` printed the opposite of the truth | Inferred performance sells from QFRA-2 below 40 only, so it printed "No fund here is sold on performance alone" while all four sells were performance calls. |
| 8 | `funds_hybrid` asserted risk from missing data | `no_stats` required ALL of worst-year, down-capture and Sortino to be missing, so a fund with one of them printed "Sortino at n/a says holders were not paid for that downside." |
| 17 | `Hold (watch)` not in the call vocabulary | A desk carve-out sorted last and counted as neither held nor actioned. |
| 18 | Disclaimer colophon at y=6.9 | `Deck.footer()` puts chrome at 7.14 on every other slide, so the closing page lifted its footer a fifth of an inch and spilled into the band the geometry gate protects. |
| 19 | `QFRA` raised eight permanent tellscan findings | The sanctioned client-facing prefix was in the blanket internal-jargon list. A gate that always fails is a gate nobody reads, and it would have masked a real finding. Now `qfra framework:` is allowed and every other use of the word still flags. |

## Delivery and disclosure

| # | Defect | What it did |
|---|---|---|
| 11 | 403 misread as proof of absence | A `raw.githubusercontent` 403 was taken as evidence the repo was private. It is not. Visibility is checked against the API or `git ls-remote`, never inferred from a fetch failure. |
| 12 | Demo branch published carrying client data | Cut from the pre-scrub master. Rebuilt on the cleaned master and force-pushed. |
| 16 | `latest_score_file()` chose by filename order | The demo file is dated 2026-08-31 and a production file dated earlier sorts before it, so the kit built a deck from **invented** scores while printing the production as-of date read from the VERSION file next door. Now prefers a non-demo file, pairs VERSION with the file chosen, refuses a mismatched pair, and shouts on fallback. |

## A wording defect in the first delivered workbook

Two shipped rationale lines contradicted their own numbers:

> `[Hold] Axis ELSS Tax Saver Fund` — "clear of the bottom third of its own category, 34th
> percentile over three years and **0th over five**"

The 0th percentile is not clear of anything. The **call** was right — the rule needs both
horizons below the threshold — but the sentence was not. The exporter now emits a distinct
third branch: "below the bottom third on one horizon of the two, Nth percentile over three
years and Nth over five. Held, and kept under review." ICICI Prudential Equity Savings had
the same defect (10th/33rd).

The general lesson: when a call is right for a reason the sentence does not state, the
sentence is still a client-facing error. Say which horizon failed.
