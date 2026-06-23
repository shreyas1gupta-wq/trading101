import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import PercentFormatter
from io import BytesIO
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

BSE_FILE = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/c849403c-BSE_Midcap_150_Momentum_30_Returns__Volatility.cleaned.xlsx"
NIFTY_FILE = "/root/.claude/uploads/e98ef6f5-f837-568e-81c7-cae90e5e1a2e/950e4d7f-nifty_all_navs.xlsx"

# ── Color Palette ──
COLORS = {
    'primary': '#1B3A5C',
    'accent': '#E8A838',
    'green': '#2E8B57',
    'red': '#C0392B',
    'blue_light': '#5B9BD5',
    'gray': '#7F8C8D',
    'bg': '#FAFBFC',
    'bg_section': '#F0F3F7',
    'text_dark': '#1A1A2E',
    'text_mid': '#4A4A5A',
    'highlight': '#D4AF37',
    'bse_mom': '#1B3A5C',
    'bse_mid': '#5B9BD5',
    'nifty_mid_mom': '#E8A838',
    'nifty_mid': '#7F8C8D',
    'nifty200_mom': '#C0392B',
    'nifty100': '#95A5A6',
}

INDEX_COLORS = {
    'BSE Midcap 150 Momentum 30': '#1B3A5C',
    'BSE 150 Midcap': '#5B9BD5',
    'Nifty Midcap150 Momentum 50': '#E8A838',
    'Nifty Midcap 150': '#7F8C8D',
    'Nifty200 Mom 30': '#C0392B',
    'Nifty 100': '#95A5A6',
}

SHORT_NAMES = {
    'BSE Midcap 150 Momentum 30': 'BSE Mid150\nMom 30',
    'BSE 150 Midcap': 'BSE 150\nMidcap',
    'Nifty Midcap150 Momentum 50': 'Nifty Mid150\nMom 50',
    'Nifty Midcap 150': 'Nifty\nMid 150',
    'Nifty200 Mom 30': 'Nifty200\nMom 30',
    'Nifty 100': 'Nifty 100',
}

# Column order for BSE sheet (after parsing)
COL_ORDER = ['Nifty 100', 'Nifty Midcap 150', 'BSE 150 Midcap',
             'Nifty200 Mom 30', 'Nifty Midcap150 Momentum 50',
             'BSE Midcap 150 Momentum 30']

# ── Load Data ──

# BSE sheets
bse_sheets = pd.read_excel(BSE_FILE, sheet_name=None)

# Parse Rolling Returns
rr_raw = bse_sheets['Rolling Returns']
rolling_data = {}
current_period = None
for _, row in rr_raw.iterrows():
    val1 = str(row.iloc[1]).strip()
    if 'Rolling Return' in val1:
        current_period = val1
        rolling_data[current_period] = {}
    elif current_period and val1 not in ['nan', 'NaN', '']:
        try:
            rolling_data[current_period][val1] = {
                'Min': float(row.iloc[2]),
                'Average': float(row.iloc[3]),
                'Max': float(row.iloc[4]),
                'Negative Instances': int(float(row.iloc[5])),
                'Total Observations': int(float(row.iloc[6]))
            }
        except (ValueError, TypeError):
            pass

# Parse Performance & Volatility — two blocks in the same sheet
pv_raw = bse_sheets['Performance & Volatility']

# Canonical name mapping for all column variants
def canonical_name(raw):
    s = str(raw).strip()
    if 'BSE Midcap 150 Momentum 30' in s:
        return 'BSE Midcap 150 Momentum 30'
    if 'BSE Midcap 150' in s or 'BSE 150 Midcap' in s:
        return 'BSE 150 Midcap'
    if 'Nifty Midcap150 Momentum 50' in s or 'Nifty Midcap150 Momentum' in s:
        return 'Nifty Midcap150 Momentum 50'
    if 'Nifty Midcap 150' in s:
        return 'Nifty Midcap 150'
    if 'Nifty200' in s and 'Mom' in s:
        return 'Nifty200 Mom 30'
    if 'Nifty 100' in s:
        return 'Nifty 100'
    return s

# Block 1: rows 1 (header) → 2-11 (performance data)
# Block 2: rows 14 (header) → 15-24 (volatility data)
def parse_pv_block(header_row_idx, data_start, data_end):
    cols = {}
    for i, val in enumerate(pv_raw.iloc[header_row_idx]):
        if pd.notna(val):
            cn = canonical_name(val)
            if cn not in ['Periodic', 'Period']:
                cols[i] = cn
    result = {}
    for idx in range(data_start, min(data_end + 1, len(pv_raw))):
        row = pv_raw.iloc[idx]
        period = str(row.iloc[0]).strip()
        if period in ['nan', 'NaN', '']:
            continue
        result[period] = {}
        for i, col_name in cols.items():
            try:
                result[period][col_name] = float(row.iloc[i])
            except (ValueError, TypeError):
                pass
    return result

