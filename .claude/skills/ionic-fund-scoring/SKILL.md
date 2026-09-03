---
name: ionic-fund-scoring
description: "The Ionic desk's fund scoring method, dated rulings, call precedence and advisor deck-kit workflow. Use this whenever the work touches an Ionic fund score, a Buy/Sell/Hold/Trim/No View call, a client portfolio review deck, a holding-statement build, the score file or VERSION.json pair, desk_calls.csv, the QFRA frameworks, the bottom-third rule, or the ionic-deck-kit / ionic-scorecard repos — including when the user just says 'build a review deck from this statement', 'why is this fund a Sell', 'refresh the scores', 'can I send this to an advisor', or asks whether a score predicts anything. Also use before answering any question about what the score means or what may leave the building, because the answer is load-bearing and getting it wrong has already cost this desk real money and real client-facing errors."
---

# Ionic fund scoring and the advisor deck kit

**Central use only. This skill and its references do not go to an advisor, to a public
repository, or to another Claude.** Only the score file and `VERSION.json` cross that line;
`references/advisor-handover.md` is the one file whose *contents* are meant to be sent.

This is the desk's working book: how a score is actually computed, which rulings bind,
what may leave the building, and the defects already paid for. It exists so the method
survives a session ending and so a defect diagnosed once is never reintroduced.

Source of record: `SCORING_RECORD.md` (central), last updated 2026-09-02. The
human-format version is the 30-slide deck `09_PRODUCT/reports/Ionic_Scoring_Methodology.pptx`.

## Before anything else: which side of the wall are you on?

Two postures, and they permit different things. Establish which one applies before acting.

**Central (the desk).** May compute scores, set calls, edit `desk_calls.csv`, run
`export_score_file.py`. Everything in `references/` is in scope.

**Advisor-side (the kit).** Renders calls; cannot derive them. The kit holds no NAV
history, no peer construction, no percentile maths and no thresholds — deliberately, so
an advisor holding the output cannot reconstruct how a number was reached. If you are
working in a clone of `ionic-scorecard` and a scheme is missing from the score file, the
answer is `No View`. Not a guess, not an inference from a similar fund, not a call
borrowed from the same AMC's other scheme.

The Principal's instruction of 2026-09-02: scores and calls are fixed centrally, and the
method, workflow and data do not go to an advisor or to another Claude. An advisor
supplies a holding statement and gets the standardised deck.

**`shreyas1gupta-wq/ionic-scorecard` is public.** Verified against the GitHub API on
2026-09-02, and re-verified 2026-09-03. Everything committed there, history included, is
world-readable. The method, the rulings and this record are gitignored out of it. Never
commit them there to "fix" the fact that they are unversioned — see the open items.

Check visibility against the API or `git ls-remote`. A `raw.githubusercontent` 403 is not
evidence a repo is private; reading one that way already produced a wrong conclusion once
(defect 11).

`references/boundary.md` has the full table of what lives where.

## The call, in strict precedence

Work down this list and stop at the first match. The order is the whole logic — a call
produced by evaluating these in any other sequence is wrong even if it lands on the same
answer by luck.

1. **A desk ruling in `desk_calls.csv`.** The only route by which the desk overrides the
   arithmetic. Carve-outs live here with a reason on the record.
2. **`No View`** for debt, arbitrage, sectoral/thematic, overseas FoFs, and anything
   unscoreable.
3. **`Hold`** for gold, index and other allocation vehicles. They track rather than
   select, so there is no manager record to rank, and owning one is an allocation
   decision rather than a selection one.
4. **`Sell`** where the scheme is below the bottom third on **both** the three-year and
   five-year horizon.
5. **`Hold`** otherwise.

One bad horizon is a bad run; two is a record. A scheme failing one horizon only is held,
and the rationale must say *which* horizon failed rather than claiming the fund is clear.
Getting this wrong shipped two self-contradicting rationale lines to a client — see
`references/defects.md`.

**Trim is not a call in the score file.** A Sell is a judgement on a fund and is the same
in every portfolio; a Trim is a judgement on a *weight*. The same scheme at 13% of one
book and 2% of another warrants a trim in the first and nothing in the second, and an
ISIN-keyed file cannot carry that. The desk publishes `single_scheme_cap_pct` (currently
10.0) in `VERSION.json`; the kit converts a held scheme above the cap into a Trim sized to
bring it back to the cap. The advisor sets nothing.

## Standing rules

These bind regardless of posture. Each one exists because breaking it produced a concrete
failure, not because it sounds prudent.

- **Never fabricate a score.** An unscored scheme is `No View`. A plausible-looking
  invented percentile is worse than a blank, because it survives review.
- **No client Buy is ever issued.** The vocabulary is Sell, Trim, Hold, `Hold (watch)`,
  No View. `Hold (watch)` is a real call and sorts with the held, not with the
  unclassified (defect 17).
- **Fund-name-to-framework mapping never uses string similarity.** Names collide in ways
  that look like matches and are not — see defects 13 and 14 for two that cost a client
  the correct call.
