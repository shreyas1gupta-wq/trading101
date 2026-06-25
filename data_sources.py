"""
Free-data WATERFALL price loader  |  maximise coverage, conserve the metered API
================================================================================
The survivorship-bias-free universe (universe.py) lists every name that was EVER
a member -- including the ~233 (Nifty200) / ~503 (Nifty500) that left the index,
many because they collapsed. Their prices must be sourced too, or the backtest is
biased on the PRICE side even with a clean membership list.

No single free source has everything, so we cascade per ticker and take the FIRST
source that covers it (per-ticker selection, never per-cell splicing -- so we never
mix adjusted and raw quotes within one series):

  1. yfinance   -- free, unlimited, split/dividend-ADJUSTED. Covers survivors well;
                   Yahoo usually drops delisted Indian names, so they fall through.
  2. local      -- the user's Kaggle EOD dumps + the bundled DELISTED price panel
                   (data/NIFTY500_delisted_prices_2005_2025.xlsx). This is where the
                   dead names Yahoo lacks come from.
  3. EODHD API  -- ADJUSTED, but the free tier is ~20 calls/day, so it runs LAST and
                   only for names STILL missing, capped by `max_calls`. Every fetch is
                   cached to disk, so repeated runs accumulate coverage without re-spending
                   the daily budget. Key comes ONLY from $EODHD_API_KEY (never hard-coded).

Each source yields {SYMBOL -> DataFrame[date x (open,high,low,close,volume)]}, already
adjusted where the source provides it. build_panel() cascades, then assembles the
strategies.Prices container the rest of the pipeline expects. Close-only sources are
fine: missing O/H/L are filled with close and volume left NaN (range/volume strategies
then simply produce no trades and are skipped, and the capacity report degrades cleanly).
"""

import os
import glob

import numpy as np
import pandas as pd

import strategies as S   # for the Prices container (no cycle: strategies never imports this)

NIFTY500_DELISTED = "data/NIFTY500_delisted_prices_2005_2025.xlsx"

# Default cascade. The user's Kaggle EOD dump is added as another {"type":"local","path":...}
# entry (a per-ticker dir or a long/wide CSV); it slots in wherever you place it in the list.
DEFAULT_SOURCES = [
    {"type": "yfinance", "suffix": ".NS"},
    {"type": "local",    "path": NIFTY500_DELISTED},   # bundled delisted price panel (wide)
    {"type": "eodhd",    "exchange": "NSE", "max_calls": 20},
]

FIELDS = ("open", "high", "low", "close", "volume")

# canonical column <- accepted aliases (NSE bhavcopy + Yahoo-style exports)
_ALIASES = {
    "Date":     {"date", "timestamp", "tradedate", "trade_date", "dt", "time", "nav date"},
    "Open":     {"open", "open price", "openprice"},
    "High":     {"high", "high price"},
    "Low":      {"low", "low price"},
    "Close":    {"close", "close price", "closeprice"},   # NOT 'last'/'ltp'
    "AdjClose": {"adj close", "adjusted", "adj_close", "adjclose", "adjusted close", "adjusted_close"},
    "Volume":   {"volume", "tottrdqty", "total traded quantity", "totaltradedquantity", "qty", "vol"},
    "Symbol":   {"symbol", "ticker", "name", "scrip", "scripname"},
    "Series":   {"series"},
}


def _norm(sym):
    return str(sym).strip().upper().replace(".NS", "").replace(".BO", "").replace(".NSE", "")


def _canon(df):
    df = df.copy()
    ren = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        for canon, al in _ALIASES.items():
            if lc in al:
                ren[c] = canon
    df = df.rename(columns=ren)
    df = df.loc[:, ~df.columns.duplicated()]
    if "Series" in df.columns:                       # bhavcopy carries EQ/BE/SM... keep cash equity
        df = df[df["Series"].astype(str).str.strip() == "EQ"]
    return df