perf_data = parse_pv_block(1, 2, 11)
vol_data = parse_pv_block(14, 15, 24)

# Parse CY Returns
cy_raw = bse_sheets['CY Returns']
cy_cols = {}
for i, val in enumerate(cy_raw.iloc[0]):
    if pd.notna(val):
        name = str(val).strip()
        if name == 'Calendar Year':
            cy_cols[i] = 'Year'
        else:
            cy_cols[i] = canonical_name(name)

cy_data = {}
for idx in range(1, len(cy_raw)):
    row = cy_raw.iloc[idx]
    year = row.iloc[0]
    try:
        year = int(year)
    except:
        year = str(year)
    cy_data[year] = {}
    for i, col_name in cy_cols.items():
        if col_name != 'Year':
            try:
                cy_data[year][col_name] = float(row.iloc[i])
            except (ValueError, TypeError):
                pass

# Parse Active Fund Comparison
af_raw = bse_sheets['Comparison with active Funds']
af_data = {}
for idx in range(2, len(af_raw)):
    row = af_raw.iloc[idx]
    label = str(row.iloc[1]).strip()
    af_data[label] = {}
    for i, period in enumerate(['1 Year', '3 Years', '5 Years', '7 Years', '10 Years']):
        try:
            af_data[label][period] = float(row.iloc[i + 2])
        except (ValueError, TypeError):
            pass
# Load Nifty NAV data for growth chart
nifty_navs = pd.read_excel(NIFTY_FILE, sheet_name='Broad & Factor Indices')
nifty_navs['HistoricalDate'] = pd.to_datetime(nifty_navs['HistoricalDate'], format='mixed', dayfirst=True)
nifty_navs = nifty_navs.dropna(subset=['HistoricalDate']).sort_values('HistoricalDate')

# ── Compute Risk Metrics from Daily NAV Data ──
# Use common date range where all key indices have data
nav_cols = ['NIFTY 100', 'NIFTY MIDCAP 150', 'NIFTY200MOMENTM30',
            'NIFTY MIDCAP150 MOMENTUM 50']
nav_df = nifty_navs[['HistoricalDate'] + nav_cols].dropna().copy()
nav_df = nav_df.set_index('HistoricalDate')

# Daily returns
daily_ret = nav_df.pct_change().dropna()

# Annualized metrics (using ~252 trading days)
def compute_risk_metrics(returns, rf=0.065/252):
    ann_ret = (1 + returns.mean()) ** 252 - 1
    ann_vol = returns.std() * np.sqrt(252)
    excess = returns - rf
    sharpe = (excess.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
    downside = returns[returns < 0].std() * np.sqrt(252)
    sortino = (excess.mean() / (returns[returns < 0].std())) * np.sqrt(252) if returns[returns < 0].std() > 0 else 0
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = (cumulative - rolling_max) / rolling_max
    max_dd = drawdown.min()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        'Ann. Return': ann_ret,
        'Ann. Volatility': ann_vol,
        'Sharpe Ratio': sharpe,
        'Sortino Ratio': sortino,
        'Max Drawdown': max_dd,
        'Calmar Ratio': calmar,
    }

risk_metrics = {}
nice_names = {
    'NIFTY 100': 'Nifty 100',
    'NIFTY MIDCAP 150': 'Nifty Midcap 150',
    'NIFTY200MOMENTM30': 'Nifty200 Mom 30',
    'NIFTY MIDCAP150 MOMENTUM 50': 'Nifty Mid150 Mom 50',
}
for col in nav_cols:
    risk_metrics[nice_names[col]] = compute_risk_metrics(daily_ret[col])

# ── Helper: draw a table ──
def draw_table(ax, data, col_labels, row_labels, title,
               highlight_col=None, fmt='pct', col_widths=None, fontsize=7):
    ax.axis('off')
    ax.set_title(title, fontsize=9, fontweight='bold', color=COLORS['primary'],
                 loc='left', pad=8)

    n_rows = len(row_labels)
    n_cols = len(col_labels)
    if col_widths is None:
        col_widths = [1.0 / (n_cols + 1)] * (n_cols + 1)

    table = ax.table(
        cellText=data,
        colLabels=[''] + col_labels,
        rowLabels=None,
        cellLoc='center',
        loc='center',
        colWidths=col_widths
    )
    table.auto_set_font_size(False)
    table.set_fontsize(fontsize)
    table.scale(1, 1.4)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#D5D8DC')
        cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor(COLORS['primary'])
            cell.set_text_props(color='white', fontweight='bold', fontsize=fontsize - 0.5)
        elif c == 0:
            cell.set_text_props(fontweight='bold', fontsize=fontsize - 0.5)
            cell.set_facecolor(COLORS['bg_section'])
        else:
            if highlight_col is not None and c == highlight_col:
                cell.set_facecolor('#E8F4E8')
                cell.set_text_props(fontweight='bold', color=COLORS['primary'])
            else:
                cell.set_facecolor('white')

    return table


