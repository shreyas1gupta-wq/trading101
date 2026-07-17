# CFA L2 2026 — Complete Curriculum Coverage Checklist

**Purpose:** the "nothing gets missed" master list. Every topic → every reading → the key concepts/LOS inside it. Check a box only after the concept is taught AND drilled with questions. Verified against the official 2026 L2 structure (45 learning modules; unchanged vs 2025 except 1 LOS removed in Quant).

**2026 change that matters for us:** Alternatives dropped the *Private Equity Investments* reading and added *Hedge Fund Strategies*. So PE/LBO math is de-emphasized this cycle; commodities, real estate (private + public), and hedge-fund strategies are the AI core.

Legend: ☐ not started · ◐ taught, needs drilling · ☑ taught + drilled + scored ≥ target

---

## 1. Quantitative Methods (7 modules · weight 5–10% · plan Days 14–15)
- ☐ **Basics of Multiple Regression & Underlying Assumptions** — the 4 (really 5) assumptions (linearity, homoskedasticity, independence/no serial correlation, normality of residuals, independent variables not random & no exact multicollinearity)
- ☐ **Evaluating Regression Model Fit & Interpreting Results** — SST/SSR/SSE, R², adjusted R², standard error of estimate, F-stat, t-tests on coefficients, confidence intervals, predicting Y
- ☐ **Model Misspecification** — omitted variables, wrong functional form, scaling, non-stationarity; consequences & fixes
- ☐ **Extensions of Multiple Regression** — dummy/qualitative variables (intercept vs slope dummies), logistic regression (log-odds, interpretation), influence analysis (leverage, studentized residuals, Cook's D), heteroskedasticity (detect: BP test; fix: robust SE), serial correlation (Durbin-Watson, BG test; fix: robust SE), multicollinearity (VIF; symptoms)
- ☐ **Time-Series Analysis** — linear/log-linear trend, autoregressive (AR) models, covariance stationarity, unit root (Dickey-Fuller), random walk, mean reversion b0/(1−b1), seasonality (add lag), ARCH, RMSE for model selection, cointegration
- ☐ **Machine Learning** — supervised vs unsupervised vs deep learning; overfitting (bias-variance); penalized regression/LASSO, SVM, KNN, CART, random forest, neural nets, K-means, hierarchical clustering, PCA
- ☐ **Big Data Projects** — steps (conceptualization → collection → prep/wrangling → exploration → model training); structured vs unstructured/text; text prep (tokenization, stemming, BOW); model eval — precision, recall, F1, accuracy, confusion matrix, ROC/AUC, RMSE

## 2. Economics (2 modules · weight 5–10% · plan Day 11)
- ☐ **Currency Exchange Rates: Understanding Equilibrium Value** — bid/offer spreads (spot + forward), triangular arbitrage, forward premium/discount & points, mark-to-market of a forward, **parity conditions** (covered IRP [always holds], uncovered IRP, PPP [absolute/relative], international Fisher), carry trade & risk, BOP/current-account influences, Mundell-Fleming, portfolio balance, FX intervention & capital controls, forecasting
- ☐ **Economic Growth** — preconditions, growth-accounting equation, labor productivity, capital deepening vs TFP, Solow/neoclassical model (steady state, convergence — absolute/conditional/club), classical (Malthusian), endogenous growth, natural resources, effects of trade openness

## 3. Financial Statement Analysis (6 modules · weight 10–15% · plan Days 16–18) ⚠️ WEAK — daily drip from Day 1
- ☐ **LM10 Intercorporate Investments** — FVPL vs FVOCI (financial assets), **equity method** (associates, 20–50%, one-line consol, upstream/downstream profits), **acquisition/consolidation** (control >50%), full vs partial goodwill, non-controlling interest, joint ventures; classic ratio-comparison across methods
- ☐ **LM11 Employee Compensation: Post-Employment & Share-Based** — DB vs DC pensions, PBO roll-forward (service cost, interest cost, actuarial G/L, benefits paid), funded status, **P&L vs OCI split under IFRS vs US GAAP**, net interest, assumption effects (discount rate, comp growth, expected return); share-based comp (options/RSUs, fair value, vesting, dilution)
- ☐ **LM12 Multinational Operations** — local vs functional vs presentation currency; **current-rate method** (all-current, CTA in equity/OCI) vs **temporal method** (monetary/nonmonetary, remeasurement G/L in NI); choosing the method (self-contained vs integrated sub); hyperinflation (IFRS restate vs GAAP temporal); ratio & margin effects
- ☐ **LM13 Analysis of Financial Institutions** — why banks are different; CAMELS framework (Capital adequacy/Basel, Asset quality, Management, Earnings, Liquidity/LCR & NSFR, Sensitivity to market risk); insurers (P&C vs life)
- ☐ **LM14 Evaluating Quality of Financial Reports** — quality spectrum (reporting vs earnings quality), conservative vs aggressive choices, accruals & earnings persistence, **Beneish M-score**, Altman Z, red flags, cash-flow quality
- ☐ **LM15 Integration of FSA Techniques** — screening, ratio decomposition (extended DuPont), earnings normalization, cash-flow analysis, forecasting; putting it all together in a case

## 4. Corporate Issuers (4 modules · weight 5–10% · plan Day 1)
- ☐ **Analysis of Dividends & Share Repurchases** — dividend theories (MM irrelevance, bird-in-hand, tax aversion), signaling, clientele, agency; tax systems (double / split-rate / imputation) & effective-rate math; payout policies (stable/Lintner target-adjustment, constant, residual); buyback methods; **buyback EPS effect (cost of debt vs earnings yield)**; buyback BVPS effect; dividend safety (payout, coverage, FCFE coverage)
- ☐ **ESG Considerations in Investment Analysis** — E/S/G factors, materiality, ESG integration approaches (negative/positive screening, thematic, engagement), effects on credit & equity analysis, green/social bonds
- ☐ **Cost of Capital: Advanced Topics** — WACC drivers (top-down/bottom-up), estimating cost of equity (CAPM, expanded CAPM/build-up, bond-yield-plus-risk-premium), ERP approaches (historical vs forward/Gordon growth vs survey), beta estimation (levered/unlevered, comparable/pure-play, adjusted beta), country risk premium, cost of debt (yield, synthetic rating), flotation costs
- ☐ **Corporate Restructuring** — types (investment/expansion, divestment, restructuring), M&A motivations, forms (merger/acquisition/asset purchase), payment (cash vs stock) & risk sharing, valuation (DCF, comparable company, comparable transaction), synergies, evaluating a deal (accretion/dilution), pre-offer/post-offer defenses, regulatory (HHI)

## 5. Equity Valuation (≈6–7 modules · weight 10–15% · plan Days 2–4)
- ☐ **Equity Valuation: Applications & Processes** — intrinsic value & the "value trap," going-concern vs liquidation, absolute vs relative models, analyst's role, quality of the model
- ☐ **Return Concepts** — required return, expected/holding-period return, ERP (historical/forward), CAPM, multifactor (Fama-French, PSM/build-up), WACC, discount-rate selection, effect of estimation errors
- ☐ **Discounted Dividend Valuation** — DDM one/multi-period, **Gordon growth** (value, implied growth, PVGO), two-stage/H-model/three-stage, sustainable growth (g = b × ROE), spreadsheet modeling, strengths/weaknesses
- ☐ **Free Cash Flow Valuation** — FCFF & FCFE definitions; bridges **from NI, EBIT, EBITDA, CFO**; treatment of WCInv, FCInv, non-cash charges, interest, borrowing; single-stage & two-stage FCFF/FCFE; forecasting; FCFF vs FCFE (when to use each)
- ☐ **Market-Based Valuation: Price & Enterprise Value Multiples** — trailing vs leading, justified vs comparables; **justified P/E, P/B, P/S, P/CF** from fundamentals; EV/EBITDA, EV/Sales; PEG; normalizing earnings; peer/sector; Molodovsky effect; momentum
- ☐ **Residual Income Valuation** — RI = NI − equity charge; **V0 = B0 + PV(RI)**; single-stage & multistage; continuing residual income & persistence factor; **clean-surplus** relation & violations; link to justified P/B; strengths/weaknesses
- ☐ **Private Company Valuation** — value definitions (fair market/investment/intrinsic), income approach (FCF, capitalized cash flow, excess earnings), market approach (GPCM/GTM/prior transactions), asset-based; normalization; CAPM adjustments for private co; **DLOC & DLOM**

## 6. Fixed Income (5 modules · weight 10–15% · plan Days 5–7)
- ☐ **The Term Structure & Interest Rate Dynamics** — spot/par/forward rates & the forward-rate model, bootstrapping, forward pricing/rates, **riding the yield curve**, swap rate curve & swap spread, **Z-spread, TED, Libor-OIS**, term-structure theories (pure/local expectations, liquidity, segmented markets, preferred habitat), key-rate/factor exposures (level/steepness/curvature)
- ☐ **The Arbitrage-Free Valuation Framework** — arbitrage-free pricing, **binomial interest-rate trees** (calibration, backward induction), pathwise valuation, Monte Carlo simulation
- ☐ **Valuation & Analysis of Bonds with Embedded Options** — callable/putable valuation in trees, effect of volatility, **OAS** (vs Z-spread), effective duration & convexity, **one-sided durations**, key-rate durations, convertibles (value, conversion, payback, risk-return)
- ☐ **Credit Analysis Models** — expected exposure, LGD, PD, **credit valuation adjustment (CVA)**, credit scores/ratings, **structural vs reduced-form** models, term structure of credit spreads, credit spread & risk-neutral vs actual PD
- ☐ **Credit Default Swaps** — single-name vs index CDS, mechanics, **upfront premium & coupon**, hazard rate/credit curve, factors driving spread, uses (naked, curve trades, basis trades, LCDX)

## 7. Derivatives (3 modules · weight 5–10% · plan Days 8–9)
- ☐ **LM31 Pricing & Valuation of Forward Commitments** — carry-arbitrage model; **forwards/futures** on equity, fixed income, currency (incl. carry benefits/costs); **FRAs** (price at initiation, value mid-life); **interest-rate swaps** (price fixed rate, value during life); **currency swaps**; **equity swaps** (pay-fixed/pay-return/two-equity)
- ☐ **LM32 Valuing a Derivative Using the One-Period Binomial Model** — no-arbitrage, replication, risk-neutral probabilities, hedge ratio, one- and two-period trees, American vs European early exercise
- ☐ **LM33 Valuation of Contingent Claims** — put-call parity/put-call-forward parity; **BSM model** (assumptions, inputs, interpretation as levered stock/bonds), option Greeks (delta/gamma/theta/vega/rho), delta hedging, implied volatility, options on futures (Black model), interest-rate options/swaptions

## 8. Alternative Investments (4 modules · weight 5–10% · plan Day 10) — ⚠️ 2026: PE reading removed, Hedge Fund Strategies added
- ☐ **Commodities & Commodity Derivatives** — spot vs futures, theories (insurance/hedging pressure, theory of storage, convenience yield), **contango vs backwardation**, futures return = spot + roll + collateral yield, **roll yield**, commodity indexes & weighting/rebalancing
- ☐ **Overview of Types of Real Estate Investment** — equity vs debt, private vs public; property types; valuation — **income approach (direct capitalization: NOI/cap rate; DCF)**, cost approach, sales comparison; cap-rate drivers; risk factors; due diligence
- ☐ **Investments in Real Estate Through Publicly Traded Securities** — REITs vs REOCs; **FFO & AFFO**; NAV/**NAVPS**; valuation (NAV, price-to-FFO/AFFO, DCF/DDM); economic drivers; advantages of public RE
- ☐ **Hedge Fund Strategies** — equity (L/S, market-neutral, activist); event-driven (merger arb, distressed); relative value (fixed-income arb, convertible arb); opportunistic (global macro, managed futures); multi-manager; **conditional risk/return (upside vs downside capture)**, replication, portfolio role

## 9. Portfolio Management (6 modules · weight 10–15% · plan Days 12–13)
- ☐ **Economics & Investment Markets** — discount-rate framework; the risk-free rate, inflation & term premium, credit & equity premiums across the business cycle; valuing assets with the framework
- ☐ **Analysis of Active Portfolio Management** — value added, Sharpe/IR relationships, **information ratio**, **fundamental law of active management (IR = IC × √BR × TC)**, information coefficient, breadth, transfer coefficient, active return decomposition
- ☐ **Exchange-Traded Funds: Mechanics & Applications** — creation/redemption (in-kind, APs), premiums/discounts, tracking error/difference, total cost of ownership, tax efficiency, ETF risks (counterparty, settlement), portfolio applications
- ☐ **Using Multifactor Models** — **APT** & arbitrage; macroeconomic vs fundamental vs statistical factor models; carhart 4-factor; active risk & return attribution (factor vs security selection); factor portfolios; uses (risk budgeting, hedging)
- ☐ **Measuring & Managing Market Risk** — **VaR** (parametric/variance-covariance, historical simulation, Monte Carlo) — strengths/weaknesses; conditional VaR/expected shortfall; incremental/marginal/relative VaR; sensitivities (beta, duration, delta/gamma/vega); scenario & stress tests; constraints (risk budgeting, position/scenario/stop-loss limits)
- ☐ **Backtesting & Simulation** — steps & pitfalls (survivorship, look-ahead, data snooping), rolling-window, historical scenario analysis, Monte Carlo vs historical simulation, sensitivity analysis

## 10. Ethics & Professional Standards (weight 10–15% · plan Day 19) — L2 tests via longer application vignettes
- ☐ **Code of Ethics & the Six Components**
- ☐ **Standards of Professional Conduct I–VII** (Professionalism; Integrity of Capital Markets; Duties to Clients; Duties to Employers; Investment Analysis, Recommendations & Actions; Conflicts of Interest; Responsibilities as a CFA Member/Candidate) — every sub-standard with L2-style application
- ☐ **Application of the Code & Standards: Level II** — the case-based reading; how L2 blurs the "obvious" violation
- ☐ **GIPS overview** (fundamentals, why compliance matters — lighter at L2)

---

## Progress roll-up (update as we go)
| Topic | Modules | Taught | Drilled | Notes |
|---|---|---|---|---|
| Quant | 7 | 0 | 0 | weak — daily drip |
| Economics | 2 | 0 | 0 | |
| FSA | 6 | 0 | 0 | weak — daily drip |
| Corporate Issuers | 4 | 0 | 0 | |
| Equity | 6–7 | 0 | 0 | |
| Fixed Income | 5 | 0 | 0 | |
| Derivatives | 3 | 0 | 0 | |
| Alternatives | 4 | 0 | 0 | 2026: no PE, +HF strategies |
| Portfolio Mgmt | 6 | 0 | 0 | |
| Ethics | ~2 | 0 | 0 | band tiebreaker |
