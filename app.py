import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import altair as alt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import fredapi
st.set_page_config(page_title='Macro Dashboard', layout='wide', page_icon='📊', initial_sidebar_state='collapsed')
st.markdown('\n<style>\n    [data-testid="stMetricValue"] { font-size: 1.1rem; }\n    .block-container { padding-top: 1rem; }\n</style>\n', unsafe_allow_html=True)
FRED_KEY = st.secrets['FRED_API_KEY']
fred = fredapi.Fred(api_key=FRED_KEY)
START = '2015-01-01'
BENCH = 'SPY'
ROLL = 126
CM = dict(b=120, t=60, l=60, r=40)
LEG = dict(orientation='h', yanchor='top', y=-0.25, x=0.5, xanchor='center', font=dict(size=11))
PCFG = dict(displayModeBar=False, scrollZoom=False)
DISCLAIMER = '*Disclaimer: This dashboard is for educational and informational purposes only. Nothing contained herein constitutes investment advice, a recommendation, or a solicitation to buy or sell any securities or financial instruments. The data presented may be delayed, incomplete, or inaccurate, and should not be relied upon for trading or investment decisions. Past performance is not indicative of future results. The authors and contributors assume no liability for any losses or damages arising from the use of this information. Consult a qualified financial advisor before making any investment decisions.*'
SRC_BOTH = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED / Yahoo Finance</p>'
SRC_FRED = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED</p>'
SRC_YF = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: Yahoo Finance</p>'
ZSCORE_LOOKBACK = 252
CHART_WINDOW = 63
FACTORS = {'USMV': 'Min Vol', 'MTUM': 'Momentum', 'QUAL': 'Quality', 'SIZE': 'Size', 'VLUE': 'Value', 'HDV': 'Yield'}
SECTORS = {'XLC': 'Comm. Serv.', 'XLY': 'Cons. Disc.', 'XLP': 'Cons. Staples', 'XLE': 'Energy', 'XLF': 'Financials', 'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLK': 'Info. Tech', 'XLB': 'Materials', 'XLRE': 'Real Estate', 'XLU': 'Utilities'}
SECTORS_CYCLICAL = {'XLC': 'Comm. Serv.', 'XLY': 'Cons. Disc.', 'XLE': 'Energy', 'XLF': 'Financials', 'XLI': 'Industrials', 'XLK': 'Info. Tech', 'XLB': 'Materials'}
SECTORS_DEFENSIVE = {'XLP': 'Cons. Staples', 'XLV': 'Healthcare', 'XLRE': 'Real Estate', 'XLU': 'Utilities'}
SECTOR_COLORS = {'XLK': '#5B9BD5', 'XLV': '#70C27A', 'XLC': '#A978DE', 'XLP': '#F0C75E', 'XLY': '#E8725C', 'XLI': '#A3A9B0', 'XLU': '#5EC4D4', 'XLE': '#4AA06D', 'XLF': '#D94F5C', 'XLB': '#C08B5C', 'XLRE': '#D97BA0'}
FACTOR_COLORS = {'MTUM': '#5B9BD5', 'VLUE': '#D94F5C', 'QUAL': '#70C27A', 'SIZE': '#F0A050', 'USMV': '#A3A9B0', 'HDV': '#D4AA4F'}
INDICES = {'SPY': 'S&P 500', 'QQQ': 'Nasdaq 100', 'IWM': 'Russell 2000', 'DIA': 'Dow 30'}
INDICES_CHART = {'^GSPC': 'S&P 500', '^IXIC': 'Nasdaq', '^RUT': 'Russell 2000', '^DJI': 'Dow 30'}
EW_SECTORS = {'XLK': 'RYT', 'XLF': 'RYF', 'XLE': 'RYE', 'XLV': 'RYH', 'XLI': 'RGI', 'XLY': 'RCD', 'XLP': 'RHS', 'XLB': 'RTM', 'XLU': 'RYU', 'XLRE': 'EWRE', 'XLC': 'RSPC'}
RETAIL_ETFS = ['TQQQ', 'SQQQ']
HOLDINGS = {'XLK': [('AAPL', 'Apple', 0.22), ('MSFT', 'Microsoft', 0.21), ('NVDA', 'Nvidia', 0.11), ('AVGO', 'Broadcom', 0.05), ('CRM', 'Salesforce', 0.03), ('ADBE', 'Adobe', 0.03), ('AMD', 'AMD', 0.03), ('CSCO', 'Cisco', 0.02)], 'XLF': [('BRK-B', 'Berkshire', 0.14), ('JPM', 'JPMorgan', 0.11), ('V', 'Visa', 0.09), ('MA', 'Mastercard', 0.07), ('BAC', 'BofA', 0.05), ('WFC', 'Wells Fargo', 0.04), ('GS', 'Goldman', 0.03), ('MS', 'Morgan Stanley', 0.03)], 'XLE': [('XOM', 'Exxon', 0.23), ('CVX', 'Chevron', 0.16), ('COP', 'ConocoPhillips', 0.08), ('WMB', 'Williams', 0.06), ('EOG', 'EOG Resources', 0.05), ('SLB', 'Schlumberger', 0.05), ('PSX', 'Phillips 66', 0.04), ('MPC', 'Marathon Petro', 0.04)], 'XLV': [('LLY', 'Eli Lilly', 0.12), ('UNH', 'UnitedHealth', 0.1), ('JNJ', 'J&J', 0.07), ('ABBV', 'AbbVie', 0.07), ('MRK', 'Merck', 0.06), ('TMO', 'Thermo Fisher', 0.04), ('ABT', 'Abbott', 0.04), ('PFE', 'Pfizer', 0.03)], 'XLI': [('GE', 'GE Aerospace', 0.09), ('CAT', 'Caterpillar', 0.06), ('RTX', 'RTX Corp', 0.05), ('UNP', 'Union Pacific', 0.05), ('HON', 'Honeywell', 0.05), ('DE', 'Deere', 0.04), ('BA', 'Boeing', 0.04), ('LMT', 'Lockheed', 0.03)], 'XLY': [('AMZN', 'Amazon', 0.23), ('TSLA', 'Tesla', 0.15), ('HD', 'Home Depot', 0.1), ('MCD', "McDonald's", 0.05), ('LOW', "Lowe's", 0.04), ('BKNG', 'Booking', 0.04), ('TJX', 'TJX Cos', 0.03), ('NKE', 'Nike', 0.02)], 'XLP': [('PG', 'Procter & Gamble', 0.15), ('COST', 'Costco', 0.14), ('WMT', 'Walmart', 0.1), ('KO', 'Coca-Cola', 0.1), ('PEP', 'PepsiCo', 0.09), ('PM', 'Philip Morris', 0.06), ('MDLZ', 'Mondelez', 0.04), ('MO', 'Altria', 0.03)], 'XLB': [('LIN', 'Linde', 0.19), ('SHW', 'Sherwin-Williams', 0.09), ('FCX', 'Freeport-McMoRan', 0.08), ('APD', 'Air Products', 0.06), ('ECL', 'Ecolab', 0.06), ('NEM', 'Newmont', 0.05), ('NUE', 'Nucor', 0.04), ('DOW', 'Dow Inc', 0.04)], 'XLU': [('NEE', 'NextEra', 0.15), ('SO', 'Southern Co', 0.1), ('DUK', 'Duke Energy', 0.08), ('CEG', 'Constellation', 0.07), ('SRE', 'Sempra', 0.05), ('AEP', 'AEP', 0.05), ('D', 'Dominion', 0.04), ('PCG', 'PG&E', 0.04)], 'XLRE': [('PLD', 'Prologis', 0.13), ('AMT', 'American Tower', 0.1), ('EQIX', 'Equinix', 0.09), ('WELL', 'Welltower', 0.07), ('SPG', 'Simon Property', 0.06), ('DLR', 'Digital Realty', 0.05), ('PSA', 'Public Storage', 0.05), ('O', 'Realty Income', 0.05)], 'XLC': [('META', 'Meta', 0.23), ('GOOGL', 'Alphabet A', 0.12), ('GOOG', 'Alphabet C', 0.11), ('NFLX', 'Netflix', 0.08), ('T', 'AT&T', 0.05), ('CMCSA', 'Comcast', 0.05), ('DIS', 'Disney', 0.04), ('TMUS', 'T-Mobile', 0.04)]}

def get_holdings(etf):
    """Return stored holdings metadata for a requested ETF."""
    return (HOLDINGS.get(etf, []), False)