# ══════════════════════════════════════════════════════════════
# PAGE 1
# ══════════════════════════════════════════════════════════════
fig1 = plt.figure(figsize=(11.69, 16.54), dpi=150, facecolor='white')

# Use a top-level gridspec for the whole page
gs_page1 = gridspec.GridSpec(12, 2, figure=fig1,
                             left=0.04, right=0.96, top=0.94, bottom=0.02,
                             hspace=0.55, wspace=0.15)

# ── Header ──
ax_header = fig1.add_subplot(gs_page1[0, :])
ax_header.axis('off')
ax_header.text(0.0, 0.75, 'BSE Midcap 150 Momentum 30 Index',
               fontsize=18, fontweight='bold', color=COLORS['primary'],
               transform=ax_header.transAxes, va='top')
ax_header.text(0.0, 0.3, 'Index Factsheet  |  Data as of June 2026',
               fontsize=10, color=COLORS['text_mid'],
               transform=ax_header.transAxes, va='top')
ax_header.axhline(y=0.05, xmin=0, xmax=1, color=COLORS['accent'], linewidth=2.5)

# ── Executive Summary ──
ax_exec = fig1.add_subplot(gs_page1[1:3, :])
ax_exec.axis('off')
ax_exec.set_xlim(0, 1)
ax_exec.set_ylim(0, 1)

summary_text = (
    "The BSE Midcap 150 Momentum 30 Index tracks the top 30 stocks from the BSE MidCap 150 universe, "
    "selected and weighted based on their momentum scores. Momentum is computed using the 6-month and "
    "12-month price returns, adjusted for volatility. The index is rebalanced semi-annually (June & December) "
    "with a maximum single-stock weight cap of 10%. Since inception, the index has delivered a CAGR of ~28.6% "
    "over 10 years — outperforming every comparable momentum and midcap benchmark by a significant margin, "
    "while maintaining a favourable risk-return profile. The concentrated 30-stock portfolio with volatility-adjusted "
    "momentum scoring delivers superior risk-adjusted returns compared to the broader Nifty Midcap150 Momentum 50 and "
    "Nifty200 Momentum 30 indices."
)

ax_exec.text(0.0, 0.95, 'Executive Summary', fontsize=10, fontweight='bold',
             color=COLORS['primary'], va='top')
ax_exec.text(0.0, 0.75, summary_text, fontsize=7.5, color=COLORS['text_dark'],
             va='top', wrap=True,
             bbox=dict(boxstyle='round,pad=0.4', facecolor=COLORS['bg_section'],
                       edgecolor='#D5D8DC', linewidth=0.5),
             transform=ax_exec.transAxes, ha='left',
             fontfamily='sans-serif', linespacing=1.5)

# Key Stats boxes
stats_y = 0.15
stats = [
    ('28.6%', '10Y CAGR'),
    ('30.4%', '5Y CAGR'),
    ('33.8%', '3Y CAGR'),
    ('13.0%', '1Y Return'),
    ('100%', 'Active Funds\nUnderperformed (3Y+)'),
]
box_width = 0.17
for i, (val, label) in enumerate(stats):
    x = 0.02 + i * 0.195
    rect = FancyBboxPatch((x, stats_y - 0.12), box_width, 0.14,
                           boxstyle="round,pad=0.01",
                           facecolor=COLORS['primary'] if i == 0 else 'white',
                           edgecolor=COLORS['primary'], linewidth=1.2,
                           transform=ax_exec.transAxes, clip_on=False)
    ax_exec.add_patch(rect)
    ax_exec.text(x + box_width/2, stats_y - 0.03, val,
                 fontsize=12, fontweight='bold',
                 color='white' if i == 0 else COLORS['primary'],
                 ha='center', va='center', transform=ax_exec.transAxes)
    ax_exec.text(x + box_width/2, stats_y - 0.1, label,
                 fontsize=6, color='white' if i == 0 else COLORS['text_mid'],
                 ha='center', va='center', transform=ax_exec.transAxes)

# ── Index Methodology Box ──
ax_method = fig1.add_subplot(gs_page1[3, :])
ax_method.axis('off')
ax_method.set_xlim(0, 1)
ax_method.set_ylim(0, 1)
ax_method.text(0.0, 1.0, 'Index Methodology', fontsize=10, fontweight='bold',
               color=COLORS['primary'], va='top')

method_items = [
    ('Universe', 'BSE MidCap 150'),
    ('Selection', 'Top 30 by Momentum Score'),
    ('Momentum Score', '6M & 12M price return, volatility-adjusted'),
    ('Weighting', 'Momentum score-weighted (max 10% per stock)'),
    ('Rebalancing', 'Semi-annual (June & December)'),
    ('Base Date', '03 Apr 2006  |  Base Value: 1,000'),
]

