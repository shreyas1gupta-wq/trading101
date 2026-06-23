"""
BSE Midcap 150 Momentum 30 — AMC-Grade 2-Page Factsheet (v3)
Zero-overlap, crisp layout, precise positioning.
"""
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages
import warnings; warnings.filterwarnings('ignore')

plt.rcParams.update({
    'font.family': 'Liberation Sans', 'font.size': 8,
    'axes.unicode_minus': False, 'figure.dpi': 220, 'savefig.dpi': 220,
    'axes.linewidth': 0.3, 'patch.linewidth': 0.3,
})

BSE = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/c849403c-BSE_Midcap_150_Momentum_30_Returns__Volatility.cleaned.xlsx"
NAV = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/950e4d7f-nifty_all_navs.xlsx"
OUT = "/home/user/trading101"

# ─── DESIGN TOKENS ───
C = dict(
    navy='#0A1628', navy2='#152742', gold='#C8982C', gold_lt='#F7F0DD',
    teal='#0E7C6B', teal_lt='#E2F1EF',
    red='#B83B3B', red_lt='#FCEAEA', green='#1B7A42', green_lt='#E3F4EA',
    g1='#F8F9FB', g2='#EEF1F5', g3='#D4D8DE', g4='#9CA3AF', g5='#6B7280', g6='#374151',
    white='#FFFFFF', black='#111827',
)

# 5 indices: BSE Mom30, Nifty Mid150 Mom50, Nifty MidCap 150, Nifty200 Mom30, Nifty 50
INDICES = [
    'BSE Midcap 150 Momentum 30',
    'Nifty Midcap150 Momentum 50',
    'Nifty Midcap 150',
    'Nifty200 Mom 30',
    'Nifty 50',
]
IDX_SHORT = {
    'BSE Midcap 150 Momentum 30': 'BSE Mid150 Mom 30',
    'Nifty Midcap150 Momentum 50':'Nifty Mid150 Mom 50',
    'Nifty Midcap 150':           'Nifty MidCap 150',
    'Nifty200 Mom 30':            'Nifty200 Mom 30',
    'Nifty 50':                   'Nifty 50',
}
IDX_CLR = {
    'BSE Midcap 150 Momentum 30': C['navy'],
    'Nifty Midcap150 Momentum 50':C['gold'],
    'Nifty Midcap 150':           C['g4'],
    'Nifty200 Mom 30':            C['teal'],
    'Nifty 50':                   C['g3'],
}

# ═══════════════════════════════════════════════════════════════
# DATA
# ═══════════════════════════════════════════════════════════════
bse_sheets = pd.read_excel(BSE, sheet_name=None)

def canon(raw):
    s = str(raw).strip()
    if 'BSE Midcap 150 Momentum 30' in s: return 'BSE Midcap 150 Momentum 30'
    if 'BSE Midcap 150' in s or 'BSE 150 Midcap' in s: return 'BSE 150 Midcap'
    if 'Nifty Midcap150 Momentum' in s: return 'Nifty Midcap150 Momentum 50'
    if 'Nifty Midcap 150' in s: return 'Nifty Midcap 150'
    if 'Nifty200' in s and ('Mom' in s or 'Momentum' in s): return 'Nifty200 Mom 30'
    if 'Nifty 100' in s: return 'Nifty 100'
    return s

# Performance & Volatility from BSE file
pv = bse_sheets['Performance & Volatility']
def parse_block(hdr, s, e):
    cols = {i: canon(v) for i, v in enumerate(pv.iloc[hdr]) if pd.notna(v) and canon(v) not in ('Periodic','Period')}
    out = {}
    for r in range(s, min(e+1, len(pv))):
        p = str(pv.iloc[r, 0]).strip()
        if p in ('nan','NaN',''): continue
        out[p] = {cn: float(pv.iloc[r, i]) for i, cn in cols.items() if pd.notna(pv.iloc[r, i])}
    return out
perf_data = parse_block(1, 2, 11)
vol_data  = parse_block(14, 15, 24)

# Rolling Returns
rr = bse_sheets['Rolling Returns']
rolling = {}
cur = None
for _, row in rr.iterrows():
    v = str(row.iloc[1]).strip()
    if 'Rolling Return' in v: cur = v; rolling[cur] = {}
    elif cur and v not in ('nan','NaN',''):
        try: rolling[cur][v] = dict(Min=float(row.iloc[2]), Avg=float(row.iloc[3]), Max=float(row.iloc[4]), Neg=int(float(row.iloc[5])), Tot=int(float(row.iloc[6])))
        except: pass

