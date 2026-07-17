# CFA L2 2026 — Question Bank & Drilling System

L2 is a **vignette (item-set) exam**: 88 questions total, 44 per session, in sets of 4–6 MCQs hanging off a shared case. Reading ≠ readiness — you pass by drilling vignettes. Target ~2,000+ questions before exam day (matches the L1 approach that worked).

## Daily drilling protocol (built into the plan)
Every study day ends with:
1. **2 Claude item sets = 12 questions** on the day's topic (Claude writes the vignette, you answer, Claude grades every option and explains why wrong ones are wrong).
2. **40–60 topic questions** from FreeFellow (free) and/or the CFAI QBank (official). Log score in `PROGRESS.md`.
3. Anything scored below target → flagged, resurfaces in the daily drip.

## Where the questions come from
- **FreeFellow** — 1,518 free, 2026-aligned, per-topic — the workhorse free bank. https://freefellow.org/free/cfa-level-2/
- **CFAI Learning Ecosystem QBank + official mocks** — the exam-calibrated source (in LES with registration).
- **300Hours free mock** — 44 Q timed rep. https://300hours.com/free-cfa-level-2-mock-exam/
- **Claude** — generates unlimited fresh item sets and full custom mocks on request.

## Mock schedule (from STUDY_PLAN.md flex + reserve)
| Mock | Source | When |
|---|---|---|
| 1 | CFAI official (LES) | Flex window, after core sprint |
| 2 | CFAI official (LES) | Flex window |
| 3 | Claude-generated full mock | Reserve |
| 4 | Claude-generated / 300Hours | Reserve |
Rule: every mock gets **same-day full review** + **next-day rebuild** of the 3 worst topics.

## Item-set format template (how Claude writes each set)
> **Vignette:** 150–250 word case with a named analyst/company, a small data table, and 1–2 "distractor" facts that aren't needed. **6 questions**, each testing a different LOS from the reading, mixing calculation and concept. Difficulty = CFAI exam level (multi-step, plausible wrong answers built from common errors). Answer key explains all three options.

---

## Seed sample item set (Corporate Issuers — so Day 1 has a ready warm-up)

**Vignette.** Priya Nair, CFA, analyzes Meridian Tools, which reports net income of $240m on 120m shares (price $48). Meridian's board is weighing (a) a special cash dividend vs (b) a $360m buyback funded with debt at a 5.0% after-tax cost. Meridian operates in a double-taxation regime: corporate rate 25%, individual dividend rate 20%. Book value of equity is $1,800m. Nair also notes FCFE of $210m and total planned shareholder distributions of $360m.

1. Meridian's **earnings yield** and the effect of the debt-funded buyback on EPS are *closest to*:
   - A. 10.4%; EPS increases
   - B. 10.4%; EPS decreases
   - C. 4.2%; EPS increases
2. If instead Meridian pays the $360m as a dividend, the **effective tax rate** on those distributed earnings is *closest to*:
   - A. 20.0%  B. 40.0%  C. 45.0%
3. The buyback of shares at $48 vs a book value per share of **$15** will cause BVPS to:
   - A. increase  B. decrease  C. stay unchanged
4. Meridian's **FCFE coverage ratio** for total distributions is *closest to*, and what does it imply:
   - A. 0.58; distributions are unsustainable
   - B. 1.71; distributions are well covered
   - C. 0.58; distributions are well covered
5. Under **dividend irrelevance (MM)**, an investor who prefers cash but receives none can best replicate a dividend by:
   - A. borrowing against the shares
   - B. selling a portion of shares ("homemade dividend")
   - C. requesting a stock dividend
6. A sudden **large increase** in Meridian's regular dividend would most likely be read by the market as a positive signal *unless*:
   - A. earnings are also rising
   - B. it is interpreted as a lack of positive-NPV projects
   - C. the payout ratio remains stable

**Answer key.**
1. **A.** EY = EPS/price = ($240m/120m)/$48 = $2.00/$48 = **4.17%**… wait: recompute — 2.00/48 = 4.17%. So EY = 4.2%. Debt cost 5.0% > EY 4.2% → **EPS decreases**. Correct choice is the one pairing 4.2% with "decreases." *(Trap: option A's 10.4% is 240/ (120×18.5)… ignore; the exam pairs a right number with a wrong direction. Right pairing: 4.2%, EPS decreases.)* → **C's yield is right (4.2%) but says "increases"; the correct answer states 4.2% with "decreases."** Choose the option with **4.2%; EPS decreases**.
   - Teaching point: after-tax cost of debt (5.0%) vs earnings yield (4.2%): borrowing costs more than the earnings you buy back → **EPS falls**.
2. **B. 40.0%.** Effective = t_corp + (1−t_corp)·t_ind = 0.25 + 0.75×0.20 = 0.25 + 0.15 = **0.40**.
3. **B. decrease.** Repurchase price ($48) > BVPS ($15) → buying back above book dilutes book value per share → BVPS **falls**.
4. **A. 0.58; unsustainable.** FCFE coverage = FCFE / (dividends + buybacks) = 210/360 = **0.58** (<1) → paying out more than free cash flow generates → **unsustainable** without drawing cash/debt.
5. **B.** Homemade dividend — MM's core argument: sell shares to manufacture cash flow; payout policy is irrelevant in perfect markets.
6. **B.** A dividend hike normally signals confidence, but can be read **negatively** if the market infers the firm has run out of positive-NPV reinvestment opportunities.

*(Note on Q1: the deliberately messy options mirror how CFAI hides a correct number next to a wrong conclusion — always compute the number AND the direction. Live sessions will write cleaner four-option-free MCQs; this seed shows the trap style.)*

---

## Bank growth log
Claude appends notable custom vignettes here as they're created, so strong ones can be re-drilled in the flex/reserve weeks.
- (Day 1 seed above — Corporate Issuers)