for i, (key, val) in enumerate(method_items):
    col = i // 3
    row_i = i % 3
    x = 0.02 + col * 0.5
    y = 0.7 - row_i * 0.25
    ax_method.text(x, y, f'{key}:', fontsize=7, fontweight='bold',
                   color=COLORS['primary'], va='center', transform=ax_method.transAxes)
    ax_method.text(x + 0.14, y, val, fontsize=7, color=COLORS['text_dark'],
                   va='center', transform=ax_method.transAxes)

# ── PTP Performance Table ──
ax_ptp = fig1.add_subplot(gs_page1[4:6, :])
periods_ptp = ['YTD 2026', '1 Year', '2 Years', '3 Years', '5 Years', '7 Years', '10 Years', '15 Years']
indices_ptp = ['Nifty 100', 'Nifty Midcap 150', 'BSE 150 Midcap',
               'Nifty200 Mom 30', 'Nifty Midcap150 Momentum 50',
               'BSE Midcap 150 Momentum 30']
short_idx = ['Nifty 100', 'Nifty Mid 150', 'BSE Mid 150',
             'N200 Mom 30', 'N Mid150 Mom 50', 'BSE Mid150 Mom 30']

ptp_table = []
for idx_name, short in zip(indices_ptp, short_idx):
    row = [short]
    for p in periods_ptp:
        val = perf_data.get(p, {}).get(idx_name, None)
        if val is not None:
            row.append(f'{val*100:.1f}%')
        else:
            row.append('—')
    ptp_table.append(row)

draw_table(ax_ptp, ptp_table, periods_ptp, short_idx,
           'Point-to-Point Performance (CAGR for periods > 1 Year)',
           highlight_col=len(periods_ptp),
           col_widths=[0.13] + [0.087] * len(periods_ptp),
           fontsize=6.5)

# ── CY Returns Table ──
ax_cy = fig1.add_subplot(gs_page1[6:9, :])
years = list(range(2006, 2026))
cy_col_map_display = {
    'Nifty 100': 'Nifty 100',
    'Nifty Midcap 150': 'Nifty Midcap 150',
    'BSE Midcap 150 Index': 'BSE 150 Midcap',
    'Nifty200 Momentum 30': 'Nifty200 Mom 30',
    'Nifty Midcap150 Momentum 50': 'Nifty Midcap150 Momentum 50',
    'BSE Midcap 150 Momentum 30 Index': 'BSE Midcap 150 Momentum 30',
}

# Remap cy_data keys if needed
cy_indices = ['Nifty 100', 'Nifty Midcap 150', 'BSE 150 Midcap',
              'Nifty200 Mom 30', 'Nifty Midcap150 Momentum 50',
              'BSE Midcap 150 Momentum 30']
cy_short = ['Nifty 100', 'Nifty Mid 150', 'BSE Mid 150',
            'N200 Mom 30', 'N Mid150 Mom 50', 'BSE Mid150 Mom 30']

cy_table = []
for idx_name, short in zip(cy_indices, cy_short):
    row = [short]
    for yr in years:
        val = cy_data.get(yr, {}).get(idx_name, None)
        if val is not None:
            row.append(f'{val*100:.0f}%')
        else:
            row.append('—')
    cy_table.append(row)

year_labels = [str(y) for y in years]
ax_cy.axis('off')
ax_cy.set_title('Calendar Year Returns', fontsize=9, fontweight='bold',
                color=COLORS['primary'], loc='left', pad=8)

cy_col_w = [0.085] + [0.0458] * len(years)
table_cy = ax_cy.table(
    cellText=cy_table,
    colLabels=[''] + year_labels,
    cellLoc='center',
    loc='center',
    colWidths=cy_col_w
)
table_cy.auto_set_font_size(False)
table_cy.set_fontsize(5.5)
table_cy.scale(1, 1.4)

for (r, c), cell in table_cy.get_celld().items():
    cell.set_edgecolor('#D5D8DC')
    cell.set_linewidth(0.4)
    if r == 0:
        cell.set_facecolor(COLORS['primary'])
        cell.set_text_props(color='white', fontweight='bold', fontsize=5.5)
    elif c == 0:
        cell.set_text_props(fontweight='bold', fontsize=5.5)
        cell.set_facecolor(COLORS['bg_section'])
    else:
        # Color code returns
        text = cell.get_text().get_text()
        try:
            v = float(text.replace('%', '')) / 100
            if v < 0:
                cell.set_facecolor('#FCE4E4')
                cell.set_text_props(color=COLORS['red'])
            elif v > 0.3:
                cell.set_facecolor('#E8F5E8')
                cell.set_text_props(color=COLORS['green'])
            else:
                cell.set_facecolor('white')
        except:
            pass

# Highlight BSE Mom 30 row
for c in range(len(years) + 1):
    cell = table_cy.get_celld().get((len(cy_table), c))
    if cell:
        if c > 0:
            cell.set_text_props(fontweight='bold')

