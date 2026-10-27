"""Build the Ionic Yield Enhancer data library: HTML page (charts + register) and Excel workbook.

Single source of truth for every data point and chart used by marketing.
Run: python3 build.py   (then render.js turns the page's chart frames into PNGs)
"""
import json
import math
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
AS_OF = "27 Oct 2026"

SRC = {
    "samco": ("Samco", "https://www.samco.in/knowledge-center/articles/nifty-gains-10-51-and-nifty-bank-rises-17-15-in-calendar-year-2025/"),
    "ziro": ("Ziromarket", "https://www.ziromarket.com/blog/nifty-50-2026-bear-phase-what-happened"),
    "mb_h1": ("Multibagg", "https://www.multibagg.ai/market-pulse/articles/nifty-50-h1-2026-outlook-cmr1v2pjcmd7wo20je21na6yz"),
    "outlook": ("Outlook Money", "https://www.outlookmoney.com/invest/nifty-september-derivatives-series-2026-fall-worst-in-25-years"),
    "sky_close": ("HDFC Sky", "https://hdfcsky.com/news/market-close-report-today-october-26-2026-sensex-nifty-rise-as-markets-snap-four-day-losing-streak"),
    "sky_vix": ("HDFC Sky", "https://hdfcsky.com/news/india-vix-rises-nifty-falls-crude-oil-global-markets-october-26-2026"),
    "macro_vix": ("Macrotrends", "https://www.macrotrends.net/2603/vix-volatility-index-historical-chart"),
    "5paisa": ("5paisa", "https://www.5paisa.com/blog/small-caps-outperform-nifty-50-by-24-percentage-points-in-february-september-2026"),
    "bs_fpi": ("Business Standard", "https://www.business-standard.com/markets/news/record-fpi-outflows-top-3-trillion-in-cy26-nearly-double-2025-tally-126101300072_1.html"),
    "statesman": ("The Statesman", "https://www.thestatesman.com/business/fpis-pull-record-rs-3-08-lakh-crore-from-indian-equities-in-2026-nearly-double-2025-outflows-1503650699.html"),
    "mb_mar": ("Multibagg", "https://www.multibagg.ai/market-pulse/articles/fii-record-outflow-march-2026-cmo9q04v6ugd2ph0j3z3orgsm"),
    "rupeecase": ("Rupeecase (NSE data)", "https://www.rupeecase.com/guides/nifty-pe-ratio"),
    "pe_mc150": ("indexpe.in", "https://indexpe.in/nifty-midcap-150"),
    "pe_mc100": ("indexpe.in", "https://indexpe.in/nifty-midcap-100"),
    "pe_ms400": ("indexpe.in", "https://indexpe.in/nifty-midsmallcap-400"),
    "pe_sc250": ("indexpe.in", "https://indexpe.in/nifty-smallcap-250"),
    "pe_sc50": ("indexpe.in", "https://indexpe.in/nifty-smallcap-50"),
    "scc_rbi": ("SCC Online", "https://www.scconline.com/blog/post/2026/10/09/rbi-hikes-repo-rate-to-5-50-percent-october-2026/"),
    "mpc_min": ("Corplaw Updates", "https://www.corplawupdates.in/updates/rbi-mpc-minutes-october-2026-repo-rate-5-50-rate-cuts-off-table"),
    "cpi": ("Econolens", "https://www.econolens.co.in/news/india-cpi-inflation-september-2026-5-54-percent"),
    "finnovate": ("Finnovate", "https://www.finnovate.in/learn/blog/india-cpi-inflation-september-2026"),
    "oilprice": ("Oilprice.com (Reuters)", "https://oilprice.com/Latest-Energy-News/World-News/Indias-Inflation-Likely-Hit-54-in-September-as-Oil-Costs-Bite.html"),
    "te_gsec": ("Trading Economics", "https://tradingeconomics.com/india/government-bond-yield/news/594949"),
    "inv_gsec": ("Investing.com", "https://www.investing.com/rates-bonds/india-10-year-bond-yield-historical-data"),
    "tbill": ("Plutus IAS (RBI auction)", "https://plutusias.com/?p=279438"),
    "absl": ("Aditya Birla Sun Life AMC fixed income tracker (ICRA Analytics / Refinitiv)", "https://mutualfund.adityabirlacapital.com/-/media/knowledgecenter/pdf/all-about-market/daily-fixed-income-tracker-01-oct-2026.pdf"),
    "imi": ("India Macro Indicators", "https://indiamacroindicators.co.in/economic-indicators/10-year-credit-spread-aaa-rated-bonds-g-sec"),
    "upstox": ("Upstox", "https://upstox.com/news/personal-finance/investing/hdfc-bank-icici-bank-punjab-national-bank-bank-of-baroda-fixed-deposit-rates-where-they-stand-after-rbi-october-repo-rate-hike/article-201783/"),
    "wolf": ("Wolf Street", "https://wolfstreet.com/2026/10/17/long-term-treasury-yields-buffeted-by-hot-inflation-and-cracks-in-ai-mania/"),
    "247": ("24/7 Wall St", "https://247wallst.com/investing/2026/10/23/the-10-year-yield-just-fell-below-5-as-investors-fled-ai-stocks/"),
    "bbg": ("Bloomberg", "https://www.bloomberg.com/news/articles/2026-10-23/ai-trade-stumbles-again-as-investors-rediscover-treasury-haven"),
    "cnbc": ("CNBC", "https://www.cnbc.com/2026/10/07/stock-market-today-live-updates-.html"),
    "equentis": ("Equentis", "https://equentis.com/blog/crude-oil-prices-today-brent-falls-below-115-as-us-iran-diplomatic-efforts-raise-hopes-of-de-escalation"),
    "te_brent": ("Trading Economics", "https://tradingeconomics.com/commodity/brent-crude-oil"),
    "motilal": ("Motilal Oswal", "https://www.motilaloswal.com/news/forex/5874"),
    "ionic": ("Ionic calculation", ""),
}