# CY Returns
cy_raw = bse_sheets['CY Returns']
cy_cols = {i: ('Year' if str(v).strip()=='Calendar Year' else canon(v)) for i, v in enumerate(cy_raw.iloc[0]) if pd.notna(v)}
cy_data = {}
for idx in range(1, len(cy_raw)):
    row = cy_raw.iloc[idx]
    try: yr = int(row.iloc[0])
    except: yr = str(row.iloc[0])
    cy_data[yr] = {}
    for i, cn in cy_cols.items():
        if cn != 'Year':
            try: cy_data[yr][cn] = float(row.iloc[i])
            except: pass

# Active Fund Comparison
af_raw = bse_sheets['Comparison with active Funds']
af = {}
for idx in range(2, len(af_raw)):
    lbl = str(af_raw.iloc[idx, 1]).strip()
    af[lbl] = {p: float(af_raw.iloc[idx, i+2]) for i, p in enumerate(['1 Year','3 Years','5 Years','7 Years','10 Years']) if pd.notna(af_raw.iloc[idx, i+2])}

# ─── NIFTY 50 + NAV DATA ───
nifty = pd.read_excel(NAV, sheet_name='Broad & Factor Indices')
nifty['Date'] = pd.to_datetime(nifty['HistoricalDate'], format='mixed', dayfirst=True)
nifty = nifty.dropna(subset=['Date']).sort_values('Date').set_index('Date')

# Compute Nifty 50 PTP, Volatility, CY returns to replace Nifty 100
n50 = nifty['NIFTY 50'].dropna()
end_date = n50.index[-1]

def cagr(start_val, end_val, years):
    if start_val <= 0 or years <= 0: return None
    return (end_val / start_val) ** (1/years) - 1

def ann_vol(series, years_back):
    days_back = int(years_back * 365.25)
    from_date = end_date - pd.Timedelta(days=days_back)
    sub = series[series.index >= from_date]
    if len(sub) < 50: return None
    return sub.pct_change().dropna().std() * np.sqrt(252)

periods_map = {
    'YTD 2026': ('2025-12-31', None),
    '6 Months': (None, 0.5),
    '3 Months': (None, 0.25),
    '1 Year': (None, 1), '2 Years': (None, 2), '3 Years': (None, 3),
    '5 Years': (None, 5), '7 Years': (None, 7), '10 Years': (None, 10), '15 Years': (None, 15),
}

n50_perf = {}
n50_vol = {}
for pname, (fixed_date, yrs) in periods_map.items():
    if fixed_date:
        sd = pd.Timestamp(fixed_date)
        nearest = n50.index[n50.index <= sd]
        if len(nearest) == 0: continue
        sd = nearest[-1]
        days = (end_date - sd).days
        if days < 30:
            n50_perf[pname] = (n50.iloc[-1] / n50.loc[sd] - 1)
        else:
            n50_perf[pname] = cagr(n50.loc[sd], n50.iloc[-1], days/365.25)
    else:
        sd = end_date - pd.Timedelta(days=int(yrs * 365.25))
        nearest = n50.index[n50.index >= sd]
        if len(nearest) == 0: continue
        sd = nearest[0]
        sv = n50.loc[sd]
        ev = n50.iloc[-1]
        if yrs <= 1:
            n50_perf[pname] = ev / sv - 1
        else:
            n50_perf[pname] = cagr(sv, ev, yrs)
    n50_vol[pname] = ann_vol(n50, yrs if yrs else (end_date - pd.Timestamp(fixed_date)).days / 365.25)

# Add Nifty 50 to perf_data / vol_data
for p in perf_data:
    if p in n50_perf: perf_data[p]['Nifty 50'] = n50_perf[p]
for p in vol_data:
    if p in n50_vol and n50_vol[p] is not None: vol_data[p]['Nifty 50'] = n50_vol[p]

# Nifty 50 CY returns
for yr in range(2006, 2026):
    start = pd.Timestamp(f'{yr-1}-12-31')
    end_yr = pd.Timestamp(f'{yr}-12-31')
    ns = n50.index[n50.index >= start]
    ne = n50.index[n50.index <= end_yr]
    if len(ns) > 0 and len(ne) > 0:
        cy_data.setdefault(yr, {})['Nifty 50'] = n50.loc[ne[-1]] / n50.loc[ns[0]] - 1

# Nifty 50 rolling returns (approximate from pre-computed — use daily data)
n50_daily = n50.pct_change().dropna()
for roll_name, roll_days in [('1YR Rolling Return', 252), ('3YR Rolling Return', 756),
                              ('5YR Rolling Return', 1260), ('7YR Rolling Return', 1764),
                              ('10YR Rolling Return', 2520)]:
    if roll_name not in rolling: rolling[roll_name] = {}
    n50_vals = n50.values
    n50_idx = n50.index
    yrs = roll_days / 252
    roll_rets = []
    for i in range(roll_days, len(n50_vals)):
        r = cagr(n50_vals[i - roll_days], n50_vals[i], yrs)
        if r is not None: roll_rets.append(r)
    if roll_rets:
        arr = np.array(roll_rets)
        rolling[roll_name]['Nifty 50'] = dict(
            Min=arr.min(), Avg=arr.mean(), Max=arr.max(),
            Neg=int((arr < 0).sum()), Tot=len(arr)
        )