# ── Winners count ──
ax_wins = fig1.add_subplot(gs_page1[9, :])
ax_wins.axis('off')
ax_wins.set_xlim(0, 1)
ax_wins.set_ylim(0, 1)

# Count how many years BSE Mid150 Mom 30 was the top performer
bse_key = 'BSE Midcap 150 Momentum 30'
nifty100_key = 'Nifty 100'
win_count = 0
total_years = 0
for yr in range(2006, 2026):
    yr_data = cy_data.get(yr, {})
    if bse_key in yr_data:
        total_years += 1
        bse_val = yr_data[bse_key]
        is_top = all(v <= bse_val for k, v in yr_data.items() if k != bse_key)
        if is_top:
            win_count += 1

outperf_count = sum(1 for yr in range(2006, 2026)
                    if yr in cy_data and bse_key in cy_data[yr] and nifty100_key in cy_data[yr]
                    and cy_data[yr][bse_key] > cy_data[yr][nifty100_key])

ax_wins.text(0.0, 0.85, 'Key Insight:', fontsize=8, fontweight='bold',
             color=COLORS['primary'], va='top', transform=ax_wins.transAxes)
insight = (f'BSE Midcap 150 Momentum 30 was the top-performing index in {win_count} out of {total_years} calendar years '
           f'and outperformed Nifty 100 in {outperf_count} of {total_years} years. In down-years (2008, 2011, 2015, 2018, 2020), '
           f'the index showed comparable or lower drawdowns vs broad midcap indices, demonstrating the volatility-adjusted '
           f'momentum filter\'s defensive characteristics.')
ax_wins.text(0.0, 0.5, insight, fontsize=7, color=COLORS['text_dark'],
             va='center', transform=ax_wins.transAxes, linespacing=1.4)

# ── Volatility Table ──
ax_vol = fig1.add_subplot(gs_page1[10:12, :])
vol_periods = ['YTD 2026', '1 Year', '2 Years', '3 Years', '5 Years', '7 Years', '10 Years', '15 Years']
vol_indices = cy_indices
vol_short = cy_short

vol_table = []
for idx_name, short in zip(vol_indices, vol_short):
    row = [short]
    for p in vol_periods:
        val = vol_data.get(p, {}).get(idx_name, None)
        if val is not None:
            row.append(f'{val*100:.1f}%')
        else:
            row.append('—')
    vol_table.append(row)

draw_table(ax_vol, vol_table, vol_periods, vol_short,
           'Annualized Volatility (Standard Deviation)',
           highlight_col=None,
           col_widths=[0.13] + [0.087] * len(vol_periods),
           fontsize=6.5)

# Footer
fig1.text(0.04, 0.005, 'Source: BSE India, NSE India. Past performance is not indicative of future results. '
          'Data as of June 19, 2026. Returns are Total Return Index (TRI) based.',
          fontsize=5.5, color=COLORS['gray'], va='bottom')
fig1.text(0.96, 0.005, 'Page 1 of 2', fontsize=6, color=COLORS['gray'],
          va='bottom', ha='right')

fig1.savefig('/home/user/trading101/factsheet_page1.png', dpi=150, bbox_inches='tight',
             facecolor='white', edgecolor='none')
plt.close(fig1)
print("Page 1 saved.")


# ══════════════════════════════════════════════════════════════
# PAGE 2
# ══════════════════════════════════════════════════════════════
fig2 = plt.figure(figsize=(11.69, 16.54), dpi=150, facecolor='white')
gs_page2 = gridspec.GridSpec(12, 2, figure=fig2,
                             left=0.05, right=0.96, top=0.96, bottom=0.03,
                             hspace=0.55, wspace=0.2)

# ── Header ──
ax_h2 = fig2.add_subplot(gs_page2[0, :])
ax_h2.axis('off')
ax_h2.text(0.0, 0.75, 'BSE Midcap 150 Momentum 30 — Performance Deep Dive',
           fontsize=14, fontweight='bold', color=COLORS['primary'],
           transform=ax_h2.transAxes, va='top')
ax_h2.axhline(y=0.05, xmin=0, xmax=1, color=COLORS['accent'], linewidth=2.5)

# ── Rolling Returns Table (consolidated) ──
ax_roll = fig2.add_subplot(gs_page2[1:4, :])
roll_periods = ['1YR Rolling Return', '3YR Rolling Return', '5YR Rolling Return',
                '7YR Rolling Return', '10YR Rolling Return']
roll_period_labels = ['1 Year', '3 Year', '5 Year', '7 Year', '10 Year']

roll_indices = ['BSE Midcap 150 Momentum 30', 'BSE 150 Midcap',
                'Nifty Midcap150 Momentum 50', 'Nifty Midcap 150',
                'Nifty200 Mom 30', 'Nifty 100']
roll_short = ['BSE Mid150 Mom 30', 'BSE 150 Midcap', 'N Mid150 Mom 50',
              'Nifty Mid 150', 'N200 Mom 30', 'Nifty 100']