# Nifty 50 calendar-year price returns (approximate). Chain-linked they reproduce the
# index from 6,139 (end-2007) to ~26,105 vs the actual 26,130 close of 2025.
NIFTY_YEARLY = [
    (2008, -51.8), (2009, 75.8), (2010, 17.9), (2011, -24.6), (2012, 27.7), (2013, 6.8),
    (2014, 31.4), (2015, -4.1), (2016, 3.0), (2017, 28.6), (2018, 3.2), (2019, 12.0),
    (2020, 14.9), (2021, 24.1), (2022, 4.3), (2023, 20.0), (2024, 8.8), (2025, 10.5),
]

TAX = 0.312          # 30% slab + 4% cess, surcharge ignored
CPI = 5.54
YE = 11.0
FD = 6.25
AAA1 = 7.48
SAV = 2.7


def post_tax(r):
    return round(r * (1 - TAX), 2)


def double_years(r):
    return round(math.log(2) / math.log(1 + r / 100), 1)


def rolling(n):
    g = [1 + v / 100 for _, v in NIFTY_YEARLY]
    out = []
    for i in range(len(g) - n + 1):
        q = 1.0
        for x in g[i:i + n]:
            q *= x
        out.append(round((q ** (1 / n) - 1) * 100, 1))
    return out


def median(xs):
    s = sorted(xs)
    m = len(s) // 2
    return round(s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2, 1)


ROLL = {}
for n in (1, 3, 5, 7):
    r = rolling(n)
    ROLL[n] = dict(min=min(r), max=max(r), med=median(r), neg=sum(v < 0 for v in r), count=len(r))

# 2026 YTD: Nifty price change and Yield Enhancer at target pro-rated to 26 Oct (298 days)
_n = (22753.2 / 26129.6 - 1) * 100
_y = ((1 + YE / 100) ** (298 / 365) - 1) * 100
NIFTY_YTD = round(_n, 1)
YE_YTD = round(_y, 2)
BLEND = {w: round((1 - w) * _n + w * _y, 1) for w in (0, 0.2, 0.3)}
GAIN18 = {k: round(((1 + r / 100) ** 1.5 - 1) * 100, 1) for k, r in (("sav", SAV), ("fd", FD), ("ye", YE))}