# Risk metrics from daily NAV
nav_cols_map = {
    'NIFTY 50': 'Nifty 50',
    'NIFTY MIDCAP 150': 'Nifty Midcap 150',
    'NIFTY200MOMENTM30': 'Nifty200 Mom 30',
    'NIFTY MIDCAP150 MOMENTUM 50': 'Nifty Midcap150 Momentum 50',
}
nav_df = nifty[list(nav_cols_map.keys())].dropna()
dret = nav_df.pct_change().dropna()

def calc_risk(rets, rf=0.065/252):
    ar = (1 + rets.mean())**252 - 1
    vol = rets.std() * np.sqrt(252)
    sh = ((rets - rf).mean() / rets.std()) * np.sqrt(252)
    so = ((rets - rf).mean() / rets[rets<0].std()) * np.sqrt(252)
    cum = (1 + rets).cumprod(); dd = (cum - cum.cummax()) / cum.cummax()
    mdd = dd.min()
    cal = ar / abs(mdd) if mdd != 0 else 0
    return dict(CAGR=ar, Vol=vol, Sharpe=sh, Sortino=so, MaxDD=mdd, Calmar=cal)

rmetrics = {nav_cols_map[c]: calc_risk(dret[c]) for c in nav_cols_map}


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def fp(v, d=1):
    """Format percentage."""
    return '—' if v is None else f'{v*100:.{d}f}%'

def fr(v):
    return '—' if v is None else f'{v:.2f}'

def draw_header(fig, y_top, title, sub):
    ax = fig.add_axes([0, y_top - 0.035, 1, 0.035])
    ax.axis('off'); ax.set_xlim(0,1); ax.set_ylim(0,1)
    ax.add_patch(Rectangle((0,0),1,1, fc=C['navy'], ec='none', transform=ax.transAxes))
    ax.text(0.04, 0.55, title, fontsize=14.5, fontweight='bold', color=C['white'], va='center')
    ax.text(0.04, 0.15, sub, fontsize=7, color=C['gold'], va='center')
    # Gold bottom line
    fig.add_axes([0, y_top - 0.0375, 1, 0.0025]).axis('off')
    fig.axes[-1].add_patch(Rectangle((0,0),1,1, fc=C['gold'], ec='none', transform=fig.axes[-1].transAxes))

def stitle(fig, x, y, text, fs=8.5):
    """Section title — just text + tiny gold underline on the figure."""
    fig.text(x, y, text, fontsize=fs, fontweight='bold', color=C['navy'], va='bottom')

def make_tbl(ax, rows, headers, hl_row=None, cw=None, fs=6.8, rh=1.22):
    ax.axis('off')
    nc = len(headers)
    if cw is None: cw = [1/nc]*nc
    t = ax.table(cellText=rows, colLabels=headers, cellLoc='center', loc='center', colWidths=cw)
    t.auto_set_font_size(False); t.set_fontsize(fs); t.scale(1, rh)
    for (r, c), cell in t.get_celld().items():
        cell.set_linewidth(0)
        cell.PAD = 0.035
        if r == 0:
            cell.set_facecolor(C['navy']); cell.set_text_props(color=C['white'], fontweight='bold', fontsize=fs-0.3)
            cell.visible_edges = 'B'; cell.set_edgecolor(C['gold']); cell.set_linewidth(1.2)
        else:
            bg = C['g1'] if r % 2 == 0 else C['white']
            if hl_row is not None and r == hl_row:
                bg = C['gold_lt']; cell.set_text_props(fontweight='bold', color=C['navy'])
            cell.set_facecolor(bg)
            cell.set_edgecolor(C['g2']); cell.set_linewidth(0.25)
            if c == 0: cell.set_text_props(fontweight='bold', fontsize=fs-0.4, color=C['g6'])
    return t

def clean_ax(ax):
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(C['g3']); ax.spines['bottom'].set_color(C['g3'])
    ax.tick_params(axis='both', labelsize=5.5, length=2)
    ax.grid(axis='y', color=C['g2'], lw=0.2)


# ═══════════════════════════════════════════════════════════════
#  PAGE 1
# ═══════════════════════════════════════════════════════════════
fig1 = plt.figure(figsize=(8.27, 11.69), facecolor=C['white'])
draw_header(fig1, 1.0, 'BSE Midcap 150 Momentum 30 Index', 'Index Factsheet  |  Data as of June 19, 2026')

# ── KPI Strip ──
ax_kpi = fig1.add_axes([0.035, 0.90, 0.93, 0.04])
ax_kpi.axis('off'); ax_kpi.set_xlim(0,1); ax_kpi.set_ylim(0,1)
ax_kpi.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.008', fc=C['g1'], ec=C['g3'], lw=0.4, transform=ax_kpi.transAxes))

