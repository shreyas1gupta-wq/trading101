"""
BSE Midcap 150 Momentum 30 — Professional AMC-Grade 2-Page Factsheet
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
import matplotlib.patheffects as pe
import matplotlib.colors as mcolors
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'font.family': 'Liberation Sans',
    'font.size': 8,
    'axes.unicode_minus': False,
    'figure.dpi': 200,
    'savefig.dpi': 200,
    'axes.linewidth': 0.4,
    'patch.linewidth': 0.4,
})

BSE_FILE = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/c849403c-BSE_Midcap_150_Momentum_30_Returns__Volatility.cleaned.xlsx"
NIFTY_FILE = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/950e4d7f-nifty_all_navs.xlsx"
OUT_DIR = "/home/user/trading101"

# ═══════════════════════════════════════════════════════════════
# DESIGN SYSTEM
# ═══════════════════════════════════════════════════════════════
C = {
    'navy':       '#0B1D3A',
    'navy2':      '#132E57',
    'accent':     '#C9962B',
    'accent_lt':  '#F5ECD7',
    'teal':       '#1A7A6D',
    'teal_lt':    '#E3F2F0',
    'red':        '#B33A3A',
    'red_lt':     '#FCEAEA',
    'green':      '#1E7A45',
    'green_lt':   '#E6F4EC',
    'gray1':      '#F7F8FA',  # lightest
    'gray2':      '#EDF0F4',
    'gray3':      '#D1D5DB',
    'gray4':      '#9CA3AF',
    'gray5':      '#6B7280',
    'gray6':      '#374151',
    'white':      '#FFFFFF',
    'black':      '#111827',
}

IDX_COLORS = {
    'BSE Midcap 150 Momentum 30': C['navy'],
    'BSE 150 Midcap':             C['gray4'],
    'Nifty Midcap150 Momentum 50':C['accent'],
    'Nifty Midcap 150':           C['gray5'],
    'Nifty200 Mom 30':            C['teal'],
    'Nifty 100':                  C['gray3'],
}

IDX_SHORT = {
    'BSE Midcap 150 Momentum 30': 'BSE Mid150 Mom 30',
    'BSE 150 Midcap':             'BSE MidCap 150',
    'Nifty Midcap150 Momentum 50':'Nifty Mid150 Mom 50',
    'Nifty Midcap 150':           'Nifty MidCap 150',
    'Nifty200 Mom 30':            'Nifty200 Mom 30',
    'Nifty 100':                  'Nifty 100',
}

ALL_INDICES = ['BSE Midcap 150 Momentum 30', 'BSE 150 Midcap',
               'Nifty Midcap150 Momentum 50', 'Nifty Midcap 150',
               'Nifty200 Mom 30', 'Nifty 100']

# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════
bse_sheets = pd.read_excel(BSE_FILE, sheet_name=None)

def canonical_name(raw):
    s = str(raw).strip()
    if 'BSE Midcap 150 Momentum 30' in s: return 'BSE Midcap 150 Momentum 30'
    if 'BSE Midcap 150' in s or 'BSE 150 Midcap' in s: return 'BSE 150 Midcap'
    if 'Nifty Midcap150 Momentum' in s: return 'Nifty Midcap150 Momentum 50'
    if 'Nifty Midcap 150' in s: return 'Nifty Midcap 150'
    if 'Nifty200' in s and ('Mom' in s or 'Momentum' in s): return 'Nifty200 Mom 30'
    if 'Nifty 100' in s: return 'Nifty 100'
    return s

# --- Performance & Volatility ---
pv_raw = bse_sheets['Performance & Volatility']
def parse_pv_block(hdr, start, end):
    cols = {}
    for i, val in enumerate(pv_raw.iloc[hdr]):
        if pd.notna(val):
            cn = canonical_name(val)
            if cn not in ['Periodic', 'Period']: cols[i] = cn
    result = {}
    for idx in range(start, min(end+1, len(pv_raw))):
        row = pv_raw.iloc[idx]
        p = str(row.iloc[0]).strip()
        if p in ('nan','NaN',''): continue
        result[p] = {}
        for i, cn in cols.items():
            try: result[p][cn] = float(row.iloc[i])
            except: pass
    return result
perf_data = parse_pv_block(1, 2, 11)
vol_data  = parse_pv_block(14, 15, 24)

# --- Rolling Returns ---
rr_raw = bse_sheets['Rolling Returns']
rolling_data = {}
cur = None
for _, row in rr_raw.iterrows():
    v = str(row.iloc[1]).strip()
    if 'Rolling Return' in v:
        cur = v; rolling_data[cur] = {}
    elif cur and v not in ('nan','NaN',''):
        try:
            rolling_data[cur][v] = {
                'Min': float(row.iloc[2]), 'Avg': float(row.iloc[3]),
                'Max': float(row.iloc[4]), 'Neg': int(float(row.iloc[5])),
                'Total': int(float(row.iloc[6]))
            }
        except: pass

# --- CY Returns ---
cy_raw = bse_sheets['CY Returns']
cy_cols = {}
for i, val in enumerate(cy_raw.iloc[0]):
    if pd.notna(val):
        n = str(val).strip()
        cy_cols[i] = 'Year' if n == 'Calendar Year' else canonical_name(n)
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

# --- Active Fund Comparison ---
af_raw = bse_sheets['Comparison with active Funds']
af = {}
for idx in range(2, len(af_raw)):
    row = af_raw.iloc[idx]
    lbl = str(row.iloc[1]).strip()
    af[lbl] = {}
    for i, p in enumerate(['1 Year','3 Years','5 Years','7 Years','10 Years']):
        try: af[lbl][p] = float(row.iloc[i+2])
        except: pass

# --- Nifty NAV data ---
nifty_navs = pd.read_excel(NIFTY_FILE, sheet_name='Broad & Factor Indices')
nifty_navs['Date'] = pd.to_datetime(nifty_navs['HistoricalDate'], format='mixed', dayfirst=True)
nifty_navs = nifty_navs.dropna(subset=['Date']).sort_values('Date').set_index('Date')

nav_map = {
    'NIFTY 100': 'Nifty 100',
    'NIFTY MIDCAP 150': 'Nifty Midcap 150',
    'NIFTY200MOMENTM30': 'Nifty200 Mom 30',
    'NIFTY MIDCAP150 MOMENTUM 50': 'Nifty Midcap150 Momentum 50',
}
nav_cols = list(nav_map.keys())
nav_df = nifty_navs[nav_cols].dropna()
daily_ret = nav_df.pct_change().dropna()

def risk_metrics(rets, rf=0.065/252):
    ar = (1 + rets.mean())**252 - 1
    vol = rets.std() * np.sqrt(252)
    sharpe = ((rets - rf).mean() / rets.std()) * np.sqrt(252) if rets.std() else 0
    ds = rets[rets < 0].std() * np.sqrt(252)
    sortino = ((rets - rf).mean() / rets[rets < 0].std()) * np.sqrt(252) if rets[rets<0].std() else 0
    cum = (1 + rets).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax()
    mdd = dd.min()
    calmar = ar / abs(mdd) if mdd != 0 else 0
    return {'CAGR': ar, 'Volatility': vol, 'Sharpe': sharpe, 'Sortino': sortino,
            'Max DD': mdd, 'Calmar': calmar}

rmetrics = {nav_map[c]: risk_metrics(daily_ret[c]) for c in nav_cols}

# ═══════════════════════════════════════════════════════════════
# DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════
def header_bar(fig, y_top, y_bot, title, subtitle=''):
    """Draw the navy header band."""
    rect = fig.add_axes([0, y_bot, 1, y_top - y_bot])
    rect.set_xlim(0, 1); rect.set_ylim(0, 1)
    rect.add_patch(Rectangle((0, 0), 1, 1, fc=C['navy'], ec='none', transform=rect.transAxes))
    rect.text(0.045, 0.58, title, fontsize=16, fontweight='bold', color=C['white'],
              va='center', transform=rect.transAxes)
    if subtitle:
        rect.text(0.045, 0.2, subtitle, fontsize=8, color=C['accent'],
                  va='center', transform=rect.transAxes)
    rect.text(0.955, 0.58, 'BSE Midcap 150', fontsize=8, color=C['accent'],
              va='center', ha='right', transform=rect.transAxes, fontstyle='italic')
    rect.text(0.955, 0.2, 'Momentum 30', fontsize=8, color=C['gray3'],
              va='center', ha='right', transform=rect.transAxes, fontstyle='italic')
    # Gold accent line at bottom
    gold = fig.add_axes([0, y_bot - 0.003, 1, 0.003])
    gold.set_xlim(0,1); gold.set_ylim(0,1); gold.axis('off')
    gold.add_patch(Rectangle((0,0),1,1, fc=C['accent'], ec='none', transform=gold.transAxes))
    rect.axis('off')
    return rect

def section_label(fig, x, y, text, fontsize=8.5):
    """Place a section title directly on the figure (no axes overlap issues)."""
    fig.text(x, y, text, fontsize=fontsize, fontweight='bold', color=C['navy'], va='bottom')
    fig.patches.append(Rectangle((x, y - 0.003), 0.14, 0.0022,
                        transform=fig.transFigure, fc=C['accent'], ec='none', clip_on=False))

def fmt_pct(v, decimals=1):
    if v is None: return '—'
    return f'{v*100:.{decimals}f}%'

def fmt_ratio(v):
    if v is None: return '—'
    return f'{v:.2f}'

def make_table(ax, cell_data, col_headers, row_colors=None, highlight_row=None,
               col_widths=None, fontsize=7.2, row_height=1.35, header_color=None):
    """Draw a clean professional table."""
    ax.axis('off')
    if header_color is None: header_color = C['navy']
    n_cols = len(col_headers)
    if col_widths is None:
        col_widths = [1.0/n_cols] * n_cols
    tbl = ax.table(cellText=cell_data, colLabels=col_headers,
                   cellLoc='center', loc='center', colWidths=col_widths)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)
    tbl.scale(1, row_height)
    n_data_rows = len(cell_data)
    for (r, c_), cell in tbl.get_celld().items():
        cell.set_linewidth(0)
        cell.PAD = 0.04
        if r == 0:
            cell.set_facecolor(header_color)
            cell.set_text_props(color=C['white'], fontweight='bold', fontsize=fontsize - 0.3)
            cell.set_edgecolor(header_color)
            cell.set_linewidth(0)
        else:
            bg = C['gray1'] if r % 2 == 0 else C['white']
            if highlight_row is not None and r == highlight_row:
                bg = C['accent_lt']
                cell.set_text_props(fontweight='bold', color=C['navy'])
            cell.set_facecolor(bg)
            cell.set_edgecolor(C['gray2'])
            cell.set_linewidth(0.3)
            if c_ == 0:
                cell.set_text_props(fontweight='bold', fontsize=fontsize - 0.3, color=C['gray6'])
    # Bottom border under header
    for c_ in range(n_cols):
        cell = tbl.get_celld().get((0, c_))
        if cell:
            cell.set_edgecolor(C['accent'])
            cell.visible_edges = 'B'
            cell.set_linewidth(1.5)
    return tbl


# ═══════════════════════════════════════════════════════════════
# PAGE 1
# ═══════════════════════════════════════════════════════════════
fig1 = plt.figure(figsize=(8.27, 11.69), facecolor=C['white'])  # A4

header_bar(fig1, 0.975, 0.935, 'BSE Midcap 150 Momentum 30 Index',
           'Index Factsheet  |  Data as of June 19, 2026')

# ── Key Metrics Strip ──
ax_kpi = fig1.add_axes([0.03, 0.875, 0.94, 0.05])
ax_kpi.axis('off'); ax_kpi.set_xlim(0, 1); ax_kpi.set_ylim(0, 1)
# Background band
ax_kpi.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle='round,pad=0.01',
                  fc=C['gray1'], ec=C['gray3'], lw=0.5, transform=ax_kpi.transAxes))

kpis = [
    ('27.7%', '15Y CAGR'),
    ('28.6%', '10Y CAGR'),
    ('35.5%', '7Y CAGR'),
    ('30.4%', '5Y CAGR'),
    ('33.8%', '3Y CAGR'),
    ('13.0%', '1Y Return'),
    ('6.2%', 'YTD 2026'),
]
for i, (val, lbl) in enumerate(kpis):
    x = 0.02 + i * 0.14
    ax_kpi.text(x + 0.06, 0.65, val, fontsize=11, fontweight='bold', color=C['navy'],
                ha='center', va='center', transform=ax_kpi.transAxes)
    ax_kpi.text(x + 0.06, 0.2, lbl, fontsize=5.8, color=C['gray5'],
                ha='center', va='center', transform=ax_kpi.transAxes)
    if i < len(kpis) - 1:
        ax_kpi.plot([x + 0.125, x + 0.125], [0.15, 0.85], color=C['gray3'],
                    lw=0.5, transform=ax_kpi.transAxes)

# ── Growth of ₹10,000 Chart ──
section_label(fig1, 0.03, 0.862, 'Growth of ₹10,000 Invested (Apr 2005 – Jun 2026)')
ax_grow = fig1.add_axes([0.055, 0.625, 0.55, 0.225])

grow_cols = {
    'NIFTY MIDCAP150 MOMENTUM 50': ('Nifty Mid150 Mom 50', C['accent'], 1.8, '-'),
    'NIFTY200MOMENTM30':           ('Nifty200 Mom 30',     C['teal'],  1.2, '-'),
    'NIFTY MIDCAP 150':            ('Nifty MidCap 150',    C['gray4'], 0.9, '--'),
    'NIFTY 100':                   ('Nifty 100',           C['gray3'], 0.9, ':'),
}

nav_grow = nifty_navs[list(grow_cols.keys())].dropna()
end_vals = {}
for col, (lbl, clr, lw, ls) in grow_cols.items():
    normalized = nav_grow[col] / nav_grow[col].iloc[0] * 10000
    ax_grow.plot(normalized.index, normalized.values, color=clr, lw=lw,
                 ls=ls, label=lbl, alpha=0.85)
    end_vals[lbl] = (normalized.values[-1], clr)

ax_grow.set_yscale('log')
ax_grow.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'₹{x/1000:.0f}L' if x >= 100000 else f'₹{x/1000:.0f}K' if x >= 1000 else f'₹{x:.0f}'))
ax_grow.set_ylabel('')
ax_grow.tick_params(axis='both', labelsize=5.5, length=2)
ax_grow.spines['top'].set_visible(False)
ax_grow.spines['right'].set_visible(False)
ax_grow.spines['left'].set_color(C['gray3'])
ax_grow.spines['bottom'].set_color(C['gray3'])
ax_grow.grid(axis='y', color=C['gray2'], lw=0.3, alpha=0.5)
import pandas as pd_dates
right_pad = pd.Timedelta(days=400)
ax_grow.set_xlim(nav_grow.index[0], nav_grow.index[-1] + right_pad)

# End-of-line labels
sorted_end = sorted(end_vals.items(), key=lambda x: -x[1][0])
offsets_y = [0, 0, 0, 0]
prev_y = None
for i, (lbl, (val, clr)) in enumerate(sorted_end):
    val_str = f'₹{val/100000:.1f}L' if val >= 100000 else f'₹{val/1000:.0f}K'
    y_off = 0
    if prev_y is not None and abs(np.log10(val) - np.log10(prev_y)) < 0.05:
        y_off = -8
    ax_grow.annotate(f'{lbl} {val_str}', xy=(nav_grow.index[-1], val),
                     xytext=(6, y_off), textcoords='offset points',
                     fontsize=4.6, color=clr, fontweight='bold', va='center')
    prev_y = val

# ── Methodology Box ──
ax_meth = fig1.add_axes([0.645, 0.625, 0.33, 0.23])
ax_meth.axis('off'); ax_meth.set_xlim(0, 1); ax_meth.set_ylim(0, 1)
ax_meth.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle='round,pad=0.02',
                   fc=C['navy'], ec=C['accent'], lw=0.8, transform=ax_meth.transAxes))

ax_meth.text(0.5, 0.93, 'INDEX METHODOLOGY', fontsize=8, fontweight='bold',
             color=C['accent'], ha='center', va='top', transform=ax_meth.transAxes)

meth = [
    ('Universe', 'BSE MidCap 150'),
    ('Portfolio', '30 Stocks'),
    ('Factor', 'Momentum (Vol-adjusted)'),
    ('Score', '6M + 12M Return / Vol'),
    ('Weighting', 'Momentum Score\n(max 10% per stock)'),
    ('Rebalance', 'Semi-Annual\n(June & December)'),
    ('Base Date', '03 Apr 2006'),
    ('Base Value', '1,000'),
]
for i, (k, v) in enumerate(meth):
    y = 0.83 - i * 0.103
    ax_meth.text(0.08, y, k, fontsize=6, fontweight='bold', color=C['accent_lt'],
                 va='top', transform=ax_meth.transAxes)
    ax_meth.text(0.42, y, v, fontsize=6, color=C['white'],
                 va='top', transform=ax_meth.transAxes)

# ── PTP Performance Table ──
section_label(fig1, 0.03, 0.608, 'Point-to-Point Performance (CAGR)')

ax_ptp = fig1.add_axes([0.03, 0.49, 0.94, 0.11])
periods_ptp = ['YTD \'26', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y']
periods_ptp_key = ['YTD 2026', '1 Year', '2 Years', '3 Years', '5 Years', '7 Years', '10 Years', '15 Years']

ptp_rows = []
for idx_name in ALL_INDICES:
    row = [IDX_SHORT[idx_name]]
    for pk in periods_ptp_key:
        v = perf_data.get(pk, {}).get(idx_name)
        row.append(fmt_pct(v))
    ptp_rows.append(row)

make_table(ax_ptp, ptp_rows, ['Index'] + periods_ptp, highlight_row=1,
           col_widths=[0.18] + [0.1025]*8, fontsize=6.8)

# ── Annualized Volatility Table ──
section_label(fig1, 0.03, 0.478, 'Annualized Volatility (Std. Deviation)')

ax_vol = fig1.add_axes([0.03, 0.36, 0.94, 0.11])
vol_rows = []
for idx_name in ALL_INDICES:
    row = [IDX_SHORT[idx_name]]
    for pk in periods_ptp_key:
        v = vol_data.get(pk, {}).get(idx_name)
        row.append(fmt_pct(v))
    vol_rows.append(row)

make_table(ax_vol, vol_rows, ['Index'] + periods_ptp, highlight_row=1,
           col_widths=[0.18] + [0.1025]*8, fontsize=6.8)

# ── CY Returns Heatmap ──
section_label(fig1, 0.03, 0.348, 'Calendar Year Returns')

ax_cy = fig1.add_axes([0.03, 0.105, 0.94, 0.235])
years = list(range(2006, 2026))
cy_matrix = []
cy_row_labels = []
for idx_name in ALL_INDICES:
    cy_row_labels.append(IDX_SHORT[idx_name])
    row = []
    for yr in years:
        v = cy_data.get(yr, {}).get(idx_name)
        row.append(v if v is not None else np.nan)
    cy_matrix.append(row)

cy_arr = np.array(cy_matrix)

# Draw as colored cells
ax_cy.axis('off')
n_rows, n_cols = cy_arr.shape
cell_w = 0.82 / n_cols
cell_h = 0.85 / n_rows
x_start = 0.16
y_start = 0.90

# Color mapping: diverging red-white-green
norm = mcolors.TwoSlopeNorm(vmin=-0.70, vcenter=0, vmax=1.0)
cmap_rg = mcolors.LinearSegmentedColormap.from_list('rg',
    [(0.0, '#C0392B'), (0.3, '#F5B7B1'), (0.5, '#FFFFFF'),
     (0.7, '#ABEBC6'), (1.0, '#1E8449')])

# Column headers (years)
for j, yr in enumerate(years):
    ax_cy.text(x_start + j * cell_w + cell_w/2, y_start + 0.04,
               f"'{str(yr)[2:]}", fontsize=5.5, fontweight='bold',
               color=C['navy'], ha='center', va='center', transform=ax_cy.transAxes)

# Row labels
for i, lbl in enumerate(cy_row_labels):
    y = y_start - i * cell_h - cell_h/2
    ax_cy.text(x_start - 0.015, y, lbl, fontsize=5.8, fontweight='bold',
               color=C['gray6'], ha='right', va='center', transform=ax_cy.transAxes)

# Cells
for i in range(n_rows):
    for j in range(n_cols):
        x = x_start + j * cell_w
        y = y_start - i * cell_h - cell_h
        v = cy_arr[i, j]
        if np.isnan(v):
            clr = C['gray2']; txt = '—'
        else:
            clr = cmap_rg(norm(v))
            txt = f'{v*100:.0f}%'
        rect = FancyBboxPatch((x + 0.001, y + 0.003), cell_w - 0.002, cell_h - 0.006,
                               boxstyle='round,pad=0.003', fc=clr,
                               ec=C['gray2'], lw=0.2, transform=ax_cy.transAxes)
        ax_cy.add_patch(rect)
        # Bold for BSE Mom 30 row (i==0)
        fw = 'bold' if i == 0 else 'normal'
        txt_color = C['white'] if (not np.isnan(v) and abs(v) > 0.45) else C['black']
        ax_cy.text(x + cell_w/2, y + cell_h/2, txt, fontsize=5.2,
                   fontweight=fw, color=txt_color, ha='center', va='center',
                   transform=ax_cy.transAxes)

# ── Key Insight Bar ──
ax_insight = fig1.add_axes([0.03, 0.04, 0.94, 0.055])
ax_insight.axis('off'); ax_insight.set_xlim(0,1); ax_insight.set_ylim(0,1)
ax_insight.add_patch(FancyBboxPatch((0,0), 1, 1, boxstyle='round,pad=0.015',
                     fc=C['accent_lt'], ec=C['accent'], lw=0.6, transform=ax_insight.transAxes))

bse_key = 'BSE Midcap 150 Momentum 30'
win_count = sum(1 for yr in range(2006,2026) if yr in cy_data and bse_key in cy_data[yr]
                and all(v <= cy_data[yr][bse_key] for k,v in cy_data[yr].items() if k != bse_key))
outperf_n100 = sum(1 for yr in range(2006,2026) if yr in cy_data
                   and bse_key in cy_data[yr] and 'Nifty 100' in cy_data[yr]
                   and cy_data[yr][bse_key] > cy_data[yr]['Nifty 100'])

ax_insight.text(0.02, 0.7, 'KEY INSIGHT', fontsize=7, fontweight='bold', color=C['navy'],
                va='center', transform=ax_insight.transAxes)
ax_insight.text(0.12, 0.7,
    f'Top performer in {win_count}/20 calendar years  ·  Outperformed Nifty 100 in {outperf_n100}/20 years  ·  '
    f'0% probability of negative returns on any 5Y+ rolling window',
    fontsize=6.5, color=C['gray6'], va='center', transform=ax_insight.transAxes)
ax_insight.text(0.02, 0.25,
    'Volatility-adjusted momentum filtering delivers defensive outperformance — comparable or lower drawdowns vs broad midcap indices in corrections (2008, 2011, 2015, 2018, 2020).',
    fontsize=6, color=C['gray5'], va='center', transform=ax_insight.transAxes, fontstyle='italic')

# Footer
fig1.text(0.04, 0.012, 'Source: BSE India, NSE India. All returns are TRI-based. CAGR shown for periods > 1 year. Past performance is not indicative of future results.',
          fontsize=4.8, color=C['gray4'])
fig1.text(0.96, 0.012, 'Page 1 of 2', fontsize=5.5, color=C['gray4'], ha='right')

fig1.savefig(f'{OUT_DIR}/factsheet_page1.png', dpi=200, facecolor=C['white'], edgecolor='none')
print("Page 1 done.")


# ═══════════════════════════════════════════════════════════════
# PAGE 2
# ═══════════════════════════════════════════════════════════════
fig2 = plt.figure(figsize=(8.27, 11.69), facecolor=C['white'])

header_bar(fig2, 0.975, 0.94, 'Performance Deep Dive & Risk Analysis',
           'Rolling Returns  ·  Risk-Adjusted Metrics  ·  Active Fund Comparison')

# ── Rolling Returns — Average CAGR ──
section_label(fig2, 0.03, 0.925, 'Rolling Returns — Average Annualized CAGR')

ax_r1 = fig2.add_axes([0.03, 0.82, 0.94, 0.095])
roll_keys = ['1YR Rolling Return','3YR Rolling Return','5YR Rolling Return',
             '7YR Rolling Return','10YR Rolling Return']
roll_labels = ['1 Year','3 Year','5 Year','7 Year','10 Year']

r1_rows = []
for idx_name in ALL_INDICES:
    row = [IDX_SHORT[idx_name]]
    for rk in roll_keys:
        rd = rolling_data.get(rk, {}).get(idx_name)
        row.append(fmt_pct(rd['Avg']) if rd else '—')
    r1_rows.append(row)

make_table(ax_r1, r1_rows, ['Index'] + roll_labels, highlight_row=1,
           col_widths=[0.20] + [0.16]*5, fontsize=7)

# ── Rolling Returns — Negative Instance Rate ──
section_label(fig2, 0.03, 0.815, 'Rolling Returns — Probability of Negative Returns')

ax_r2 = fig2.add_axes([0.03, 0.715, 0.94, 0.095])
r2_rows = []
for idx_name in ALL_INDICES:
    row = [IDX_SHORT[idx_name]]
    for rk in roll_keys:
        rd = rolling_data.get(rk, {}).get(idx_name)
        if rd and rd['Total'] > 0:
            neg_pct = rd['Neg'] / rd['Total']
            row.append(fmt_pct(neg_pct))
        else:
            row.append('—')
    r2_rows.append(row)

tbl_r2 = make_table(ax_r2, r2_rows, ['Index'] + roll_labels, highlight_row=1,
                    col_widths=[0.20] + [0.16]*5, fontsize=7)
# Color code negative-rate cells
for (r, c_), cell in tbl_r2.get_celld().items():
    if r > 0 and c_ > 0:
        txt = cell.get_text().get_text()
        try:
            v = float(txt.replace('%',''))
            if v == 0:
                cell.set_facecolor(C['green_lt'])
                cell.set_text_props(color=C['green'], fontweight='bold')
            elif v > 20:
                cell.set_facecolor(C['red_lt'])
                cell.set_text_props(color=C['red'])
        except: pass

# ── Rolling Returns Range Chart ──
section_label(fig2, 0.03, 0.705, 'Rolling Return Range (Min / Avg / Max)')

ax_rng = fig2.add_axes([0.05, 0.51, 0.50, 0.185])

rng_indices_short = [IDX_SHORT[n] for n in ALL_INDICES]
x = np.arange(len(ALL_INDICES))
width = 0.25
rng_periods = [('1YR Rolling Return', C['navy2'], '1Y'),
               ('3YR Rolling Return', C['accent'], '3Y'),
               ('5YR Rolling Return', C['teal'], '5Y')]

for pi, (rk, clr, plbl) in enumerate(rng_periods):
    avgs, mins, maxs = [], [], []
    for idx_name in ALL_INDICES:
        rd = rolling_data.get(rk, {}).get(idx_name, {})
        avgs.append(rd.get('Avg', 0))
        mins.append(rd.get('Min', 0))
        maxs.append(rd.get('Max', 0))
    avgs, mins, maxs = np.array(avgs), np.array(mins), np.array(maxs)
    offset = (pi - 1) * width
    bars = ax_rng.bar(x + offset, avgs * 100, width * 0.85, label=plbl,
                       color=clr, alpha=0.88, edgecolor=C['white'], linewidth=0.3)
    ax_rng.errorbar(x + offset, avgs * 100,
                     yerr=[(avgs - mins) * 100, (maxs - avgs) * 100],
                     fmt='none', ecolor=C['gray5'], capsize=1.5, capthick=0.5, lw=0.5)

ax_rng.set_xticks(x)
ax_rng.set_xticklabels([n.replace(' ', '\n') for n in rng_indices_short], fontsize=5.5)
ax_rng.yaxis.set_major_formatter(mticker.PercentFormatter())
ax_rng.set_ylabel('Return (Ann.)', fontsize=6)
ax_rng.axhline(0, color=C['gray3'], lw=0.4)
ax_rng.spines['top'].set_visible(False)
ax_rng.spines['right'].set_visible(False)
ax_rng.spines['left'].set_color(C['gray3'])
ax_rng.spines['bottom'].set_color(C['gray3'])
ax_rng.tick_params(axis='both', labelsize=5.5, length=2)
ax_rng.legend(fontsize=6, loc='upper right', edgecolor=C['gray3'], framealpha=0.95)
ax_rng.grid(axis='y', color=C['gray2'], lw=0.2)

# ── Drawdown Chart ──
section_label(fig2, 0.60, 0.705, 'Drawdown Profile')

ax_dd = fig2.add_axes([0.62, 0.51, 0.35, 0.185])
dd_cols = {
    'NIFTY MIDCAP150 MOMENTUM 50': ('Mid150 Mom 50', C['accent'], 0.8),
    'NIFTY MIDCAP 150':            ('MidCap 150',    C['gray4'], 0.6),
    'NIFTY200MOMENTM30':           ('N200 Mom 30',   C['teal'],  0.7),
    'NIFTY 100':                   ('Nifty 100',     C['gray3'], 0.6),
}
for col, (lbl, clr, lw) in dd_cols.items():
    cum = (1 + daily_ret[col]).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax() * 100
    ax_dd.fill_between(dd.index, dd.values, 0, alpha=0.15, color=clr)
    ax_dd.plot(dd.index, dd.values, color=clr, lw=lw, label=lbl, alpha=0.8)

ax_dd.yaxis.set_major_formatter(mticker.PercentFormatter())
ax_dd.spines['top'].set_visible(False)
ax_dd.spines['right'].set_visible(False)
ax_dd.spines['left'].set_color(C['gray3'])
ax_dd.spines['bottom'].set_color(C['gray3'])
ax_dd.tick_params(axis='both', labelsize=5, length=2)
ax_dd.legend(fontsize=5, loc='lower left', edgecolor=C['gray3'], framealpha=0.9)
ax_dd.grid(axis='y', color=C['gray2'], lw=0.2)
ax_dd.set_ylabel('Drawdown', fontsize=6)

# ── Risk-Adjusted Metrics ──
section_label(fig2, 0.03, 0.498, 'Risk-Adjusted Performance (Since Apr 2005)')

ax_risk = fig2.add_axes([0.03, 0.415, 0.94, 0.075])
risk_order = ['CAGR','Volatility','Sharpe','Sortino','Max DD','Calmar']
risk_headers = ['Index','CAGR','Volatility','Sharpe','Sortino','Max Drawdown','Calmar']

risk_rows = []
risk_display = ['Nifty 100','Nifty Midcap 150','Nifty200 Mom 30','Nifty Mid150 Mom 50']
for nm in risk_display:
    m = rmetrics.get(nm, {})
    row = [nm]
    for k in risk_order:
        v = m.get(k)
        if v is None: row.append('—')
        elif k in ('CAGR','Volatility','Max DD'): row.append(fmt_pct(v))
        else: row.append(fmt_ratio(v))
    risk_rows.append(row)

tbl_risk = make_table(ax_risk, risk_rows, risk_headers, highlight_row=4,
                      col_widths=[0.19]+[0.135]*6, fontsize=6.8)

# ── vs Active Funds — clean bar chart ──
section_label(fig2, 0.03, 0.398, 'BSE Mid150 Mom 30 vs Avg. Active Mid-Cap Fund')

ax_af = fig2.add_axes([0.06, 0.255, 0.50, 0.135])
af_periods = ['1 Year','3 Years','5 Years','7 Years','10 Years']
af_labels = ['1Y','3Y','5Y','7Y','10Y']
idx_ret = [af.get('BSE Midcap 150 Momentum 30 Index', {}).get(p, 0) for p in af_periods]
avg_ret = [af.get('Average of the Mid Cap category', {}).get(p, 0) for p in af_periods]

x_af = np.arange(len(af_periods))
bw = 0.32
b1 = ax_af.bar(x_af - bw/2, [r*100 for r in idx_ret], bw, label='BSE Mid150 Mom 30',
               color=C['navy'], edgecolor=C['white'], lw=0.3)
b2 = ax_af.bar(x_af + bw/2, [r*100 for r in avg_ret], bw, label='Avg Active Mid-Cap',
               color=C['gray4'], edgecolor=C['white'], lw=0.3)

for bar in b1:
    ax_af.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
               f'{bar.get_height():.1f}%', ha='center', fontsize=5.5, fontweight='bold', color=C['navy'])
for bar in b2:
    ax_af.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
               f'{bar.get_height():.1f}%', ha='center', fontsize=5.5, color=C['gray5'])

ax_af.set_xticks(x_af)
ax_af.set_xticklabels(af_labels, fontsize=7)
ax_af.yaxis.set_major_formatter(mticker.PercentFormatter())
ax_af.spines['top'].set_visible(False)
ax_af.spines['right'].set_visible(False)
ax_af.spines['left'].set_color(C['gray3'])
ax_af.spines['bottom'].set_color(C['gray3'])
ax_af.tick_params(axis='both', labelsize=6, length=2)
ax_af.legend(fontsize=6, loc='upper right', edgecolor=C['gray3'])
ax_af.grid(axis='y', color=C['gray2'], lw=0.2)

# ── Momentum Factor Edge (Why Box) ──
section_label(fig2, 0.60, 0.398, 'Why BSE Mid150 Mom 30?')

ax_why = fig2.add_axes([0.60, 0.255, 0.37, 0.135])
ax_why.axis('off'); ax_why.set_xlim(0,1); ax_why.set_ylim(0,1)
ax_why.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.02',
                 fc=C['gray1'], ec=C['gray3'], lw=0.5, transform=ax_why.transAxes))

bullets = [
    ('Highest CAGR', 'across every horizon — 28.6% (10Y)\nvs 21.9% (Nifty Mid150 Mom 50)'),
    ('Concentrated Alpha', '30 stocks vs 50 — higher\nconviction, better factor purity'),
    ('Vol-Adjusted Scoring', 'filters out high-beta mean-\nreverters — lower drawdowns'),
    ('Zero Negative 5Y+', '0% probability of loss on any\n5-year+ rolling window'),
    ('Superior to Active', 'Outperforms avg mid-cap fund\nCAGR across all time horizons'),
]

for i, (title, desc) in enumerate(bullets):
    y = 0.92 - i * 0.195
    ax_why.text(0.05, y, title, fontsize=6.2, fontweight='bold', color=C['navy'],
                va='top', transform=ax_why.transAxes)
    ax_why.text(0.05, y - 0.06, desc, fontsize=5.3, color=C['gray5'],
                va='top', transform=ax_why.transAxes, linespacing=1.25)

# ── Return/Risk Scatter ──
section_label(fig2, 0.03, 0.238, 'Return vs Risk — All Momentum & Midcap Indices')

ax_sc = fig2.add_axes([0.08, 0.095, 0.84, 0.135])

# Plot from PTP (10Y) performance vs 10Y volatility
scatter_data = []
for idx_name in ALL_INDICES:
    ret_10 = perf_data.get('10 Years', {}).get(idx_name)
    vol_10 = vol_data.get('10 Years', {}).get(idx_name)
    if ret_10 is not None and vol_10 is not None:
        scatter_data.append((idx_name, vol_10 * 100, ret_10 * 100))

for idx_name, vol_, ret_ in scatter_data:
    clr = IDX_COLORS.get(idx_name, C['gray4'])
    sz = 120 if idx_name == 'BSE Midcap 150 Momentum 30' else 50
    zorder = 10 if idx_name == 'BSE Midcap 150 Momentum 30' else 5
    marker = '*' if idx_name == 'BSE Midcap 150 Momentum 30' else 'o'
    ax_sc.scatter(vol_, ret_, color=clr, s=sz, zorder=zorder, edgecolors=C['white'],
                  linewidth=0.8, marker=marker)
    # Label
    offset_x = 0.5 if idx_name != 'BSE Midcap 150 Momentum 30' else 0.6
    offset_y = 0.5 if idx_name != 'BSE Midcap 150 Momentum 30' else 0.8
    ax_sc.annotate(IDX_SHORT[idx_name], (vol_, ret_), fontsize=5.5,
                   xytext=(offset_x * 10, offset_y * 8), textcoords='offset points',
                   color=clr, fontweight='bold' if idx_name == 'BSE Midcap 150 Momentum 30' else 'normal',
                   arrowprops=dict(arrowstyle='->', color=C['gray4'], lw=0.4) if idx_name == 'BSE Midcap 150 Momentum 30' else None)

ax_sc.set_xlabel('Volatility (10Y Ann.)', fontsize=7)
ax_sc.set_ylabel('CAGR (10Y)', fontsize=7)
ax_sc.yaxis.set_major_formatter(mticker.PercentFormatter())
ax_sc.xaxis.set_major_formatter(mticker.PercentFormatter())
ax_sc.spines['top'].set_visible(False)
ax_sc.spines['right'].set_visible(False)
ax_sc.spines['left'].set_color(C['gray3'])
ax_sc.spines['bottom'].set_color(C['gray3'])
ax_sc.tick_params(axis='both', labelsize=6, length=2)
ax_sc.grid(True, color=C['gray2'], lw=0.2)

# Arrow annotation: "Higher return, similar vol"
bse_pt = next((v, r) for n, v, r in scatter_data if n == 'BSE Midcap 150 Momentum 30')
ax_sc.annotate('Higher Return\nSimilar Volatility', xy=(bse_pt[0], bse_pt[1]),
               xytext=(bse_pt[0] + 2, bse_pt[1] - 4), fontsize=5, color=C['accent'],
               fontstyle='italic',
               arrowprops=dict(arrowstyle='->', color=C['accent'], lw=0.8))

# ── Disclaimer Footer ──
ax_disc = fig2.add_axes([0.03, 0.015, 0.94, 0.07])
ax_disc.axis('off'); ax_disc.set_xlim(0,1); ax_disc.set_ylim(0,1)
ax_disc.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.01',
                  fc=C['gray1'], ec=C['gray2'], lw=0.3, transform=ax_disc.transAxes))

disc = (
    "Disclaimer: This document is for informational purposes only and does not constitute investment advice, an offer, or solicitation. "
    "Past performance is not indicative of future results. The BSE Midcap 150 Momentum 30 Index is a rules-based index published by BSE India. "
    "All performance data is Total Return Index (TRI) based. Risk-free rate assumed at 6.5% p.a. for ratio calculations. "
    "Risk metrics computed from daily NAV data since common inception (Apr 2005). Active fund comparison uses Regular Plan Growth NAVs. "
    "Investors should consult their financial advisor before making investment decisions. Data Source: BSE India, NSE India, AMFI."
)
ax_disc.text(0.02, 0.85, 'DISCLAIMER', fontsize=5.5, fontweight='bold', color=C['gray5'],
             va='top', transform=ax_disc.transAxes)
ax_disc.text(0.02, 0.65, disc, fontsize=4.5, color=C['gray4'], va='top',
             transform=ax_disc.transAxes, wrap=True, linespacing=1.3)

fig2.text(0.96, 0.008, 'Page 2 of 2', fontsize=5.5, color=C['gray4'], ha='right')

fig2.savefig(f'{OUT_DIR}/factsheet_page2.png', dpi=200, facecolor=C['white'], edgecolor='none')
print("Page 2 done.")


# ═══════════════════════════════════════════════════════════════
# COMBINE INTO PDF (direct figure save — no image round-trip)
# ═══════════════════════════════════════════════════════════════
with PdfPages(f'{OUT_DIR}/BSE_Midcap150_Momentum30_Factsheet.pdf') as pdf:
    pdf.savefig(fig1)
    pdf.savefig(fig2)
plt.close('all')

print(f"\nPDF: {OUT_DIR}/BSE_Midcap150_Momentum30_Factsheet.pdf")
print("Done!")
