# What lives where, and what may leave the building

`shreyas1gupta-wq/ionic-scorecard` is **public**. Verified against the GitHub API
(`private: false`, `visibility: public`), not inferred from a fetch failure. Everything
committed there, including history, is world-readable.

| Thing | Path | Public? |
|---|---|---|
| The scoring method | `09_PRODUCT/scripts/export_score_file.py` | **No.** Gitignored. |
| The desk's rulings | `09_PRODUCT/scripts/desk_calls.csv` | **No.** Gitignored. |
| The central record | `09_PRODUCT/_CENTRAL/` | **No.** Gitignored. |
| The score file it produces | published privately to advisors | **No.** `*.csv` ignored; only `*_DEMO.csv` whitelisted. |
| The slide engine | `09_PRODUCT/pr_template/` | Yes. Layout only, no calls. |
| The advisor kit | `ionic-deck-kit/` | Yes. Renders calls, cannot derive them. |

The split is what enforces the Principal's instruction of 2026-09-02. The kit holds no NAV
history, no peer construction, no percentile maths and no thresholds, so an advisor
holding the output cannot reconstruct how a number was reached.

## The open risk

The method and the rulings are gitignored, which means they are **not version-controlled
anywhere**. They exist only in the working tree. They need a private repository. This is a
decision for the Principal, not something to solve by committing them to the public repo.

## Verification of the split

Verified 2026-09-02 from a fresh `git clone` of public master: the method and rulings are
absent, a 43-holding statement reconciles to its own total, 42 of 43 holdings match the
score file, the cap fires on one holding, and the 31-slide deck passes all three gates with
zero findings.

Re-run that check after any change that moves a file across the line.