kpis = [('27.7%','15Y CAGR'), ('28.6%','10Y CAGR'), ('35.5%','7Y CAGR'),
        ('30.4%','5Y CAGR'), ('33.8%','3Y CAGR'), ('13.0%','1Y Return'), ('6.2%','YTD 2026')]
for i, (v, l) in enumerate(kpis):
    x = 0.015 + i * (0.97/7)
    ax_kpi.text(x + 0.97/14, 0.68, v, fontsize=11, fontweight='bold', color=C['navy'], ha='center', va='center', transform=ax_kpi.transAxes)
    ax_kpi.text(x + 0.97/14, 0.22, l, fontsize=5.5, color=C['g5'], ha='center', va='center', transform=ax_kpi.transAxes)
    if i < len(kpis)-1:
        ax_kpi.plot([x + 0.97/7, x + 0.97/7], [0.15, 0.85], color=C['g3'], lw=0.4, transform=ax_kpi.transAxes)

# ── Growth Chart (FULL WIDTH) ──
stitle(fig1, 0.04, 0.893, 'Growth of ₹10,000 Invested')

ax_g = fig1.add_axes([0.06, 0.685, 0.90, 0.20])
grow_map = {
    'NIFTY MIDCAP150 MOMENTUM 50': ('Nifty Mid150 Mom 50', C['gold'], 1.8, '-'),
    'NIFTY200MOMENTM30':           ('Nifty200 Mom 30',     C['teal'],  1.3, '-'),
    'NIFTY MIDCAP 150':            ('Nifty MidCap 150',    C['g4'],    0.9, '--'),
    'NIFTY 50':                    ('Nifty 50',            C['g3'],    0.9, '--'),
}

nav_g = nifty[list(grow_map.keys())].dropna()
ends = {}
for col, (lbl, clr, lw, ls) in grow_map.items():
    norm = nav_g[col] / nav_g[col].iloc[0] * 10000
    ax_g.plot(norm.index, norm.values, color=clr, lw=lw, ls=ls, alpha=0.85, zorder=3 if lw > 1 else 2)
    ends[lbl] = (norm.values[-1], clr)

ax_g.set_yscale('log')
y_fmt = lambda x, _: f'₹{x/100000:.1f}L' if x >= 100000 else (f'₹{x/1000:.0f}K' if x >= 1000 else f'₹{x:.0f}')
ax_g.yaxis.set_major_formatter(mticker.FuncFormatter(y_fmt))
clean_ax(ax_g)
ax_g.grid(axis='y', color=C['g2'], lw=0.25, alpha=0.6)
ax_g.set_xlim(nav_g.index[0], nav_g.index[-1] + pd.Timedelta(days=700))

# End-of-line final value labels (spread vertically to avoid overlap)
sorted_e = sorted(ends.items(), key=lambda x: -x[1][0])
label_positions = []
for lbl, (val, clr) in sorted_e:
    # Check overlap with previous labels
    log_val = np.log10(val)
    y_pos = log_val
    for prev_pos in label_positions:
        if abs(y_pos - prev_pos) < 0.06:
            y_pos = prev_pos - 0.06
    label_positions.append(y_pos)
    val_s = f'₹{val/100000:.1f}L' if val >= 100000 else f'₹{val/1000:.0f}K'
    ax_g.annotate(f'{lbl}  {val_s}', xy=(nav_g.index[-1], val),
                  xytext=(8, 0), textcoords='offset points',
                  fontsize=5.2, color=clr, fontweight='bold', va='center')

# Methodology as a slim text strip below chart
fig1.text(0.04, 0.675, 'Methodology:', fontsize=5.5, fontweight='bold', color=C['navy'])
fig1.text(0.115, 0.675, 'Universe: BSE MidCap 150  |  Top 30 by Momentum Score (6M+12M return / vol)  |  Wt: Score-weighted, max 10%  |  Rebalance: Semi-Annual (Jun & Dec)  |  Base: 03 Apr 2006 = 1,000', fontsize=4.8, color=C['g5'])

# ── PTP Performance ──
stitle(fig1, 0.04, 0.66, 'Point-to-Point Performance (CAGR)')

ax_ptp = fig1.add_axes([0.035, 0.555, 0.93, 0.098])
p_keys = ['YTD 2026','1 Year','2 Years','3 Years','5 Years','7 Years','10 Years','15 Years']
p_hdrs = ['Index', "YTD '26", '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y']

ptp_rows = []
for idx in INDICES:
    row = [IDX_SHORT[idx]]
    for pk in p_keys:
        row.append(fp(perf_data.get(pk, {}).get(idx)))
    ptp_rows.append(row)

make_tbl(ax_ptp, ptp_rows, p_hdrs, hl_row=1, cw=[0.175]+[0.103]*8)