# Data point register -----------------------------------------------------------------
# type: Reported = from news/aggregators, verify at primary before external use
#       Market data = aggregator time series, verify at primary
#       Ionic calculation = derived by us from the inputs named in the note
#       Hypothetical = illustration assuming the 11% target is achieved
#       Assumption = an input we chose
DP = [
    # Equity markets
    ("D01", "Equity markets", "Nifty 50 ended 2025 at 26,129.6, up 10.5% for the year, its 10th straight year of gains.", "+10.5%", "31 Dec 2025", ["samco"], "NSE", "Reported", "Equity-positive context. Use alongside 2026 volatility points for balance."),
    ("D02", "Equity markets", "Nifty 50 hit a record high of 26,373.2 on 5 Jan 2026.", "26,373.2", "5 Jan 2026", ["ziro"], "NSE", "Reported", ""),
    ("D03", "Equity markets", "Nifty 50 fell 15.9% from its record high to 22,182.6 on 2 Apr 2026.", "−15.9%", "2 Apr 2026", ["ziro"], "NSE", "Reported", "Describe as a swing or volatility, not as a verdict on equity."),
    ("D04", "Equity markets", "Nifty 50 closed at 22,753.2 on 26 Oct 2026: −12.9% in 2026 and 13.7% below its January high.", "−12.9% YTD", "26 Oct 2026", ["sky_close"], "NSE", "Reported", "Factual. Pair with D01, D12 or D13 so equity is not shown one-sidedly."),
    ("D05", "Equity markets", "Nifty 50 fell 8.7% in H1 2026, its weakest first half since 2022.", "−8.7%", "30 Jun 2026", ["mb_h1"], "NSE", "Reported", ""),
    ("D06", "Equity markets", "The September 2026 Nifty F&O series settled 5.7% lower (24,090.9 to 22,716.2).", "−5.7%", "29 Sep 2026", ["outlook"], "NSE", "Reported", ""),
    ("D07", "Equity markets", "India VIX rose from 13.47 (24 Dec 2025) to 31.05 (27 Mar 2026), and was 17.41 on 26 Oct 2026.", "13.5 → 31.1 → 17.4", "26 Oct 2026", ["macro_vix", "sky_vix"], "NSE (India VIX)", "Market data", "Sources disagree on the 52-week range; confirm on NSE."),
    ("D08", "Equity markets", "Feb–Sep 2026: Nifty Smallcap 250 TRI +15.95% vs Nifty 50 TRI −8.08%. Returns have varied widely across market segments.", "+15.95% vs −8.08%", "30 Sep 2026", ["5paisa"], "NSE Indices", "Reported", "Shows equity is not uniformly weak. Useful balance for equity-selling teams."),
    # Flows
    ("D09", "Flows", "FPIs sold a record ₹3.08 lakh crore (~$32.7 bn) of Indian equities in Jan–Sep 2026, 1.9× the ₹1.66 lakh crore sold in all of 2025.", "₹3.08 L cr", "30 Sep 2026", ["bs_fpi", "statesman"], "NSDL FPI Monitor", "Reported", "Totals differ slightly by NSDL cut (primary vs secondary market)."),
    ("D10", "Flows", "March 2026 was the worst month on record for FPI equity selling, about ₹1.14–1.18 lakh crore.", "~₹1.14 L cr", "31 Mar 2026", ["mb_mar"], "NSDL FPI Monitor", "Reported", "Figures vary by source; quote as 'over ₹1.1 lakh crore'."),
    ("D11", "Flows", "FPIs sold ₹35,861 crore in September and ₹47,417 crore in 1–12 October 2026.", "₹47,417 cr in 12 days", "12 Oct 2026", ["bs_fpi"], "NSDL FPI Monitor", "Reported", ""),
    ("D12", "Flows", "Domestic institutions (DIIs) bought about ₹6.83 lakh crore of Indian equities in 2026, more than offsetting FPI selling.", "₹6.83 L cr", "12 Oct 2026", ["bs_fpi"], "NSE / NSDL", "Reported", "Equity-positive: domestic investors are supporting the market."),
    # Valuations
    ("D13", "Valuations", "Nifty 50 P/E was 19.12 on 12 Oct 2026, below its median of 22.14 since March 2021 (range 18.92–33.61).", "19.1× vs 22.1×", "12 Oct 2026", ["rupeecase"], "NSE", "Market data", "Equity-positive: large caps are cheaper than their recent history."),
    ("D14", "Valuations", "Nifty Midcap 150 P/E 27.03 vs 5-yr median 29.56 (−9%); Midcap 100 26.63 vs 29.65 (−10%).", "−9% / −10% vs median", "22 Oct 2026", ["pe_mc150", "pe_mc100"], "NSE", "Market data", "Equity-positive."),
    ("D15", "Valuations", "Nifty Smallcap 250 P/E 32.10 vs 5-yr median 28.31 (+13%); Smallcap 50 35.34 vs 28.18 (+25%).", "+13% / +25% vs median", "22 Oct 2026", ["pe_sc250", "pe_sc50"], "NSE", "Market data", "Internal context. Avoid in external material if Ionic is promoting smallcap strategies."),
    # Rates & inflation
    ("D16", "Rates & inflation", "RBI raised the repo rate by 25 bps to 5.50% on 7 Oct 2026, its first hike since Feb 2023 (6–0 vote). SDF 5.25%, MSF 5.75%.", "5.50%", "7 Oct 2026", ["scc_rbi"], "RBI press release", "Reported", ""),
    ("D17", "Rates & inflation", "MPC minutes (21 Oct 2026) signal rate cuts are off the table for now. Next MPC meeting: 2–4 Dec 2026.", "Cuts off the table", "21 Oct 2026", ["mpc_min"], "RBI MPC minutes", "Reported", ""),
    ("D18", "Rates & inflation", "CPI inflation rose to 5.54% in Sep 2026 from 4.83% (Aug) and 4.45% (Jul); food inflation 7.74%. Highest since Oct 2024.", "5.54%", "Sep 2026", ["cpi", "finnovate"], "MoSPI / NSO", "Reported", ""),
    ("D19", "Rates & inflation", "WPI inflation was 11.4% in Sep 2026, driven by energy and freight costs.", "11.4%", "Sep 2026", ["oilprice"], "Office of the Economic Adviser (DPIIT)", "Reported", "Verify; single secondary source."),
    ("D20", "Rates & inflation", "India 10-yr G-Sec yield was 7.465% on 23 Oct 2026, the highest since March 2023, up ~99 bps from its 52-week low of 6.476%.", "7.47%", "23 Oct 2026", ["te_gsec", "inv_gsec"], "FBIL / CCIL", "Market data", ""),
    ("D21", "Rates & inflation", "364-day T-bill cut-off yield was 6.29% at the 7 Oct 2026 RBI auction (91-day 5.57%, 182-day 6.10%).", "6.29%", "7 Oct 2026", ["tbill"], "RBI auction results", "Reported", "Single secondary source; confirm on RBI website."),
    ("D22", "Rates & inflation", "AAA corporate bond yields on 30 Sep 2026: 1-yr 7.48%, 3-yr 7.70%, 5-yr 7.78%, 10-yr 7.83%. 3-yr AAA was 7.45% a month earlier.", "1-yr AAA 7.48%", "30 Sep 2026", ["absl"], "FIMMDA / FBIL corporate bond valuation", "Market data", "Seen via search summary of the tracker; confirm the PDF."),
    ("D23", "Rates & inflation", "The 10-yr AAA corporate bond spread over the G-Sec was 0.53% on 9 Oct 2026.", "0.53%", "9 Oct 2026", ["imi"], "FIMMDA", "Market data", ""),
    ("D24", "Rates & inflation", "1-year fixed deposit rates for the general public at SBI, HDFC Bank and ICICI Bank are 6.25%.", "6.25%", "Oct 2026", ["upstox"], "Bank rate cards", "Reported", "Some sources show HDFC at 6.60%; check rate cards on the day."),
    ("D25", "Rates & inflation", "Savings account rate assumed at 2.7% for comparisons.", "2.7%", "—", ["ionic"], "Bank rate cards", "Assumption", "Typical large-bank savings rate; adjust if needed."),
    # Global
    ("D26", "Global", "US 10-yr Treasury yield peaked at 5.36% on 7 Oct 2026, its highest since April 2002.", "5.36%", "7 Oct 2026", ["wolf"], "US Treasury", "Reported", ""),
    ("D27", "Global", "The US 10-yr yield fell 19 bps to ~4.95% on 22 Oct as investors moved out of AI stocks into Treasuries.", "−19 bps", "22 Oct 2026", ["247", "bbg"], "US Treasury", "Reported", ""),
    ("D28", "Global", "The Nasdaq-100 had its worst two-week drop since April 2025 (to 23 Oct 2026) as investors questioned AI revenue and spending.", "Worst 2 weeks since Apr 2025", "23 Oct 2026", ["bbg", "cnbc"], "Nasdaq", "Reported", ""),
    ("D29", "Global", "Brent crude was about $115 a barrel on 27 Oct 2026, amid US–Iran tensions.", "~$115", "27 Oct 2026", ["equentis", "te_brent"], "ICE Brent", "Market data", "Intraday quotes vary $110–116."),
    ("D30", "Global", "The rupee hit a record low near ₹94 per dollar in March 2026 amid high crude prices and FPI selling.", "~₹94/$", "Mar 2026", ["motilal"], "RBI reference rate / FBIL", "Reported", "Sources differ (93.8–94.8); quote as 'around ₹94'."),
    ("D31", "Global", "Markets price roughly 78% odds of a US Fed rate hike in December 2026; FOMC met 27–28 Oct.", "~78%", "Oct 2026", ["wolf"], "CME FedWatch", "Reported", ""),
    # Ionic calculations
    ("D32", "Returns math", f"A 6.25% FD keeps {post_tax(FD)}% after 30% slab tax + cess; after 5.54% CPI the real return is {round(post_tax(FD) - CPI, 2)}%.", f"{round(post_tax(FD) - CPI, 2)}%", AS_OF, ["ionic"], "—", "Ionic calculation", "6.25 × (1 − 0.312) − 5.54. Surcharge ignored."),
    ("D33", "Returns math", f"A 1-yr AAA bond at 7.48% keeps {post_tax(AAA1)}% after tax; real return {round(post_tax(AAA1) - CPI, 2)}%.", f"{round(post_tax(AAA1) - CPI, 2)}%", AS_OF, ["ionic"], "—", "Ionic calculation", ""),
    ("D34", "Returns math", f"At the 11% target, Yield Enhancer would keep {post_tax(YE)}% after tax; real return +{round(post_tax(YE) - CPI, 2)}%.", f"+{round(post_tax(YE) - CPI, 2)}%", AS_OF, ["ionic"], "—", "Hypothetical", "Target, not assured."),
    ("D35", "Returns math", f"On ₹1 crore, 11% vs a 6.25% FD is ₹4.75 lakh more a year pre-tax and ₹{round((post_tax(YE) - post_tax(FD)), 2)} lakh more after tax.", "₹3.27 L / yr", AS_OF, ["ionic"], "—", "Hypothetical", "Interest from bonds and FDs is taxed at slab rates."),
    ("D36", "Returns math", f"Years for money to double after tax: Yield Enhancer at 11% target {double_years(post_tax(YE))}; 1-yr AAA {double_years(post_tax(AAA1))}; FD {double_years(post_tax(FD))}; savings {double_years(post_tax(SAV))}.", f"{double_years(post_tax(YE))} vs {double_years(post_tax(FD))} yrs", AS_OF, ["ionic"], "—", "Hypothetical", ""),
    ("D37", "Returns math", f"The 11% target is {round(YE - AAA1, 2)} points above the 1-yr AAA corporate yield and {round(YE - FD, 2)} points above a 1-yr FD.", f"+{round(YE - AAA1, 2)} pts", AS_OF, ["ionic", "absl"], "—", "Ionic calculation", "Describe as the premium for credit and liquidity risk."),
    ("D38", "Returns math", "If interest rates rise 1%, a 1.25-yr duration portfolio loses ~1.25% in price vs ~6.8% for a 10-yr G-Sec; recovered in ~1.4 vs ~11 months of carry.", "−1.25% vs −6.8%", AS_OF, ["ionic"], "—", "Ionic calculation", "Price change ≈ −duration × change in yield. Category durations indicative."),
    ("D39", "Returns math", f"₹1 crore over 18 months (pre-tax): savings +₹{GAIN18['sav']} L, FD +₹{GAIN18['fd']} L, Yield Enhancer at 11% target +₹{GAIN18['ye']} L.", f"+₹{GAIN18['ye']} L", AS_OF, ["ionic"], "—", "Hypothetical", ""),
    ("D40", "Returns math", "Every month in a savings account instead of an 11% target forgoes about ₹69,000 per ₹1 crore (pre-tax).", "₹69,167 / month", AS_OF, ["ionic"], "—", "Hypothetical", "(11% − 2.7%) ÷ 12 × ₹1 crore."),
    ("D41", "Equity horizon", f"Nifty 50 1-year returns since 2008 ranged from {ROLL[1]['min']}% to +{ROLL[1]['max']}% (price).", f"{ROLL[1]['min']}% to +{ROLL[1]['max']}%", "2008–2025", ["ionic"], "NSE index data", "Ionic calculation", "Built from approximate calendar-year price returns; verify with NSE TRI."),
    ("D42", "Equity horizon", f"Over every 7-year period since 2008, Nifty 50 returned +{ROLL[7]['min']}% to +{ROLL[7]['max']}% a year, with none negative; median {ROLL[7]['med']}% (price only; dividends add ~1–1.5 pts).", f"+{ROLL[7]['min']}% to +{ROLL[7]['max']}%", "2008–2025", ["ionic"], "NSE index data", "Ionic calculation", "Equity-positive: supports long-term equity."),
    ("D43", "Equity horizon", f"2026 to date (hypothetical): 100% equity {BLEND[0]}%; with a 20% Yield Enhancer sleeve {BLEND[0.2]}%; with 30% {BLEND[0.3]}%.", f"{BLEND[0]}% → {BLEND[0.3]}%", "26 Oct 2026", ["ionic", "sky_close"], "—", "Hypothetical", "Assumes 11% target pro-rated to 26 Oct; simple weighted blend."),
    ("D44", "Tax", "Since 1 Apr 2023, gains on debt mutual funds are taxed at slab rates, and interest from bonds and FDs is always taxed at slab rates.", "Slab rate", "Finance Act 2023", ["ionic"], "Income Tax Act (Sec 50AA)", "Reported", "Capital gains on listed bonds held >12 months are taxed differently; consult a tax advisor."),
]

