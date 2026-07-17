# CFA Level 2 — 30-Day Chat-Taught Study Plan

**Candidate:** Neha | **Exam:** ~Aug 26, 2026 (40 days from Jul 17) | **Buffer:** 10 days
**Prep level at start:** Zero | **Weakest areas:** FSA, Quant (formulas)
**Materials:** Claude chat is the primary study material. Teaching happens in-conversation: concepts → worked examples → vignette practice.
**Assumed effort:** 5–6 focused hrs/day (compress blocks proportionally if a day is shorter).

---

## How any Claude session should run a study day (TEACHING PROTOCOL)

When the user says "Start Day X" (or "continue"), do this:

1. **Read `cfa-l2/PROGRESS.md`** to see what's done and any flagged weak spots.
2. **Teach the scheduled reading(s)** for that day, topic by topic:
   - Explain each concept in plain language first, then the formal version.
   - Every formula gets a **worked numeric example** immediately (real numbers, step-by-step).
   - Use exam-style framing: "how CFAI tests this", common traps, calculator (BA II Plus) keystrokes where relevant.
   - Teach in chunks of ~15–20 min of reading; after each chunk ask 1–2 quick check questions before moving on.
3. **End-of-session item set:** generate a 6-question vignette (L2 format: one shared case, 6 MCQs), grade the user's answers, explain every option including why wrong ones are wrong.
4. **Update the tracker files** and commit+push to branch `claude/hopeful-dijkstra-tgopmr`:
   - `PROGRESS.md` — mark sessions done, log scores, flag weak topics.
   - `FORMULA_SHEET.md` — append every formula taught that day (grows into the master revision sheet).
   - `HIGH_YIELD.md` — append any "repeatable exam pattern" identified (grows into the final-week drill list).
5. **Parallel track (last 20–30 min, EVERY day from Day 1):** because FSA and Quant are the weakest areas but scheduled late, drip-feed them daily — 5 flashcard-style FSA concept questions + 3 formula-recall drills from `FORMULA_SHEET.md` (spaced repetition: pull from all prior days, oldest first).

**Session prompt the user pastes to start any day:**
> Read cfa-l2/STUDY_PLAN.md and cfa-l2/PROGRESS.md, then teach me Day X per the teaching protocol.

---

## Exam weights (2026 L2) — where the points are

| Topic | Weight | Days | Priority |
|---|---|---|---|
| Ethics | 10–15% | 2 | High (also tiebreaker band) |
| Quantitative Methods | 5–10% | 2 (+daily drip) | Medium |
| Economics | 5–10% | 2 | Medium |
| Financial Statement Analysis | 10–15% | 4 (+daily drip) | **Highest — weakest area** |
| Corporate Issuers | 5–10% | 2 | Medium |
| Equity Valuation | 10–15% | 5 | Highest |
| Fixed Income | 10–15% | 5 | Highest |
| Derivatives | 5–10% | 3 | Medium-high |
| Alternative Investments | 5–10% | 2 | Medium |
| Portfolio Management | 10–15% | 3 | High |

---

## Phase 1 — Learn everything (Days 1–30)

### Days 1–2 · Corporate Issuers
- **Day 1:** Dividends & share repurchases (payout policy, dividend theories, buyback math, FCFE coverage ratio); ESG considerations in investment analysis.
- **Day 2:** Cost of capital — advanced topics (ERP approaches, cost of debt nuances, country risk); Corporate restructuring (M&A, divestitures, LBO basics, valuation effects). Full-topic item set.

### Days 3–7 · Equity Valuation
- **Day 3:** Valuation process & return concepts; Discounted dividend valuation (GGM, two-stage, H-model, sustainable growth, PVGO).
- **Day 4:** Free cash flow valuation I — FCFF/FCFE from net income, EBIT, EBITDA, CFO; forecasting FCF.
- **Day 5:** Free cash flow valuation II — single/two-stage models, sensitivity; start Market-based valuation (justified P/E, P/B, P/S).
- **Day 6:** Market-based valuation II (EV/EBITDA, PEG, method of comparables); Residual income (RI model, clean surplus, justified P/B link).
- **Day 7:** Private company valuation (income/market/asset approaches, discounts & premiums); full Equity mega item-set + recap.

### Days 8–12 · Fixed Income
- **Day 8:** Term structure & interest rate dynamics (spot/forward rates, bootstrapping, riding the curve, swap curve, Z-spread, TED/Libor-OIS, term structure theories).
- **Day 9:** Arbitrage-free valuation (binomial trees, backward induction, pathwise valuation, Monte Carlo).
- **Day 10:** Bonds with embedded options (callable/putable valuation in trees, OAS, effective/one-sided durations, convertibles).
- **Day 11:** Credit analysis models (credit scores/ratings, structural vs reduced form, credit spread decomposition, CVA).
- **Day 12:** Credit default swaps (mechanics, upfront premium, hazard rates, uses); full FI mega item-set + recap.