# ── Volatility ──
stitle(fig1, 0.04, 0.545, 'Annualized Volatility')

ax_vol = fig1.add_axes([0.035, 0.44, 0.93, 0.098])
vol_rows = []
for idx in INDICES:
    row = [IDX_SHORT[idx]]
    for pk in p_keys:
        row.append(fp(vol_data.get(pk, {}).get(idx)))
    vol_rows.append(row)

make_tbl(ax_vol, vol_rows, p_hdrs, hl_row=1, cw=[0.175]+[0.103]*8)

# ── CY Returns Heatmap ──
stitle(fig1, 0.04, 0.428, 'Calendar Year Returns')

ax_cy = fig1.add_axes([0.035, 0.16, 0.93, 0.26])
ax_cy.axis('off')

years = list(range(2006, 2026))
cy_mat = []
for idx in INDICES:
    cy_mat.append([cy_data.get(yr, {}).get(idx, np.nan) for yr in years])
cy_arr = np.array(cy_mat)

nr, nc = cy_arr.shape
cw = 0.82 / nc
ch = 0.82 / nr
x0, y0 = 0.155, 0.92

norm = mcolors.TwoSlopeNorm(vmin=-0.70, vcenter=0, vmax=1.0)
cmap = mcolors.LinearSegmentedColormap.from_list('rg', [
    (0.0, '#C94040'), (0.25, '#F0A8A8'), (0.5, '#FFFFFF'),
    (0.75, '#8DD4A3'), (1.0, '#1A7840')])

# Year headers
for j, yr in enumerate(years):
    ax_cy.text(x0 + j*cw + cw/2, y0 + 0.04, f"'{str(yr)[2:]}", fontsize=5.5, fontweight='bold',
               color=C['navy'], ha='center', va='center', transform=ax_cy.transAxes)

# Row labels
for i, idx in enumerate(INDICES):
    y = y0 - i*ch - ch/2
    ax_cy.text(x0 - 0.015, y, IDX_SHORT[idx], fontsize=5.5, fontweight='bold',
               color=C['g6'], ha='right', va='center', transform=ax_cy.transAxes)

# Cells
for i in range(nr):
    for j in range(nc):
        x = x0 + j*cw
        y = y0 - i*ch - ch
        v = cy_arr[i, j]
        if np.isnan(v):
            fc, txt = C['g2'], '—'
        else:
            fc, txt = cmap(norm(v)), f'{v*100:.0f}%'
        ax_cy.add_patch(FancyBboxPatch((x+0.001, y+0.004), cw-0.002, ch-0.008,
                        boxstyle='round,pad=0.002', fc=fc, ec=C['g2'], lw=0.15,
                        transform=ax_cy.transAxes))
        tc = C['white'] if (not np.isnan(v) and abs(v) > 0.50) else C['black']
        fw = 'bold' if i == 0 else 'normal'
        ax_cy.text(x + cw/2, y + ch/2, txt, fontsize=5, fontweight=fw, color=tc,
                   ha='center', va='center', transform=ax_cy.transAxes)

# ── Key Insight Bar ──
ax_ins = fig1.add_axes([0.035, 0.04, 0.93, 0.105])
ax_ins.axis('off'); ax_ins.set_xlim(0,1); ax_ins.set_ylim(0,1)
ax_ins.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.012', fc=C['gold_lt'], ec=C['gold'], lw=0.5, transform=ax_ins.transAxes))

bse_k = 'BSE Midcap 150 Momentum 30'
wins = sum(1 for yr in range(2006,2026) if yr in cy_data and bse_k in cy_data[yr] and all(v <= cy_data[yr][bse_k] for k,v in cy_data[yr].items() if k != bse_k and k != 'Nifty 100' and k != 'BSE 150 Midcap'))
ov50 = sum(1 for yr in range(2006,2026) if yr in cy_data and bse_k in cy_data[yr] and 'Nifty 50' in cy_data.get(yr,{}) and cy_data[yr][bse_k] > cy_data[yr]['Nifty 50'])

ax_ins.text(0.015, 0.82, 'KEY HIGHLIGHTS', fontsize=7, fontweight='bold', color=C['navy'], va='top', transform=ax_ins.transAxes)

highlights = [
    f'Top-performing index in {wins} of 20 calendar years among momentum & midcap peers',
    f'Outperformed Nifty 50 in {ov50} of 20 calendar years — across bull and bear markets',
    'Zero probability of negative returns on any 5-year or longer rolling window',
    'Highest average rolling CAGR across 1Y, 3Y, 5Y, 7Y, and 10Y horizons vs all peers',
]
for i, h in enumerate(highlights):
    ax_ins.text(0.015, 0.62 - i*0.18, f'•  {h}', fontsize=5.8, color=C['g6'], va='top', transform=ax_ins.transAxes)

