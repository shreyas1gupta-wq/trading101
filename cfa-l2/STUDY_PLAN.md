# CFA Level 2 — 20-Day Sprint Plan (±5–7 days flex)

**Candidate:** Neha | **Start:** Mon 2026-07-20 (Day 1) | **Exam:** ~Aug 26, 2026 | **Core plan:** 20 days | **Flex window:** up to Day 27 | **Reserve:** remaining days for mocks + final polish
**Profile:** Very fast learner — cleared L1 in 8 days @ ~10 hr/day with ~2,000 questions. Zero L2 prep at start. Weakest: FSA, Quant formulas.
**Method:** Claude chat is the primary teacher (concepts → worked examples → vignettes). Target effort ~10 hr/day. Target question volume: **60–80 Q/day, ~2,000+ total including mocks.**

**Companion files (read alongside this plan):**
- `CURRICULUM_CHECKLIST.md` — every topic → reading → concept, verified vs official 2026 structure. The "nothing missed" master; tick items as taught+drilled.
- `RESOURCES.md` — verified links (official, free, paid, communities) + the daily drilling loop.
- `QUESTION_BANK.md` — drilling system, mock schedule, item-set format, seed questions.
- `FORMULA_SHEET.md` / `HIGH_YIELD.md` — auto-built revision + pattern bank.
- `PROGRESS.md` — status, scores, weak flags. **Read this first every session.**

**Curriculum note (verified July 2026):** 45 learning modules, unchanged vs 2025 except 1 LOS removed in Quant. **2026 change:** Alternatives dropped the *Private Equity Investments* reading and added *Hedge Fund Strategies* — PE/LBO math is de-emphasized this cycle (see Day 10).

---

## TEACHING PROTOCOL (how any Claude session runs a study day)

When the user says "Start Day X" (or "continue"):

1. **Read `cfa-l2/PROGRESS.md`** for status and weak flags.
2. **Teach fast and dense** — this candidate moves quickly:
   - Plain-language intuition first, formal version immediately after. No padding, no repetition of what's already understood.
   - Every formula → instant worked numeric example (real numbers, BA II Plus keystrokes where relevant).
   - Flag exam traps and "how CFAI words it" inline.
   - Check understanding with 1–2 rapid questions per chunk; if answered instantly, accelerate.
3. **Question drilling (non-negotiable, ~2.5–3 hrs/day):**
   - Claude generates **2 full item sets (12 questions)** on the day's material, exam-difficulty, grades and explains all options.
   - User additionally drills **40–60 topic questions in the CFAI Learning Ecosystem QBank** (official wording > any third party). Log the score.
4. **Update tracker files** and commit+push to `claude/hopeful-dijkstra-tgopmr`:
   - `PROGRESS.md` (sessions done, scores, weak flags), `FORMULA_SHEET.md` (every formula taught), `HIGH_YIELD.md` (every repeatable pattern spotted).
5. **Daily drip (last 30 min, from Day 1):** 5 FSA concept flashcards + 5 formula-recall drills pulled from all prior days (oldest first) + re-ask yesterday's wrong answers. This is the fix for FSA/Quant sitting late in the order.

**Session prompt to paste in any new session:**
> Read cfa-l2/STUDY_PLAN.md and cfa-l2/PROGRESS.md, then teach me Day X per the teaching protocol. Go fast.

**Daily rhythm (~10 hr):** 3h teach → 3h teach → 2.5–3h questions (item sets + QBank) → 30 min drip/review.

---

## Exam weights — where the points are

Ethics 10–15 · Quant 5–10 · Econ 5–10 · **FSA 10–15** · Corp Issuers 5–10 · **Equity 10–15** · **Fixed Income 10–15** · Derivatives 5–10 · Alts 5–10 · **PM 10–15**

---

## PHASE 1 — Core sprint (Days 1–20)

### Day 1 · Corporate Issuers (entire topic)
Dividends & buybacks (payout theories, buyback EPS/BV math, FCFE coverage) · ESG considerations · Cost of capital advanced (ERP methods, country risk) · Corporate restructuring (M&A, divestitures, LBOs). Item sets + 50 QBank.

### Days 2–4 · Equity Valuation
- **Day 2:** Valuation process, return concepts · DDM full suite (GGM, multistage, H-model, PVGO, sustainable growth) · start FCFF/FCFE (all bridge formulas: from NI, EBIT, EBITDA, CFO).
- **Day 3:** FCF models (single/two-stage, sensitivity) · Market-based valuation complete (justified P/E, P/B, P/S, EV/EBITDA, PEG, comparables).
- **Day 4:** Residual income (RI, clean surplus, justified P/B) · Private company valuation (approaches, DLOC/DLOM) · Equity mega item-set.

### Days 5–7 · Fixed Income
- **Day 5:** Term structure (spot/forward, bootstrapping, riding the curve, swap spreads, Z-spread, theories) · Arbitrage-free framework (binomial trees, backward induction, pathwise, Monte Carlo).
- **Day 6:** Embedded options (callable/putable in trees, OAS, one-sided durations, convertibles) — the single most repeatable FI vignette.
- **Day 7:** Credit models (structural vs reduced form, spread decomposition, CVA) · CDS (mechanics, upfront, hazard rates) · FI mega item-set.

### Days 8–9 · Derivatives
- **Day 8:** Forward commitments — equity/bond forwards & futures, FRAs (price + mid-life value), interest rate swaps, currency & equity swaps.
- **Day 9:** Contingent claims — binomial (1/2-period, hedge ratio), BSM interpretation, Greeks, implied vol · Derivatives mega item-set.