def ensure_dataframe(obj):
    """Return *obj* as a DataFrame with a DatetimeIndex when possible."""
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
        df.columns = [BENCH]
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
YIELDS = {'DGS2': '2Y', 'DGS5': '5Y', 'DGS10': '10Y', 'DGS30': '30Y'}
SPREADS = {'T10Y2Y': '10Y-2Y Spread', 'T10Y3M': '10Y-3M Spread'}
CREDIT = {'BAMLH0A0HYM2': 'HY OAS', 'BAMLC0A0CM': 'IG OAS'}
KEY_RELEASES = [('Nonfarm Payrolls', 'PAYEMS', '000s MoM', 'diff'), ('Unemployment Rate', 'UNRATE', '%', 'level'), ('CPI YoY', 'CPIAUCSL', '% YoY', 'yoy'), ('Core CPI YoY', 'CPILFESL', '% YoY', 'yoy'), ('PCE YoY', 'PCEPI', '% YoY', 'yoy'), ('Core PCE YoY', 'PCEPILFE', '% YoY', 'yoy'), ('GDP Growth QoQ Ann.', 'A191RL1Q225SBEA', '% Ann.', 'level'), ('Retail Sales MoM', 'RSAFS', '% MoM', 'mom'), ('Industrial Production', 'INDPRO', '% MoM', 'mom'), ('Fed Funds Rate', 'FEDFUNDS', '%', 'level'), ('10Y-2Y Spread', 'T10Y2Y', '%', 'level')]
FOMC = {'2025': [('Jan 28-29', '2025-01-29', 'Hold (4.25-4.50%)'), ('Mar 18-19', '2025-03-19', 'Hold (4.25-4.50%)'), ('May 6-7', '2025-05-07', 'Hold (4.25-4.50%)'), ('Jun 17-18', '2025-06-18', 'Hold (4.25-4.50%)'), ('Jul 29-30', '2025-07-30', 'Hold (4.25-4.50%)'), ('Sep 16-17', '2025-09-17', 'Cut -25bp (4.00-4.25%)'), ('Oct 28-29', '2025-10-29', 'Cut -25bp (3.75-4.00%)'), ('Dec 9-10', '2025-12-10', 'Cut -25bp (3.50-3.75%)')], '2026': [('Jan 27-28', '2026-01-28', 'Hold (3.50-3.75%)'), ('Mar 17-18', '2026-03-18', ''), ('Apr 28-29', '2026-04-29', ''), ('Jun 9-10', '2026-06-10', ''), ('Jul 28-29', '2026-07-29', ''), ('Sep 15-16', '2026-09-16', ''), ('Oct 27-28', '2026-10-28', ''), ('Dec 8-9', '2026-12-09', '')]}

@st.cache_data(ttl=86400)
def fetch_fred(sid, start=START):
    """Fetch a FRED series from the configured start date."""
    s = fred.get_series(sid, observation_start=start)
    s.index = pd.to_datetime(s.index)
    return s.dropna()


@st.cache_data(ttl=86400)
def fetch_equity():
    """Fetch close and volume data for dashboard tickers from Yahoo Finance."""
    ht = [t for e in HOLDINGS.values() for t, _, _ in e]
    tks = list(set(
        list(FACTORS) + list(SECTORS) + list(INDICES) + list(INDICES_CHART)
        + list(EW_SECTORS.values()) + RETAIL_ETFS + ht + [BENCH, "RSP"]
    ))

    try:
        raw = yf.download(
            tks,
            start=START,
            auto_adjust=True,
            progress=False,
            threads=True
        )
        close_df = normalize_yf_panel(raw, "Close")
        volume_df = normalize_yf_panel(raw, "Volume")

        if close_df.empty:
            raise ValueError("No close data returned from Yahoo Finance.")

        return close_df, volume_df

    except Exception:
        core = list(set(
            list(FACTORS) + list(SECTORS) + list(INDICES) + list(INDICES_CHART)
            + list(EW_SECTORS.values()) + RETAIL_ETFS + [BENCH, "RSP"]
        ))

        raw = yf.download(
            core,
            start=START,
            auto_adjust=True,
            progress=False,
            threads=True
        )
        close_df = normalize_yf_panel(raw, "Close")
        volume_df = normalize_yf_panel(raw, "Volume")
        return close_df, volume_df

@st.cache_data(ttl=86400)
def fetch_benchmark_ohlc(start=START, ticker=BENCH):
    """Fetch OHLCV history for a single benchmark ticker."""
    raw = yf.download(ticker, start=start, auto_adjust=True, progress=False, threads=True)
    if raw is None or len(raw) == 0:
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.index = pd.to_datetime(raw.index, errors='coerce')
    raw = raw[~raw.index.isna()]
    cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in raw.columns]
    if len(cols) < 4:
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    out = raw[cols].copy()
    for missing in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if missing not in out.columns:
            out[missing] = np.nan
    return out[['Open', 'High', 'Low', 'Close', 'Volume']].dropna(how='all')

@st.cache_data(ttl=86400)
def fetch_release_snapshot():
    """Build the macro release snapshot table displayed on the calendar tab."""
    rows = []
    for name, sid, unit, calc in KEY_RELEASES:
        try:
            s = fetch_fred(sid, start='2022-01-01')
            if len(s) < 2:
                continue
            lv, pv = (s.iloc[-1], s.iloc[-2])
            ld = s.index[-1].strftime('%b %d, %Y')
            if calc == 'yoy':
                sy = s.pct_change(12) * 100
                lv, pv = (round(sy.iloc[-1], 2), round(sy.iloc[-2], 2))
            elif calc == 'mom':
                sm = s.pct_change() * 100
                lv, pv = (round(sm.iloc[-1], 2), round(sm.iloc[-2], 2))
            elif calc == 'diff':
                lv, pv = (round(s.diff().iloc[-1], 2), round(s.diff().iloc[-2], 2))
            else:
                lv, pv = (round(lv, 2), round(pv, 2))
            nd = '---'
            try:
                ts = datetime.today().strftime('%Y-%m-%d')
                te = (datetime.today() + timedelta(days=60)).strftime('%Y-%m-%d')
                rr = requests.get(f'https://api.stlouisfed.org/fred/series/release?series_id={sid}&api_key={FRED_KEY}&file_type=json', timeout=5)
                if rr.status_code == 200:
                    releases = rr.json().get('releases', [])
                    if not releases:
                        raise ValueError('No release metadata')
                    rid = releases[0]['id']
                    dr = requests.get(f'https://api.stlouisfed.org/fred/release/dates?release_id={rid}&api_key={FRED_KEY}&file_type=json&realtime_start={ts}&realtime_end={te}&include_release_dates_with_no_data=true', timeout=5)
                    if dr.status_code == 200:
                        fu = [d['date'] for d in dr.json().get('release_dates', []) if d['date'] >= ts]
                        if fu:
                            nd = pd.Timestamp(fu[0]).strftime('%b %d, %Y')
            except Exception:
                pass
            rows.append({'Release': name, 'Last Updated': ld, 'Previous': pv, 'Latest': lv, 'Unit': unit, 'Next Release': nd})
        except Exception:
            continue
    return pd.DataFrame(rows)

@st.cache_data(ttl=86400)
def fetch_fred_calendar():
    """Fetch recent and upcoming FRED release dates."""
    today = datetime.today()
    ps = (today - timedelta(days=35)).strftime('%Y-%m-%d')
    fs = (today + timedelta(days=45)).strftime('%Y-%m-%d')
    try:
        r = requests.get(f'https://api.stlouisfed.org/fred/releases/dates?api_key={FRED_KEY}&file_type=json&realtime_start={ps}&realtime_end={fs}&include_release_dates_with_no_data=true', timeout=10)
        if r.status_code != 200:
            return pd.DataFrame()
        df = pd.DataFrame(r.json().get('release_dates', []))
        if df.empty:
            return df
        df = df.rename(columns={'release_name': 'Release', 'date': 'Date'})
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        return df[['Date', 'Release']].sort_values('Date').reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

def to_yoy(s):
    """Convert a level series into year-over-year percent change."""
    s = s.dropna()
    return s.pct_change(12) * 100

def trim(s, m):
    """Trim a time series to the trailing *m* months when requested."""
    s = s.dropna()
    if s.empty or not m:
        return s
    return s[s.index >= s.index.max() - pd.DateOffset(months=m)]

def compute_relative(p, d):
    """Compute ETF/SPY relative price and rolling relative alpha series."""
    if p.empty or BENCH not in p.columns:
        return (pd.DataFrame(), pd.DataFrame())
    avail = [k for k in d.keys() if k in p.columns]
    if not avail:
        return (pd.DataFrame(), pd.DataFrame())
    rel = p[avail].div(p[BENCH], axis=0).dropna(how='all')
    alpha = (1 + rel.pct_change()).rolling(ROLL).apply(np.prod, raw=True) - 1
    return (rel, alpha)

def reindex_from(df, bd):
    """Reindex a DataFrame to 1.0 from a requested base date."""
    if df.empty:
        return df
    df = df[df.index >= pd.Timestamp(bd)].dropna(how='all')
    if df.empty:
        return df
    base = df.iloc[0].replace(0, np.nan)
    return df.div(base, axis=1)

def src_ann(y=-0.3):
    """Return a reusable Plotly source annotation dictionary."""
    return dict(text='Source: FRED / Yahoo Finance', xref='paper', yref='paper', x=1.0, y=y, showarrow=False, font=dict(size=10, color='#888888'), xanchor='right')

def get_negative_spread_ranges(s):
    """Return contiguous date ranges where a spread series is negative."""
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
    """Compose a consistent chart title string."""
    return f'{m} {s}'

def safe_fmt(v):
    """Safely format a scalar as a 2-decimal string."""
    try:
        if pd.isna(v):
            return '---'
        return f'{float(v):.2f}'
    except (ValueError, TypeError):
        return str(v)

def snap_color(row):
    """Highlight the latest macro release value relative to the previous print."""
    st_ = [''] * len(row)
    try:
        l, p = (float(row['Latest']), float(row['Previous']))
        i = list(row.index).index('Latest')
        st_[i] = 'color:#2ca02c;font-weight:bold' if l > p else 'color:#d62728;font-weight:bold' if l < p else ''
    except (ValueError, TypeError):
        pass
    return st_

