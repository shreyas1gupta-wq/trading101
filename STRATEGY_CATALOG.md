# Long-Only Swing-Trading Strategy Catalog

**Mandate:** long-only · no options (covered-call overlays "later") · hold a few days to a few
weeks (not intraday, not buy-and-hold) · Indian liquid large/mid-caps (Nifty 50/500) ·
systematic & backtestable · built for an assumed **bear + sideways** 5-year regime.

**Tags:** `[E]` = backed by academic/strong practitioner evidence · `[D]` = derived / proposed
variant to validate. **Every entry is a distinct, codeable rule** (entry → exit, hold).

> The core principle throughout: **mean-reversion is the edge in sideways/high-vol tape; a
> sustained downtrend is hostile to long-only MR (falling-knife), so a regime filter that
> defaults to cash is mandatory.** Reversal pays you for providing liquidity to panic sellers,
> and that payment is largest exactly when fear is high (Nagel 2012).

---

## A. Mean-reversion core & variants (16)

1. **RSI(2) oversold bounce** `[E]` — buy when 2-period RSI < 10 & close > 200-DMA; exit RSI(2) > 70 (2–6 days). *Connors baseline.*
2. **ConnorsRSI composite** `[E]` — ConnorsRSI = avg(RSI(3) of price, RSI(2) of up/down streak, percent-rank of 1-day return); buy < 10, exit > 70.
3. **Cumulative RSI** `[E]` — sum RSI(2) over 2–3 days; buy when cumulative < 35, exit when RSI(2) > 65. Filters one-bar noise.
4. **RSI(2) + TPS scale-in** `[E]` — RSI(2)<25 → 10% slug, add 20/30/40% on each lower close; exit RSI(2)>70. Averages into capitulation.
5. **IBS (Internal Bar Strength)** `[E]` — IBS = (Close−Low)/(High−Low); buy < 0.2, exit > 0.7. Dead simple, strong on indices/ETFs.
6. **Bollinger %b fade** `[E]` — buy when close < lower band (20, 2σ) i.e. %b < 0; exit at the 20-DMA midline.
7. **Distance-from-MA z-score** `[D]` — z = (Close−SMA50)/ATR; buy z < −2.5, exit at z ≈ 0. ATR-normalized → one threshold fits all names.
8. **Ornstein-Uhlenbeck half-life** `[E]` — fit OU, estimate half-life *h*; buy z < −1.5, exit z ≈ 0, **max-hold ≈ 1×h**; skip names with h>15d or h<1d.
9. **Williams %R(10) bounce** `[D]` — buy %R < −90, exit %R > −30. Faster cousin of RSI.
10. **CCI(20) reversion** `[D]` — buy CCI < −150, exit CCI > 0.
11. **Double-7s (index/ETF)** `[E]` — above 200-DMA, buy at a 7-day low, exit at a 7-day high. Connors' ETF staple.
12. **RSI(2) + bullish divergence** `[D]` — require RSI(14) higher-low while price lower-low, plus RSI(2)<10; screens out "still-crashing" names.
13. **Index/ETF mean reversion** `[D]` — run RSI(2)/IBS on Niftybees/index itself (lower idiosyncratic noise than single names).
14. **India-VIX-timed reversion** `[D]` — take oversold entries only when India-VIX > 1.2× its 20-DMA; size up on spikes. Concentrates trades on high-payoff days.
15. **Gap-down reclaim** `[D]` — after an oversized down-gap, buy when the gap-day's high is reclaimed; target the gap fill, time-stop 5d.
16. **Ensemble / voting MR** `[D]` — enter only when ≥2 of {RSI2, IBS, %b, z-score} agree. Diversifies away each indicator's false signals → higher win-rate.

## B. Risk / regime / portfolio overlays (13) — *the consistency layer*

