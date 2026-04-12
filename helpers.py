import numpy as np
import pandas as pd
from constants import (
    BENCH, ROLL, ZSCORE_LOOKBACK, HOLDINGS, SECTORS, EW_SECTORS
)

def get_holdings(etf):
    """Return stored holdings metadata for a requested ETF."""
    return (HOLDINGS.get(etf, []), False)

def ensure_dataframe(obj):
    """Return obj as a DataFrame when possible."""
    if isinstance(obj, pd.Series):
        return obj.to_frame()
    if isinstance(obj, pd.DataFrame):
        return obj.copy()
    return pd.DataFrame()

def normalize_yf_panel(raw, field):
    """Extract a clean field-level DataFrame from a yfinance download result."""
    if raw is None or len(raw) == 0:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        if field in raw.columns.get_level_values(0):
            df = raw[field].copy()
        elif field in raw.columns.get_level_values(-1):
            df = raw.xs(field, axis=1, level=-1, drop_level=True).copy()
        else:
            return pd.DataFrame()
    else:
        if field not in raw.columns:
            return pd.DataFrame()
        df = raw[[field]].copy()
    df.index = pd.to_datetime(df.index, errors='coerce')
    df = df[~df.index.isna()]
    return ensure_dataframe(df).sort_index()

def latest_business_window(series, business_days):
    """Return the most recent business-day slice of a Series."""
    series = series.dropna()
    if series.empty:
        return series
    cutoff = series.index.max() - pd.tseries.offsets.BDay(business_days)
    return series[series.index >= cutoff]

def latest_common_window(left, right, business_days):
    """Align two series on a recent common business-day window."""
    left = latest_business_window(left, business_days)
    right = latest_business_window(right, business_days)
    common = left.index.intersection(right.index)
    return (left.loc[common], right.loc[common])

def to_yoy(s):
    s = s.dropna()
    return s.pct_change(12) * 100

def trim(s, m):
    s = s.dropna()
    if s.empty or not m:
        return s
    return s[s.index >= s.index.max() - pd.DateOffset(months=m)]

def compute_relative(p, d):
    if p.empty or BENCH not in p.columns:
        return (pd.DataFrame(), pd.DataFrame())
    avail = [k for k in d.keys() if k in p.columns]
    if not avail:
        return (pd.DataFrame(), pd.DataFrame())
    rel = p[avail].div(p[BENCH], axis=0).dropna(how='all')
    alpha = (1 + rel.pct_change()).rolling(ROLL).apply(np.prod, raw=True) - 1
    return (rel, alpha)

def reindex_from(df, bd):
    if df.empty:
        return df
    df = df[df.index >= pd.Timestamp(bd)].dropna(how='all')
    if df.empty:
        return df
    base = df.iloc[0].replace(0, np.nan)
    return df.div(base, axis=1)

def get_negative_spread_ranges(s):
    periods = []
    s = s.dropna()
    if s.empty:
        return periods
    inv = (s < 0).astype(int)
    in_neg = False
    start = None
    prev = None
    for dt, val in inv.items():
        if val == 1 and (not in_neg):
            in_neg = True
            start = dt
        elif val == 0 and in_neg:
            periods.append((start, prev))
            in_neg = False
        prev = dt
    if in_neg and start is not None:
        periods.append((start, prev))
    return periods

def chart_title(m, s):
    return f'{m} {s}'

def safe_fmt(v):
    try:
        if pd.isna(v):
            return '---'
        return f'{float(v):.2f}'
    except (ValueError, TypeError):
        return str(v)

def snap_color(row):
    styles = [''] * len(row)
    try:
        latest, previous = float(row['Latest']), float(row['Previous'])
        idx = list(row.index).index('Latest')
        if latest > previous:
            styles[idx] = 'color:#2ca02c;font-weight:bold'
        elif latest < previous:
            styles[idx] = 'color:#d62728;font-weight:bold'
    except (ValueError, TypeError):
        pass
    return styles

def add_src(fig, y=-0.25):
    fig.add_annotation(text='Source: FRED / Yahoo Finance', xref='paper', yref='paper', x=1.0, y=y, showarrow=False, font=dict(size=10, color='#888888'), xanchor='right')

def compute_volume_zscore(v, lb=ZSCORE_LOOKBACK):
    v = v.dropna()
    if v.empty:
        return pd.Series(dtype=float)
    rm = v.rolling(lb, min_periods=60).mean()
    rs = v.rolling(lb, min_periods=60).std().replace(0, np.nan)
    return ((v - rm) / rs).clip(-3, 3).dropna()