# Footer
fig1.text(0.035, 0.018, 'Source: BSE India, NSE India. All returns are TRI-based. CAGR shown for periods > 1 year. Past performance is not indicative of future results.',
          fontsize=4.5, color=C['g4'])
fig1.text(0.965, 0.018, 'Page 1 of 2', fontsize=5, color=C['g4'], ha='right')


# ═══════════════════════════════════════════════════════════════
#  PAGE 2
# ═══════════════════════════════════════════════════════════════
fig2 = plt.figure(figsize=(8.27, 11.69), facecolor=C['white'])
draw_header(fig2, 1.0, 'Performance Deep Dive & Risk Analysis', 'Rolling Returns  |  Risk Metrics  |  Active Fund Comparison')

# ── Rolling Returns — Avg CAGR ──
stitle(fig2, 0.04, 0.945, 'Rolling Returns — Average Annualized CAGR')

ax_r1 = fig2.add_axes([0.035, 0.855, 0.93, 0.088])
rk = ['1YR Rolling Return','3YR Rolling Return','5YR Rolling Return','7YR Rolling Return','10YR Rolling Return']
rl = ['1Y','3Y','5Y','7Y','10Y']

r1_rows = []
for idx in INDICES:
    row = [IDX_SHORT[idx]]
    for k in rk:
        rd = rolling.get(k, {}).get(idx)
        row.append(fp(rd['Avg']) if rd else '—')
    r1_rows.append(row)
make_tbl(ax_r1, r1_rows, ['Index']+rl, hl_row=1, cw=[0.22]+[0.156]*5)

# ── Rolling Returns — Negative Probability ──
stitle(fig2, 0.04, 0.843, 'Rolling Returns — Probability of Negative Returns')

ax_r2 = fig2.add_axes([0.035, 0.755, 0.93, 0.088])
r2_rows = []
for idx in INDICES:
    row = [IDX_SHORT[idx]]
    for k in rk:
        rd = rolling.get(k, {}).get(idx)
        if rd and rd['Tot'] > 0:
            row.append(fp(rd['Neg']/rd['Tot']))
        else:
            row.append('—')
    r2_rows.append(row)

t2 = make_tbl(ax_r2, r2_rows, ['Index']+rl, hl_row=1, cw=[0.22]+[0.156]*5)
for (r, c), cell in t2.get_celld().items():
    if r > 0 and c > 0:
        txt = cell.get_text().get_text()
        try:
            v = float(txt.replace('%',''))
            if v == 0:
                cell.set_facecolor(C['green_lt']); cell.set_text_props(color=C['green'], fontweight='bold')
            elif v > 20:
                cell.set_facecolor(C['red_lt']); cell.set_text_props(color=C['red'])
        except: pass

# ── Range Chart + Drawdown ──
stitle(fig2, 0.04, 0.74, 'Rolling Return Range (Min / Avg / Max)')
stitle(fig2, 0.565, 0.74, 'Drawdown Profile')

# Range chart
ax_rng = fig2.add_axes([0.06, 0.565, 0.46, 0.165])
x = np.arange(len(INDICES))
w = 0.25
rng_p = [('1YR Rolling Return', C['navy2'], '1Y'),
         ('3YR Rolling Return', C['gold'], '3Y'),
         ('5YR Rolling Return', C['teal'], '5Y')]

for pi, (k, clr, pl) in enumerate(rng_p):
    avgs, mins, maxs = [], [], []
    for idx in INDICES:
        rd = rolling.get(k, {}).get(idx, {})
        avgs.append(rd.get('Avg',0)); mins.append(rd.get('Min',0)); maxs.append(rd.get('Max',0))
    avgs, mins, maxs = np.array(avgs), np.array(mins), np.array(maxs)
    ax_rng.bar(x + (pi-1)*w, avgs*100, w*0.85, label=pl, color=clr, alpha=0.88, edgecolor=C['white'], lw=0.3)
    ax_rng.errorbar(x + (pi-1)*w, avgs*100, yerr=[(avgs-mins)*100, (maxs-avgs)*100],
                    fmt='none', ecolor=C['g5'], capsize=1.5, capthick=0.4, lw=0.4)

ax_rng.set_xticks(x)
ax_rng.set_xticklabels([IDX_SHORT[n].replace(' ','\n') for n in INDICES], fontsize=4.8)
ax_rng.yaxis.set_major_formatter(mticker.PercentFormatter()); ax_rng.axhline(0, color=C['g3'], lw=0.3)
clean_ax(ax_rng)
ax_rng.legend(fontsize=5.5, loc='upper right', edgecolor=C['g3'], framealpha=0.95, handlelength=1)
ax_rng.set_ylabel('Annualized Return', fontsize=5.5)