def _ohlcv_from_canon(df):
    """Canonical-column frame (Date-indexed) -> lowercase OHLCV frame, back-adjusted to AdjClose."""
    if "Date" not in df.columns or "Close" not in df.columns:
        return None
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).set_index("Date").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    close = df["AdjClose"] if "AdjClose" in df.columns else df["Close"]
    scale = (close / df["Close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)   # back-adjust OHLC
    out = pd.DataFrame(index=df.index)
    out["open"]   = df["Open"]  * scale if "Open"  in df.columns else close
    out["high"]   = df["High"]  * scale if "High"  in df.columns else close
    out["low"]    = df["Low"]   * scale if "Low"   in df.columns else close
    out["close"]  = close
    out["volume"] = df["Volume"] if "Volume" in df.columns else np.nan
    return out


# ── source: local files (per-ticker dir, long bhavcopy CSV, or wide Date x ticker panel) ──
def load_local(path):
    """Return {SYMBOL -> ohlcv frame} from whatever local layout `path` points at."""
    if not path or not os.path.exists(path):
        return {}
    out = {}
    if os.path.isdir(path):                                  # (a) one CSV per ticker
        for fp in glob.glob(os.path.join(path, "*.csv")):
            df = _ohlcv_from_canon(_canon(pd.read_csv(fp)))
            if df is not None:
                out[_norm(os.path.splitext(os.path.basename(fp))[0])] = df
        return out

    read = pd.read_excel if path.lower().endswith((".xlsx", ".xls")) else pd.read_csv
    raw = read(path)
    canon = _canon(raw)
    if "Symbol" in canon.columns and "Close" in canon.columns:   # (b) long CSV (bhavcopy)
        for sym, g in canon.groupby("Symbol"):
            df = _ohlcv_from_canon(g)
            if df is not None:
                out[_norm(sym)] = df
        return out

    # (c) wide panel: a Date column + one close column per ticker (the delisted panel)
    cols = {str(c).strip().lower(): c for c in raw.columns}
    dcol = next((cols[k] for k in ("date", "nav date", "timestamp", "dt") if k in cols), raw.columns[0])
    w = raw.copy()
    w[dcol] = pd.to_datetime(w[dcol], errors="coerce")
    w = w.dropna(subset=[dcol]).set_index(dcol).sort_index()
    for c in w.columns:
        s = pd.to_numeric(w[c], errors="coerce").dropna()
        if len(s):
            out[_norm(c)] = pd.DataFrame({"open": s, "high": s, "low": s, "close": s,
                                          "volume": np.nan})
    return out


# ── source: yfinance (adjusted, free, per-ticker CSV cache; batch fetch for speed) ──
def _extract_yf(raw, ytk):
    try:
        sub = raw[ytk] if isinstance(raw.columns, pd.MultiIndex) else raw
    except Exception:
        return None
    sub = sub.rename(columns={c: str(c).strip().lower() for c in sub.columns})
    keep = [c for c in FIELDS if c in sub.columns]
    if "close" not in keep:
        return None
    df = sub[keep].dropna(how="all")
    return df if len(df) else None


def fetch_yfinance(syms, start, end, cache_dir, suffix=".NS", chunk=40):
    cdir = os.path.join(cache_dir, "yfinance")
    os.makedirs(cdir, exist_ok=True)
    out, to_fetch = {}, []
    for s in syms:
        fp = os.path.join(cdir, s + ".csv")
        if os.path.exists(fp):
            df = pd.read_csv(fp, index_col=0, parse_dates=True)
            if len(df):
                out[s] = df
        else:
            to_fetch.append(s)
    if not to_fetch:
        return out
    try:
        import yfinance as yf
    except Exception:
        return out
    for i in range(0, len(to_fetch), chunk):
        grp = to_fetch[i:i + chunk]
        ymap = {s: s + suffix for s in grp}
        try:
            raw = yf.download(list(ymap.values()), start=start, end=end, auto_adjust=True,
                              progress=False, group_by="ticker", threads=True)
        except Exception:
            continue
        if raw is None or not len(raw):
            continue
        for s, y in ymap.items():
            df = _extract_yf(raw, y)
            if df is not None:
                df.to_csv(os.path.join(cdir, s + ".csv"))
                out[s] = df
    return out


# ── source: EODHD (adjusted; metered free tier -> last resort, capped, cached) ──
def fetch_eodhd(syms, start, end, cache_dir, exchange="NSE", max_calls=20, api_key=None):
    cdir = os.path.join(cache_dir, "eodhd")
    os.makedirs(cdir, exist_ok=True)
    key = api_key or os.environ.get("EODHD_API_KEY")
    out, calls = {}, 0
    for s in syms:
        fp = os.path.join(cdir, s + ".csv")
        if os.path.exists(fp):                          # cached -> costs no call
            df = pd.read_csv(fp, index_col=0, parse_dates=True)
            if len(df):
                out[s] = df
            continue
        if not key or calls >= max_calls:               # conserve the daily budget
            continue
        try:
            import requests
            r = requests.get(f"https://eodhd.com/api/eod/{s}.{exchange}",
                             params={"api_token": key, "fmt": "json", "from": start, "to": end},
                             timeout=30)
            calls += 1
            if r.status_code != 200 or not r.json():
                continue
            df = pd.DataFrame(r.json())
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            close = df["adjusted_close"] if "adjusted_close" in df.columns else df["close"]
            scale = (close / df["close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
            o = pd.DataFrame({"open": df.get("open", close) * scale,
                              "high": df.get("high", close) * scale,
                              "low":  df.get("low", close) * scale,
                              "close": close,
                              "volume": df.get("volume", np.nan)})
            o.to_csv(fp)
            out[s] = o
        except Exception:
            continue
    return out, calls


# ── data hygiene: kill isolated bad ticks before they compound ──────────────────
def _despike_panel(close, win=11, lo=1 / 3.0, hi=3.0):
    """Null prices that deviate >hi× or <lo× from their LOCAL (centred) median.
    Free EOD panels carry isolated bad ticks (e.g. a one-day 6649->46->6649 round-trip,
    or a 132->6000->129 spike); a long backtest that compounds the +144x 'recovery'
    off such a tick reports fantasy CAGRs. NSE circuit bands cap REAL daily moves near
    ±20%, so a >3x deviation from the local median is unambiguously a data error, not a
    tradable move. We null those cells (later bridged by a short ffill), so the bad day
    becomes a no-trade rather than a fake gain. Real multi-day declines stay (each day
    sits near its local median). Returns (cleaned, n_removed)."""
    med = close.rolling(win, center=True, min_periods=3).median()
    ratio = close / med
    bad = (ratio < lo) | (ratio > hi)
    return close.mask(bad), int(bad.to_numpy().sum())


# ── the cascade ──────────────────────────────────────────────────────────────
def build_panel(cfg, tickers, dates, min_obs=40):
    """Cascade through cfg['sources'] and take the first source that covers each ticker.
    Returns (Prices, provenance dict {SYMBOL->source}, notes list)."""
    want = sorted({_norm(t) for t in tickers})
    start = str(pd.Timestamp(dates.min()).date())
    end = str(pd.Timestamp(dates.max()).date())
    cache = cfg.get("cache_dir", "cache")
    sources = cfg.get("sources", DEFAULT_SOURCES)

    resolved, prov, notes = {}, {}, []
    for src in sources:
        remaining = [s for s in want if s not in resolved]
        if not remaining:
            break
        t = src.get("type")
        if t == "yfinance":
            got = fetch_yfinance(remaining, start, end, cache, src.get("suffix", ".NS"))
        elif t == "eodhd":
            got, calls = fetch_eodhd(remaining, start, end, cache, src.get("exchange", "NSE"),
                                     src.get("max_calls", 20), src.get("api_key"))
            notes.append(f"EODHD: {calls} API call(s) spent (cap {src.get('max_calls', 20)}/run); "
                         f"key {'present' if os.environ.get('EODHD_API_KEY') or src.get('api_key') else 'ABSENT -> skipped'}")
        elif t in ("local", "wide", "panel", "dir", "long"):
            got = load_local(src.get("path"))
        else:
            continue
        n_before = len(resolved)
        for s, df in got.items():
            if s in resolved or s not in want:
                continue
            if df is None or "close" not in df.columns or df["close"].notna().sum() < min_obs:
                continue
            resolved[s], prov[s] = df, t
        notes.append(f"{t}: +{len(resolved) - n_before} tickers ({len(resolved)}/{len(want)} covered)")

    idx = pd.bdate_range(dates.min(), dates.max())
    frames = {f: {} for f in FIELDS}
    for s, df in resolved.items():
        for f in FIELDS:
            if f in df.columns:
                frames[f][s] = df[f]

    def raw(d):                                          # align to the calendar, no fill yet
        return (pd.DataFrame(d).reindex(idx).sort_index()
                if d else pd.DataFrame(index=idx))

    raw_f = {f: raw(frames[f]) for f in FIELDS}
    clean_close, n_spikes = _despike_panel(raw_f["close"])
    bad = raw_f["close"].notna() & clean_close.isna()    # cells removed as bad ticks
    for f in FIELDS:                                     # drop the same (date,name) cells everywhere
        raw_f[f] = raw_f[f].mask(bad.reindex(index=raw_f[f].index, columns=raw_f[f].columns).fillna(False))
    if n_spikes:
        notes.append(f"despike: removed {n_spikes} bad-tick day(s) (>3x or <1/3x local median)")

    close = clean_close.ffill(limit=5)                   # bridge the nulled ticks (and short gaps)
    cols = close.columns

    def or_close(d):                                     # fill absent O/H/L with close
        p = raw_f[d].ffill(limit=5).reindex(columns=cols)
        return p.where(p.notna(), close)

    px = S.Prices(or_close("open"), or_close("high"), or_close("low"),
                  close, raw_f["volume"].ffill(limit=5).reindex(columns=cols))
    return px, prov, notes


def provenance_summary(prov, want):
    """One-line-per-source coverage tally + the missing count."""
    by = {}
    for s, t in prov.items():
        by[t] = by.get(t, 0) + 1
    missing = len(set(want)) - len(prov)
    parts = [f"{t}={n}" for t, n in sorted(by.items(), key=lambda kv: -kv[1])]
    return f"sources -> {', '.join(parts) if parts else 'none'};  missing={missing}/{len(set(want))}"


# ── benchmarks (factor_navs.xlsx): index NAV series for buy&hold comparison ──
def load_benchmarks(path, names=("NIFTY 50", "NIFTY 500")):
    if not path or not os.path.exists(path):
        return None
    df = pd.read_excel(path)
    dcol = next((c for c in df.columns if str(c).strip().lower() in ("nav date", "date")), df.columns[0])
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    df = df.dropna(subset=[dcol]).set_index(dcol).sort_index()
    cols = [c for c in df.columns if str(c).strip() in names]
    return df[cols].apply(pd.to_numeric, errors="coerce") if cols else None
