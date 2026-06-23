"""
BSE Midcap 150 Momentum 30 — AMC-Grade 3-Page Factsheet (v5)
Actual daily NAV for BSE Mom30. Blue BSE line. Improved CY contrast.
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
    'axes.linewidth': 0.3,
})

BSE = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/c849403c-BSE_Midcap_150_Momentum_30_Returns__Volatility.cleaned.xlsx"
NAV = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/950e4d7f-nifty_all_navs.xlsx"
NAV2 = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/730c2c8c-factor_navs_1.xlsx"
OUT = "/home/user/trading101"
FW, FH = 8.27, 11.69  # A4

# ─── DESIGN TOKENS ───
C = dict(
    navy='#0A1628', navy2='#152742', blue='#1565C0', blue_dk='#0D47A1',
    gold='#C8982C', gold_lt='#F7F0DD',
    teal='#0E7C6B', red='#B83B3B', red_lt='#FCEAEA',
    green='#1B7A42', green_lt='#E3F4EA',
    g1='#F8F9FB', g2='#EEF1F5', g3='#D4D8DE', g4='#9CA3AF',
    g5='#6B7280', g6='#374151', white='#FFFFFF', black='#111827',
)

INDICES = [
    'BSE Midcap 150 Momentum 30',
    'Nifty Midcap150 Momentum 50',
    'Nifty Midcap 150',
    'Nifty200 Mom 30',
    'Nifty 50',
]
IDX_SHORT = {
    'BSE Midcap 150 Momentum 30': 'BSE Mid150 Mom 30',
    'Nifty Midcap150 Momentum 50': 'Nifty Mid150 Mom 50',
    'Nifty Midcap 150': 'Nifty MidCap 150',
    'Nifty200 Mom 30': 'Nifty200 Mom 30',
    'Nifty 50': 'Nifty 50',
}
IDX_CLR = {
    'BSE Midcap 150 Momentum 30': C['blue'],
    'Nifty Midcap150 Momentum 50': C['gold'],
    'Nifty Midcap 150': C['g4'],
    'Nifty200 Mom 30': C['teal'],
    'Nifty 50': C['g5'],
}

# ═══════════════════════════════════════════════════════════════
# DATA LOADING
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

rr = bse_sheets['Rolling Returns']
rolling = {}; cur = None
for _, row in rr.iterrows():
    v = str(row.iloc[1]).strip()
    if 'Rolling Return' in v: cur = v; rolling[cur] = {}
    elif cur and v not in ('nan','NaN',''):
        try: rolling[cur][v] = dict(Min=float(row.iloc[2]), Avg=float(row.iloc[3]), Max=float(row.iloc[4]), Neg=int(float(row.iloc[5])), Tot=int(float(row.iloc[6])))
        except: pass

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

af_raw = bse_sheets['Comparison with active Funds']
af = {}
for idx in range(2, len(af_raw)):
    lbl = str(af_raw.iloc[idx, 1]).strip()
    af[lbl] = {p: float(af_raw.iloc[idx, i+2]) for i, p in enumerate(['1 Year','3 Years','5 Years','7 Years','10 Years']) if pd.notna(af_raw.iloc[idx, i+2])}

# --- Nifty NAV data ---
nifty = pd.read_excel(NAV, sheet_name='Broad & Factor Indices')
nifty['Date'] = pd.to_datetime(nifty['HistoricalDate'], format='mixed', dayfirst=True)
nifty = nifty.dropna(subset=['Date']).sort_values('Date').set_index('Date')

# --- Factor NAV data (includes BSE Mom30 daily) ---
fac = pd.read_excel(NAV2)
fac['Date'] = pd.to_datetime(fac['NAV Date'], format='mixed', dayfirst=True)
fac = fac.dropna(subset=['Date']).sort_values('Date').set_index('Date')

n50 = nifty['NIFTY 50'].dropna()
end_date = n50.index[-1]

def cagr(s, e, y):
    if s <= 0 or y <= 0: return None
    return (e/s)**(1/y) - 1

# Nifty 50 PTP
periods_map = {
    'YTD 2026': ('2025-12-31', None), '6 Months': (None, 0.5), '3 Months': (None, 0.25),
    '1 Year': (None, 1), '2 Years': (None, 2), '3 Years': (None, 3),
    '5 Years': (None, 5), '7 Years': (None, 7), '10 Years': (None, 10), '15 Years': (None, 15),
}
for pname, (fd, yrs) in periods_map.items():
    if fd:
        sd = n50.index[n50.index <= pd.Timestamp(fd)][-1]
        d = (end_date - sd).days
        perf_data.setdefault(pname, {})['Nifty 50'] = (n50.iloc[-1]/n50.loc[sd] - 1) if d < 200 else cagr(n50.loc[sd], n50.iloc[-1], d/365.25)
    else:
        sd = n50.index[n50.index >= end_date - pd.Timedelta(days=int(yrs*365.25))][0]
        sv, ev = n50.loc[sd], n50.iloc[-1]
        perf_data.setdefault(pname, {})['Nifty 50'] = (ev/sv - 1) if yrs <= 1 else cagr(sv, ev, yrs)
    # Volatility
    days_back = int((yrs if yrs else (end_date - pd.Timestamp(fd)).days/365.25) * 365.25)
    sub = n50[n50.index >= end_date - pd.Timedelta(days=days_back)]
    if len(sub) > 50:
        vol_data.setdefault(pname, {})['Nifty 50'] = sub.pct_change().dropna().std() * np.sqrt(252)

# Nifty 50 CY
for yr in range(2006, 2026):
    s_idx = n50.index[n50.index >= pd.Timestamp(f'{yr-1}-12-31')]
    e_idx = n50.index[n50.index <= pd.Timestamp(f'{yr}-12-31')]
    if len(s_idx) > 0 and len(e_idx) > 0:
        cy_data.setdefault(yr, {})['Nifty 50'] = n50.loc[e_idx[-1]] / n50.loc[s_idx[0]] - 1

# Nifty 50 Rolling
for roll_name, roll_days in [('1YR Rolling Return',252),('3YR Rolling Return',756),
                              ('5YR Rolling Return',1260),('7YR Rolling Return',1764),('10YR Rolling Return',2520)]:
    yrs = roll_days / 252
    arr = np.array([cagr(n50.values[i-roll_days], n50.values[i], yrs) for i in range(roll_days, len(n50)) if n50.values[i-roll_days] > 0])
    arr = arr[~np.isnan(arr)]
    rolling.setdefault(roll_name, {})['Nifty 50'] = dict(Min=arr.min(), Avg=arr.mean(), Max=arr.max(), Neg=int((arr<0).sum()), Tot=len(arr))

# Risk metrics
nav_map = {'NIFTY 50':'Nifty 50','NIFTY MIDCAP 150':'Nifty Midcap 150',
           'NIFTY200MOMENTM30':'Nifty200 Mom 30','NIFTY MIDCAP150 MOMENTUM 50':'Nifty Midcap150 Momentum 50'}
nav_df = nifty[list(nav_map.keys())].dropna()
dret = nav_df.pct_change().dropna()
def calc_risk(r, rf=0.065/252):
    ar=(1+r.mean())**252-1; vol=r.std()*np.sqrt(252)
    sh=((r-rf).mean()/r.std())*np.sqrt(252); so=((r-rf).mean()/r[r<0].std())*np.sqrt(252)
    cum=(1+r).cumprod(); dd=(cum-cum.cummax())/cum.cummax(); mdd=dd.min(); cal=ar/abs(mdd) if mdd!=0 else 0
    return dict(CAGR=ar,Vol=vol,Sharpe=sh,Sortino=so,MaxDD=mdd,Calmar=cal)
rmetrics = {nav_map[c]: calc_risk(dret[c]) for c in nav_map}

# ─── BSE Mom30 actual daily NAV ───
bse_k = 'BSE Midcap 150 Momentum 30'
bse_nav_raw = fac['BSE Midcap 150 Momentum 30 Index'].dropna()

# BSE risk metrics from ACTUAL daily returns only (before any extension)
bse_dret = bse_nav_raw.pct_change().dropna()
rmetrics[bse_k] = calc_risk(bse_dret)

# Align risk metrics to common date range (BSE start to BSE end)
common_start = bse_nav_raw.index[0]
common_end = bse_nav_raw.index[-1]
for col_old, nm in nav_map.items():
    sub = dret[col_old].loc[common_start:common_end].dropna()
    if len(sub) > 50:
        rmetrics[nm] = calc_risk(sub)

# Extend BSE NAV for growth chart only
bse_nav = bse_nav_raw.copy()
ytd_ret = perf_data.get('YTD 2026', {}).get(bse_k, 0)
if bse_nav.index[-1] < end_date:
    dec25_idx = bse_nav.index[bse_nav.index <= pd.Timestamp('2025-12-31')]
    if len(dec25_idx) > 0:
        dec25_val = bse_nav.loc[dec25_idx[-1]]
        projected = dec25_val * (1 + ytd_ret)
        bse_nav = pd.concat([bse_nav, pd.Series([projected], index=[end_date])])


# ═══════════════════════════════════════════════════════════════
# DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════
def fp(v, d=1):
    return '—' if v is None else f'{v*100:.{d}f}%'
def fr(v):
    return '—' if v is None else f'{v:.2f}'

def draw_header(fig, title, sub):
    ax = fig.add_axes([0, 0.965, 1, 0.035])
    ax.axis('off'); ax.set_xlim(0,1); ax.set_ylim(0,1)
    ax.add_patch(Rectangle((0,0),1,1, fc=C['navy'], ec='none', transform=ax.transAxes))
    ax.text(0.04, 0.55, title, fontsize=14, fontweight='bold', color=C['white'], va='center')
    ax.text(0.04, 0.15, sub, fontsize=7, color=C['gold'], va='center')
    # Gold accent line
    line = fig.add_axes([0, 0.9625, 1, 0.0025]); line.axis('off')
    line.add_patch(Rectangle((0,0),1,1, fc=C['gold'], ec='none', transform=line.transAxes))

def stitle(fig, x, y, text, fs=8.5):
    fig.text(x, y, text, fontsize=fs, fontweight='bold', color=C['navy'], va='bottom')

def make_tbl(ax, rows, headers, hl_row=None, cw=None, fs=7.0, rh=1.15, cell_colors=None):
    """Manual table renderer. matplotlib's ax.table() silently drops the
    header row under wide/short A4 axes geometry, so we draw cells as
    Rectangle patches with full control. `cell_colors` optionally maps
    (data_row_idx, col_idx) -> dict(fc=..., color=..., bold=bool)."""
    ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    nc = len(headers); nr = len(rows) + 1
    if cw is None: cw = [1/nc]*nc
    xs = [0.0]
    for w in cw: xs.append(xs[-1] + w)
    row_h = 1.0 / nr
    # Header row (navy band, white bold labels)
    for ci in range(nc):
        x0, x1 = xs[ci], xs[ci+1]; y0 = 1.0 - row_h
        ax.add_patch(Rectangle((x0, y0), x1-x0, row_h, fc=C['navy'], ec='none', zorder=1))
        ax.text((x0+x1)/2, y0 + row_h/2, headers[ci], ha='center', va='center',
                color=C['white'], fontweight='bold', fontsize=fs-0.2, zorder=3)
    ax.plot([0, 1], [1.0-row_h, 1.0-row_h], color=C['gold'], lw=1.4, zorder=4)
    # Data rows
    for ri, row in enumerate(rows):
        y1 = 1.0 - row_h*(ri+1); y0 = y1 - row_h
        is_hl = hl_row is not None and (ri+1) == hl_row
        base_bg = C['gold_lt'] if is_hl else (C['g1'] if (ri+1) % 2 == 0 else C['white'])
        for ci in range(nc):
            x0, x1 = xs[ci], xs[ci+1]
            cc = cell_colors.get((ri, ci)) if cell_colors else None
            bg = cc['fc'] if (cc and 'fc' in cc) else base_bg
            ax.add_patch(Rectangle((x0, y0), x1-x0, row_h, fc=bg, ec=C['g2'], lw=0.2, zorder=1))
            if ci == 0:
                ax.text((x0+x1)/2, y0+row_h/2, row[ci], ha='center', va='center',
                        color=C['navy'] if is_hl else C['g6'], fontweight='bold',
                        fontsize=fs-0.4, zorder=3)
            else:
                tcolor = cc['color'] if (cc and 'color' in cc) else C['navy']
                tbold = 'bold' if (is_hl or (cc and cc.get('bold'))) else 'normal'
                ax.text((x0+x1)/2, y0+row_h/2, row[ci], ha='center', va='center',
                        color=tcolor, fontweight=tbold, fontsize=fs, zorder=3)
    return None

def clean_ax(ax):
    for s in ['top','right']: ax.spines[s].set_visible(False)
    for s in ['left','bottom']: ax.spines[s].set_color(C['g3'])
    ax.tick_params(axis='both', labelsize=5.5, length=2)
    ax.grid(axis='y', color=C['g2'], lw=0.2)

def footer(fig, page, total):
    fig.text(0.04, 0.01, 'Source: BSE India, NSE India. TRI-based returns. CAGR for periods >1Y. Past performance is not indicative of future results.',
             fontsize=4.5, color=C['g4'])
    fig.text(0.96, 0.01, f'Page {page} of {total}', fontsize=5, color=C['g4'], ha='right')


# ═══════════════════════════════════════════════════════════════
#  PAGE 1 — Overview & Performance
# ═══════════════════════════════════════════════════════════════
fig1 = plt.figure(figsize=(FW, FH), facecolor=C['white'])
draw_header(fig1, 'BSE Midcap 150 Momentum 30 Index', f'Index Factsheet  |  Data as of {end_date.strftime("%B %d, %Y")}')

# ── KPI Strip: y = 0.905 to 0.945 ──
ax_kpi = fig1.add_axes([0.035, 0.905, 0.93, 0.042])
ax_kpi.axis('off'); ax_kpi.set_xlim(0,1); ax_kpi.set_ylim(0,1)
ax_kpi.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.008',
                 fc=C['g1'], ec=C['g3'], lw=0.4, transform=ax_kpi.transAxes))
kpi_def = [('15 Years','15Y CAGR'),('10 Years','10Y CAGR'),('7 Years','7Y CAGR'),
           ('5 Years','5Y CAGR'),('3 Years','3Y CAGR'),('1 Year','1Y Return'),('YTD 2026','YTD 2026')]
kpis = [(fp(perf_data.get(pk,{}).get(bse_k), 1), lbl) for pk, lbl in kpi_def]
for i,(v,l) in enumerate(kpis):
    x = 0.01 + i * 0.14
    ax_kpi.text(x+0.07, 0.68, v, fontsize=11, fontweight='bold', color=C['navy'], ha='center', va='center')
    ax_kpi.text(x+0.07, 0.22, l, fontsize=5.5, color=C['g5'], ha='center', va='center')
    if i < len(kpis)-1:
        ax_kpi.plot([x+0.14, x+0.14], [0.15, 0.85], color=C['g3'], lw=0.4, transform=ax_kpi.transAxes)

# ── Growth Chart: y = 0.61 to 0.89 ──
stitle(fig1, 0.04, 0.895, 'Growth of ₹10,000 Invested')
ax_g = fig1.add_axes([0.06, 0.62, 0.88, 0.265])

# Use BSE start date as common start for apples-to-apples comparison
grow_map = {
    'NIFTY MIDCAP150 MOMENTUM 50': ('Nifty Mid150 Mom 50', C['gold'], 1.5, '-'),
    'NIFTY200MOMENTM30':           ('Nifty200 Mom 30',     C['teal'], 1.1, '-'),
    'NIFTY MIDCAP 150':            ('Nifty MidCap 150',    C['g4'],   0.8, '--'),
    'NIFTY 50':                    ('Nifty 50',            C['g5'],   0.8, '--'),
}
chart_start = bse_nav_raw.index[0]  # Jun 20, 2005 — common start
nav_g = nifty[list(grow_map.keys())].loc[chart_start:].dropna()
ends = {}
for col, (lbl, clr, lw, ls) in grow_map.items():
    series = nav_g[col]
    norm = series / series.iloc[0] * 10000
    ax_g.plot(norm.index, norm.values, color=clr, lw=lw, ls=ls, alpha=0.8, zorder=3)
    ends[lbl] = (norm.values[-1], clr)

# BSE Mom30 line — actual daily NAV data (normalized from same start date)
bse_plot = bse_nav.loc[chart_start:]
bse_norm = bse_plot / bse_plot.iloc[0] * 10000
ax_g.plot(bse_norm.index, bse_norm.values, color=C['blue'], lw=2.5, ls='-',
          alpha=0.95, zorder=5, label='BSE Mid150 Mom 30')
ends['BSE Mid150 Mom 30'] = (bse_norm.values[-1], C['blue'])

ax_g.set_yscale('log')
y_fmt = lambda x, _: f'₹{x/100000:.1f}L' if x >= 100000 else (f'₹{x/1000:.0f}K' if x >= 1000 else f'₹{x:.0f}')
ax_g.yaxis.set_major_formatter(mticker.FuncFormatter(y_fmt))
clean_ax(ax_g); ax_g.grid(axis='y', color=C['g2'], lw=0.25, alpha=0.5)
ax_g.set_xlim(chart_start - pd.Timedelta(days=30), end_date + pd.Timedelta(days=900))

# End-of-line labels sorted top-to-bottom with spacing
sorted_e = sorted(ends.items(), key=lambda x: -x[1][0])
used_y = []
for lbl, (val, clr) in sorted_e:
    val_s = f'₹{val/100000:.1f}L' if val >= 100000 else f'₹{val/1000:.0f}K'
    fw = 'bold' if lbl == 'BSE Mid150 Mom 30' else 'normal'
    fz = 6 if lbl == 'BSE Mid150 Mom 30' else 5
    ax_g.annotate(f'{lbl}  {val_s}', xy=(end_date, val),
                  xytext=(10, 0), textcoords='offset points',
                  fontsize=fz, color=clr, fontweight=fw, va='center')

# ── PTP Table: y = 0.44 to 0.58 ──
stitle(fig1, 0.04, 0.585, 'Point-to-Point Performance (CAGR)')
ax_ptp = fig1.add_axes([0.035, 0.445, 0.93, 0.132])

p_keys = ['YTD 2026','1 Year','2 Years','3 Years','5 Years','7 Years','10 Years','15 Years']
p_hdrs = ['Index', "YTD '26", '1Y', '2Y', '3Y', '5Y', '7Y', '10Y', '15Y']
ptp_rows = []
for idx in INDICES:
    row = [IDX_SHORT[idx]]
    for pk in p_keys:
        row.append(fp(perf_data.get(pk, {}).get(idx)))
    ptp_rows.append(row)
make_tbl(ax_ptp, ptp_rows, p_hdrs, hl_row=1, cw=[0.175]+[0.103]*8)

# ── Volatility Table: y = 0.24 to 0.38 ──
stitle(fig1, 0.04, 0.395, 'Annualized Volatility')
ax_vol = fig1.add_axes([0.035, 0.255, 0.93, 0.132])

vol_rows = []
for idx in INDICES:
    row = [IDX_SHORT[idx]]
    for pk in p_keys:
        row.append(fp(vol_data.get(pk, {}).get(idx)))
    vol_rows.append(row)
make_tbl(ax_vol, vol_rows, p_hdrs, hl_row=1, cw=[0.175]+[0.103]*8)

# ── Return/Risk Profile (compact): y = 0.04 to 0.22 ──
stitle(fig1, 0.04, 0.225, 'Return vs Risk Profile — 10Y CAGR vs Volatility')
ax_sc = fig1.add_axes([0.10, 0.05, 0.80, 0.165])

sdata = []
for idx in INDICES:
    ret_ = perf_data.get('10 Years', {}).get(idx)
    vol_ = vol_data.get('10 Years', {}).get(idx)
    if ret_ is not None and vol_ is not None:
        sdata.append((idx, vol_*100, ret_*100))

for idx, vl, rt in sdata:
    clr = IDX_CLR.get(idx, C['g4'])
    sz = 180 if idx == bse_k else 60
    mk = '*' if idx == bse_k else 'o'
    zo = 10 if idx == bse_k else 5
    ax_sc.scatter(vl, rt, color=clr, s=sz, marker=mk, zorder=zo, edgecolors=C['white'], linewidth=0.8)

# Smart label placement
for idx, vl, rt in sdata:
    clr = IDX_CLR.get(idx, C['g4'])
    if idx == bse_k:
        ax_sc.annotate(IDX_SHORT[idx], (vl, rt), xytext=(15, 5), textcoords='offset points',
                       fontsize=6.5, fontweight='bold', color=clr,
                       arrowprops=dict(arrowstyle='->', color=C['blue'], lw=0.8))
    else:
        y_off = 8 if rt < 22 else -10
        ax_sc.annotate(IDX_SHORT[idx], (vl, rt), xytext=(8, y_off), textcoords='offset points',
                       fontsize=5.5, color=clr)

ax_sc.set_xlabel('Volatility (10Y Ann.)', fontsize=7)
ax_sc.set_ylabel('CAGR (10Y)', fontsize=7)
ax_sc.xaxis.set_major_formatter(mticker.PercentFormatter())
ax_sc.yaxis.set_major_formatter(mticker.PercentFormatter())
clean_ax(ax_sc); ax_sc.grid(True, color=C['g2'], lw=0.2)

footer(fig1, 1, 3)


# ═══════════════════════════════════════════════════════════════
#  PAGE 2 — Calendar Year & Rolling Returns
# ═══════════════════════════════════════════════════════════════
fig2 = plt.figure(figsize=(FW, FH), facecolor=C['white'])
draw_header(fig2, 'Calendar Year & Rolling Returns', 'Annual Performance  |  Rolling Window Analysis')

# ── CY Returns Heatmap: y = 0.58 to 0.94 ──
stitle(fig2, 0.04, 0.945, 'Calendar Year Returns')
ax_cy = fig2.add_axes([0.035, 0.60, 0.93, 0.335])
ax_cy.axis('off')

years = list(range(2006, 2026))
cy_mat = []
for idx in INDICES:
    cy_mat.append([cy_data.get(yr, {}).get(idx, np.nan) for yr in years])
cy_arr = np.array(cy_mat)

nr, nc = cy_arr.shape
cw_ = 0.82 / nc
ch_ = 0.78 / nr
x0, y0 = 0.155, 0.92

norm_cy = mcolors.TwoSlopeNorm(vmin=-0.60, vcenter=0, vmax=1.0)
cmap_cy = mcolors.LinearSegmentedColormap.from_list('rg', [
    (0.0, '#B71C1C'), (0.15, '#E53935'), (0.35, '#FFCDD2'), (0.5, '#F5F5F5'),
    (0.65, '#A5D6A7'), (0.85, '#2E7D32'), (1.0, '#1B5E20')])

for j, yr in enumerate(years):
    ax_cy.text(x0 + j*cw_ + cw_/2, y0 + 0.035, f"'{str(yr)[2:]}", fontsize=6.5,
               fontweight='bold', color=C['navy'], ha='center', va='center', transform=ax_cy.transAxes)

for i, idx in enumerate(INDICES):
    y = y0 - i*ch_ - ch_/2
    ax_cy.text(x0 - 0.012, y, IDX_SHORT[idx], fontsize=6.5, fontweight='bold',
               color=C['g6'], ha='right', va='center', transform=ax_cy.transAxes)

for i in range(nr):
    for j in range(nc):
        x = x0 + j*cw_; y = y0 - i*ch_ - ch_
        v = cy_arr[i, j]
        if np.isnan(v): fc, txt = C['g2'], '—'
        else: fc, txt = cmap_cy(norm_cy(v)), f'{v*100:.0f}%'
        ax_cy.add_patch(FancyBboxPatch((x+0.001, y+0.006), cw_-0.002, ch_-0.012,
                        boxstyle='round,pad=0.003', fc=fc, ec=C['g2'], lw=0.15, transform=ax_cy.transAxes))
        if np.isnan(v):
            tc = C['g5']
        elif v > 0.35 or v < -0.30:
            tc = C['white']
        elif abs(v) < 0.08:
            tc = C['g6']
        else:
            tc = C['white'] if (v > 0.20 or v < -0.15) else C['black']
        fw = 'bold' if i == 0 else 'normal'
        ax_cy.text(x + cw_/2, y + ch_/2, txt, fontsize=6, fontweight=fw, color=tc,
                   ha='center', va='center', transform=ax_cy.transAxes)

# ── Key Highlights: y = 0.465 to 0.57 ──
ax_hl = fig2.add_axes([0.035, 0.465, 0.93, 0.105])
ax_hl.axis('off'); ax_hl.set_xlim(0,1); ax_hl.set_ylim(0,1)
ax_hl.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.012',
                fc=C['gold_lt'], ec=C['gold'], lw=0.5, transform=ax_hl.transAxes))

wins = sum(1 for yr in range(2006,2026) if yr in cy_data and bse_k in cy_data[yr]
           and all(v <= cy_data[yr][bse_k] for k,v in cy_data[yr].items()
                   if k != bse_k and k != 'Nifty 100' and k != 'BSE 150 Midcap'))
ov50 = sum(1 for yr in range(2006,2026) if yr in cy_data and bse_k in cy_data[yr]
           and 'Nifty 50' in cy_data.get(yr,{}) and cy_data[yr][bse_k] > cy_data[yr]['Nifty 50'])

ax_hl.text(0.015, 0.88, 'KEY HIGHLIGHTS', fontsize=7.5, fontweight='bold', color=C['navy'], va='top')
highlights = [
    f'Top-performing index in {wins} of 20 calendar years among momentum & midcap peers',
    f'Outperformed Nifty 50 in {ov50} of 20 calendar years — across bull and bear markets',
    'Zero probability of negative returns on any 5-year or longer rolling window',
    'Highest average rolling CAGR across 1Y, 3Y, 5Y, 7Y, and 10Y horizons vs all peers',
]
for i, h in enumerate(highlights):
    ax_hl.text(0.02, 0.68 - i*0.19, f'•  {h}', fontsize=6.5, color=C['g6'], va='top')

# ── Rolling Avg CAGR: y = 0.29 to 0.43 ──
stitle(fig2, 0.04, 0.44, 'Rolling Returns — Average Annualized CAGR')
ax_r1 = fig2.add_axes([0.035, 0.295, 0.93, 0.135])

rk_ = ['1YR Rolling Return','3YR Rolling Return','5YR Rolling Return','7YR Rolling Return','10YR Rolling Return']
rl_ = ['1 Year','3 Year','5 Year','7 Year','10 Year']
r1_rows = []
for idx in INDICES:
    row = [IDX_SHORT[idx]]
    for k in rk_:
        rd = rolling.get(k, {}).get(idx)
        row.append(fp(rd['Avg']) if rd else '—')
    r1_rows.append(row)
make_tbl(ax_r1, r1_rows, ['Index']+rl_, hl_row=1, cw=[0.22]+[0.156]*5)

# ── Rolling Neg Probability: y = 0.10 to 0.24 ──
stitle(fig2, 0.04, 0.255, 'Rolling Returns — Probability of Negative Returns')
ax_r2 = fig2.add_axes([0.035, 0.11, 0.93, 0.135])

r2_rows = []
r2_colors = {}
for ri, idx in enumerate(INDICES):
    row = [IDX_SHORT[idx]]
    for ci, k in enumerate(rk_):
        rd = rolling.get(k, {}).get(idx)
        if rd and rd['Tot'] > 0:
            prob = rd['Neg']/rd['Tot']
            row.append(fp(prob))
            if prob == 0:
                r2_colors[(ri, ci+1)] = dict(fc=C['green_lt'], color=C['green'], bold=True)
            elif prob > 0.20:
                r2_colors[(ri, ci+1)] = dict(fc=C['red_lt'], color=C['red'])
        else:
            row.append('—')
    r2_rows.append(row)

make_tbl(ax_r2, r2_rows, ['Index']+rl_, hl_row=1, cw=[0.22]+[0.156]*5, cell_colors=r2_colors)

footer(fig2, 2, 3)


# ═══════════════════════════════════════════════════════════════
#  PAGE 3 — Risk Analysis & Comparison
# ═══════════════════════════════════════════════════════════════
fig3 = plt.figure(figsize=(FW, FH), facecolor=C['white'])
draw_header(fig3, 'Risk Analysis & Fund Comparison', 'Drawdowns  |  Risk-Adjusted Metrics  |  Active Fund Comparison')

# ── Rolling Range Chart: y = 0.72 to 0.94 ──
stitle(fig3, 0.04, 0.945, 'Rolling Return Range — Min / Avg / Max')
ax_rng = fig3.add_axes([0.06, 0.735, 0.88, 0.20])

x = np.arange(len(INDICES)); w = 0.25
rng_p = [('1YR Rolling Return', C['blue'], '1 Year'),
         ('3YR Rolling Return', C['gold'],  '3 Year'),
         ('5YR Rolling Return', C['teal'],  '5 Year')]

for pi, (k, clr, pl) in enumerate(rng_p):
    avgs, mins, maxs = [], [], []
    for idx in INDICES:
        rd = rolling.get(k, {}).get(idx, {})
        avgs.append(rd.get('Avg',0)); mins.append(rd.get('Min',0)); maxs.append(rd.get('Max',0))
    avgs, mins, maxs = np.array(avgs), np.array(mins), np.array(maxs)
    ax_rng.bar(x + (pi-1)*w, avgs*100, w*0.85, label=pl, color=clr, alpha=0.88, edgecolor=C['white'], lw=0.3)
    ax_rng.errorbar(x + (pi-1)*w, avgs*100, yerr=[(avgs-mins)*100, (maxs-avgs)*100],
                    fmt='none', ecolor=C['g5'], capsize=2, capthick=0.5, lw=0.5)

ax_rng.set_xticks(x)
ax_rng.set_xticklabels([IDX_SHORT[n].replace(' ', '\n') for n in INDICES], fontsize=5.5)
ax_rng.yaxis.set_major_formatter(mticker.PercentFormatter())
ax_rng.axhline(0, color=C['g3'], lw=0.3)
clean_ax(ax_rng); ax_rng.set_ylabel('Annualized Return', fontsize=6.5)
ax_rng.legend(fontsize=6, loc='upper right', edgecolor=C['g3'], framealpha=0.95, handlelength=1.5)

# ── Drawdown Chart: y = 0.50 to 0.70 ──
stitle(fig3, 0.04, 0.715, 'Drawdown Profile (Daily)')
ax_dd = fig3.add_axes([0.06, 0.52, 0.88, 0.185])

dd_map = {
    'NIFTY MIDCAP150 MOMENTUM 50': ('Nifty Mid150 Mom 50', C['gold'], 1.2),
    'NIFTY MIDCAP 150':            ('Nifty MidCap 150',    C['g4'],   0.7),
    'NIFTY200MOMENTM30':           ('Nifty200 Mom 30',     C['teal'], 0.9),
    'NIFTY 50':                    ('Nifty 50',            C['g5'],   0.7),
}
# BSE Mom30 drawdown from actual daily NAV (raw, no extension)
bse_cum = (1 + bse_dret).cumprod()
bse_dd = (bse_cum - bse_cum.cummax()) / bse_cum.cummax() * 100
ax_dd.fill_between(bse_dd.index, bse_dd.values, 0, alpha=0.15, color=C['blue'])
ax_dd.plot(bse_dd.index, bse_dd.values, color=C['blue'], lw=1.8, label='BSE Mid150 Mom 30', alpha=0.9, zorder=5)
for col, (lbl, clr, lw) in dd_map.items():
    cum = (1 + dret[col]).cumprod()
    dd = (cum - cum.cummax()) / cum.cummax() * 100
    ax_dd.fill_between(dd.index, dd.values, 0, alpha=0.08, color=clr)
    ax_dd.plot(dd.index, dd.values, color=clr, lw=lw, label=lbl, alpha=0.8)

ax_dd.yaxis.set_major_formatter(mticker.PercentFormatter())
clean_ax(ax_dd); ax_dd.set_ylabel('Drawdown', fontsize=6.5)
ax_dd.legend(fontsize=5.5, loc='lower left', edgecolor=C['g3'], framealpha=0.9, ncol=2, handlelength=1.2)

# ── Risk Metrics Table: y = 0.36 to 0.49 ──
stitle(fig3, 0.04, 0.50, 'Risk-Adjusted Performance Metrics (Since Jun 2005)')
ax_risk = fig3.add_axes([0.035, 0.355, 0.93, 0.135])

r_hdr = ['Index','CAGR','Volatility','Sharpe','Sortino','Max Drawdown','Calmar']
r_order = ['BSE Midcap 150 Momentum 30','Nifty Midcap150 Momentum 50','Nifty Midcap 150','Nifty200 Mom 30','Nifty 50']
r_rows = []
for nm in r_order:
    m = rmetrics.get(nm, {})
    r_rows.append([IDX_SHORT.get(nm, nm), fp(m.get('CAGR')), fp(m.get('Vol')),
                   fr(m.get('Sharpe')), fr(m.get('Sortino')), fp(m.get('MaxDD')), fr(m.get('Calmar'))])
make_tbl(ax_risk, r_rows, r_hdr, hl_row=1, cw=[0.19]+[0.135]*6, fs=7)

# ── Active Fund Comparison: y = 0.15 to 0.33 ──
stitle(fig3, 0.04, 0.34, 'BSE Mid150 Mom 30 vs Avg. Active Mid-Cap Fund')
ax_af = fig3.add_axes([0.06, 0.155, 0.42, 0.175])

af_p = ['1 Year','3 Years','5 Years','7 Years','10 Years']
af_l = ['1Y','3Y','5Y','7Y','10Y']
ir_ = [af.get('BSE Midcap 150 Momentum 30 Index', {}).get(p, 0) for p in af_p]
ar_ = [af.get('Average of the Mid Cap category', {}).get(p, 0) for p in af_p]

x_af = np.arange(len(af_p)); bw = 0.32
b1 = ax_af.bar(x_af - bw/2, [r*100 for r in ir_], bw, label='BSE Mid150 Mom 30',
               color=C['blue'], edgecolor=C['white'], lw=0.3, zorder=3)
b2 = ax_af.bar(x_af + bw/2, [r*100 for r in ar_], bw, label='Avg Active Mid-Cap',
               color=C['g4'], edgecolor=C['white'], lw=0.3, zorder=3)

for bar in b1:
    ax_af.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.4, f'{bar.get_height():.1f}%',
               ha='center', fontsize=5.5, fontweight='bold', color=C['blue'], zorder=4)
for bar in b2:
    ax_af.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.4, f'{bar.get_height():.1f}%',
               ha='center', fontsize=5.5, color=C['g5'], zorder=4)

ax_af.set_xticks(x_af); ax_af.set_xticklabels(af_l, fontsize=7)
ax_af.yaxis.set_major_formatter(mticker.PercentFormatter()); clean_ax(ax_af)
ax_af.legend(fontsize=5.5, loc='upper left', edgecolor=C['g3'], handlelength=1)

# ── Why Box: y = 0.155 to 0.33 ──
stitle(fig3, 0.535, 0.34, 'Why BSE Mid150 Mom 30?')
ax_why = fig3.add_axes([0.525, 0.155, 0.44, 0.175])
ax_why.axis('off'); ax_why.set_xlim(0,1); ax_why.set_ylim(0,1)
ax_why.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.018',
                 fc=C['g1'], ec=C['g3'], lw=0.4, transform=ax_why.transAxes))

bullets = [
    ('Highest CAGR', '28.6% (10Y) vs 21.9% (Nifty Mid150\nMom 50) & 18.0% (Nifty200 Mom 30)'),
    ('Concentrated Alpha', '30 stocks vs 50 — higher conviction,\nbetter factor purity & payoff'),
    ('Vol-Adjusted Scoring', 'Filters high-beta mean-reverters\n— shallower drawdowns in corrections'),
    ('Zero Negative 5Y+', '0% loss probability on any 5-year+\nrolling window since inception'),
    ('Superior to Active', 'Outperforms avg mid-cap fund\nacross every time horizon'),
]
for i, (title, desc) in enumerate(bullets):
    y = 0.92 - i * 0.19
    ax_why.text(0.04, y, title, fontsize=6.5, fontweight='bold', color=C['navy'], va='top')
    ax_why.text(0.04, y - 0.055, desc, fontsize=5.5, color=C['g5'], va='top', linespacing=1.2)

# ── Disclaimer: y = 0.02 to 0.12 ──
ax_d = fig3.add_axes([0.035, 0.025, 0.93, 0.105])
ax_d.axis('off'); ax_d.set_xlim(0,1); ax_d.set_ylim(0,1)
ax_d.add_patch(FancyBboxPatch((0,0),1,1, boxstyle='round,pad=0.01',
               fc=C['g1'], ec=C['g2'], lw=0.3, transform=ax_d.transAxes))
disc = ("Disclaimer: This document is for informational purposes only and does not constitute investment advice. "
        "Past performance is not indicative of future results. The BSE Midcap 150 Momentum 30 Index is published by BSE India. "
        "All data is TRI-based. Risk-free rate: 6.5% p.a. Risk metrics from daily NAV since Apr 2005. "
        "Active fund comparison uses Regular Plan Growth NAVs (source: AMFI). "
        "Investors should consult their financial advisor before making investment decisions. "
        "Sources: BSE India, NSE India, AMFI.")
ax_d.text(0.015, 0.90, 'DISCLAIMER', fontsize=5.5, fontweight='bold', color=C['g5'], va='top')
ax_d.text(0.015, 0.72, disc, fontsize=4.8, color=C['g4'], va='top', wrap=True, linespacing=1.3)

footer(fig3, 3, 3)


# ═══════════════════════════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════════════════════════
for i, fig in enumerate([fig1, fig2, fig3], 1):
    fig.savefig(f'{OUT}/factsheet_page{i}.png', dpi=220, facecolor=C['white'], edgecolor='none')
print("PNGs saved.")

with PdfPages(f'{OUT}/BSE_Midcap150_Momentum30_Factsheet.pdf') as pdf:
    for fig in [fig1, fig2, fig3]:
        pdf.savefig(fig)
plt.close('all')
print(f"PDF: {OUT}/BSE_Midcap150_Momentum30_Factsheet.pdf")
print("Done!")