# Chart specs ------------------------------------------------------------------------
pe = [("Nifty 50", 19.12, 22.14), ("Midcap 100", 26.63, 29.65), ("Midcap 150", 27.03, 29.56),
      ("MidSmallcap 400", 27.92, 30.09), ("Smallcap 250", 32.10, 28.31), ("Smallcap 50", 35.34, 28.18)]

CHARTS = [
    dict(id="C01", file="C01-nifty-2026-path", dp=["D01", "D02", "D03", "D04"], type="line",
         title="Nifty 50 in 2026: a 16% swing from peak to trough",
         sub="Record high on 5 January, low on 2 April, partial recovery since",
         source="NSE closing levels via Samco, Ziromarket, Multibagg, Outlook Money, HDFC Sky. Mid-June level approximate.",
         asof="26 Oct 2026",
         pts=[[0, 26129.6], [5, 26373.2], [92, 22182.55], [166, 23632], [239, 24090.85], [272, 22716.2], [299, 22753.2]]),
    dict(id="C02", file="C02-india-vix", dp=["D07"], type="vbar",
         title="India VIX more than doubled in 2026 before easing",
         sub="The market's expected-volatility gauge, at three points in time",
         source="NSE India VIX via Macrotrends and HDFC Sky.", asof="26 Oct 2026",
         min=0, max=36, ticks=[0, 10, 20, 30], dec=2, unit="",
         data=[["24 Dec 2025 (low)", 13.47, "mute"], ["27 Mar 2026 (peak)", 31.05, "bad"], ["26 Oct 2026", 17.41, "warn"]]),
    dict(id="C03", file="C03-fpi-dii-flows", dp=["D09", "D12"], type="vbar",
         title="Foreign investors sold a record amount; domestic investors bought more",
         sub="Net investment in Indian equities, ₹ lakh crore",
         source="NSDL / NSE data via Business Standard and The Statesman.", asof="12 Oct 2026",
         min=-4, max=8, ticks=[-4, -2, 0, 2, 4, 6, 8], dec=2, unit="", prefix="₹", suffix=" L cr",
         data=[["FPI, all of 2025", -1.66, "mute"], ["FPI, Jan–Sep 2026", -3.08, "bad"], ["DII, 2026 to date", 6.83, "good"]]),
    dict(id="C04", file="C04-cpi-vs-fd", dp=["D18", "D24"], type="vbar",
         title="Inflation has risen three months in a row",
         sub="CPI inflation vs the 1-year bank FD rate",
         source="CPI: NSO via Econolens / Finnovate. FD: SBI, HDFC Bank, ICICI Bank via Upstox.", asof="Sep 2026",
         min=0, max=7.5, ticks=[0, 2, 4, 6], dec=2, unit="%",
         data=[["Jul 2026 CPI", 4.45, "mute"], ["Aug 2026 CPI", 4.83, "mute"], ["Sep 2026 CPI", 5.54, "bad"]],
         refs=[[6.25, "1-yr bank FD 6.25%", "brand"]]),
    dict(id="C05", file="C05-rates-turned-up", dp=["D16", "D18", "D20", "D22"], type="dumbbell",
         title="Interest rates and inflation have turned up",
         sub="Earlier reading (grey) vs latest reading (blue), %",
         source="RBI; NSO; ICRA Analytics / Refinitiv via ABSL tracker; Trading Economics, Investing.com.", asof="23 Oct 2026",
         min=4, max=8, ticks=[4, 5, 6, 7, 8],
         rows=[["RBI repo rate", 5.25, "before 7 Oct", 5.50, "now"],
               ["CPI inflation", 4.45, "Jul", 5.54, "Sep"],
               ["3-yr AAA corporate yield", 7.45, "end-Aug", 7.70, "30 Sep"],
               ["10-yr G-Sec yield", 6.48, "52-wk low", 7.47, "23 Oct"]]),
    dict(id="C06", file="C06-short-term-yield-ladder", dp=["D21", "D22", "D24", "D25", "D37"], type="vbar",
         title="Where an 11% target sits among short-term rates",
         sub="About 3.5 points above 1-yr AAA corporate bonds: the premium for credit and liquidity risk",
         source="RBI; RBI T-bill auction 7 Oct; ICRA Analytics / Refinitiv (30 Sep); bank rate cards. Savings rate assumed. Yield Enhancer: target, not assured.",
         asof="Oct 2026", min=0, max=12.5, ticks=[0, 3, 6, 9, 12], dec=2, unit="%",
         data=[["Savings a/c", 2.7, "mute"], ["RBI repo", 5.5, "mute"], ["1-yr bank FD", 6.25, "mute"],
               ["364-day T-bill", 6.29, "mute"], ["1-yr AAA bond", 7.48, "mute"], ["Yield Enhancer (target)", 11.0, "brand"]],
         bracket=[4, 5, "+3.5 pts"]),
    dict(id="C07", file="C07-rate-sensitivity", dp=["D38"], type="hbar",
         title="Price impact if interest rates rise by 1%",
         sub="Approximate change in bond price by portfolio duration",
         source="Ionic calculation: price change ≈ −duration × change in yield. Category durations are indicative.",
         asof=AS_OF, min=-12, max=0, ticks=[-12, -9, -6, -3, 0], dec=2, unit="%", labelw=230,
         rows=[["Yield Enhancer (1.25 yr)", -1.25, "brand"], ["Short-term bond fund (2.5 yr)", -2.5, "mute"],
               ["Corporate bond fund (4 yr)", -4.0, "mute"], ["10-yr G-Sec (6.8 yr)", -6.8, "warn"], ["Long gilt fund (10 yr)", -10.0, "warn"]]),
    dict(id="C08", file="C08-pretax-posttax-real", dp=["D32", "D33", "D34"], type="grouped",
         title="Pre-tax, after-tax and real returns",
         sub="30% slab + 4% cess; real return = after-tax return minus 5.54% CPI",
         source="Ionic calculation. Yield Enhancer shown at its 11% target, which is not assured. Surcharge ignored.",
         asof=AS_OF, min=-2, max=12, ticks=[-2, 0, 2, 4, 6, 8, 10, 12], dec=2, unit="%",
         cats=["1-yr bank FD", "1-yr AAA bond", "Yield Enhancer (11% target)"],
         series=[["Pre-tax", [FD, AAA1, YE], "mute"],
                 ["After tax", [post_tax(FD), post_tax(AAA1), post_tax(YE)], "brand"],
                 ["After tax and inflation", [round(post_tax(FD) - CPI, 2), round(post_tax(AAA1) - CPI, 2), round(post_tax(YE) - CPI, 2)], "navy"]]),
    dict(id="C09", file="C09-equity-horizon-range", dp=["D41", "D42"], type="range",
         title="Nifty 50: the range of returns narrows with time",
         sub="Annualised price return over rolling periods since 2008: worst to best, with median",
         source="Ionic calculation from approximate Nifty 50 calendar-year price returns, 2008–2025. Dividends add ~1–1.5 pts a year.",
         asof="2008–2025", min=-60, max=85, ticks=[-50, -25, 0, 25, 50, 75],
         rows=[[f"{n} year" + ("s" if n > 1 else ""), ROLL[n]["min"], ROLL[n]["max"], ROLL[n]["med"]] for n in (1, 3, 5, 7)]),
    dict(id="C10", file="C10-topup-2026-blend", dp=["D43"], type="hbar",
         title="2026 so far: an equity portfolio with a Yield Enhancer sleeve",
         sub="Hypothetical change, 1 Jan to 26 Oct 2026",
         source="Nifty 50 price change (NSE via HDFC Sky). Yield Enhancer assumed at its 11% target, pro-rated; simple weighted blend. Not actual returns.",
         asof="26 Oct 2026", min=-15, max=0, ticks=[-15, -10, -5, 0], dec=1, unit="%", labelw=230,
         rows=[["100% equity (Nifty 50)", BLEND[0], "mute"], ["80% equity + 20% Yield Enhancer", BLEND[0.2], "soft"],
               ["70% equity + 30% Yield Enhancer", BLEND[0.3], "brand"]]),
    dict(id="C11", file="C11-1cr-18-months", dp=["D39"], type="hbar",
         title="₹1 crore over 18 months: gain at each rate",
         sub="Pre-tax, compounded annually",
         source="Ionic calculation. Savings rate assumed at 2.7%. Yield Enhancer at its 11% target, which is not assured.",
         asof=AS_OF, min=0, max=20, ticks=[0, 5, 10, 15, 20], dec=1, unit="", prefix="+₹", suffix=" L", labelw=230,
         rows=[["Savings account @ 2.7%", GAIN18["sav"], "mute"], ["1-yr bank FD @ 6.25%", GAIN18["fd"], "mute"],
               ["Yield Enhancer @ 11% target", GAIN18["ye"], "brand"]]),
    dict(id="C12", file="C12-pe-vs-median", dp=["D13", "D14", "D15"], type="hbar",
         title="Index valuations vs their own history",
         sub="P/E premium (+) or discount (−) to median: large and midcaps below, small caps above",
         source="NSE data via Rupeecase and indexpe.in, 6–23 Oct 2026. Nifty 50 median since Mar 2021; others 5-year median.",
         asof="Oct 2026", min=-20, max=30, ticks=[-20, -10, 0, 10, 20, 30], dec=1, unit="%", labelw=230, signed=True,
         rows=[[f"{n} ({p}× vs {m}×)", round((p / m - 1) * 100, 1), "brand" if p < m else "amber"] for n, p, m in pe]),
    dict(id="C13", file="C13-years-to-double", dp=["D36"], type="vbar",
         title="Years for money to double, after tax",
         sub="At each rate after 30% slab tax + cess",
         source="Ionic calculation: ln 2 ÷ ln(1 + after-tax rate). Yield Enhancer at its 11% target, which is not assured.",
         asof=AS_OF, min=0, max=40, ticks=[0, 10, 20, 30, 40], dec=1, unit=" yrs",
         data=[["Savings a/c (2.7%)", double_years(post_tax(SAV)), "mute"], ["1-yr bank FD (6.25%)", double_years(post_tax(FD)), "mute"],
               ["1-yr AAA bond (7.48%)", double_years(post_tax(AAA1)), "mute"], ["Yield Enhancer (11% target)", double_years(post_tax(YE)), "brand"]]),
]