def compute_flow_proxy_z(P, V, t, lb=ZSCORE_LOOKBACK):
    if P.empty or V.empty or t not in P.columns or (t not in V.columns):
        return pd.Series(dtype=float)
    p, v = (P[t].dropna(), V[t].dropna())
    c = p.index.intersection(v.index)
    p, v = (p.loc[c], v.loc[c])
    if len(c) < 60:
        return pd.Series(dtype=float)
    dv = p * v
    ret = p.pct_change()
    flow = dv.diff() - ret * dv.shift(1)
    rm = flow.rolling(lb, min_periods=60).mean()
    rs = flow.rolling(lb, min_periods=60).std().replace(0, np.nan)
    return ((flow - rm) / rs).clip(-3, 3).dropna()

def compute_signed_volume_z(P, V, t, lb=ZSCORE_LOOKBACK):
    if P.empty or V.empty or t not in P.columns or (t not in V.columns):
        return pd.Series(dtype=float)
    p, v = (P[t].dropna(), V[t].dropna())
    c = p.index.intersection(v.index)
    p, v = (p.loc[c], v.loc[c])
    if len(c) < 60:
        return pd.Series(dtype=float)
    sv = v * np.sign(p.pct_change())
    rm = sv.rolling(lb, min_periods=60).mean()
    rs = sv.rolling(lb, min_periods=60).std().replace(0, np.nan)
    return ((sv - rm) / rs).clip(-3, 3).dropna()

def compute_breadth(P):
    if P.empty or 'RSP' not in P.columns or 'SPY' not in P.columns:
        return pd.Series(dtype=float)
    r, s = (P['RSP'].dropna(), P['SPY'].dropna())
    c = r.index.intersection(s.index)
    if len(c) == 0:
        return pd.Series(dtype=float)
    return (r.loc[c] / s.loc[c]).dropna()

def compute_rotation_ratio(P, smooth=21, nw=252):
    sector_cols = [c for c in SECTORS.keys() if c in P.columns]
    if not sector_cols:
        return (pd.Series(dtype=float), pd.Series(dtype=float))
    sr = P[sector_cols].pct_change().dropna()
    bw = sr.std(axis=1)
    wp = []
    for cw, ew in EW_SECTORS.items():
        if cw in P.columns and ew in P.columns:
            wp.append((P[ew].pct_change() - P[cw].pct_change()).abs())
    if not wp:
        return (pd.Series(dtype=float), pd.Series(dtype=float))
    wi = pd.concat(wp, axis=1).mean(axis=1).dropna()
    c = bw.index.intersection(wi.index)
    bw, wi = (bw.loc[c], wi.loc[c])
    wi = wi.replace(0, np.nan)
    raw = bw / wi
    sm = raw.rolling(smooth, min_periods=10).mean()
    pr = sm.rolling(nw, min_periods=60).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    return (pr.dropna(), sm.dropna())

def style_attr(df):
    def c(v):
        if pd.isna(v):
            return ''
        return 'color:#2ca02c' if v > 0 else 'color:#d62728' if v < 0 else ''
    s = df.style
    for col in [x for x in ['1D Ret %', 'Contribution', '5D Ret %', '1M Ret %'] if x in df.columns]:
        s = s.map(c, subset=[col])
    return s.format({'1D Ret %': '{:+.2f}', 'Contribution': '{:+.3f}', '5D Ret %': '{:+.2f}', '1M Ret %': '{:+.2f}'}, na_rep='---')

def build_holdings_attr(etf, P):
    h, live = get_holdings(etf)
    if not h:
        return (pd.DataFrame(), np.nan, False)
    er = P[etf].pct_change().iloc[-1] * 100 if etf in P.columns else np.nan
    rows = []
    for t, n, w in h:
        if t not in P.columns:
            continue
        p = P[t].dropna()
        if len(p) < 2:
            continue
        sr = p.pct_change().iloc[-1] * 100
        co = w * sr
        r5 = (p.iloc[-1] / p.iloc[-5] - 1) * 100 if len(p) >= 5 else np.nan
        r1m = (p.iloc[-1] / p.iloc[-21] - 1) * 100 if len(p) >= 21 else np.nan
        rows.append({'Ticker': t, 'Name': n, 'Weight': f'{w:.0%}', '1D Ret %': round(sr, 2), 'Contribution': round(co, 3), '5D Ret %': round(r5, 2) if not np.isnan(r5) else np.nan, '1M Ret %': round(r1m, 2) if not np.isnan(r1m) else np.nan})
    df = pd.DataFrame(rows)
    if not df.empty:
        df['_ac'] = df['Contribution'].abs()
        df = df.sort_values('_ac', ascending=False).drop(columns=['_ac']).reset_index(drop=True)
    return (df, er, live)