def add_src(fig, y=-0.25):
    """Add a standard source annotation to a Plotly figure."""
    fig.add_annotation(text='Source: FRED / Yahoo Finance', xref='paper', yref='paper', x=1.0, y=y, showarrow=False, font=dict(size=10, color='#888888'), xanchor='right')

def compute_volume_zscore(v, lb=ZSCORE_LOOKBACK):
    """Compute a clipped rolling z-score for raw volume."""
    v = v.dropna()
    if v.empty:
        return pd.Series(dtype=float)
    rm = v.rolling(lb, min_periods=60).mean()
    rs = v.rolling(lb, min_periods=60).std().replace(0, np.nan)
    return ((v - rm) / rs).clip(-3, 3).dropna()

def compute_flow_proxy_z(P, V, t, lb=ZSCORE_LOOKBACK):
    """Estimate a simple ETF flow proxy and return its rolling z-score."""
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
    """Compute a signed-volume rolling z-score using daily return direction."""
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
    """Return the equal-weight versus cap-weight breadth ratio (RSP/SPY)."""
    if P.empty or 'RSP' not in P.columns or 'SPY' not in P.columns:
        return pd.Series(dtype=float)
    r, s = (P['RSP'].dropna(), P['SPY'].dropna())
    c = r.index.intersection(s.index)
    if len(c) == 0:
        return pd.Series(dtype=float)
    return (r.loc[c] / s.loc[c]).dropna()

def compute_rotation_ratio(P, smooth=21, nw=252):
    """Compare between-sector dispersion with within-sector dispersion."""
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

def build_positioning_table(P, V, d, rd):
    """Build a cross-sectional positioning table for a ticker dictionary."""
    rows = []
    for t, n in d.items():
        try:
            p = P[t].dropna()
            if len(p) < 2:
                continue
            ret = p.pct_change().iloc[-1] * 100 if rd == 1 else (p.iloc[-1] / p.iloc[-rd] - 1) * 100 if len(p) > rd else np.nan
            fz = compute_flow_proxy_z(P, V, t)
            fzv = round(fz.iloc[-1], 2) if len(fz) > 0 else np.nan
            svz = compute_signed_volume_z(P, V, t)
            svzv = round(svz.iloc[-1], 2) if len(svz) > 0 else np.nan
            rs = p.pct_change()
            rm = rs.rolling(ZSCORE_LOOKBACK, min_periods=60).mean()
            rsd = rs.rolling(ZSCORE_LOOKBACK, min_periods=60).std()
            rzv = float(np.clip((rs.iloc[-1] - rm.iloc[-1]) / rsd.iloc[-1], -3, 3))
            comp = [v for v in [fzv, svzv, rzv] if not np.isnan(v)]
            cv = round(np.mean(comp), 2) if comp else np.nan
            rows.append({'Ticker': t, 'Name': n, 'Return %': round(ret, 2) if not np.isnan(ret) else np.nan, 'Flow Z': fzv, 'Signed Vol Z': svzv, 'Composite': cv})
        except Exception:
            continue
    return pd.DataFrame(rows)

def style_pos(df):
    """Apply color styling to the positioning table."""

    def cz(v):
        """Cz."""
        if pd.isna(v):
            return ''
        if v >= 2:
            return 'color:#2ca02c;font-weight:bold'
        if v <= -2:
            return 'color:#d62728;font-weight:bold'
        if v >= 1:
            return 'color:#2ca02c'
        if v <= -1:
            return 'color:#d62728'
        return ''

    def cr(v):
        """Cr."""
        if pd.isna(v):
            return ''
        return 'color:#2ca02c' if v > 0 else 'color:#d62728' if v < 0 else ''
    s = df.style
    for c in ['Flow Z', 'Signed Vol Z', 'Composite']:
        if c in df.columns:
            s = s.map(cz, subset=[c])
    for c in ['Return %']:
        if c in df.columns:
            s = s.map(cr, subset=[c])
    fmt = {c: '{:+.2f}' for c in ['Return %', 'Flow Z', 'Signed Vol Z', 'Composite'] if c in df.columns}
    return s.format(fmt, na_rep='---')

def style_attr(df):
    """Apply return-based color styling to the holdings attribution table."""

    def c(v):
        """C."""
        if pd.isna(v):
            return ''
        return 'color:#2ca02c' if v > 0 else 'color:#d62728' if v < 0 else ''
    s = df.style
    for col in [x for x in ['1D Ret %', 'Contribution', '5D Ret %', '1M Ret %'] if x in df.columns]:
        s = s.map(c, subset=[col])
    return s.format({'1D Ret %': '{:+.2f}', 'Contribution': '{:+.3f}', '5D Ret %': '{:+.2f}', '1M Ret %': '{:+.2f}'}, na_rep='---')

def build_holdings_attr(etf, P):
    """Build a holdings-level daily attribution table for a sector ETF."""
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

def yield_curve_commentary():
    """Generate a plain-English summary of the current Treasury curve."""
    try:
        y2, y10, y30 = (fetch_fred('DGS2').iloc[-1], fetch_fred('DGS10').iloc[-1], fetch_fred('DGS30').iloc[-1])
        sp = (fetch_fred('DGS10') - fetch_fred('DGS2')).dropna()
        sn = sp.iloc[-1]
        sp2 = sp.iloc[-63] if len(sp) > 63 else sp.iloc[0]
        ch = sn - sp2
        sh = 'inverted' if sn < -0.1 else 'flat' if sn < 0.1 else 'upward sloping'
        tr = 'steepening' if ch > 0.1 else 'flattening' if ch < -0.1 else 'unchanged'
        return f'Currently **{sh}** -- 2Y {y2:.2f}% / 10Y {y10:.2f}% / 30Y {y30:.2f}% / 10Y-2Y {sn:+.2f}% / {tr} over 3M'
    except Exception:
        return ''

def build_yield_curve():
    """Build the current Treasury spot-rate curve chart."""
    mats = {'DGS1MO': '1M', 'DGS3MO': '3M', 'DGS6MO': '6M', 'DGS1': '1Y', 'DGS2': '2Y', 'DGS5': '5Y', 'DGS10': '10Y', 'DGS20': '20Y', 'DGS30': '30Y'}
    vs, ls = ([], [])
    for sid, lbl in mats.items():
        try:
            s = fetch_fred(sid, start='2020-01-01')
            vs.append(round(s.iloc[-1], 3))
            ls.append(lbl)
        except Exception:
            pass
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ls, y=vs, mode='lines+markers', line=dict(color='#1f77b4', width=2.5), marker=dict(size=8), showlegend=False))
    fig.update_layout(title=chart_title('Current Yield Curve', 'Spot rates 1M-30Y'), template='plotly_white', height=380, yaxis_title='Yield (%)', xaxis_title='Maturity', margin=dict(b=70, t=60, l=60, r=40), dragmode=False)
    add_src(fig, -0.18)
    return fig

# Info/Help Content Dictionary
HELP_CONTENT = {
    'us_major_indices': 'Shows how the four major U.S. stock indices are performing — S&P 500 (large caps), Nasdaq 100 (tech-heavy), Russell 2000 (small caps), and Dow 30 (large-cap industrials). When these move together, the market is "bullish." When they diverge, it signals confusion or sector concentration.',
    'sector_positioning': 'Each sector (Tech, Healthcare, Financials, etc.) gets a score based on three factors: money flowing in/out, unusual trading volume, and recent price momentum. Higher scores suggest strength; lower scores suggest weakness. The green and red colors quickly show which sectors are hot and cold.',
    'daily_positioning': 'These four metrics tell the story of market breadth and behavior: Sector Rotation tracks if large-cap stocks or smaller stocks are leading. Breadth Ratio compares equal-weight vs. cap-weight SPY (narrow leadership = caution). Flow Z-Score measures unusual money movement. Vol Regime tracks if volatility is elevated.',
    'benchmark_price_action': 'This candlestick chart shows the daily open, high, low, and close prices for SPY (S&P 500 ETF). The 20-day moving average (blue line) acts as a trend indicator. Green candles = price up, red candles = price down. Use this to spot support/resistance levels and recent trend direction.',
    'relative_performance': 'Compares how each sector or factor has performed vs. SPY. A ratio above 1.0 = outperforming. A ratio below 1.0 = underperforming. The 126-day rolling alpha strips out the market effect to show whether a sector is truly beating or lagging on its own merits.',
    'etf_flow_analysis': 'Monitors buying and selling activity (flow proxy) and price changes for a single ETF you select. Green = inflows + rising prices (strength). Red = outflows + falling prices (weakness). The z-scores highlight whether this activity is unusual or "normal."',
    'sector_holdings': 'Breaks down the largest holdings (e.g., AAPL in Tech) and shows their daily performance. The "Contribution" column tells you which stocks are helping or hurting the sector ETF return today. A large negative contribution means that stock is dragging down the sector.',
    'top_bottom_composite': 'Identifies the strongest and weakest performers ranked by a composite score combining flow, volume, and momentum. The Composite score averages three z-scores (Flow Z-Score, Signed Volume Z-Score, Return Z-Score), all calculated over 252 trading days. A score of +2 or higher is very bullish; -2 or lower is very bearish.',
    'yield_curve': 'Shows current U.S. Treasury yields across maturities (1 month to 30 years). When the curve is steep (long-term yields much higher than short-term), growth is expected. When flat or inverted, recession risk is rising. Higher yields = tighter monetary conditions.',
    'yield_curve_trends': 'Tracks how the 10Y-2Y spread has moved over time. When it turns negative (inverted), it historically precedes recessions. When it steepens, it suggests economic recovery. The shaded regions highlight inversion periods.',
    'credit_spreads': 'The gap between risky corporate bonds and safe U.S. Treasuries. Higher spreads = market is fearful. Lower spreads = market is confident. High-yield (junk bond) spreads are most sensitive to recession fears.',
    'macro_releases': 'Displays the most recent economic data (Nonfarm Payrolls, Unemployment, CPI, etc.) and compares it to the previous release. Green = better than previous; Red = worse than previous. The "Next Release" column tells you when new data is coming.',
    'fomc_calendar': 'Lists upcoming Federal Reserve decision dates and what the market expects. FOMC meetings occur 8 times per year. Policy changes at these meetings can move markets significantly.',
}