17. **200-DMA market gate** `[E]` — enable MR only when the index is below/around its 200-DMA (sideways/down = MR's home). *(Implemented in `swing_backtest.py`.)*
18. **Breadth washout gate** `[D]` — deploy aggressively when % of universe above 50-DMA < 20% (capitulation); throttle when > 80%.
19. **ADX(14) range filter** `[D]` — take MR only when ADX < 25 (non-trending). Avoids fighting strong trends.
20. **Vol throttle** `[E]` — scale gross exposure inversely to realized vol / India-VIX. Auto-de-risks into selloffs (Moreira–Muir logic).
21. **Volatility targeting** `[E]` — size each position to a constant risk (target_vol / realized_vol). Biggest single drawdown reducer.
22. **ATR position sizing** `[D]` — risk a fixed % of equity per trade via an ATR-based stop distance. Equal *risk*, not equal *rupees*.
23. **Fractional-Kelly sizing** `[D]` — size by ½-Kelly on the measured per-trade edge; caps blow-up risk vs full Kelly.
24. **Equity-curve trading** `[D]` — pause new entries when the strategy's own equity < its 20-day MA. Stops trading a temporarily-dead edge.
25. **Crash-brake** `[D]` — cut gross to ~30% when index 10-day return < −8%. Avoids knife-catching in waterfalls. *(Implemented.)*
26. **Position & sector caps** `[D]` — ≤ 8–10 names, ≤ 2 per sector. Stops the book becoming one correlated "everything-oversold" bet.
27. **Signal-stacking portfolio** `[D]` — blend uncorrelated sleeves (MR + event + rel-strength) at fixed risk budgets; smoother aggregate curve.
28. **Time-stop overlay** `[D]` — force exit after N days regardless of signal. Caps the tail loss on names that never revert.
29. **Hurst-exponent detector** `[D]` — compute rolling Hurst; enable MR when H < 0.5 (mean-reverting regime), stand down when H > 0.5 (trending).

## C. Event-driven & seasonal (13)

30. **PEAD (long-only)** `[E]` — buy top-decile earnings-surprise names, hold 20–40 days (Bernard–Thomas). Works better in non-bear tape; pair with regime gate.
31. **Earnings-gap reversal** `[D]` — in quality names, buy day-2 reclaim of a large *down*-gap on results; exit at gap fill. (Opposite of PEAD; suits choppy tape.)
32. **Pre-earnings drift** `[D]` — enter ~10 days before results in names with rising revisions; **exit the day before** the print (sidesteps the binary event — good for a no-options book).
33. **Estimate-revision momentum** `[E]` — buy on analyst upgrades / upward EPS revisions; hold 1–4 weeks.
34. **Buyback / insider-buy follow** `[E]` — enter on buyback announcement or promoter open-market buying; hold weeks.
35. **Index reconstitution** `[E]` — buy Nifty/Sensex *additions* a few days before the effective date; exit on/after inclusion (front-runs passive flows).
36. **F&O ban-list exit bounce** `[D]` — *India-specific*: over-shorted stocks exiting the NSE F&O ban often pop in cash; buy on ban-exit, hold 2–5 days.
37. **Bulk/block-deal follow** `[D]` — enter alongside disclosed smart-money block deals; hold days–weeks. Verify with backtest.
38. **Turn-of-the-month** `[E]` — buy last trading day, hold first 3–4 days of the new month; flows-driven seasonal.
39. **Expiry-week effect** `[D]` — exploit monthly F&O-expiry-week drift/reversion in the cash underlyings (India-specific).
40. **Post-ex-date reversion** `[D]` — buy quality names oversold immediately after the ex-dividend drop; short hold.
41. **Demerger/spinoff drift** `[E]` — buy the spun-off entity post-listing (documented under-pricing/drift); hold weeks.
42. **Results-season sector seasonality** `[D]` — pre-position in sectors with historically strong post-results seasonal windows.

## D. Cross-sectional / relative-strength (12)

43. **XS 5-day reversal** `[E]` — weekly, buy the bottom-decile 5-day losers, vol-weighted, regime-gated. *(Implemented — flagship.)*
44. **1-month reversal (long-only)** `[E]` — buy bottom-decile trailing-1-month names, hold ~1 month (Jegadeesh 1990; Lehmann 1990).
45. **Residual/idiosyncratic momentum** `[E]` — rank by momentum of factor *residuals*; crashes far less than raw momentum in bears (Blitz et al).
46. **Short-window relative strength** `[E]` — buy top-decile 1–4-week winners; rebalance weekly. *Flag: momentum-crash risk in bear turns.*
47. **Low-beta / low-vol tilt** `[E]` — rotate the swing universe to the lowest-beta quintile in confirmed downtrends (Baker–Bradley–Wurgler; Frazzini–Pedersen).
48. **Quality-minus-junk tilt** `[E]` — restrict longs to high-quality (profitable, low-leverage, stable) names; they bleed less (Asness–Frazzini–Pedersen).
49. **Defensive sector rotation** `[D]` — rotate into the strongest of staples/utilities/healthcare/IT by 1-month relative strength.
50. **Long-only cointegration pairs** `[E]` — for a cointegrated pair, buy *only the lagging leg* when the spread is stretched (Avellaneda–Lee, adapted to no-short).
51. **Reversal-within-strong-sector** `[D]` — apply XS reversal only inside the top relative-strength sectors (combines defense + bounce).
52. **Dispersion-gated reversal** `[D]` — take XS reversal only when cross-sectional return dispersion is high (more to revert).
53. **Beta rotation** `[D]` — rotate toward low-beta in down regimes, mid-beta in sideways, by regime signal.
54. **52-week-range rank bounce** `[D]` — buy *quality* names trading near 52-week lows that show a reclaim; careful — value-trap risk.

## E. Price-action / microstructure (12)

55. **Gap-down fade / gap-fill** `[D]` — buy an oversized down-gap (e.g. > −3% in a large-cap) at next open; target prior close, time-stop 3–5d.
56. **Failed-breakdown / Wyckoff spring** `[D]` — price breaks multi-week support then reclaims within 1–3 bars on volume → buy reclaim, stop below spring low. High R:R, built-in knife filter.
57. **Range / support bounce** `[D]` — in an established range, buy near the lower bound, exit near the midpoint/upper bound.
58. **Selling-climax reversal** `[D]` — down-day with volume > 2× 20-day avg and a long lower wick (close in top third) → buy next open, exit at 5-DMA.
59. **Multi-day VWAP reversion** `[D]` — buy when price is > N% below its anchored (weekly/monthly) VWAP; exit on reversion to VWAP.
60. **Bollinger squeeze → expansion** `[D]` — band-width at 6-month low, then first close outside the band with a higher low → ride the expansion (one of the few setups that works *out of* sideways).
61. **Pullback-to-rising-MA** `[D]` — in a micro-uptrend (above rising 20-DMA), buy the 20-DMA touch; exit on new swing high.
62. **Candlestick reversal + confirmation** `[D]` — hammer / bullish-engulfing at a support level, confirmed by next-bar strength and volume.
63. **Inside-day / NR7 expansion** `[E]`-practitioner — buy the upside break of a narrowest-range-of-7 contraction (Crabel), regime-filtered.
64. **N-down-days reversal** `[D]` — buy after 3–4 consecutive down closes in a large-cap above its 50-DMA; exit on first up-close cluster.
65. **Double-bottom / higher-low** `[D]` — buy confirmed higher-low or double-bottom structure; stop under the pattern low.
66. **Opening-range failure fade** `[D]` — fade a failed early breakout (gap-and-fail) back into the prior range; multi-day hold.

---

## Cross-cutting improvements & combinations (the "consistency stack")

Stack these onto any A/C/D/E entry — each is a documented or logical drawdown-reducer:

```
Regime gate (200-DMA / breadth / ADX)  →  Ensemble entry (≥2 signals agree)
   →  Vol-targeted or ATR sizing  →  Time-stop + hard stop
   →  Position & sector caps  →  Equity-curve circuit-breaker  →  cash as default
```

A bare RSI(2) and the *same* system wrapped in this stack are night-and-day on max-drawdown
and Sharpe. The entries find the edge; the stack makes it **consistent** — which is the
stated goal. The single highest-leverage additions: (a) a **regime gate** (kills the
falling-knife losses), (b) **vol-targeting** (smooths the equity curve), (c) **lower
turnover** (India frictions + 20% STCG punish churn the hardest).

## Already coded vs. next to implement

- **Implemented** in `swing_backtest.py`: #43 (XS reversal), #1/#4 (RSI-2), #17/#25 regime gate + crash-brake, vol-weighting, full India cost/STCG model.
- **Best next builds** (highest expected value, easy in pandas): #8 OU half-life, #45 residual momentum, #36 F&O ban-exit (genuine India edge), #56 failed-breakdown, #16 ensemble MR, #21 vol-targeting overlay.

## Honest caveats — what probably *won't* work long-only in a real bear

- A **sustained** downtrend forces the regime gate to sit you in **mostly cash** — accept low exposure; that *is* correct bear behavior, not a bug.
- Mean reversion has **negative skew**: many small wins, occasional ugly losses (you're long exactly when gaps-down hit). Stops + vol-targeting manage it; nothing removes it without options.
- **Published edges decay** (Connors et al. are crowded). Fresher edge lives in the India-specific quirks (#36 F&O ban, #35 reconstitution, #39 expiry) and in the *combinations*, not the textbook signals.
- **Net-of-cost only.** STT + slippage on panic fills + 20% STCG routinely halve gross edges. Backtest with frictions on (the harness already does).

## Status of the web/social/paper-sourced layer

The 3 alpha-scout agents (X.com/FinTwit, quant blogs/backtests, India platforms) and 2
research-paper agents **did not run** — the org hit its monthly spend limit, so those
externally-sourced strategies and citations are not yet collected. Relaunch the saved
`swing-alpha-hunt` workflow once the limit is raised (`/usage-credits`) to add that layer
with live URLs and paper citations. Everything above is generated from model knowledge
(canonical references named where applicable), not freshly web-verified.