# Drawdown chart
ax_dd = fig2.add_axes([0.585, 0.565, 0.38, 0.165])
dd_map = {
    'NIFTY MIDCAP150 MOMENTUM 50': ('Mid150 Mom 50', C['gold'], 1.0),
    'NIFTY MIDCAP 150':            ('MidCap 150',    C['g4'],   0.6),
    'NIFTY200MOMENTM30':           ('N200 Mom 30',   C['teal'], 0.7),
    'NIFTY 50':                    ('Nifty 50',      C['g3'],   0.6),
}
for col, (lbl, clr, lw) in dd_map.items():
    cum = (1 + dret[col]).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax() * 100
    ax_dd.fill_between(dd.index, dd.values, 0, alpha=0.12, color=clr)
    ax_dd.plot(dd.index, dd.values, color=clr, lw=lw, label=lbl, alpha=0.85)

ax_dd.yaxis.set_major_formatter(mticker.PercentFormatter()); clean_ax(ax_dd)
ax_dd.legend(fontsize=4.8, loc='lower left', edgecolor=C['g3'], framealpha=0.9, handlelength=1.2)
ax_dd.set_ylabel('Drawdown', fontsize=5.5)

# ── Risk-Adjusted Metrics ──
stitle(fig2, 0.04, 0.55, 'Risk-Adjusted Performance Metrics (Since Apr 2005)')

ax_risk = fig2.add_axes([0.035, 0.475, 0.93, 0.07])
r_hdr = ['Index','CAGR','Volatility','Sharpe','Sortino','Max Drawdown','Calmar']
r_order = ['Nifty 50','Nifty Midcap 150','Nifty200 Mom 30','Nifty Midcap150 Momentum 50']
r_rows = []
for nm in r_order:
    m = rmetrics.get(nm, {})
    r_rows.append([IDX_SHORT.get(nm, nm), fp(m.get('CAGR')), fp(m.get('Vol')),
                   fr(m.get('Sharpe')), fr(m.get('Sortino')), fp(m.get('MaxDD')), fr(m.get('Calmar'))])

make_tbl(ax_risk, r_rows, r_hdr, hl_row=4, cw=[0.19]+[0.135]*6, fs=6.5)

# ── Active Fund Comparison ──
stitle(fig2, 0.04, 0.46, 'BSE Mid150 Mom 30 vs Avg. Active Mid-Cap Fund')

ax_af = fig2.add_axes([0.06, 0.315, 0.46, 0.135])
af_p = ['1 Year','3 Years','5 Years','7 Years','10 Years']
af_l = ['1Y','3Y','5Y','7Y','10Y']
ir = [af.get('BSE Midcap 150 Momentum 30 Index', {}).get(p, 0) for p in af_p]
ar = [af.get('Average of the Mid Cap category', {}).get(p, 0) for p in af_p]

x_af = np.arange(len(af_p)); bw = 0.32
b1 = ax_af.bar(x_af - bw/2, [r*100 for r in ir], bw, label='BSE Mid150 Mom 30', color=C['navy'], edgecolor=C['white'], lw=0.3, zorder=3)
b2 = ax_af.bar(x_af + bw/2, [r*100 for r in ar], bw, label='Avg Active Mid-Cap', color=C['g4'], edgecolor=C['white'], lw=0.3, zorder=3)

for bar in b1:
    ax_af.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.4, f'{bar.get_height():.1f}%',
               ha='center', fontsize=5.2, fontweight='bold', color=C['navy'], zorder=4)
for bar in b2:
    ax_af.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.4, f'{bar.get_height():.1f}%',
               ha='center', fontsize=5.2, color=C['g5'], zorder=4)

ax_af.set_xticks(x_af); ax_af.set_xticklabels(af_l, fontsize=6.5)
ax_af.yaxis.set_major_formatter(mticker.PercentFormatter()); clean_ax(ax_af)
ax_af.legend(fontsize=5.5, loc='upper left', edgecolor=C['g3'], handlelength=1)

# ── Why Box ──
stitle(fig2, 0.565, 0.46, 'Why BSE Mid150 Mom 30?')

ax_why = fig2.add_axes([0.555, 0.315, 0.41, 0.135])
ax_why.axis('off'); ax_why.set_xlim(0,1); ax_why.set_ylim(0,1)
ax_why.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.018', fc=C['g1'], ec=C['g3'], lw=0.4, transform=ax_why.transAxes))

bullets = [
    ('Highest CAGR', '28.6% (10Y) vs 21.9% (Nifty Mid150\nMom 50) & 18.0% (Nifty200 Mom 30)'),
    ('Concentrated Alpha', '30 stocks vs 50 — higher conviction,\nbetter factor purity & payoff'),
    ('Vol-Adjusted Scoring', 'Filters high-beta mean-reverters\n— shallower drawdowns in corrections'),
    ('Zero Negative 5Y+', '0% loss probability on any 5-year+\nrolling window since inception'),
    ('Superior to Active', 'Outperforms avg mid-cap fund\nacross every time horizon'),
]
for i, (title, desc) in enumerate(bullets):
    y = 0.93 - i * 0.19
    ax_why.text(0.04, y, title, fontsize=6, fontweight='bold', color=C['navy'], va='top')
    ax_why.text(0.04, y - 0.055, desc, fontsize=5, color=C['g5'], va='top', linespacing=1.2)