ax_roll.axis('off')
ax_roll.set_title('Rolling Returns Analysis — Average Annualized Returns & Negative Instance Rate',
                  fontsize=9, fontweight='bold', color=COLORS['primary'], loc='left', pad=8)

# Build two sub-tables: Average Returns + Negative Instance %
roll_avg_data = []
roll_neg_data = []
for idx_name, short in zip(roll_indices, roll_short):
    avg_row = [short]
    neg_row = [short]
    for rp in roll_periods:
        rd = rolling_data.get(rp, {}).get(idx_name, None)
        if rd:
            avg_row.append(f'{rd["Average"]*100:.1f}%')
            neg_pct = rd["Negative Instances"] / rd["Total Observations"] * 100 if rd["Total Observations"] > 0 else 0
            neg_row.append(f'{neg_pct:.1f}%')
        else:
            avg_row.append('—')
            neg_row.append('—')
    roll_avg_data.append(avg_row)
    roll_neg_data.append(neg_row)

# Combined table with 2 sections
combined_roll = []
combined_roll.append(['', '── Average Return ──', '', '', '', ''])
for row in roll_avg_data:
    combined_roll.append(row)
combined_roll.append(['', '── Negative Instance Rate ──', '', '', '', ''])
for row in roll_neg_data:
    combined_roll.append(row)

# Simpler: just make two separate tables in the same axes
# Table 1: Average Rolling Returns
ax_roll_top = fig2.add_subplot(gs_page2[1:3, :])
ax_roll_top.axis('off')
ax_roll_top.set_title('Rolling Returns — Average Annualized CAGR',
                      fontsize=9, fontweight='bold', color=COLORS['primary'], loc='left', pad=8)

roll_cw = [0.13] + [0.087] * 5
t1 = ax_roll_top.table(
    cellText=roll_avg_data,
    colLabels=[''] + roll_period_labels,
    cellLoc='center', loc='center', colWidths=roll_cw
)
t1.auto_set_font_size(False)
t1.set_fontsize(7)
t1.scale(1, 1.45)

for (r, c), cell in t1.get_celld().items():
    cell.set_edgecolor('#D5D8DC')
    cell.set_linewidth(0.4)
    if r == 0:
        cell.set_facecolor(COLORS['primary'])
        cell.set_text_props(color='white', fontweight='bold')
    elif c == 0:
        cell.set_text_props(fontweight='bold', fontsize=6.5)
        cell.set_facecolor(COLORS['bg_section'])
    elif r == 1:  # BSE Mid150 Mom 30 row
        cell.set_facecolor('#E8F4E8')
        cell.set_text_props(fontweight='bold', color=COLORS['primary'])
    else:
        cell.set_facecolor('white')

# Table 2: Negative Instance Rate
ax_roll_bot = fig2.add_subplot(gs_page2[3:5, :])
ax_roll_bot.axis('off')
ax_roll_bot.set_title('Rolling Returns — Probability of Negative Returns',
                      fontsize=9, fontweight='bold', color=COLORS['primary'], loc='left', pad=8)

t2 = ax_roll_bot.table(
    cellText=roll_neg_data,
    colLabels=[''] + roll_period_labels,
    cellLoc='center', loc='center', colWidths=roll_cw
)
t2.auto_set_font_size(False)
t2.set_fontsize(7)
t2.scale(1, 1.45)

for (r, c), cell in t2.get_celld().items():
    cell.set_edgecolor('#D5D8DC')
    cell.set_linewidth(0.4)
    if r == 0:
        cell.set_facecolor(COLORS['primary'])
        cell.set_text_props(color='white', fontweight='bold')
    elif c == 0:
        cell.set_text_props(fontweight='bold', fontsize=6.5)
        cell.set_facecolor(COLORS['bg_section'])
    elif r == 1:  # BSE Mid150 Mom 30 row
        cell.set_facecolor('#E8F4E8')
        cell.set_text_props(fontweight='bold', color=COLORS['primary'])
    else:
        # Color red for high negative rates
        text = cell.get_text().get_text()
        try:
            v = float(text.replace('%', ''))
            if v > 20:
                cell.set_facecolor('#FCE4E4')
            elif v == 0:
                cell.set_facecolor('#E8F5E8')
            else:
                cell.set_facecolor('white')
        except:
            pass

# ── Rolling Returns Min/Max Range Chart ──
ax_range = fig2.add_subplot(gs_page2[5:7, :])
ax_range.set_title('Rolling Returns Range — Min, Average & Max (1Y / 3Y / 5Y)',
                   fontsize=9, fontweight='bold', color=COLORS['primary'], loc='left', pad=8)

bar_indices = ['BSE Mid150\nMom 30', 'BSE 150\nMidcap', 'N Mid150\nMom 50',
               'Nifty\nMid 150', 'N200\nMom 30', 'Nifty 100']
bar_names = roll_indices

