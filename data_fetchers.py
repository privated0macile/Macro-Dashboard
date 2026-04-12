from datetime import datetime, timedelta

import fredapi
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

from constants import (
    START, BENCH, FACTORS, SECTORS, INDICES, INDICES_CHART,
    EW_SECTORS, RETAIL_ETFS, HOLDINGS, YIELDS, KEY_RELEASES
)
from helpers import normalize_yf_panel, add_src, chart_title
from constants import PCFG

FRED_KEY = st.secrets['FRED_API_KEY']
fred = fredapi.Fred(api_key=FRED_KEY)

@st.cache_data(ttl=3600)
def fetch_fred(sid, start=START):
    s = fred.get_series(sid, observation_start=start)
    s.index = pd.to_datetime(s.index)
    return s.dropna()

@st.cache_data(ttl=3600)
def fetch_equity():
    ht = [t for e in HOLDINGS.values() for t, _, _ in e]
    tks = list(set(
        list(FACTORS) + list(SECTORS) + list(INDICES) + list(INDICES_CHART)
        + list(EW_SECTORS.values()) + RETAIL_ETFS + ht + [BENCH, 'RSP']
    ))
    try:
        raw = yf.download(tks, start=START, auto_adjust=True, progress=False, threads=True)
        close_df = normalize_yf_panel(raw, 'Close')
        volume_df = normalize_yf_panel(raw, 'Volume')
        if close_df.empty:
            raise ValueError('No close data returned from Yahoo Finance.')
        return close_df, volume_df
    except Exception:
        core = list(set(
            list(FACTORS) + list(SECTORS) + list(INDICES) + list(INDICES_CHART)
            + list(EW_SECTORS.values()) + RETAIL_ETFS + [BENCH, 'RSP']
        ))
        raw = yf.download(core, start=START, auto_adjust=True, progress=False, threads=True)
        close_df = normalize_yf_panel(raw, 'Close')
        volume_df = normalize_yf_panel(raw, 'Volume')
        return close_df, volume_df

@st.cache_data(ttl=3600)
def fetch_benchmark_ohlc(start=START, ticker=BENCH):
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
            out[missing] = pd.NA
    return out[['Open', 'High', 'Low', 'Close', 'Volume']].dropna(how='all')

@st.cache_data(ttl=3600)
def fetch_release_snapshot():
    rows = []
    for name, sid, unit, calc in KEY_RELEASES:
        try:
            s = fetch_fred(sid, start='2022-01-01')
            if len(s) < 2:
                continue
            lv, pv = s.iloc[-1], s.iloc[-2]
            ld = s.index[-1].strftime('%b %d, %Y')
            if calc == 'yoy':
                sy = s.pct_change(12) * 100
                lv, pv = round(sy.iloc[-1], 2), round(sy.iloc[-2], 2)
            elif calc == 'mom':
                sm = s.pct_change() * 100
                lv, pv = round(sm.iloc[-1], 2), round(sm.iloc[-2], 2)
            elif calc == 'diff':
                lv, pv = round(s.diff().iloc[-1], 2), round(s.diff().iloc[-2], 2)
            else:
                lv, pv = round(lv, 2), round(pv, 2)
            nd = '---'
            try:
                ts = datetime.today().strftime('%Y-%m-%d')
                te = (datetime.today() + timedelta(days=60)).strftime('%Y-%m-%d')
                rr = requests.get(f'https://api.stlouisfed.org/fred/series/release?series_id={sid}&api_key={FRED_KEY}&file_type=json', timeout=5)
                if rr.status_code == 200:
                    releases = rr.json().get('releases', [])
                    if releases:
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

@st.cache_data(ttl=1800)
def fetch_fred_calendar():
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
        return df.dropna(subset=['Date'])[['Date', 'Release']].sort_values('Date').reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

def yield_curve_commentary():
    try:
        y2, y10, y30 = fetch_fred('DGS2').iloc[-1], fetch_fred('DGS10').iloc[-1], fetch_fred('DGS30').iloc[-1]
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
    mats = {'DGS1MO': '1M', 'DGS3MO': '3M', 'DGS6MO': '6M', 'DGS1': '1Y', 'DGS2': '2Y', 'DGS5': '5Y', 'DGS10': '10Y', 'DGS20': '20Y', 'DGS30': '30Y'}
    vs, ls = [], []
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