def init_modal_state():
    """Initialize session state for modals."""
    pass

def toggle_modal(modal_key):
    """Toggle modal open/closed state."""
    pass

def render_modal_overlay(modal_key, title, content):
    """Render a tooltip on hover - no modal overlay."""
    pass

def show_section_title_with_icon(title_text, icon_key):
    """
    Display a section title with "about" text in italics next to it.
    Hovering shows a CSS-based tooltip with help text.
    
    Args:
        title_text: The title to display
        icon_key: Key for HELP_CONTENT
    """
    if icon_key not in HELP_CONTENT:
        st.subheader(title_text)
        return
    
    help_text = HELP_CONTENT[icon_key]
    # Escape quotes and newlines for HTML
    safe_help = help_text.replace('"', '&quot;').replace('\n', ' ')
    
    # Create HTML with CSS tooltip on hover
    title_html = f"""
    <style>
        .title-about-wrapper {{
            display: flex;
            align-items: baseline;
            gap: 8px;
            position: relative;
        }}
        .title-about {{
            font-style: italic;
            color: #666;
            font-size: 0.85rem;
            cursor: help;
            border-bottom: 1px dotted #999;
            position: relative;
            display: inline-block;
        }}
        .title-about:hover {{
            color: #333;
        }}
        .title-about .tooltip {{
            visibility: hidden;
            background-color: #333;
            color: #fff;
            text-align: left;
            padding: 8px 12px;
            border-radius: 4px;
            position: absolute;
            z-index: 1000;
            bottom: 125%;
            left: 0;
            white-space: normal;
            width: 280px;
            font-size: 0.8rem;
            font-style: normal;
            line-height: 1.4;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
        }}
        .title-about:hover .tooltip {{
            visibility: visible;
            opacity: 1;
        }}
        .title-about .tooltip::after {{
            content: "";
            position: absolute;
            top: 100%;
            left: 8px;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #333 transparent transparent transparent;
        }}
    </style>
    <div class="title-about-wrapper">
        <h3 style="margin: 0; font-size: 1.3rem;">{title_text}</h3>
        <span class="title-about">i<div class="tooltip">{safe_help}</div></span>
    </div>
    """
    st.markdown(title_html, unsafe_allow_html=True)


st.markdown(f"""\n<div style="display:flex;justify-content:space-between;align-items:baseline">\n    <h1 style="margin:0">Macro Dashboard</h1>\n    <span style="color:#888;font-size:0.85rem">\n        Refreshed: {datetime.now().strftime('%b %d, %Y %H:%M')}\n        &nbsp;/&nbsp; Data: FRED / Yahoo Finance\n    </span>\n</div>\n""", unsafe_allow_html=True)
st.markdown(f"""
<div style="margin:1rem 0 1.5rem;padding:0.9rem 1rem;border-radius:8px;border:1px solid #e6e6e6;background:#fafafa">
  <p style="margin:0 0 0.5rem;font-size:0.95rem;color:#222">
    <strong>Dashboard overview</strong>: This report combines macroeconomic series from FRED with equity and ETF data from Yahoo Finance. Data scope begins {START} and reflects the last trading day (updated daily from cached calls).
  </p>
  <p style="margin:0;font-size:0.85rem;color:#555">
    Use hover details and legend clicks to inspect each series. Radio buttons and dropdown menus allow you to change time windows and compare market behavior across multiple horizons.
  </p>
</div>
""", unsafe_allow_html=True)
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    'Introduction',
    'Equities',
    'Fixed Income & Macro',
    'Calendar',
    'Conclusion'
])

with tab0:
    st.title("Introduction")

    st.markdown("""
### Project Overview
This dashboard connects **macroeconomic conditions** with **equity market behavior** using data from **FRED** and **Yahoo Finance**. The goal is to help users interpret how inflation, interest rates, growth expectations, breadth, and ETF positioning interact rather than looking at each signal in isolation.

The app is organized around several linked layers:
- broad U.S. index performance
- sector and factor leadership
- ETF flow and positioning signals
- fixed income and macro context
- calendar timing through releases and FOMC dates

### How to Use the Dashboard
- Navigate with the tabs across the top
- Use radio buttons and dropdowns to adjust the time horizon
- Hover over charts for exact values
- Click legend items on interactive charts to isolate series

### Main Questions This Dashboard Helps Answer
- Is the market broad or concentrated?
- Are sectors and factors seeing accumulation or distribution?
- What macro conditions are supporting or challenging risk appetite?
- When are the next important economic and policy catalysts?
""")

    st.divider()

    st.subheader("Quick Preview")
    st.caption("These two visuals introduce the dashboard by showing a short-term market snapshot and a cross-sectional sector heatmap.")

    intro_left, intro_right = st.columns(2)

    with intro_left:
        st.markdown("**SPY Candlestick Preview**")
        st.caption("Interactive instructions: hover for OHLC details and use the moving-average legend to isolate the line. Takeaway: candlesticks help show short-term trend direction, reversal behavior, and recent volatility in the broad market.")

        try:
            intro_ohlc = fetch_benchmark_ohlc(
                start=(pd.Timestamp.today() - pd.DateOffset(months=3)).strftime("%Y-%m-%d")
            )

            if not intro_ohlc.empty:
                fig_intro_candle = go.Figure()
                fig_intro_candle.add_trace(go.Candlestick(
                    x=intro_ohlc.index,
                    open=intro_ohlc["Open"],
                    high=intro_ohlc["High"],
                    low=intro_ohlc["Low"],
                    close=intro_ohlc["Close"],
                    increasing_line_color="#2ca02c",
                    decreasing_line_color="#d62728",
                    name="SPY"
                ))
                fig_intro_candle.add_trace(go.Scatter(
                    x=intro_ohlc.index,
                    y=intro_ohlc["Close"].rolling(20).mean(),
                    mode="lines",
                    line=dict(color="#1f77b4", width=1.8),
                    name="20D MA"
                ))
                fig_intro_candle.update_layout(
                    title=chart_title("SPY Preview", "Recent candlestick view"),
                    template="plotly_white",
                    height=360,
                    margin=dict(b=65, t=55, l=55, r=35),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.18,
                        x=0.5,
                        xanchor="center",
                        font=dict(size=11)
                    ),
                    dragmode=False
                )
                fig_intro_candle.update_yaxes(title_text="Price ($)")
                add_src(fig_intro_candle, -0.22)
                st.plotly_chart(fig_intro_candle, use_container_width=True, config=PCFG)
            else:
                st.info("Intro candlestick preview unavailable.")
        except Exception:
            st.info("Intro candlestick preview unavailable.")

    with intro_right:
        st.markdown("**Sector Heatmap Preview**")
        st.caption("Interactive instructions: hover over each cell to compare 5-day and 1-month returns across sectors. Takeaway: the heatmap quickly shows which sectors are leading, lagging, or diverging across short-term horizons.")

        try:
            prices_intro, _ = fetch_equity()
            sector_rows_intro = []

            for ticker, name in SECTORS.items():
                if ticker not in prices_intro.columns:
                    continue
                series = prices_intro[ticker].dropna()
                if len(series) < 22:
                    continue

                ret_1m = (series.iloc[-1] / series.iloc[-21] - 1) * 100
                ret_5d = (series.iloc[-1] / series.iloc[-5] - 1) * 100 if len(series) >= 5 else np.nan

                sector_rows_intro.append({
                    "Ticker": ticker,
                    "Sector": name,
                    "1M Return": round(ret_1m, 2),
                    "5D Return": round(ret_5d, 2) if pd.notna(ret_5d) else np.nan
                })

            intro_heat_df = pd.DataFrame(sector_rows_intro)

            if not intro_heat_df.empty:
                intro_heat = (
                    alt.Chart(intro_heat_df)
                    .mark_rect(cornerRadius=4)
                    .encode(
                        x=alt.X("Ticker:N", sort=list(SECTORS.keys()), title=None),
                        y=alt.Y("Metric:N", title=None),
                        color=alt.Color(
                            "Value:Q",
                            scale=alt.Scale(scheme="redyellowgreen"),
                            title="Return %"
                        ),
                        tooltip=[
                            "Sector:N",
                            "Ticker:N",
                            "Metric:N",
                            alt.Tooltip("Value:Q", format=".2f")
                        ]
                    )
                    .transform_fold(
                        ["1M Return", "5D Return"],
                        as_=["Metric", "Value"]
                    )
                    .properties(height=220, title="Sector return heatmap preview")
                )
                st.altair_chart(intro_heat, use_container_width=True)
                st.markdown(SRC_BOTH, unsafe_allow_html=True)
            else:
                st.info("Intro heatmap preview unavailable.")
        except Exception:
            st.info("Intro heatmap preview unavailable.")

    st.divider()

    st.markdown("""
### How to Read the Rest of the Dashboard
- The **Equities** tab focuses on index behavior, breadth, relative performance, ETF flows, and holdings attribution.
- The **Fixed Income & Macro** tab provides the policy and economic backdrop through yields, spreads, inflation, and growth.
- The **Calendar** tab adds timing context through recent and upcoming macro releases and FOMC dates.

### Intro Takeaway
The dashboard is intended to be read as a **connected system**. Price action, sector leadership, flows, yields, inflation, and policy all reinforce or challenge one another. The strongest signals usually come from **confluence across multiple sections**, not from a single chart alone.
""")