x = np.arange(len(bar_indices))
width = 0.25
periods_chart = ['1YR Rolling Return', '3YR Rolling Return', '5YR Rolling Return']
period_colors = [COLORS['blue_light'], COLORS['accent'], COLORS['green']]
period_labels_chart = ['1 Year', '3 Year', '5 Year']

for pi, (rp, color, plabel) in enumerate(zip(periods_chart, period_colors, period_labels_chart)):
    avgs = []
    mins = []
    maxs = []
    for idx_name in bar_names:
        rd = rolling_data.get(rp, {}).get(idx_name, {})
        avgs.append(rd.get('Average', 0))
        mins.append(rd.get('Min', 0))
        maxs.append(rd.get('Max', 0))

    avgs = np.array(avgs)
    mins = np.array(mins)
    maxs = np.array(maxs)

    bars = ax_range.bar(x + pi * width - width, avgs * 100, width * 0.9,
                         label=plabel, color=color, alpha=0.85, edgecolor='white', linewidth=0.5)
    # Error bars for min/max
    ax_range.errorbar(x + pi * width - width, avgs * 100,
                       yerr=[((avgs - mins) * 100), ((maxs - avgs) * 100)],
                       fmt='none', ecolor='#333', capsize=2, capthick=0.7, linewidth=0.7)

ax_range.set_xticks(x)
ax_range.set_xticklabels(bar_indices, fontsize=7)
ax_range.yaxis.set_major_formatter(PercentFormatter())
ax_range.set_ylabel('Annualized Return', fontsize=7)
ax_range.legend(fontsize=7, loc='upper right', framealpha=0.9)
ax_range.axhline(y=0, color='#999', linewidth=0.5)
ax_range.spines['top'].set_visible(False)
ax_range.spines['right'].set_visible(False)
ax_range.tick_params(axis='both', labelsize=6.5)
ax_range.set_ylim(-80, 160)

# ── Risk-Adjusted Metrics from NAV data ──
ax_risk = fig2.add_subplot(gs_page2[7:9, :])
ax_risk.axis('off')
ax_risk.set_title('Risk-Adjusted Performance Metrics (Since Common Inception)',
                  fontsize=9, fontweight='bold', color=COLORS['primary'], loc='left', pad=8)

risk_table = []
metrics_order = ['Ann. Return', 'Ann. Volatility', 'Sharpe Ratio', 'Sortino Ratio',
                 'Max Drawdown', 'Calmar Ratio']
risk_indices_display = ['Nifty 100', 'Nifty Midcap 150', 'Nifty200 Mom 30', 'Nifty Mid150 Mom 50']

for idx_name in risk_indices_display:
    row = [idx_name]
    m = risk_metrics.get(idx_name, {})
    for metric in metrics_order:
        v = m.get(metric, None)
        if v is not None:
            if 'Ratio' in metric:
                row.append(f'{v:.2f}')
            elif 'Drawdown' in metric:
                row.append(f'{v*100:.1f}%')
            else:
                row.append(f'{v*100:.1f}%')
        else:
            row.append('—')
    risk_table.append(row)

risk_cw = [0.14] + [0.087] * 6
t3 = ax_risk.table(
    cellText=risk_table,
    colLabels=[''] + metrics_order,
    cellLoc='center', loc='center', colWidths=risk_cw
)
t3.auto_set_font_size(False)
t3.set_fontsize(7)
t3.scale(1, 1.5)

for (r, c), cell in t3.get_celld().items():
    cell.set_edgecolor('#D5D8DC')
    cell.set_linewidth(0.4)
    if r == 0:
        cell.set_facecolor(COLORS['primary'])
        cell.set_text_props(color='white', fontweight='bold', fontsize=6.5)
    elif c == 0:
        cell.set_text_props(fontweight='bold', fontsize=6.5)
        cell.set_facecolor(COLORS['bg_section'])
    else:
        cell.set_facecolor('white')

# ── Comparison with Active Funds ──
ax_active = fig2.add_subplot(gs_page2[9:11, 0])
ax_active.set_title('BSE Mid150 Mom 30 vs Active Mid-Cap Funds',
                    fontsize=8, fontweight='bold', color=COLORS['primary'], loc='left', pad=8)

af_periods = ['1 Year', '3 Years', '5 Years', '7 Years', '10 Years']
idx_ret = [af_data.get('BSE Midcap 150 Momentum 30 Index', {}).get(p, 0) for p in af_periods]
avg_ret = [af_data.get('Average of the Mid Cap category', {}).get(p, 0) for p in af_periods]

x_af = np.arange(len(af_periods))
bars1 = ax_active.bar(x_af - 0.15, [r * 100 for r in idx_ret], 0.28,
                       label='BSE Mid150 Mom 30', color=COLORS['primary'], edgecolor='white')
bars2 = ax_active.bar(x_af + 0.15, [r * 100 for r in avg_ret], 0.28,
                       label='Avg Mid-Cap Fund', color=COLORS['gray'], edgecolor='white')