CARDS = [
    dict(id="S01", file="S01-fpi-record", big="₹3.08 L cr", label="Record foreign selling of Indian equities", ctx="January–September 2026, 1.9× all of 2025", source="NSDL via Business Standard, Oct 2026"),
    dict(id="S02", file="S02-dii-buying", big="₹6.83 L cr", label="Bought by domestic institutions in 2026", ctx="More than offsetting foreign selling", source="NSE / NSDL via Business Standard, Oct 2026"),
    dict(id="S03", file="S03-vix", big="31", label="India VIX peak, 27 March 2026", ctx="Up from 13.5 in December 2025", source="NSE via Macrotrends"),
    dict(id="S04", file="S04-repo-hike", big="5.50%", label="RBI repo rate after the 7 Oct hike", ctx="First increase since February 2023", source="RBI, 7 Oct 2026"),
    dict(id="S05", file="S05-gsec", big="7.47%", label="10-year G-Sec yield", ctx="Highest since March 2023", source="Trading Economics, 23 Oct 2026"),
    dict(id="S06", file="S06-us-10y", big="5.36%", label="US 10-year Treasury yield peak", ctx="Highest since 2002, on 7 Oct 2026", source="Wolf Street / US Treasury"),
    dict(id="S07", file="S07-fd-real", big=f"{round(post_tax(FD) - CPI, 1)}%", label="Real return on a 6.25% FD", ctx="After 30% slab tax and 5.54% inflation", source="Ionic calculation, Oct 2026"),
    dict(id="S08", file="S08-premium-over-aaa", big=f"+{round(YE - AAA1, 1)} pts", label="11% target vs the 7.48% yield on 1‑year AAA bonds", ctx="The premium for credit and liquidity risk. Target, not assured.", source="Ionic calculation; ICRA Analytics, 30 Sep 2026"),
    dict(id="S09", file="S09-doubling", big=f"{double_years(post_tax(YE))} vs {double_years(post_tax(FD))}", size=68, label="Years to double after tax", ctx="11% target vs a 6.25% FD. Target, not assured.", source="Ionic calculation"),
    dict(id="S10", file="S10-nifty-pe", big="19.1×", label="Nifty 50 P/E, vs a 22.1× median", ctx="Large caps are cheaper than their recent history", source="NSE, 12 Oct 2026"),
]