- **Two share classes of the same scheme always carry the same call.** One score per
  scheme, from the Direct plan, falling back to Regular only where a scheme has no Direct
  plan. Never average the plans a particular client happens to hold (defect 15).
- **Every client-facing rationale opens `QFRA Framework:`** followed by the reason. No
  rationale for a No View. (Ruling of 2026-08-31; the tellscan gate allows this prefix and
  flags every other use of the word.)
- **State what has happened, never what will.** The score does not predict — read
  `references/limits.md` before quoting it to anyone.

## Reading the score before you quote it

The forward test runs 64 monthly formations over 28,376 observations. Rank correlation
between the score and the next twelve months of category-relative return is **+0.04**, and
in the equity categories it is mildly **negative**. It is materially positive only in the
low-dispersion hybrid categories.

So the score describes a record accurately and forecasts nothing. Do not describe it as
predictive, do not annualise it, and do not let a deck or a conversation imply the ranking
is a forecast. `references/limits.md` carries the coverage gaps, the QFRA-1 data staleness
and the rest — read it before answering any "what does this score mean" question.

## Building a deck

```bash
# 1. central: produce the score file (needs the NAV store; datasets/ is gitignored)
python Shreyas_Ionic_AMC/09_PRODUCT/scripts/export_score_file.py --out <dir>

# 2. hand the advisor ionic_scores_<date>.csv and VERSION.json, privately, as a pair

# 3. advisor: drop the pair into ionic-deck-kit/scores/, then
python ionic-deck-kit/build/build_review.py <statement.xlsx> --client "Family Name"

# 4. all three gates, before anything is sent
python ionic-deck-kit/qa/check_geometry.py  <deck.pptx>
python ionic-deck-kit/qa/check_geometry2.py <deck.pptx>
python ionic-deck-kit/qa/tellscan.py        <deck.pptx>
```

The score file and `VERSION.json` travel as a **pair** and are read as a pair. Splitting
them let the kit build a deck from invented demo scores while printing a production as-of
date (defect 16). Tiers: `--tier HNI_DEEP` (default, full), `STANDARD`, `RM_SIMPLE`.

**Three outputs to read before anything is sent:**

- *Reconciliation.* The parser totals what it read and compares against the total the
  statement prints for itself. A MISMATCH means the deck is built on a partial read and
  every number on it is wrong. Do not "eyeball whether it's close" — a silently disabled
  reconciliation once passed a half-read statement (defects 9 and 10).
- *Schemes absent from the score file.* They come out as No View, which is correct
  behaviour rather than a failure. A large holding at No View is a question for the desk.
- *Exceptions.* Rows carrying money that could not be tied to a scheme. They go back to
  the desk, never ignored.

A block of exclamation marks saying the calls are invented demo data means the score files
are not in place. Stop; the deck is worthless.

`references/advisor-handover.md` has the email text and the two attachments, for when the
desk onboards an advisor.

## Do not reintroduce a known defect

`references/defects.md` lists 19 defects and the failure each caused — a dead parser, a
self-approving health gate, a biased peer filter, two horizons collapsed into one test, a
slide table rendering 75 shapes below the page trim, a section printing the opposite of
the truth. Every entry cost real diagnosis.

Read it before changing the exporter, the parser, the peer construction or any deck
section. When touching one of those areas, check whether the change re-opens an entry;
reintroducing one is a regression, not a fresh bug.

## Open items for the Principal

Carry these forward rather than solving them unilaterally — the first two in particular
have an obvious wrong fix.

1. **The method and rulings have no version-controlled home.** They are gitignored out of
   a public repo and exist only in the working tree. They need a *private* repository.
   Committing them where they are is the wrong fix.
2. **Git history still contains both scrubbed client surnames.** Deleting from HEAD does
   not purge history; needs `filter-repo` and a force-push.
3. **A committed HuggingFace token** sits in `HANDOFF.md` (twice) and in several scripts,
   in public history. Treat as leaked; rotation deferred.
4. **Axis ELSS Tax Saver changed call.** Shipped as `Hold` on a Regular-pool percentile of
   34.2. On the Direct pool it is 27th, with a 0th-percentile five-year record, so the rule
   now makes it a `Sell`. One row in `desk_calls.csv` pins it back if the desk wants it held.
5. **Stale skill text.** "A fund Sell requires BOTH frameworks" still appears in the
   `Ionic_Portfolio_Review` and `qfra1-rerun` skills, superseded by originate-and-veto
   (2026-08-04). Correct them when you next have them in reach.
6. **QFRA-2 file conflict** needs an authoritative run declared by the engine owner.

## Reference files

- `references/method.md` — the score, the peer set, the horizons, redemption/tax mechanics
- `references/rulings.md` — dated rulings and the two carve-outs
- `references/defects.md` — the 19 defects and the failure each caused
- `references/limits.md` — what the score cannot do, coverage, data staleness
- `references/boundary.md` — what lives where and what may leave the building
- `references/advisor-handover.md` — the advisor email and its two attachments