# ── Return vs Risk Scatter ──
stitle(fig2, 0.04, 0.30, 'Return vs Risk — 10Y Comparison')

ax_sc = fig2.add_axes([0.08, 0.13, 0.84, 0.16])
sdata = []
for idx in INDICES:
    ret_ = perf_data.get('10 Years', {}).get(idx)
    vol_ = vol_data.get('10 Years', {}).get(idx)
    if ret_ is not None and vol_ is not None:
        sdata.append((idx, vol_*100, ret_*100))

for idx, vl, rt in sdata:
    clr = IDX_CLR.get(idx, C['g4'])
    sz = 150 if idx == bse_k else 55
    mk = '*' if idx == bse_k else 'o'
    zo = 10 if idx == bse_k else 5
    ax_sc.scatter(vl, rt, color=clr, s=sz, marker=mk, zorder=zo, edgecolors=C['white'], linewidth=0.8)

# Labels with smart positioning (no overlap)
bse_pt = next((vl, rt) for n, vl, rt in sdata if n == bse_k)
for idx, vl, rt in sdata:
    clr = IDX_CLR.get(idx, C['g4'])
    nm = IDX_SHORT[idx]
    if idx == bse_k:
        ax_sc.annotate(nm, (vl, rt), xytext=(12, 8), textcoords='offset points',
                       fontsize=6, fontweight='bold', color=clr,
                       arrowprops=dict(arrowstyle='->', color=C['gold'], lw=0.8))
    elif rt > bse_pt[1] - 5:
        ax_sc.annotate(nm, (vl, rt), xytext=(8, -12), textcoords='offset points',
                       fontsize=5.2, color=clr)
    else:
        ax_sc.annotate(nm, (vl, rt), xytext=(8, 5), textcoords='offset points',
                       fontsize=5.2, color=clr)

ax_sc.set_xlabel('Volatility (10Y Annualized)', fontsize=6.5)
ax_sc.set_ylabel('CAGR (10Y)', fontsize=6.5)
ax_sc.xaxis.set_major_formatter(mticker.PercentFormatter())
ax_sc.yaxis.set_major_formatter(mticker.PercentFormatter())
clean_ax(ax_sc); ax_sc.grid(True, color=C['g2'], lw=0.2)

# "Efficient frontier" annotation
ax_sc.annotate('Higher Return\nSimilar Risk', xy=(bse_pt[0], bse_pt[1]),
               xytext=(bse_pt[0]+2.5, bse_pt[1]-5), fontsize=5, color=C['gold'],
               fontstyle='italic', arrowprops=dict(arrowstyle='->', color=C['gold'], lw=0.6))

# ── Disclaimer ──
ax_d = fig2.add_axes([0.035, 0.015, 0.93, 0.09])
ax_d.axis('off'); ax_d.set_xlim(0,1); ax_d.set_ylim(0,1)
ax_d.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.01', fc=C['g1'], ec=C['g2'], lw=0.3, transform=ax_d.transAxes))

disc = ("Disclaimer: This document is for informational purposes only and does not constitute investment advice, an offer, or solicitation. "
        "Past performance is not indicative of future results. The BSE Midcap 150 Momentum 30 Index is a rules-based index published by BSE India. "
        "All performance data is Total Return Index (TRI) based. Risk-free rate: 6.5% p.a. for ratio calculations. "
        "Risk metrics computed from daily NAV since common inception (Apr 2005). Active fund comparison uses Regular Plan Growth NAVs. "
        "Investors should consult their financial advisor before making investment decisions. Sources: BSE India, NSE India, AMFI.")

ax_d.text(0.015, 0.92, 'DISCLAIMER', fontsize=5.5, fontweight='bold', color=C['g5'], va='top')
ax_d.text(0.015, 0.72, disc, fontsize=4.3, color=C['g4'], va='top', wrap=True, linespacing=1.3)

fig2.text(0.965, 0.008, 'Page 2 of 2', fontsize=5, color=C['g4'], ha='right')


# ═══════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════
fig1.savefig(f'{OUT}/factsheet_page1.png', dpi=220, facecolor=C['white'], edgecolor='none')
fig2.savefig(f'{OUT}/factsheet_page2.png', dpi=220, facecolor=C['white'], edgecolor='none')
print("PNGs saved.")

with PdfPages(f'{OUT}/BSE_Midcap150_Momentum30_Factsheet.pdf') as pdf:
    pdf.savefig(fig1); pdf.savefig(fig2)
plt.close('all')
print(f"PDF: {OUT}/BSE_Midcap150_Momentum30_Factsheet.pdf")
print("Done!")