### Day 10 · Alternative Investments (entire topic — 2026: 4 modules, no standalone PE reading)
Commodities & commodity derivatives (spot vs futures, theory of storage, convenience yield, **contango/backwardation, roll yield**, index construction) · Private real estate (income approach — **direct cap NOI/cap rate, DCF**, cost & sales-comparison) · REITs / public real estate (**FFO, AFFO, NAVPS**, price-to-FFO) · **Hedge fund strategies** (equity L/S & market-neutral, event-driven, relative value, opportunistic/global macro; upside/downside capture). Item sets + QBank. *(PE metrics like DPI/RVPI/TVPI are no longer a standalone L2 reading — only touch lightly if time permits.)*

### Day 11 · Economics (entire topic)
FX: bid-ask, cross rates, forward points, **all parity conditions** (CIRP/UIRP/PPP/Fisher), carry trade, FX forecasting · Economic growth (growth accounting, convergence, classical/neoclassical/endogenous). Item sets + QBank.

### Days 12–13 · Portfolio Management
- **Day 12:** ETFs (creation/redemption, premiums, costs) · Multifactor models (APT, factor types, active risk/return attribution) · Measuring & managing market risk (VaR methods, ES, sensitivities, stress).
- **Day 13:** Backtesting & simulation · Economics and investment markets · Active portfolio management (**IR, IC, TC, fundamental law**) · Trading costs & electronic markets · PM mega item-set.

### Days 14–15 · Quantitative Methods *(weak area — but dripped daily since Day 1)*
- **Day 14:** Multiple regression complete — interpretation, ANOVA, R²/adj-R², F/t-tests, misspecification, heteroskedasticity/serial correlation/multicollinearity (symptom → detection → fix table), dummies, logistic, influence points.
- **Day 15:** Time series (trend, AR, unit roots, seasonality, mean reversion, ARCH, cointegration) · ML + Big data (algorithm map, overfitting, precision/recall/F1) · Quant mega item-set.

### Days 16–18 · FSA *(weakest area — 3 dense days after 15 days of drip)*
- **Day 16:** Intercorporate investments (FVPL/FVOCI, equity method, consolidation, full vs partial goodwill) — the classic ratio-comparison vignette.
- **Day 17:** Pensions & share-based comp (PBO mechanics, IFRS vs GAAP splits, assumption-change effects) · Multinational operations (current rate vs temporal, functional currency, ratio effects, hyperinflation).
- **Day 18:** Financial institutions (CAMELS) · Quality of financial reports (Beneish, accruals) · Integration of FSA · FSA mega item-set.

### Day 19 · Ethics (entire topic)
All seven Standards via L2-style long-case application · Asset Manager Code · Ethics mega item-set. (Ethics returns on the final pre-exam days — it's the band tiebreaker.)

### Day 20 · Consolidation day
Full `FORMULA_SHEET.md` speed run (every formula from memory, <30s each) · Full `HIGH_YIELD.md` pattern drill · **Mixed 3-topic mega item-set** (Claude generates, cross-topic like the real exam) · Mark the 5 weakest readings for flex-window rebuilds.

---

## FLEX WINDOW (Days 21–27) — absorb overruns, then attack

Use in priority order:
1. **Overrun absorption:** any topic that needed more time lands here (expected candidates: FSA, embedded options, swaps). Max 2–3 days.
2. **Mock 1** (full timed: 88 Q, 2 sessions of 2h12m — use CFAI official mock #1). Same-day full review of every wrong answer.
3. **Weak rebuild:** re-teach the 3 worst topics from Mock 1.
4. **Mock 2** (CFAI official #2) + same-day review.

**Checkpoints (hard gates):** end of Day 7 → Corp Issuers+Equity+FI done · end of Day 13 → through PM done · end of Day 18 → FSA done. If behind at a gate: cut depth on Alts/Econ (low weight), never cut Equity/FI/FSA.
**If ahead of schedule:** pull mocks earlier — more mock-review cycles beat more reading.

## RESERVE (through Day ~40 / exam)

- **Mock 3 and 4** (CFAI mocks or Claude-generated full mocks), each with same-day review + next-day weak rebuild.
- Two dedicated **FSA+Quant final drill days**.
- **Day −2:** Ethics final pass + top-20 most-missed patterns from `HIGH_YIELD.md`.
- **Day −1:** formula-sheet skim only. Sleep.

---

## RESOURCES (upgraded)

| Resource | Use for | Priority |
|---|---|---|
| **Claude chat (this)** | All teaching, worked examples, item sets, mock generation, weak-area rebuilds | Primary |
| **CFAI Learning Ecosystem QBank** | 40–60 official-wording questions/day on the day's topic — official phrasing is the exam | Mandatory |
| **CFAI official mocks (in LES)** | Mocks 1–2 minimum; the only truly exam-calibrated mocks | Mandatory |
| **CFAI curriculum EOC questions** | If a topic feels shaky after QBank — EOCs are closest to vignette style | As needed |
| **`FORMULA_SHEET.md` / `HIGH_YIELD.md`** | Daily recall drills + final-week revision — built automatically as we study | Auto |
| IFT free YouTube summaries / MM if subscribed | Optional 15-min topic refresh before a day starts | Optional |
| AnalystForum + r/CFA "most tested" threads | Sanity-check the high-yield list in the flex window | Optional |

## Rules of engagement

1. **Volume is the strategy** — you passed L1 on 2,000 questions; L2 target is the same. Reading without the daily 60–80 Q is a failed day.
2. **Never skip the daily FSA/formula drip** — it's why the late FSA slot is safe.
3. Missed/short day → compress within the topic block or spend flex days; never shift the whole plan.
4. Item-set scores <4/6 and QBank <65% → flag in `PROGRESS.md`, resurfaces in the drip until beaten twice.
5. Every session ends with commit+push.