### Days 13–15 · Derivatives
- **Day 13:** Pricing & valuation of forward commitments I — equity/fixed-income forwards & futures, FRAs (the classic FRA vignette).
- **Day 14:** Forward commitments II — interest rate swaps, currency swaps, equity swaps (pricing at initiation, valuation during life).
- **Day 15:** Contingent claims — binomial option pricing (one/two period, hedge ratio), BSM inputs & interpretation, Greeks, implied vol; item set.

### Days 16–17 · Alternative Investments
- **Day 16:** Real estate — private (income approach: direct cap, DCF; cap rates; NOI) and public (REITs: NAVPS, FFO/AFFO, valuation).
- **Day 17:** Private equity (LBO/VC valuation, DPI/RVPI/TVPI, fee math, carried interest); Commodities & commodity derivatives (contango/backwardation, roll yield, index construction); Hedge funds overview; item set.

### Days 18–19 · Economics
- **Day 18:** Currency exchange rates (bid-ask, cross rates, forward points, **all parity conditions**: CIRP, UIRP, PPP, Fisher, carry trade, FX forecasting).
- **Day 19:** Economic growth (production function, growth accounting, convergence, theories: classical/neoclassical/endogenous); item set.

### Days 20–22 · Portfolio Management
- **Day 20:** Exchange-traded funds (creation/redemption, premiums, tracking error, costs); Using multifactor models (APT, macro/fundamental/statistical factors, active risk & return attribution).
- **Day 21:** Measuring & managing market risk (VaR methods, expected shortfall, sensitivities, scenario/stress, constraints); Backtesting & simulation.
- **Day 22:** Economics and investment markets (discount-rate framework); Analysis of active portfolio management (**information ratio, transfer coefficient, fundamental law**); Trading costs & electronic markets; item set.

### Days 23–24 · Quantitative Methods *(weak area — extra rigor, but drip started Day 1)*
- **Day 23:** Multiple regression suite — coefficients & interpretation, ANOVA, R²/adjusted R², F-test, t-tests, misspecification, heteroskedasticity/serial correlation/multicollinearity (detect + fix), dummy variables, logistic regression, influence points.
- **Day 24:** Time series (trend models, AR models, unit roots, seasonality, ARCH, cointegration); Machine learning (supervised/unsupervised map, overfitting, algorithms) + Big data projects (steps, text prep, model evaluation: precision/recall/F1); item set.

### Days 25–28 · FSA *(weakest area — most days + it's been dripping daily for 24 days already)*
- **Day 25:** Intercorporate investments (FV through P/L / OCI, equity method, consolidation, full vs partial goodwill, joint ventures — the classic "how does the balance sheet change" vignette).
- **Day 26:** Employee compensation — pensions (PBO mechanics, service/interest cost, remeasurements, IFRS vs US GAAP P&L split) and share-based comp.
- **Day 27:** Multinational operations (current rate vs temporal method, functional currency logic, translation gains/losses, hyperinflation, ratio effects).
- **Day 28:** Analysis of financial institutions (CAMELS, banks' ratios); Evaluating quality of financial reports (Beneish, accruals quality); Integration of FSA techniques; FSA mega item-set.

### Days 29–30 · Ethics
- **Day 29:** Code & Standards deep application — all seven standards with L2-style case vignettes (the testing style shifts from L1: longer cases, subtler violations).
- **Day 30:** Guidance for Standards cases continued; Asset Manager Code; ethics mega item-set. Evening: **full formula sheet review** (everything in `FORMULA_SHEET.md`).

---

## Phase 2 — Buffer / Attack mode (Days 31–40)

- **Day 31:** High-yield pattern day 1 — drill everything in `HIGH_YIELD.md`: the repeatable vignette patterns (FRA valuation, pension cost components, current-vs-temporal, FCFF bridges, binomial trees, parity triangles, justified multiples, swap valuation).
- **Day 32:** **Mock 1** (full timed, 88 questions, 2×2h12m) — Claude generates or user uses CFAI mock. Same-day review of every wrong answer.
- **Day 33:** Weak-area rebuild from Mock 1 (re-teach the 3 worst readings).
- **Day 34:** High-yield pattern day 2 + formula speed drills (target: every formula from memory in <30s).
- **Day 35:** **Mock 2** (timed). Same-day review.
- **Day 36:** Weak-area rebuild from Mock 2.
- **Day 37:** FSA + Quant final deep drill (the designated weak areas get a dedicated last pass).
- **Day 38:** **Mock 3** (timed). Same-day review.
- **Day 39:** Ethics final pass (ethics last = fresh in memory, band tiebreaker) + top-20 most-missed patterns.
- **Day 40:** Light review only — formula sheet skim, sleep. No new material.

---

## Rules of engagement

1. **Never skip the end-of-day item set** — L2 is a vignette exam; reading ≠ readiness.
2. **Never skip the daily FSA/formula drip** — it is the fix for the weak areas being scheduled late.
3. If a day is missed, **do not shift the whole plan** — compress the next same-topic day; buffer days absorb overflow.
4. Log every item-set score in `PROGRESS.md`; anything <4/6 gets flagged and resurfaces in the daily drip.
5. Every session ends with commit+push so no work is ever lost.