with tab1:
    with st.spinner('Loading equity data...'):
        prices, volumes = fetch_equity()
    period_opts = {'Past 12M': None, 'Since 2015': '2015-01-01', 'Since 2020': '2020-01-01', 'Since 2025': '2025-01-01'}
    
    # U.S. Major Indices Section with Info Icon
    show_section_title_with_icon("U.S. Major Indices", 'us_major_indices')
    
    hdr_l, hdr_r = st.columns(2)
    with hdr_l:
        idx_period = st.radio('Period', ['1M', '3M', '6M', 'YTD', '1Y'], horizontal=True, key='idx_period')
        latest = prices.index.max()
        idx_start = pd.Timestamp(f'{latest.year}-01-01') if idx_period == 'YTD' else latest - pd.DateOffset(months={'1M': 1, '3M': 3, '6M': 6, '1Y': 12}[idx_period])
        idx_colors = {'^GSPC': '#1f77b4', '^IXIC': '#ff7f0e', '^RUT': '#2ca02c', '^DJI': '#d62728'}
        fig_idx = go.Figure()
        for t, n in INDICES_CHART.items():
            if t in prices.columns:
                s = prices[t].dropna()
                s = s[s.index >= idx_start]
                if len(s) > 1:
                    ix = (s / s.iloc[0] - 1) * 100
                    fig_idx.add_trace(go.Scatter(x=ix.index, y=np.round(ix.values, 2), name=n, mode='lines', line=dict(color=idx_colors.get(t, '#999'), width=2.5), customdata=np.round(s.values, 2), hovertemplate=f'<b>{n}</b><br>Date: %{{x|%b %d, %Y}}<br>Return: %{{y:+.2f}}%<br>Level: %{{customdata:,.2f}}<extra></extra>'))
        fig_idx.add_hline(y=0, line_dash='dash', line_color='gray', line_width=1)
        fig_idx.update_layout(title=chart_title('U.S. Major Indices', f'{idx_period} cumulative return'), template='plotly_white', height=420, yaxis_title='Return (%)', margin=dict(b=60, t=40, l=50, r=30), legend=dict(orientation='h', yanchor='top', y=-0.35, x=0.5, xanchor='center', font=dict(size=11)), dragmode=False, font=dict(size=11))
        add_src(fig_idx, -0.35)
        st.plotly_chart(fig_idx, use_container_width=True, key='fig_idx', config=PCFG)
    with hdr_r:
        # Sector Positioning with Info Icon
        show_section_title_with_icon("Sector Positioning", 'sector_positioning')
        
        rows = []
        for t, n in SECTORS.items():
            try:
                p = prices[t].dropna()
                if len(p) < 2:
                    continue
                r1 = p.pct_change().iloc[-1] * 100
                r5 = (p.iloc[-1] / p.iloc[-5] - 1) * 100 if len(p) >= 5 else np.nan
                r1m = (p.iloc[-1] / p.iloc[-21] - 1) * 100 if len(p) >= 21 else np.nan
                r12m = (p.iloc[-1] / p.iloc[-252] - 1) * 100 if len(p) >= 252 else np.nan
                fz = compute_flow_proxy_z(prices, volumes, t)
                fzv = round(fz.iloc[-1], 2) if len(fz) > 0 else np.nan
                svz = compute_signed_volume_z(prices, volumes, t)
                svzv = round(svz.iloc[-1], 2) if len(svz) > 0 else np.nan
                rs = p.pct_change()
                rm = rs.rolling(ZSCORE_LOOKBACK, min_periods=60).mean()
                rsd = rs.rolling(ZSCORE_LOOKBACK, min_periods=60).std()
                rzv = float(np.clip((rs.iloc[-1] - rm.iloc[-1]) / rsd.iloc[-1], -3, 3))
                comp = [v for v in [fzv, svzv, rzv] if not np.isnan(v)]
                cv = round(np.mean(comp), 2) if comp else np.nan
                rows.append({'Ticker': t, 'Name': n, '1D': round(r1, 2), '5D': round(r5, 2) if not np.isnan(r5) else np.nan, '1M': round(r1m, 2) if not np.isnan(r1m) else np.nan, '12M': round(r12m, 2) if not np.isnan(r12m) else np.nan, 'Flow Z': fzv, 'Composite': cv})
            except Exception:
                continue
        df_pos = pd.DataFrame(rows)
        if not df_pos.empty and 'Composite' in df_pos.columns:
            df_pos = df_pos.dropna(subset=['Composite']).sort_values('Composite', ascending=False).reset_index(drop=True)
            t3, b3 = (df_pos.head(3), df_pos.tail(3))

            def _sty(d):
                """ sty."""

                def cz(v):
                    """Cz."""
                    if pd.isna(v):
                        return ''
                    if v >= 2:
                        return 'color:#2ca02c;font-weight:bold'
                    if v <= -2:
                        return 'color:#d62728;font-weight:bold'
                    if v >= 1:
                        return 'color:#2ca02c'
                    if v <= -1:
                        return 'color:#d62728'
                    return ''

                def cr2(v):
                    """Cr2."""
                    if pd.isna(v):
                        return ''
                    return 'color:#2ca02c' if v > 0 else 'color:#d62728' if v < 0 else ''

                s = d.style
                for c in ['Flow Z', 'Composite']:
                    if c in d.columns:
                        s = s.map(cz, subset=[c])
                for c in ['1D', '5D', '1M', '12M']:
                    if c in d.columns:
                        s = s.map(cr2, subset=[c])
                fmt = {c: '{:+.2f}' for c in ['1D', '5D', '1M', '12M', 'Flow Z', 'Composite'] if c in d.columns}
                return s.format(fmt, na_rep='---')
            
            col_top_title, col_top_info = st.columns([0.95, 0.05])
            with col_top_title:
                st.markdown('**Top 3 by Composite** <span style="font-style: italic; color: #666; font-size: 0.85rem; cursor: help; border-bottom: 1px dotted #999;" title="' + HELP_CONTENT['top_bottom_composite'].replace('"', '&quot;') + '">about</span>', unsafe_allow_html=True)
            with col_top_info:
                pass
            
            st.caption('Composite = (Flow Z + Signed Vol Z + Return Z) / 3 -- all 252-day rolling, clipped +/-3')
            st.dataframe(_sty(t3), hide_index=True, use_container_width=True, height=140)
            
            st.markdown('**Bottom 3 by Composite**')
            st.caption('Composite = (Flow Z + Signed Vol Z + Return Z) / 3 -- all 252-day rolling, clipped +/-3')
            st.dataframe(_sty(b3), hide_index=True, use_container_width=True, height=140)
            
            st.markdown(SRC_BOTH, unsafe_allow_html=True)
    st.divider()
    
    # Benchmark Price Action with Info Icon
    show_section_title_with_icon('Benchmark Price Action', 'benchmark_price_action')
    
    st.caption('Interactive instructions: hover for OHLC details and use the dropdown to change the viewing window. Takeaway: this chart shows short-term trend structure, reversals, and volatility in SPY.')
    spy_window = st.selectbox('SPY candlestick window', ['3M', '6M', '1Y', 'Since 2015'], key='spy_window', index=1)
    spy_start = {'3M': prices.index.max() - pd.DateOffset(months=3), '6M': prices.index.max() - pd.DateOffset(months=6), '1Y': prices.index.max() - pd.DateOffset(years=1), 'Since 2015': pd.Timestamp(START)}[spy_window]
    spy_ohlc = fetch_benchmark_ohlc(start=spy_start.strftime('%Y-%m-%d'))
    if not spy_ohlc.empty:
        fig_spy = go.Figure()
        fig_spy.add_trace(go.Candlestick(x=spy_ohlc.index, open=spy_ohlc['Open'], high=spy_ohlc['High'], low=spy_ohlc['Low'], close=spy_ohlc['Close'], increasing_line_color='#2ca02c', decreasing_line_color='#d62728', name=BENCH))
        fig_spy.add_trace(go.Scatter(x=spy_ohlc.index, y=spy_ohlc['Close'].rolling(20).mean(), mode='lines', line=dict(color='#1f77b4', width=1.8), name='20D MA'))
        fig_spy.update_layout(title=chart_title('SPY Candlestick', 'Price action with 20-day moving average'), template='plotly_white', height=420, margin=dict(b=70, t=60, l=60, r=40), legend=LEG, dragmode=False)
        fig_spy.update_yaxes(title_text='Price ($)')
        add_src(fig_spy, -0.18)
        st.plotly_chart(fig_spy, use_container_width=True, key='fig_spy_candle', config=PCFG)
    else:
        st.info('SPY candlestick data unavailable.')
    
    # Daily Positioning Feed with Info Icon
    show_section_title_with_icon('Daily Positioning Feed', 'daily_positioning')
    
    st.caption('Interactive instructions: use the regime window selector to compare recent shifts across 3M, 6M, and 12M horizons. Takeaway: these four charts summarize whether leadership is broad or narrow, defensive or cyclical, and whether trading activity is unusually elevated.')
    regime_window = st.radio('Regime window', ['3M', '6M', '12M'], horizontal=True, key='regime_window', index=2)
    regime_months = {'3M': 3, '6M': 6, '12M': 12}[regime_window]
    regime_cutoff = prices.index.max() - pd.DateOffset(months=regime_months)
    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        try:
            rr_pct, rr_raw = compute_rotation_ratio(prices)
            if len(rr_pct) > 0:
                rv = rr_pct.iloc[-1]
                rl = 'Sector rotation' if rv > 0.75 else 'Stock dispersion' if rv < 0.25 else 'Balanced'
                rt = rr_pct[rr_pct.index >= regime_cutoff]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=rt.index, y=rt.values, mode='lines', line=dict(color='#1f77b4', width=2), showlegend=False))
                fig.add_hline(y=0.5, line_dash='dash', line_color='gray')
                fig.add_hrect(y0=0.25, y1=0.75, fillcolor='gray', opacity=0.08, line_width=0)
                fig.update_layout(title=dict(text=f"<b>Macro vs Micro</b> -- {rv:.2f} ({rl})<br><span style='font-size:11px;color:#666'>>0.75 sector-driven / <0.25 stock-driven</span>", font=dict(size=12)), template='plotly_white', height=380, yaxis_title='%-tile', yaxis=dict(range=[0, 1], dtick=0.25), margin=dict(b=70, t=65, l=45, r=25), dragmode=False)
                add_src(fig, -0.25)
                st.plotly_chart(fig, use_container_width=True, key='fig_rotation', config=PCFG)
            else:
                st.info('Rotation ratio unavailable.')
        except Exception:
            rr_pct, rr_raw = (pd.Series(dtype=float), pd.Series(dtype=float))
            st.info('Rotation ratio unavailable.')
    with rc2:
        try:
            br = compute_breadth(prices)
            if len(br) > 0:
                bt = br[br.index >= regime_cutoff]
                bi = bt / bt.iloc[0]
                bn = bi.iloc[-1]
                bl = 'Broad' if bn > 1.005 else 'Concentrated' if bn < 0.995 else 'Neutral'
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=bi.index, y=bi.values, mode='lines', line=dict(color='#ff7f0e', width=2), showlegend=False))
                fig.add_hline(y=1.0, line_dash='dash', line_color='gray')
                fig.update_layout(title=dict(text=f"<b>Breadth</b> -- {bn:.4f} ({bl})<br><span style='font-size:11px;color:#666'>RSP/SPY / rising = broadening</span>", font=dict(size=12)), template='plotly_white', height=380, yaxis_title='Indexed', margin=dict(b=70, t=65, l=45, r=25), dragmode=False)
                add_src(fig, -0.25)
                st.plotly_chart(fig, use_container_width=True, key='fig_breadth', config=PCFG)
        except Exception:
            st.info('Breadth data unavailable.')
    with rc3:
        try:
            cy = prices[list(SECTORS_CYCLICAL.keys())].pct_change().mean(axis=1)
            de = prices[list(SECTORS_DEFENSIVE.keys())].pct_change().mean(axis=1)
            cc, dc = ((1 + cy).cumprod(), (1 + de).cumprod())
            ratio = cc / dc
            rt2 = ratio[ratio.index >= regime_cutoff]
            ri2 = rt2 / rt2.iloc[0]
            cn = ri2.iloc[-1]
            cl = 'Risk-on' if cn > 1.005 else 'Risk-off' if cn < 0.995 else 'Neutral'
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ri2.index, y=ri2.values, mode='lines', line=dict(color='#2ca02c', width=2), showlegend=False))
            fig.add_hline(y=1.0, line_dash='dash', line_color='gray')
            fig.update_layout(title=dict(text=f"<b>Cyclical / Defensive</b> -- {cn:.4f} ({cl})<br><span style='font-size:11px;color:#666'>Rising = risk-on / falling = risk-off</span>", font=dict(size=12)), template='plotly_white', height=380, yaxis_title='Ratio', margin=dict(b=70, t=65, l=45, r=25), dragmode=False)
            add_src(fig, -0.25)
            st.plotly_chart(fig, use_container_width=True, key='fig_cyc_def', config=PCFG)
        except Exception:
            st.info('Cyclical/Defensive unavailable.')
    with rc4:
        try:
            sv = volumes['SPY'].dropna()
            s1y = sv[sv.index >= sv.index.max() - pd.DateOffset(months=12)]
            sm, ss = (s1y.median(), s1y.std())
            szf = ((sv - sm) / ss).clip(-3, 3)
            c3m = sv.index.max() - pd.DateOffset(months=3)
            sz = szf[szf.index >= c3m]
            szn = sz.iloc[-1]
            bc = ['#2ca02c' if v >= 0 else '#d62728' for v in sz.values]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=sz.index, y=sz.values, marker_color=bc, opacity=0.7, showlegend=False))
            fig.add_hline(y=0, line_dash='dash', line_color='gray', line_width=1)
            fig.add_hline(y=2, line_dash='dot', line_color='#2ca02c', line_width=0.8)
            fig.add_hline(y=-2, line_dash='dot', line_color='#d62728', line_width=0.8)
            fig.update_layout(title=dict(text=f"<b>SPY Volume</b> -- {szn:+.2f}s today<br><span style='font-size:11px;color:#666'>0 = 1Y median / 3M window / +/-3</span>", font=dict(size=12)), template='plotly_white', height=380, yaxis_title='Z-Score', yaxis=dict(range=[-3.5, 3.5], dtick=1), margin=dict(b=70, t=65, l=45, r=25), bargap=0.15, dragmode=False)
            add_src(fig, -0.25)
            st.plotly_chart(fig, use_container_width=True, key='fig_spy_vol', config=PCFG)
        except Exception:
            st.info('SPY volume unavailable.')
    st.divider()
    
    # Relative Performance with Info Icon
    show_section_title_with_icon('Relative Performance', 'relative_performance')
    
    pf = st.radio('Period', list(period_opts.keys()), horizontal=True, key='pf')
    base = period_opts[pf] or (prices.index.max() - pd.DateOffset(months=12)).strftime('%Y-%m-%d')

    def _build_pair(ad, gl, bd, ks):
        """ build pair."""
        rel, alpha = compute_relative(prices, ad)
        ri = reindex_from(rel, bd)
        al = alpha[alpha.index >= pd.Timestamp(bd)]
        cl, cr2 = st.columns(2)
        with cl:
            fig = go.Figure()
            for t, n in ad.items():
                if t in ri.columns:
                    c = SECTOR_COLORS.get(t) or FACTOR_COLORS.get(t)
                    fig.add_trace(go.Scatter(x=ri.index, y=ri[t], name=n, mode='lines', line=dict(color=c, width=2) if c else dict(width=2)))
            fig.add_hline(y=1.0, line_dash='dash', line_color='gray')
            fig.update_layout(title=chart_title(f'{gl} Relative Performance', 'ETF / SPY, indexed to 1.0'), template='plotly_white', height=380, margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
            add_src(fig, -0.22)
            st.plotly_chart(fig, use_container_width=True, key=f'rel_{ks}', config=PCFG)
        with cr2:
            fig = go.Figure()
            for t, n in ad.items():
                if t in al.columns:
                    c = SECTOR_COLORS.get(t) or FACTOR_COLORS.get(t)
                    fig.add_trace(go.Scatter(x=al.index, y=al[t], name=n, mode='lines', line=dict(color=c, width=2) if c else dict(width=2)))
            fig.add_hline(y=0.0, line_dash='dash', line_color='gray')
            fig.update_layout(title=chart_title(f'{gl} Rolling 6M Alpha', 'Compounded 126-day relative return'), template='plotly_white', height=380, margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
            add_src(fig, -0.22)
            st.plotly_chart(fig, use_container_width=True, key=f'alpha_{ks}', config=PCFG)
    st.markdown('#### Factors')
    _build_pair(FACTORS, 'Factor', base, 'factors')
    st.markdown('#### Cyclical-Tilt Sectors')
    _build_pair(SECTORS_CYCLICAL, 'Cyclical-Tilt', base, 'cyclical')
    st.markdown('#### Defensive-Tilt Sectors')
    _build_pair(SECTORS_DEFENSIVE, 'Defensive-Tilt', base, 'defensive')
    st.divider()
    st.subheader('Individual ETF -- Flow & Price')
    st.caption('Interactive instructions: use the chart window selector to switch between 3M, 6M, and 1Y views, then hover over each chart for values. Takeaway: rising prices with positive flow bars suggest stronger confirmation, while price gains with negative flows may indicate weaker participation.')
    cwopt = st.radio('Chart window', ['3M', '6M', '1Y'], horizontal=True, key='etf_cw', index=1)
    cbd = {'3M': 63, '6M': 126, '1Y': 252}[cwopt]

    def build_flow_chart(t, lbl, P, V, w):
        """Build a recent return-plus-flow chart for one ETF."""
        if P.empty or V.empty or t not in P.columns or (t not in V.columns):
            return None
        p, v = latest_common_window(P[t].dropna(), V[t].dropna(), w)
        if p.empty or v.empty or len(p) < 10:
            return None
        pi = (p / p.iloc[0] - 1) * 100
        fz = compute_flow_proxy_z(P, V, t)
        if fz.empty:
            return None
        fz = fz[fz.index >= p.index.min()]
        cm = pi.index.intersection(fz.index)
        pi, fz = (pi.loc[cm], fz.loc[cm])
        if len(cm) < 5:
            return None
        bc = ['#2ca02c' if v >= 0 else '#d62728' for v in fz.values]
        fig = make_subplots(specs=[[{'secondary_y': True}]])
        fig.add_trace(go.Bar(x=fz.index, y=fz.values, name='Flow Z', marker_color=bc, opacity=0.35, showlegend=False), secondary_y=True)
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', name='🟩🟥 Flow Z', marker=dict(size=0, color='rgba(0,0,0,0)')))
        fig.add_trace(go.Scatter(x=pi.index, y=pi.values, name='Return %', mode='lines', line=dict(color='#1f77b4', width=2.5)), secondary_y=False)
        fig.add_hline(y=0, line_dash='dash', line_color='gray', line_width=0.8, secondary_y=False)
        fig.update_layout(title=dict(text=f"<b>{lbl}</b> ({t})<br><span style='font-size:11px;color:#666'>Return % / Flow z (252d) / green = accumulation</span>", font=dict(size=13)), template='plotly_white', height=320, margin=dict(b=55, t=65, l=50, r=40), legend=dict(orientation='h', yanchor='top', y=-0.18, x=0.5, xanchor='center', font=dict(size=11)), dragmode=False, bargap=0.1)
        fig.update_yaxes(title_text='Return %', secondary_y=False)
        fig.update_yaxes(title_text='Flow Z', secondary_y=True, range=[-3.5, 3.5], dtick=1, showgrid=False)
        add_src(fig, -0.22)
        return fig
    st.markdown('#### Sector ETFs')
    sc = st.columns(3)
    for i, (t, n) in enumerate(SECTORS.items()):
        f = build_flow_chart(t, n, prices, volumes, cbd)
        if f:
            with sc[i % 3]:
                st.plotly_chart(f, use_container_width=True, key=f'flow_{t}', config=PCFG)
    st.markdown('#### Factor ETFs')
    fc = st.columns(3)
    for i, (t, n) in enumerate(FACTORS.items()):
        f = build_flow_chart(t, n, prices, volumes, cbd)
        if f:
            with fc[i % 3]:
                st.plotly_chart(f, use_container_width=True, key=f'flow_{t}', config=PCFG)
    st.divider()
    st.subheader('Altair Views')
    st.caption('Interactive instructions: hover to compare sectors and macro series more quickly than in the larger charts. Takeaway: these compressed views help identify short-term winners, laggards, and macro relationships at a glance.')
    alt_left, alt_right = st.columns(2)
    with alt_left:
        try:
            sector_rows = []
            for ticker, name in SECTORS.items():
                if ticker not in prices.columns:
                    continue
                series = prices[ticker].dropna()
                if len(series) < 22:
                    continue
                ret_1m = (series.iloc[-1] / series.iloc[-21] - 1) * 100
                ret_5d = (series.iloc[-1] / series.iloc[-5] - 1) * 100 if len(series) >= 5 else np.nan
                sector_rows.append({'Ticker': ticker, 'Sector': name, '1M Return': round(ret_1m, 2), '5D Return': round(ret_5d, 2) if pd.notna(ret_5d) else np.nan})
            alt_df = pd.DataFrame(sector_rows)
            if not alt_df.empty:
                heat = alt.Chart(alt_df).mark_rect(cornerRadius=4).encode(x=alt.X('Ticker:N', sort=list(SECTORS.keys()), title=None), y=alt.Y('Metric:N', title=None), color=alt.Color('Value:Q', scale=alt.Scale(scheme='redyellowgreen'), title='Return %'), tooltip=['Sector:N', 'Ticker:N', 'Metric:N', alt.Tooltip('Value:Q', format='.2f')]).transform_fold(['1M Return', '5D Return'], as_=['Metric', 'Value']).properties(height=160, title='Sector return heatmap')
                st.altair_chart(heat, use_container_width=True)
                st.markdown(SRC_BOTH, unsafe_allow_html=True)
            else:
                st.info('Not enough sector data for the Altair heatmap.')
        except Exception:
            st.info('Altair sector heatmap unavailable.')
    with alt_right:
        try:
            spread = fetch_fred('T10Y2Y', start='2023-01-01')
            ff = fetch_fred('FEDFUNDS', start='2023-01-01')
            un = fetch_fred('UNRATE', start='2023-01-01')
            macro_df = pd.concat({'10Y-2Y Spread': spread, 'Fed Funds': ff, 'Unemployment': un}, axis=1).dropna().reset_index(names='Date')
            if not macro_df.empty:
                long_macro = macro_df.melt(id_vars='Date', var_name='Series', value_name='Value')
                line = alt.Chart(long_macro).mark_line(point=False).encode(x=alt.X('Date:T', title=None), y=alt.Y('Value:Q', title=None), color=alt.Color('Series:N', legend=alt.Legend(orient='bottom')), tooltip=[alt.Tooltip('Date:T'), 'Series:N', alt.Tooltip('Value:Q', format='.2f')]).properties(height=220, title='Macro pulse')
                st.altair_chart(line, use_container_width=True)
                st.markdown(SRC_FRED, unsafe_allow_html=True)
            else:
                st.info('Not enough macro data for the Altair line chart.')
        except Exception:
            st.info('Altair macro chart unavailable.')
    st.divider()
    st.subheader('Sector ETF Holdings & Daily Attribution')
    st.caption('Interactive instructions: expand any sector ETF to inspect the holdings table. Takeaway: this section shows which stocks are driving daily ETF performance and whether sector moves are concentrated in a few names or spread more broadly.')
    ec = st.columns(2)
    for i, (t, n) in enumerate(SECTORS.items()):
        with ec[i % 2]:
            with st.expander(f'**{n}** ({t})'):
                try:
                    da, er, il = build_holdings_attr(t, prices)
                    st2 = 'live' if il else 'static'
                    if not da.empty:
                        ex = da['Contribution'].sum()
                        if pd.notna(er) and abs(er) > 0.001:
                            st.caption(f'ETF 1D: **{er:+.2f}%** / Top holdings explain: **{ex:+.3f}%** ({ex / er * 100:.0f}%) / {st2}')
                        else:
                            er_txt = f'{er:+.2f}%' if pd.notna(er) else 'N/A'
                            st.caption(f'ETF 1D: **{er_txt}** / {st2}')
                        st.dataframe(style_attr(da), hide_index=True, use_container_width=True, height=min(35 * len(da) + 38, 340))
                    else:
                        st.info('Holdings data unavailable.')
                except Exception:
                    st.info('Holdings data unavailable.')
    st.markdown(SRC_YF, unsafe_allow_html=True)
    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>', unsafe_allow_html=True)
with tab2:
    ri1, ri2, ri3, ri4, ri5, ri6 = st.columns(6)
    for col, sid, lbl, sd, u in [(ri1, 'DGS2', '2Y Treasury', True, '%'), (ri2, 'DGS10', '10Y Treasury', True, '%'), (ri3, 'DGS30', '30Y Treasury', True, '%'), (ri4, 'FEDFUNDS', 'Fed Funds', False, '%'), (ri5, 'CPIAUCSL', 'CPI YoY', True, '%'), (ri6, 'T10Y2Y', '10Y-2Y', True, '%')]:
        try:
            s = to_yoy(fetch_fred(sid)) if sid == 'CPIAUCSL' else fetch_fred(sid)
            c, p = (s.iloc[-1], s.iloc[-2])
            d = f'{c - p:+.2f}{u}' if sd else None
            col.metric(lbl, f'{c:.2f}{u}', d)
        except Exception:
            col.metric(lbl, 'N/A')
    st.markdown(SRC_FRED, unsafe_allow_html=True)
    st.divider()
    
    # Yield Curve Section with Info Icon
    show_section_title_with_icon('Yield Curve & Treasury Rates', 'yield_curve')
    
    rp = st.radio('Period', ['1Y', '3Y', '5Y', '10Y', 'Full'], horizontal=True, key='rp')
    rmons = {'1Y': 12, '3Y': 36, '5Y': 60, '10Y': 120, 'Full': None}[rp]
    yc_col, yld_col = st.columns(2)
    with yc_col:
        st.plotly_chart(build_yield_curve(), use_container_width=True, key='yc_rates', config=PCFG)
        c = yield_curve_commentary()
        if c:
            st.caption(c)
    with yld_col:
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        fig = go.Figure()
        for i, (sid, lbl) in enumerate(YIELDS.items()):
            try:
                s = trim(fetch_fred(sid), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines', line=dict(color=colors[i], width=2)))
            except Exception:
                pass
        fig.update_layout(title=chart_title('Treasury Yields', 'Constant-maturity daily'), template='plotly_white', height=380, yaxis_title='Yield (%)', margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key='fig_yields', config=PCFG)
    
    # Yield Spreads, Real Yields, and Credit Spreads Section with Info Icon
    show_section_title_with_icon('Market Structure: Spreads & Credit', 'credit_spreads')
    
    r2a, r2b, r2c = st.columns(3)
    with r2a:
        fig = go.Figure()
        for sid, lbl in SPREADS.items():
            try:
                s = trim(fetch_fred(sid), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            except Exception:
                pass
        fig.add_hline(y=0, line_dash='dash', line_color='red', line_width=1)
        try:
            spread = trim(fetch_fred('T10Y2Y'), rmons)
            inv_periods = get_negative_spread_ranges(spread)
            for start, end in inv_periods:
                fig.add_vrect(x0=start, x1=end, fillcolor='LightSalmon', opacity=0.12, line_width=0)
        except Exception:
            pass
        fig.update_layout(title=chart_title('Curve Spreads', 'Below 0 = inverted / shaded = contiguous inversion'), template='plotly_white', height=340, yaxis_title='Spread (%)', margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key='fig_spreads', config=PCFG)
    with r2b:
        fig = go.Figure()
        for sid, lbl in [('DFII10', '10Y Real Yield'), ('T10YIE', '10Y Breakeven')]:
            try:
                s = trim(fetch_fred(sid), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            except Exception:
                pass
        fig.update_layout(title=chart_title('Real Yield & Breakeven', 'TIPS + implied inflation'), template='plotly_white', height=340, yaxis_title='%', margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key='fig_realyield', config=PCFG)
    with r2c:
        fig = go.Figure()
        for sid, lbl in CREDIT.items():
            try:
                s = trim(fetch_fred(sid), rmons) * 100
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            except Exception:
                pass
        try:
            hy = trim(fetch_fred('BAMLH0A0HYM2'), rmons)
            ig = trim(fetch_fred('BAMLC0A0CM'), rmons)
            gap = (hy - ig).dropna() * 100
            fig.add_trace(go.Scatter(x=gap.index, y=gap.values, name='HY-IG Gap', mode='lines', line=dict(dash='dot', width=1.5)))
        except Exception:
            pass
        fig.update_layout(title=chart_title('Credit Spreads (OAS)', 'Wider = risk-off'), template='plotly_white', height=340, yaxis_title='bps', margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key='fig_credit', config=PCFG)
    st.divider()
    il, ir = st.columns(2)
    with il:
        fig = go.Figure()
        for sid, lbl in [('CPIAUCSL', 'CPI'), ('CPILFESL', 'Core CPI')]:
            try:
                s = trim(to_yoy(fetch_fred(sid)), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            except Exception:
                pass
        fig.add_hline(y=2.0, line_dash='dash', line_color='red', annotation_text='2%', annotation_position='bottom right')
        fig.update_layout(title=chart_title('CPI & Core CPI', 'YoY %'), template='plotly_white', height=360, yaxis_title='YoY %', margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key='fig_cpi', config=PCFG)
    with ir:
        fig = go.Figure()
        for sid, lbl in [('PCEPI', 'PCE'), ('PCEPILFE', 'Core PCE')]:
            try:
                s = trim(to_yoy(fetch_fred(sid)), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            except Exception:
                pass
        fig.add_hline(y=2.0, line_dash='dash', line_color='red', annotation_text='2%', annotation_position='bottom right')
        fig.update_layout(title=chart_title('PCE & Core PCE', "YoY % / Fed's preferred gauge"), template='plotly_white', height=360, yaxis_title='YoY %', margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key='fig_pce', config=PCFG)
    el, gl = st.columns(2)
    with el:
        fig = go.Figure()
        for sid, lbl, clr in [('FEDFUNDS', 'Fed Funds', '#1f77b4'), ('UNRATE', 'Unemployment', '#ff7f0e')]:
            try:
                s = trim(fetch_fred(sid), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines', line=dict(color=clr, width=2)))
            except Exception:
                pass
        fig.update_layout(title=chart_title('Fed Funds & Unemployment', 'Dual mandate'), template='plotly_white', height=360, yaxis_title='%', margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key='fig_ff', config=PCFG)
    with gl:
        try:
            gdp = trim(fetch_fred('A191RL1Q225SBEA'), rmons)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=gdp.index, y=gdp.values, name='GDP Growth', marker_color=['#2ca02c' if v >= 0 else '#d62728' for v in gdp.values]))
            fig.add_hline(y=0, line_color='black', line_width=1)
            fig.update_layout(title=chart_title('Real GDP Growth', 'QoQ annualized %'), template='plotly_white', height=360, yaxis_title='% QoQ Ann.', margin=dict(b=90, t=50, l=55, r=30), legend=LEG, dragmode=False)
            add_src(fig, -0.22)
            st.plotly_chart(fig, use_container_width=True, key='fig_gdp', config=PCFG)
        except Exception:
            st.info('GDP data unavailable.')
    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>', unsafe_allow_html=True)
with tab3:
    cl, cr3 = st.columns([3, 1])
    with cl:
        show_section_title_with_icon('Upcoming Releases', 'macro_releases')
        
        st.caption('Interactive instructions: scroll the table to compare recent and upcoming releases. Takeaway: this section highlights the latest macro prints and their previous values so the user can see where economic momentum is accelerating or slowing.')
        with st.spinner('Loading...'):
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(snap.style.apply(snap_color, axis=1).format({'Previous': safe_fmt, 'Latest': safe_fmt}, na_rep='---'), hide_index=True, use_container_width=True, height=420)
                st.markdown(SRC_FRED, unsafe_allow_html=True)
        st.divider()
        
        show_section_title_with_icon('Release Calendar', 'fomc_calendar')
        
        st.caption('Interactive instructions: scroll through the calendar and use the color cues to distinguish past, present, and upcoming events. Takeaway: this gives timing context for when major macro catalysts may affect the market.')
        with st.spinner('Loading calendar...'):
            cal = fetch_fred_calendar()
            if cal.empty:
                st.info('No calendar data available.')
            else:
                tts = pd.Timestamp.today().normalize()

                def cs(row):
                    """Cs."""
                    d = pd.Timestamp(row['Date'])
                    if d.normalize() == tts:
                        return ['background-color:#fff3cd;font-weight:bold'] * len(row)
                    if d < tts:
                        return ['color:#aaaaaa'] * len(row)
                    return [''] * len(row)
                dc = cal.copy()
                dc['Date'] = dc['Date'].dt.strftime('%b %d, %Y')
                st.dataframe(dc.style.apply(cs, axis=1), hide_index=True, use_container_width=True, height=520)
                st.markdown(SRC_FRED, unsafe_allow_html=True)
    with cr3:
        st.subheader('FOMC Dates')
        td = datetime.today().date()
        for yr, mtgs in FOMC.items():
            st.caption(f'**{yr}**')
            for lbl, d, res in mtgs:
                md = datetime.strptime(d, '%Y-%m-%d').date()
                days = (md - td).days
                if days > 0:
                    st.markdown(f'🔵 **{lbl}** -- *{days}d*')
                elif days == 0:
                    st.markdown(f'🟡 **{lbl}** -- *today*')
                else:
                    note = f' / {res}' if res else ''
                    st.markdown(f'✅ ~~{lbl}~~{note}')
        st.divider()
        st.caption('**Current Fed Funds Rate**')
        try:
            ff = fetch_fred('FEDFUNDS')
            st.metric('Fed Funds', f'{ff.iloc[-1]:.2f}%')
        except Exception:
            st.metric('Fed Funds', 'N/A')
    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>', unsafe_allow_html=True)

with tab4:
    st.title("Conclusion")

    st.markdown("""
### Final Conclusions
This dashboard suggests that market interpretation is strongest when **price action**, **positioning**, and the **macro backdrop** are read together rather than in isolation.

### Main Lessons from the Dashboard
- **Breadth** helps distinguish healthy market participation from narrow concentration.
- **Sector and factor relative performance** show where leadership is rotating.
- **Flow z-scores** offer a proxy for accumulation versus distribution.
- **Yield curves, spreads, inflation, and Fed policy** provide the macro explanation for shifts in risk appetite.
- **Calendar timing** matters because macro releases and Fed meetings often act as catalysts for repricing.

### Interaction Guidance
- Use the **Equities** tab to compare leadership and positioning across sectors and factors.
- Use the **Fixed Income & Macro** tab to connect market moves to rates, inflation, and economic growth.
- Use the **Calendar** tab to identify upcoming events that may influence these trends.

### Overall Takeaway
The most useful signal in this project is not any single chart. Instead, the strongest interpretation comes from **confluence**:
- broad participation plus positive flows plus supportive macro conditions suggests a healthier backdrop
- narrowing breadth, defensive leadership, and wider spreads suggest a more cautious environment

### Limitations
- ETF flows here are proxies rather than exact fund flow data
- market data can be delayed or incomplete
- short-term readings may reverse quickly without broader confirmation

### Final Note
This dashboard is meant to support interpretation and discussion. Its value comes from helping the user move from isolated observations to a broader market narrative.
""")