def src_text(keys):
    return "; ".join(SRC[k][0] for k in keys)


def build_html():
    dp_json = [dict(id=d[0], theme=d[1], text=d[2], value=d[3], asof=d[4],
                    sources=[dict(name=SRC[k][0], url=SRC[k][1]) for k in d[5]], verify=d[6], kind=d[7], note=d[8]) for d in DP]
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = (tpl.replace("/*__CHARTS__*/[]", json.dumps(CHARTS, ensure_ascii=False))
               .replace("/*__CARDS__*/[]", json.dumps(CARDS, ensure_ascii=False))
               .replace("/*__DP__*/[]", json.dumps(dp_json, ensure_ascii=False)))
    out = os.path.join(HERE, "ionic-ye-data-library.html")
    open(out, "w", encoding="utf-8").write(html)
    return out


def build_xlsx():
    wb = Workbook()
    head = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="0E113F")
    wrap = Alignment(wrap_text=True, vertical="top")

    ws = wb.active
    ws.title = "Read me"
    rows = [
        ["Ionic Yield Enhancer: data points for marketing"],
        [f"Data as of {AS_OF}. Every figure has an ID (D = data point, C = chart, S = stat card) used across the HTML library and chart PNGs."],
        [""],
        ["Type", "Meaning"],
        ["Reported", "From news or aggregator reports. Confirm at the primary source in the 'Verify at' column before external use."],
        ["Market data", "From a market-data aggregator. Confirm at the primary source before external use."],
        ["Ionic calculation", "Derived by Ionic from the inputs in the note. Method shown."],
        ["Hypothetical", "Illustration that assumes the 11% target is achieved. Label as hypothetical; not actual or assured returns."],
        ["Assumption", "An input chosen by Ionic."],
        [""],
        ["Ionic also sells equity strategies. Use equity data factually; notes flag points that are equity-positive or need balancing."],
        ["Yield Enhancer's 11% is a target, not an assured return. All external use needs compliance sign-off."],
    ]
    for r in rows:
        ws.append(r)
    ws["A1"].font = Font(bold=True, size=14)
    for c in ("A4", "B4"):
        ws[c].font = head
        ws[c].fill = fill
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 110

    ws = wb.create_sheet("Data points")
    cols = ["ID", "Theme", "Data point", "Value", "As of", "Source", "Source URL", "Verify at (primary)", "Type", "Usage note"]
    ws.append(cols)
    for d in DP:
        ws.append([d[0], d[1], d[2], d[3], d[4], src_text(d[5]), " | ".join(SRC[k][1] for k in d[5] if SRC[k][1]), d[6], d[7], d[8]])
    widths = [6, 16, 70, 18, 14, 28, 50, 24, 16, 50]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for c in ws[1]:
        c.font = head
        c.fill = fill
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = wrap
    ws.freeze_panes = "C2"

    ws = wb.create_sheet("Chart data")
    for ch in CHARTS:
        ws.append([f"{ch['id']}  {ch['title']}"])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
        ws.append([f"File: {ch['file']}.png   |   Data points: {', '.join(ch['dp'])}   |   Source: {ch['source']}   |   As of: {ch['asof']}"])
        t = ch["type"]
        if t == "line":
            ws.append(["Day of 2026", "Nifty 50"])
            for d, v in ch["pts"]:
                ws.append([d, v])
        elif t == "vbar":
            ws.append(["Label", "Value"])
            for l, v, _ in ch["data"]:
                ws.append([l, v])
        elif t == "hbar":
            ws.append(["Label", "Value"])
            for l, v, _ in ch["rows"]:
                ws.append([l, v])
        elif t == "dumbbell":
            ws.append(["Measure", "Earlier", "Earlier period", "Latest", "Latest period"])
            for r in ch["rows"]:
                ws.append(r)
        elif t == "grouped":
            ws.append(["Series"] + ch["cats"])
            for name, vals, _ in ch["series"]:
                ws.append([name] + vals)
        elif t == "range":
            ws.append(["Holding period", "Worst (% p.a.)", "Best (% p.a.)", "Median (% p.a.)"])
            for r in ch["rows"]:
                ws.append(r)
        ws.append([])
    ws.column_dimensions["A"].width = 44
    for c in "BCDE":
        ws.column_dimensions[c].width = 18

    ws = wb.create_sheet("Nifty yearly returns")
    ws.append(["Year", "Nifty 50 price return (%)", "Note"])
    for y, v in NIFTY_YEARLY:
        ws.append([y, v, "Approximate"])
    ws.append([2026, NIFTY_YTD, "To 26 Oct 2026"])
    ws.append([])
    ws.append(["Rolling period", "Worst", "Best", "Median", "Negative periods", "Periods"])
    for n in (1, 3, 5, 7):
        r = ROLL[n]
        ws.append([f"{n} yr", r["min"], r["max"], r["med"], r["neg"], r["count"]])
    for c in ws[1]:
        c.font = head
        c.fill = fill
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 18

    ws = wb.create_sheet("Sources")
    ws.append(["Source", "URL"])
    seen = set()
    for k, (name, url) in SRC.items():
        if url and url not in seen:
            seen.add(url)
            ws.append([name, url])
    for c in ws[1]:
        c.font = head
        c.fill = fill
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 120

    out = os.path.join(HERE, "Ionic-YE-data-points.xlsx")
    wb.save(out)
    return out


if __name__ == "__main__":
    print(build_html())
    print(build_xlsx())
    print("rolling", ROLL)
    print("blend", BLEND, "gain18", GAIN18, "ye_ytd", YE_YTD)