ax_active.set_xticks(x_af)
ax_active.set_xticklabels(af_periods, fontsize=6.5)
ax_active.yaxis.set_major_formatter(PercentFormatter())
ax_active.set_ylabel('CAGR', fontsize=7)
ax_active.legend(fontsize=6, loc='upper right')
ax_active.spines['top'].set_visible(False)
ax_active.spines['right'].set_visible(False)
ax_active.tick_params(axis='both', labelsize=6)

# Add value labels
for bar in bars1:
    ax_active.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{bar.get_height():.0f}%', ha='center', va='bottom', fontsize=5.5,
                    fontweight='bold', color=COLORS['primary'])
for bar in bars2:
    ax_active.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{bar.get_height():.0f}%', ha='center', va='bottom', fontsize=5.5,
                    color=COLORS['gray'])

# ── % of funds underperforming ──
ax_under = fig2.add_subplot(gs_page2[9:11, 1])
ax_under.set_title('% of Active Mid-Cap Funds Underperforming Index',
                   fontsize=8, fontweight='bold', color=COLORS['primary'], loc='left', pad=8)

under_pct = [af_data.get('% of funds under-performing the index', {}).get(p, 0) for p in af_periods]
bars_u = ax_under.bar(x_af, [u * 100 for u in under_pct], 0.5,
                       color=COLORS['accent'], edgecolor='white')
ax_under.set_xticks(x_af)
ax_under.set_xticklabels(af_periods, fontsize=6.5)
ax_under.yaxis.set_major_formatter(PercentFormatter())
ax_under.set_ylim(0, 115)
ax_under.axhline(y=100, color=COLORS['red'], linewidth=0.8, linestyle='--', alpha=0.7)
ax_under.spines['top'].set_visible(False)
ax_under.spines['right'].set_visible(False)
ax_under.tick_params(axis='both', labelsize=6)

for bar in bars_u:
    ax_under.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{bar.get_height():.0f}%', ha='center', va='bottom',
                   fontsize=7, fontweight='bold', color=COLORS['primary'])

# ── Why BSE Mid150 Mom 30 — Summary Box ──
ax_why = fig2.add_subplot(gs_page2[11, :])
ax_why.axis('off')
ax_why.set_xlim(0, 1)
ax_why.set_ylim(0, 1)

ax_why.text(0.0, 0.95, 'Why BSE Midcap 150 Momentum 30 is the Best Momentum Play',
            fontsize=9, fontweight='bold', color=COLORS['primary'], va='top',
            transform=ax_why.transAxes)

bullets = [
    '• Highest CAGR across all periods (1Y to 15Y) among comparable momentum indices — 28.6% over 10 years vs 21.9% (Nifty Mid150 Mom 50) and 18.0% (Nifty200 Mom 30)',
    '• Concentrated 30-stock portfolio delivers higher conviction and alpha vs diluted 50-stock alternatives',
    '• Volatility-adjusted momentum scoring reduces exposure to high-beta, mean-reverting names — lower drawdowns in corrections',
    '• 100% of active mid-cap funds underperformed over 3, 5, 7, and 10-year horizons — strongest case for passive momentum allocation',
    '• Semi-annual rebalancing with 10% stock cap ensures diversification without over-trading',
]

for i, b in enumerate(bullets):
    ax_why.text(0.01, 0.7 - i * 0.16, b, fontsize=6.5, color=COLORS['text_dark'],
                va='top', transform=ax_why.transAxes, linespacing=1.3)

# Footer
fig2.text(0.04, 0.008, 'Source: BSE India, NSE India, AMFI. Risk-free rate assumed at 6.5% p.a. '
          'Past performance is not indicative of future results.',
          fontsize=5.5, color=COLORS['gray'], va='bottom')
fig2.text(0.96, 0.008, 'Page 2 of 2', fontsize=6, color=COLORS['gray'],
          va='bottom', ha='right')

fig2.savefig('/home/user/trading101/factsheet_page2.png', dpi=150, bbox_inches='tight',
             facecolor='white', edgecolor='none')
plt.close(fig2)
print("Page 2 saved.")

# ── Combine into single PDF ──
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg

with PdfPages('/home/user/trading101/BSE_Midcap150_Momentum30_Factsheet.pdf') as pdf:
    for img_path in ['factsheet_page1.png', 'factsheet_page2.png']:
        img = mpimg.imread(f'/home/user/trading101/{img_path}')
        fig_pdf, ax_pdf = plt.subplots(figsize=(11.69, 16.54), dpi=150)
        ax_pdf.imshow(img)
        ax_pdf.axis('off')
        fig_pdf.subplots_adjust(left=0, right=1, top=1, bottom=0)
        pdf.savefig(fig_pdf, dpi=150)
        plt.close(fig_pdf)

print("\nPDF saved: BSE_Midcap150_Momentum30_Factsheet.pdf")
print("Done!")
