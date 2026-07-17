# CFA L2 Master Formula Sheet

Starter sheet — the highest-yield formulas per topic, seeded in advance. As we teach each day, we append worked examples, calculator keystrokes, and any formula not yet listed. Notation: r = required return, g = growth, b = retention ratio, t = tax rate.

---

## Corporate Issuers
- **Effective tax, double taxation:** `t_corp + (1 − t_corp) × t_individual`
- **Effective tax, imputation:** = investor's marginal tax rate (corporate tax credited back)
- **Target payout adjustment (Lintner):** `Expected div = Prev div + (Expected ΔEPS × target payout × adj factor)`, adj factor = 1/(# years to adjust)
- **Residual dividend:** `Div = Net income − (Capital budget × equity weight)`
- **Buyback EPS rule (debt-funded):** EPS ↑ if **after-tax cost of debt < earnings yield (E/P)**; ↓ if >
- **Buyback BVPS rule:** BVPS ↓ if repurchase price > BVPS; ↑ if <
- **FCFE coverage:** `FCFE / (Dividends + Share repurchases)` (<1 = unsustainable)
- **Sustainable growth:** `g = b × ROE`

## Equity
- **Gordon growth (GGM):** `V0 = D1/(r − g)`; implied `r = D1/P0 + g`
- **PVGO:** `V0 = E1/r + PVGO`
- **H-model:** `V0 = [D0(1+gL) + D0·H·(gS − gL)] / (r − gL)`, H = half the high-growth years
- **Justified leading P/E:** `(1 − b)/(r − g)` · **trailing P/E:** `(1 − b)(1 + g)/(r − g)`
- **Justified P/B:** `(ROE − g)/(r − g)` · **Justified P/S:** `(E0/S0)(1 − b)(1 + g)/(r − g)`
- **FCFF bridges:**
  - `FCFF = NI + NCC + Int(1 − t) − FCInv − WCInv`
  - `FCFF = CFO + Int(1 − t) − FCInv`
  - `FCFF = EBIT(1 − t) + Dep − FCInv − WCInv`
  - `FCFF = EBITDA(1 − t) + Dep·t − FCInv − WCInv`
- **FCFE bridges:** `FCFE = FCFF − Int(1 − t) + Net borrowing` = `NI + NCC − FCInv − WCInv + Net borrowing`
- **Values:** Firm `= FCFF/(WACC − g)`; Equity `= FCFE/(r − g)`
- **Residual income:** `RI = NIt − r·Bt−1 = (ROE − r)·Bt−1`; `V0 = B0 + Σ PV(RI)`; single-stage `V0 = B0 + (ROE − r)/(r − g) · B0`

## Fixed Income
- **Forward-rate model:** `[1 + z(A+B)]^(A+B) = (1 + zA)^A · [1 + f(A,B)]^B`
- **Spread relations:** `OAS = Z-spread − option cost` (callable: option cost > 0; putable: < 0)
- **Embedded options:** `V_callable = V_straight − V_call`; `V_putable = V_straight + V_put`
- **Effective duration:** `(PV₋ − PV₊)/(2 · PV0 · Δcurve)` · **Effective convexity:** `(PV₋ + PV₊ − 2·PV0)/(PV0 · Δcurve²)`
- **Credit:** `Expected loss = PD × LGD`; `LGD = exposure × (1 − recovery)`; CVA = PV of expected credit losses
- **CDS (approx):** `Upfront ≈ (CDS spread − coupon) × EffSpreadDuration`; `Price per 100 ≈ 100 − upfront%`; profit ≈ Δspread × duration × notional

## Derivatives
- **Forward price:** `F0 = S0(1 + r)^T`; with carry `F0 = [S0 − PV(income) + PV(cost)](1 + r)^T`
- **Swap fixed rate:** `= (1 − final discount factor) / (Σ discount factors)`
- **Binomial:** risk-neutral `π = (1 + r − d)/(u − d)`; `c = [π·c⁺ + (1−π)·c⁻]/(1 + r)`; hedge ratio `h = (c⁺ − c⁻)/(S⁺ − S⁻)`
- **Put-call parity:** `S + p = c + X/(1+r)^T` · **put-call-forward parity:** `F0/(1+r)^T + p = c + X/(1+r)^T`
- **BSM call:** `c = S·N(d1) − X·e^(−rT)·N(d2)`; interpret as levered long stock (N(d1) shares, borrow X·e^-rT·N(d2))

## Alternatives
- **Commodity futures total return:** `spot return + roll return + collateral return`; roll return **positive in backwardation**, negative in contango
- **Direct capitalization:** `Value = NOI / cap rate`; `cap rate = discount rate − growth`
- **RE terminal value:** `NOI(n+1) / terminal cap rate`
- **REIT:** `FFO = NI + Depreciation − Gains on sale (+ Losses)`; `AFFO = FFO − maintenance capex − straight-line rent adj`
- **NAVPS:** `(Market value of assets − liabilities) / shares`
- **Hedge fund fees:** "2 and 20" (mgmt on AUM, incentive on profit), with hurdle rate & high-water mark

## Economics
- **Forward points:** `Forward − Spot` (scaled); base-currency forward premium if F > S
- **Covered IRP (holds):** `F(d/f) = S(d/f) · (1 + r_d)/(1 + r_f)`; forward premium ≈ `r_d − r_f`
- **Uncovered IRP:** `E(%ΔS_d/f) ≈ r_d − r_f`
- **Relative PPP:** `E(%ΔS_d/f) ≈ inflation_d − inflation_f`
- **International Fisher:** `r_d − r_f ≈ E(inflation_d) − E(inflation_f)`
- **Growth accounting (Cobb-Douglas Y = A·K^α·L^(1−α)):** `ΔY/Y = ΔA/A + α(ΔK/K) + (1−α)(ΔL/L)`
- **Potential GDP growth** = growth in labor force + growth in labor productivity

## Portfolio Management
- **APT:** `E(Rp) = Rf + Σ βp,j · λj`
- **Information ratio:** `IR = (Rp − Rb)/σ(Rp − Rb)` = active return / active risk
- **Fundamental law:** `IR = IC · √BR · TC`; `E(active return) = IC · √BR · TC · σ_active`
- **Sharpe–IR link:** `SR_p² = SR_b² + IR²`
- **Parametric VaR:** `VaR = (−μ + z·σ) × portfolio value` over the period (z = 1.65 at 95%, 2.33 at 99%)
- **Value added:** `Rp − Rb`

## Quant
- **R²:** `SSR/SST = 1 − SSE/SST` · **Adjusted R²:** `1 − [(n−1)/(n−k−1)](1 − R²)`
- **F-stat:** `(SSR/k)/(SSE/(n−k−1)) = MSR/MSE` · **SEE:** `√MSE`
- **t-stat coefficient:** `(b̂ − b)/SE(b̂)`, df = n − k − 1
- **Durbin-Watson:** `≈ 2(1 − r)` (r = residual autocorrelation; ~2 = none)
- **Multicollinearity:** `VIF_j = 1/(1 − R²_j)` (>5 caution, >10 serious)
- **AR mean-reverting level:** `b0/(1 − b1)`; covariance-stationary requires |b1| < 1
- **Log-linear trend:** `ln(yt) = b0 + b1·t`
- **Classification metrics:** `Precision = TP/(TP+FP)`, `Recall = TP/(TP+FN)`, `F1 = 2·P·R/(P+R)`, `Accuracy = (TP+TN)/total`

## FSA
- **Equity method:** `Investment = Cost + %·(Investee NI) − %·(Dividends received)`
- **Goodwill:** Full `= Fair value of entity − FV of net identifiable assets`; Partial `= Price paid − %·(FV net identifiable assets)`
- **Pension funded status:** `Plan assets − PBO` (asset if +, liability if −)
- **Total periodic pension cost:** `= Employer contributions − Δ(funded status)` = service + interest + past service − actual return + actuarial losses − gains
- **Translation — current-rate method:** all assets/liabilities at current rate; equity at historical; income at average; **CTA in OCI/equity**
- **Translation — temporal method:** monetary items at current rate, nonmonetary at historical; **remeasurement gain/loss in net income**
- **Quality flags:** Beneish M-score (8 vars — probability of manipulation), Altman Z (bankruptcy), accruals ratio (lower = higher quality)

---

## Worked examples & calculator keystrokes
_(appended as each day is taught — Day 1 Corporate Issuers examples go here first)_
