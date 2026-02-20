import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import fredapi

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Macro Dashboard", layout="wide", page_icon="📊")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.1rem; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

# ─── SECRETS ─────────────────────────────────────────────────────────────────
FRED_KEY = st.secrets["FRED_API_KEY"]
fred = fredapi.Fred(api_key=FRED_KEY)

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
START = "2015-01-01"
BENCH = "SPY"
ROLL = 126

CM = dict(b=120, t=60, l=60, r=40)
LEG = dict(orientation="h", yanchor="top", y=-0.25, x=0.5, xanchor="center")
PCFG = dict(displayModeBar=False, scrollZoom=False)

FACTORS = {
    "MTUM": "Momentum", "QUAL": "Quality", "SIZE": "Size",
    "VLUE": "Value", "USMV": "Min Vol"
}
SECTORS = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Healthcare", "XLI": "Industrials", "XLY": "Cons. Disc.",
    "XLP": "Cons. Staples", "XLB": "Materials", "XLU": "Utilities",
    "XLRE": "Real Estate"
}
INDICES = {
    "SPY": "S&P 500", "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000", "DIA": "Dow 30"
}
EW_SECTORS = {
    "XLK": "RYT", "XLF": "RYF", "XLE": "RYE", "XLV": "RYH",
    "XLI": "RGI", "XLY": "RCD", "XLP": "RHS", "XLB": "RTM",
    "XLU": "RYU", "XLRE": "EWRE"
}
RETAIL_ETFS = ["TQQQ", "SQQQ"]

# Hardcoded holdings (always available as fallback)
HOLDINGS = {
    "XLK": [
        ("AAPL", "Apple", 0.22), ("MSFT", "Microsoft", 0.21),
        ("NVDA", "Nvidia", 0.11), ("AVGO", "Broadcom", 0.05),
        ("CRM", "Salesforce", 0.03), ("ADBE", "Adobe", 0.03),
        ("AMD", "AMD", 0.03), ("CSCO", "Cisco", 0.02),
    ],
    "XLF": [
        ("BRK-B", "Berkshire", 0.14), ("JPM", "JPMorgan", 0.11),
        ("V", "Visa", 0.09), ("MA", "Mastercard", 0.07),
        ("BAC", "BofA", 0.05), ("WFC", "Wells Fargo", 0.04),
        ("GS", "Goldman", 0.03), ("MS", "Morgan Stanley", 0.03),
    ],
    "XLE": [
        ("XOM", "Exxon", 0.23), ("CVX", "Chevron", 0.16),
        ("COP", "ConocoPhillips", 0.08), ("WMB", "Williams", 0.06),
        ("EOG", "EOG Resources", 0.05), ("SLB", "Schlumberger", 0.05),
        ("PSX", "Phillips 66", 0.04), ("MPC", "Marathon Petro", 0.04),
    ],
    "XLV": [
        ("LLY", "Eli Lilly", 0.12), ("UNH", "UnitedHealth", 0.10),
        ("JNJ", "J&J", 0.07), ("ABBV", "AbbVie", 0.07),
        ("MRK", "Merck", 0.06), ("TMO", "Thermo Fisher", 0.04),
        ("ABT", "Abbott", 0.04), ("PFE", "Pfizer", 0.03),
    ],
    "XLI": [
        ("GE", "GE Aerospace", 0.09), ("CAT", "Caterpillar", 0.06),
        ("RTX", "RTX Corp", 0.05), ("UNP", "Union Pacific", 0.05),
        ("HON", "Honeywell", 0.05), ("DE", "Deere", 0.04),
        ("BA", "Boeing", 0.04), ("LMT", "Lockheed", 0.03),
    ],
    "XLY": [
        ("AMZN", "Amazon", 0.23), ("TSLA", "Tesla", 0.15),
        ("HD", "Home Depot", 0.10), ("MCD", "McDonald's", 0.05),
        ("LOW", "Lowe's", 0.04), ("BKNG", "Booking", 0.04),
        ("TJX", "TJX Cos", 0.03), ("NKE", "Nike", 0.02),
    ],
    "XLP": [
        ("PG", "Procter & Gamble", 0.15), ("COST", "Costco", 0.14),
        ("WMT", "Walmart", 0.10), ("KO", "Coca-Cola", 0.10),
        ("PEP", "PepsiCo", 0.09), ("PM", "Philip Morris", 0.06),
        ("MDLZ", "Mondelez", 0.04), ("MO", "Altria", 0.03),
    ],
    "XLB": [
        ("LIN", "Linde", 0.19), ("SHW", "Sherwin-Williams", 0.09),
        ("FCX", "Freeport-McMoRan", 0.08), ("APD", "Air Products", 0.06),
        ("ECL", "Ecolab", 0.06), ("NEM", "Newmont", 0.05),
        ("NUE", "Nucor", 0.04), ("DOW", "Dow Inc", 0.04),
    ],
    "XLU": [
        ("NEE", "NextEra", 0.15), ("SO", "Southern Co", 0.10),
        ("DUK", "Duke Energy", 0.08), ("CEG", "Constellation", 0.07),
        ("SRE", "Sempra", 0.05), ("AEP", "AEP", 0.05),
        ("D", "Dominion", 0.04), ("PCG", "PG&E", 0.04),
    ],
    "XLRE": [
        ("PLD", "Prologis", 0.13), ("AMT", "American Tower", 0.10),
        ("EQIX", "Equinix", 0.09), ("WELL", "Welltower", 0.07),
        ("SPG", "Simon Property", 0.06), ("DLR", "Digital Realty", 0.05),
        ("PSA", "Public Storage", 0.05), ("O", "Realty Income", 0.05),
    ],
}

@st.cache_data(ttl=86400)
def fetch_live_holdings(etf_ticker, top_n=10):
    """Try to pull live holdings from yfinance. Returns list or None."""
    try:
        t = yf.Ticker(etf_ticker)
        fd = t.funds_data
        if fd is None:
            return None
        df = fd.top_holdings
        if df is None or df.empty:
            return None
        result = []
        for idx_val in df.index[:top_n]:
            tkr = str(idx_val).strip()
            wt = float(df.iloc[df.index.get_loc(idx_val), 0])
            if wt > 1:
                wt = wt / 100.0
            result.append((tkr, tkr, round(wt, 4)))
        return result if len(result) >= 3 else None
    except Exception:
        return None

def get_holdings(etf_ticker):
    """Return holdings for an ETF: try live, fall back to hardcoded."""
    live = fetch_live_holdings(etf_ticker)
    if live:
        return live, True
    return HOLDINGS.get(etf_ticker, []), False

YIELDS = {"DGS2": "2Y", "DGS5": "5Y", "DGS10": "10Y", "DGS30": "30Y"}
SPREADS = {"T10Y2Y": "10Y–2Y Spread", "T10Y3M": "10Y–3M Spread"}
CREDIT = {"BAMLH0A0HYM2": "HY OAS", "BAMLC0A0CM": "IG OAS"}

KEY_RELEASES = [
    ("Nonfarm Payrolls",       "PAYEMS",            "000s MoM", "diff"),
    ("Unemployment Rate",      "UNRATE",            "%",        "level"),
    ("CPI YoY",                "CPIAUCSL",          "% YoY",    "yoy"),
    ("Core CPI YoY",           "CPILFESL",          "% YoY",    "yoy"),
    ("PCE YoY",                "PCEPI",             "% YoY",    "yoy"),
    ("Core PCE YoY",           "PCEPILFE",          "% YoY",    "yoy"),
    ("GDP Growth QoQ Ann.",    "A191RL1Q225SBEA",   "% Ann.",   "level"),
    ("Retail Sales MoM",       "RSAFS",             "% MoM",    "mom"),
    ("Industrial Production",  "INDPRO",            "% MoM",    "mom"),
    ("Fed Funds Rate",         "FEDFUNDS",          "%",        "level"),
    ("10Y–2Y Spread",          "T10Y2Y",            "%",        "level"),
]

FOMC = {
    "2025": [
        ("Jan 28–29", "2025-01-29"), ("Mar 18–19", "2025-03-19"),
        ("May 6–7",   "2025-05-07"), ("Jun 17–18", "2025-06-18"),
        ("Jul 29–30", "2025-07-30"), ("Sep 16–17", "2025-09-17"),
        ("Oct 28–29", "2025-10-29"), ("Dec 9–10",  "2025-12-10"),
    ],
    "2026": [
        ("Jan 27–28", "2026-01-28"), ("Mar 17–18", "2026-03-18"),
        ("Apr 28–29", "2026-04-29"), ("Jun 9–10",  "2026-06-10"),
        ("Jul 28–29", "2026-07-29"), ("Sep 15–16", "2026-09-16"),
        ("Oct 27–28", "2026-10-28"), ("Dec 8–9",   "2026-12-09"),
    ]
}

ZSCORE_LOOKBACK = 63
CHART_WINDOW = 63

# ─── DATA FETCHERS ───────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_fred_series(series_id, start=START):
    s = fred.get_series(series_id, observation_start=start)
    s.index = pd.to_datetime(s.index)
    return s.dropna()

@st.cache_data(ttl=3600)
def fetch_equity():
    holding_tickers = []
    for etf, stocks in HOLDINGS.items():
        for tkr, _, _ in stocks:
            holding_tickers.append(tkr)
    tickers = (list(FACTORS.keys()) + list(SECTORS.keys())
               + list(INDICES.keys()) + list(EW_SECTORS.values())
               + RETAIL_ETFS + holding_tickers
               + [BENCH, "RSP"])
    tickers = list(set(tickers))
    raw = yf.download(tickers, start=START, auto_adjust=True, progress=False)
    close = raw["Close"]
    volume = raw["Volume"]
    return close, volume

@st.cache_data(ttl=3600)
def fetch_release_snapshot():
    rows = []
    for name, sid, unit, calc in KEY_RELEASES:
        try:
            s = fetch_fred_series(sid, start="2022-01-01")
            if len(s) < 2:
                continue
            last_val, prev_val = s.iloc[-1], s.iloc[-2]
            last_date = s.index[-1].strftime("%b %d, %Y")
            if calc == "yoy":
                sy = s.pct_change(12) * 100
                last_val, prev_val = round(sy.iloc[-1], 2), round(sy.iloc[-2], 2)
            elif calc == "mom":
                sm = s.pct_change() * 100
                last_val, prev_val = round(sm.iloc[-1], 2), round(sm.iloc[-2], 2)
            elif calc == "diff":
                last_val = round(s.diff().iloc[-1], 2)
                prev_val = round(s.diff().iloc[-2], 2)
            else:
                last_val, prev_val = round(last_val, 2), round(prev_val, 2)
            next_date = "—"
            try:
                today_str = datetime.today().strftime("%Y-%m-%d")
                to_str = (datetime.today() + timedelta(days=60)).strftime("%Y-%m-%d")
                rel_r = requests.get(
                    f"https://api.stlouisfed.org/fred/series/release"
                    f"?series_id={sid}&api_key={FRED_KEY}&file_type=json",
                    timeout=5)
                if rel_r.status_code == 200:
                    rel_id = rel_r.json()["releases"][0]["id"]
                    dates_r = requests.get(
                        f"https://api.stlouisfed.org/fred/release/dates"
                        f"?release_id={rel_id}&api_key={FRED_KEY}&file_type=json"
                        f"&realtime_start={today_str}&realtime_end={to_str}"
                        f"&include_release_dates_with_no_data=true",
                        timeout=5)
                    if dates_r.status_code == 200:
                        future = [d["date"] for d in dates_r.json().get("release_dates", [])
                                  if d["date"] >= today_str]
                        if future:
                            next_date = pd.Timestamp(future[0]).strftime("%b %d, %Y")
            except Exception:
                pass
            rows.append({
                "Release": name, "Last Updated": last_date,
                "Previous": prev_val, "Latest": last_val,
                "Unit": unit, "Next Release": next_date
            })
        except Exception:
            continue
    # Append next FOMC as a row
    today_d = datetime.today().date()
    all_fomc = FOMC.get("2025", []) + FOMC.get("2026", [])
    nxt = next(((l, d) for l, d in all_fomc
                if datetime.strptime(d, "%Y-%m-%d").date() >= today_d), None)
    if nxt:
        lbl, d = nxt
        days_away = (datetime.strptime(d, "%Y-%m-%d").date() - today_d).days
        rows.append({
            "Release": f"FOMC ({lbl})",
            "Last Updated": "—",
            "Previous": "—",
            "Latest": f"{days_away}d away",
            "Unit": "",
            "Next Release": pd.Timestamp(d).strftime("%b %d, %Y")
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=1800)
def fetch_fred_calendar():
    today = datetime.today()
    past_str = (today - timedelta(days=35)).strftime("%Y-%m-%d")
    fut_str = (today + timedelta(days=45)).strftime("%Y-%m-%d")
    url = (f"https://api.stlouisfed.org/fred/releases/dates"
           f"?api_key={FRED_KEY}&file_type=json"
           f"&realtime_start={past_str}&realtime_end={fut_str}"
           f"&include_release_dates_with_no_data=true")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return pd.DataFrame()
        rows = r.json().get("release_dates", [])
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df = df.rename(columns={"release_name": "Release", "date": "Date"})
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df[["Date", "Release"]].sort_values("Date").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def to_yoy(s):
    return s.pct_change(12) * 100

def trim(s, months):
    return s[s.index >= s.index.max() - pd.DateOffset(months=months)] if months else s

def compute_relative(prices, asset_dict):
    rel = prices[list(asset_dict.keys())].div(prices[BENCH], axis=0)
    alpha = (1 + rel.pct_change()).rolling(ROLL).apply(np.prod, raw=True) - 1
    return rel, alpha

def reindex_from(df, base_date):
    df = df[df.index >= pd.Timestamp(base_date)]
    return df / df.iloc[0]

def src_ann(y=-0.30):
    return dict(
        text="Source: FRED / Yahoo Finance",
        xref="paper", yref="paper", x=1.0, y=y,
        showarrow=False, font=dict(size=10, color="#888888"), xanchor="right"
    )

def chart_title(main, sub):
    return f"{main} {sub}"

# ─── VOLUME & POSITIONING HELPERS ────────────────────────────────────────────

def compute_volume_zscore(vol_series, lookback=ZSCORE_LOOKBACK):
    rm = vol_series.rolling(lookback, min_periods=20).mean()
    rs = vol_series.rolling(lookback, min_periods=20).std()
    return ((vol_series - rm) / rs).clip(-3, 3)

def compute_flow_proxy_z(prices, volumes, ticker, lookback=ZSCORE_LOOKBACK):
    if ticker not in prices.columns or ticker not in volumes.columns:
        return pd.Series(dtype=float)
    p = prices[ticker].dropna()
    v = volumes[ticker].dropna()
    common = p.index.intersection(v.index)
    p, v = p.loc[common], v.loc[common]
    dv = p * v
    ret = p.pct_change()
    flow = dv.diff() - (ret * dv.shift(1))
    rm = flow.rolling(lookback, min_periods=20).mean()
    rs = flow.rolling(lookback, min_periods=20).std()
    return ((flow - rm) / rs).clip(-3, 3)

def compute_signed_volume_z(prices, volumes, ticker, lookback=ZSCORE_LOOKBACK):
    if ticker not in prices.columns or ticker not in volumes.columns:
        return pd.Series(dtype=float)
    p = prices[ticker].dropna()
    v = volumes[ticker].dropna()
    common = p.index.intersection(v.index)
    p, v = p.loc[common], v.loc[common]
    sv = v * np.sign(p.pct_change())
    rm = sv.rolling(lookback, min_periods=20).mean()
    rs = sv.rolling(lookback, min_periods=20).std()
    return ((sv - rm) / rs).clip(-3, 3)

def compute_retail_intensity(volumes, lookback=ZSCORE_LOOKBACK):
    for t in ["TQQQ", "SQQQ", "QQQ"]:
        if t not in volumes.columns:
            return pd.Series(dtype=float)
    tqqq = volumes["TQQQ"].dropna()
    sqqq = volumes["SQQQ"].dropna()
    qqq = volumes["QQQ"].dropna()
    common = tqqq.index.intersection(sqqq.index).intersection(qqq.index)
    tqqq, sqqq, qqq = tqqq.loc[common], sqqq.loc[common], qqq.loc[common]
    qqq = qqq.replace(0, np.nan)
    ratio = (tqqq + sqqq) / qqq
    rm = ratio.rolling(lookback, min_periods=20).mean()
    rs = ratio.rolling(lookback, min_periods=20).std()
    return ((ratio - rm) / rs).clip(-3, 3)

def compute_breadth(prices):
    if "RSP" not in prices.columns or "SPY" not in prices.columns:
        return pd.Series(dtype=float)
    rsp = prices["RSP"].dropna()
    spy = prices["SPY"].dropna()
    common = rsp.index.intersection(spy.index)
    return rsp.loc[common] / spy.loc[common]

def compute_rotation_ratio(prices, smooth=21, norm_window=252):
    sec_rets = prices[list(SECTORS.keys())].pct_change().dropna()
    between = sec_rets.std(axis=1)
    within_parts = []
    for cw, ew in EW_SECTORS.items():
        if cw in prices.columns and ew in prices.columns:
            diff = (prices[ew].pct_change() - prices[cw].pct_change()).abs()
            within_parts.append(diff)
    if not within_parts:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    within = pd.concat(within_parts, axis=1).mean(axis=1).dropna()
    common = between.index.intersection(within.index)
    between, within = between.loc[common], within.loc[common]
    within = within.replace(0, np.nan)
    raw_ratio = between / within
    smoothed = raw_ratio.rolling(smooth, min_periods=10).mean()
    pct_rank = smoothed.rolling(norm_window, min_periods=60).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    return pct_rank.dropna(), smoothed.dropna()

def build_holdings_attribution(etf_ticker, prices):
    """Compute daily return attribution for an ETF's top holdings."""
    holdings, is_live = get_holdings(etf_ticker)
    if not holdings:
        return pd.DataFrame(), np.nan, False
    rows = []
    etf_ret = prices[etf_ticker].pct_change().iloc[-1] * 100 if etf_ticker in prices.columns else np.nan
    for tkr, name, wt in holdings:
        if tkr not in prices.columns:
            continue
        p = prices[tkr].dropna()
        if len(p) < 2:
            continue
        stock_ret = p.pct_change().iloc[-1] * 100
        contrib = wt * stock_ret
        ret_5d = ((p.iloc[-1] / p.iloc[-5]) - 1) * 100 if len(p) >= 5 else np.nan
        ret_1m = ((p.iloc[-1] / p.iloc[-21]) - 1) * 100 if len(p) >= 21 else np.nan
        rows.append({
            "Ticker": tkr, "Name": name, "Weight": f"{wt:.0%}",
            "1D Ret %": round(stock_ret, 2), "Contribution": round(contrib, 3),
            "5D Ret %": round(ret_5d, 2) if not np.isnan(ret_5d) else np.nan,
            "1M Ret %": round(ret_1m, 2) if not np.isnan(ret_1m) else np.nan,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Contribution", key=abs, ascending=False).reset_index(drop=True)
    return df, etf_ret, is_live

def build_positioning_table(prices, volumes, asset_dict, period_start):
    rows = []
    for tkr, name in asset_dict.items():
        try:
            p = prices[tkr].dropna()
            if len(p) < 2:
                continue
            ret_1d = p.pct_change().iloc[-1] * 100
            p_trim = p[p.index >= pd.Timestamp(period_start)]
            idx_ret = ((p_trim.iloc[-1] / p_trim.iloc[0]) - 1) * 100 if len(p_trim) > 1 else np.nan
            fz = compute_flow_proxy_z(prices, volumes, tkr)
            flow_z = round(fz.iloc[-1], 2) if len(fz) > 0 else np.nan
            svz = compute_signed_volume_z(prices, volumes, tkr)
            svol_z = round(svz.iloc[-1], 2) if len(svz) > 0 else np.nan
            ret_series = p.pct_change()
            ret_rm = ret_series.rolling(63, min_periods=20).mean()
            ret_rs = ret_series.rolling(63, min_periods=20).std()
            ret_z_val = float(np.clip(
                (ret_series.iloc[-1] - ret_rm.iloc[-1]) / ret_rs.iloc[-1], -3, 3))
            components = [v for v in [flow_z, svol_z, ret_z_val] if not np.isnan(v)]
            composite = round(np.mean(components), 2) if components else np.nan
            rows.append({
                "Ticker": tkr, "Name": name,
                "1D Ret %": round(ret_1d, 2), "Period Ret %": round(idx_ret, 2),
                "Flow Z": flow_z, "Signed Vol Z": svol_z, "Composite": composite
            })
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Flow Z", ascending=False).reset_index(drop=True)
    return df

def style_positioning_table(df):
    def _color_z(val):
        if pd.isna(val): return ""
        if val >= 2:  return "color:#2ca02c;font-weight:bold"
        if val <= -2: return "color:#d62728;font-weight:bold"
        if val >= 1:  return "color:#2ca02c"
        if val <= -1: return "color:#d62728"
        return ""
    def _color_ret(val):
        if pd.isna(val): return ""
        return "color:#2ca02c" if val > 0 else "color:#d62728" if val < 0 else ""
    styler = df.style
    for c in ["Flow Z", "Signed Vol Z", "Composite"]:
        if c in df.columns:
            styler = styler.map(_color_z, subset=[c])
    for c in ["1D Ret %", "Period Ret %"]:
        if c in df.columns:
            styler = styler.map(_color_ret, subset=[c])
    styler = styler.format({
        "1D Ret %": "{:+.2f}", "Period Ret %": "{:+.2f}",
        "Flow Z": "{:+.2f}", "Signed Vol Z": "{:+.2f}",
        "Composite": "{:+.2f}"
    }, na_rep="—")
    return styler

def style_attribution_table(df):
    def _c(val):
        if pd.isna(val): return ""
        return "color:#2ca02c" if val > 0 else "color:#d62728" if val < 0 else ""
    styler = df.style
    for c in [c for c in ["1D Ret %", "Contribution", "5D Ret %", "1M Ret %"] if c in df.columns]:
        styler = styler.map(_c, subset=[c])
    styler = styler.format({
        "1D Ret %": "{:+.2f}", "Contribution": "{:+.3f}",
        "5D Ret %": "{:+.2f}", "1M Ret %": "{:+.2f}",
    }, na_rep="—")
    return styler

def build_volume_chart(ticker, label, prices, volumes, window=CHART_WINDOW):
    if ticker not in prices.columns or ticker not in volumes.columns:
        return None
    p = prices[ticker].dropna()
    v = volumes[ticker].dropna()
    cutoff = p.index[-1] - pd.tseries.offsets.BDay(window)
    p, v = p[p.index >= cutoff], v[v.index >= cutoff]
    if len(p) < 10:
        return None
    p_idx = p / p.iloc[0]
    z_full = compute_volume_zscore(volumes[ticker].dropna())
    z = z_full[z_full.index >= cutoff]
    common = p_idx.index.intersection(z.index)
    p_idx, z = p_idx.loc[common], z.loc[common]
    bar_colors = ["#2ca02c" if val >= 0 else "#d62728" for val in z.values]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=z.index, y=z.values, name="Vol Z",
                         marker_color=bar_colors, opacity=0.35), secondary_y=True)
    fig.add_trace(go.Scatter(x=p_idx.index, y=p_idx.values, name=f"{label}",
                             mode="lines", line=dict(color="#1f77b4", width=2.5)),
                  secondary_y=False)
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray", line_width=1,
                  secondary_y=False)
    fig.update_layout(
        title=dict(text=(f"<b>{label}</b> ({ticker})<br>"
                         f"<span style='font-size:12px;color:#666'>"
                         f"Price indexed · Vol z-score (63d) ±3</span>"),
                   font=dict(size=14)),
        template="plotly_white", height=340,
        margin=dict(b=60, t=70, l=55, r=45),
        legend=dict(orientation="h", yanchor="top", y=-0.18,
                    x=0.5, xanchor="center", font=dict(size=10)),
        dragmode=False, bargap=0.1, annotations=[src_ann(-0.25)])
    fig.update_yaxes(title_text="Indexed", secondary_y=False)
    fig.update_yaxes(title_text="Vol Z", secondary_y=True,
                     range=[-3.5, 3.5], dtick=1, showgrid=False)
    return fig

# ─── YIELD / MACRO HELPERS ──────────────────────────────────────────────────

def yield_curve_commentary():
    try:
        y2 = fetch_fred_series("DGS2").iloc[-1]
        y10 = fetch_fred_series("DGS10").iloc[-1]
        y30 = fetch_fred_series("DGS30").iloc[-1]
        sp = (fetch_fred_series("DGS10") - fetch_fred_series("DGS2")).dropna()
        spread_now = sp.iloc[-1]
        spread_prev = sp.iloc[-63] if len(sp) > 63 else sp.iloc[0]
        change = spread_now - spread_prev
        shape = ("inverted" if spread_now < -0.1
                 else ("flat" if spread_now < 0.1 else "upward sloping"))
        trend = ("steepening" if change > 0.1
                 else ("flattening" if change < -0.1 else "unchanged"))
        return (f"Currently **{shape}** — 2Y {y2:.2f}% · 10Y {y10:.2f}% · "
                f"30Y {y30:.2f}% · 10Y–2Y {spread_now:+.2f}% · {trend} over 3M")
    except Exception:
        return ""

def build_yield_curve():
    maturities = {
        "DGS1MO": "1M", "DGS3MO": "3M", "DGS6MO": "6M", "DGS1": "1Y",
        "DGS2": "2Y", "DGS5": "5Y", "DGS10": "10Y", "DGS20": "20Y",
        "DGS30": "30Y"
    }
    vals, labels = [], []
    for sid, lbl in maturities.items():
        try:
            s = fetch_fred_series(sid, start="2020-01-01")
            vals.append(round(s.iloc[-1], 3))
            labels.append(lbl)
        except Exception:
            pass
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=vals, mode="lines+markers",
        line=dict(color="#1f77b4", width=2.5), marker=dict(size=8),
        showlegend=False))
    fig.update_layout(
        title=chart_title("Current Yield Curve",
                          "Spot rates 1M–30Y as of latest FRED data"),
        template="plotly_white", height=380,
        yaxis_title="Yield (%)", xaxis_title="Maturity",
        margin=dict(b=70, t=60, l=60, r=40),
        dragmode=False, annotations=[src_ann(-0.18)])
    return fig

def safe_fmt(val):
    """Format numeric values to 2dp, pass strings through unchanged."""
    try:
        return f"{float(val):.2f}"
    except (ValueError, TypeError):
        return str(val)

def snap_color(row):
    styles = [""] * len(row)
    try:
        cols = list(row.index)
        l, p = float(row["Latest"]), float(row["Previous"])
        idx = cols.index("Latest")
        styles[idx] = ("color:#2ca02c;font-weight:bold" if l > p
                       else "color:#d62728;font-weight:bold" if l < p else "")
    except (ValueError, TypeError):
        pass
    return styles

# ─── PAGE HEADER ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:baseline">
    <h1 style="margin:0">Macro Dashboard</h1>
    <span style="color:#888;font-size:0.85rem">
        Refreshed: {datetime.now().strftime('%b %d, %Y %H:%M')}
        &nbsp;·&nbsp; Data: FRED · Yahoo Finance
    </span>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Markets", "Rates & Macro", "Calendar"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    ind_col, idx_col = st.columns([2, 3])

    with ind_col:
        st.subheader("Key Indicators")
        row1 = st.columns(3)
        row2 = st.columns(3)
        snapshot = [
            ("DGS2",     "2Y Treasury",   True,  "%"),
            ("DGS10",    "10Y Treasury",  True,  "%"),
            ("DGS30",    "30Y Treasury",  True,  "%"),
            ("FEDFUNDS", "Fed Funds",     False, "%"),
            ("CPIAUCSL", "CPI YoY",       True,  "%"),
            ("T10Y2Y",   "10Y–2Y Spread", True,  "%"),
        ]
        for i, (sid, label, show_delta, unit) in enumerate(snapshot):
            col = row1[i] if i < 3 else row2[i - 3]
            try:
                s = (to_yoy(fetch_fred_series(sid)) if sid == "CPIAUCSL"
                     else fetch_fred_series(sid))
                cur, prev = s.iloc[-1], s.iloc[-2]
                delta = f"{cur - prev:+.2f}{unit} DoD" if show_delta else None
                col.metric(label, f"{cur:.2f}{unit}", delta)
            except Exception:
                col.metric(label, "N/A")

    with idx_col:
        st.subheader("Major Indices")
        idx_period = st.radio(
            "Period", ["1M", "3M", "6M", "YTD", "1Y"],
            horizontal=True, key="idx_period")
        with st.spinner("Loading index data…"):
            prices, volumes = fetch_equity()
            latest = prices.index.max()
            if idx_period == "YTD":
                idx_start = pd.Timestamp(f"{latest.year}-01-01")
            else:
                months = {"1M": 1, "3M": 3, "6M": 6, "1Y": 12}[idx_period]
                idx_start = latest - pd.DateOffset(months=months)
            idx_colors = {
                "SPY": "#1f77b4", "QQQ": "#ff7f0e",
                "IWM": "#2ca02c", "DIA": "#d62728"
            }
            fig_idx = go.Figure()
            for tkr, name in INDICES.items():
                if tkr in prices.columns:
                    s = prices[tkr].dropna()
                    s = s[s.index >= idx_start]
                    if len(s) > 1:
                        indexed = (s / s.iloc[0] - 1) * 100
                        fig_idx.add_trace(go.Scatter(
                            x=indexed.index, y=indexed.values,
                            name=name, mode="lines",
                            line=dict(color=idx_colors.get(tkr, "#999"), width=2.5)))
            fig_idx.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
            fig_idx.update_layout(
                title=chart_title("Index Returns", f"{idx_period} cumulative % return"),
                template="plotly_white", height=340,
                yaxis_title="Return (%)",
                margin=dict(b=80, t=60, l=55, r=40),
                legend=dict(orientation="h", yanchor="top", y=-0.22,
                            x=0.5, xanchor="center"),
                dragmode=False, annotations=[src_ann(-0.28)])
            st.plotly_chart(fig_idx, use_container_width=True,
                            key="fig_idx_overview", config=PCFG)

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(build_yield_curve(), use_container_width=True,
                        key="yc_overview", config=PCFG)
        c = yield_curve_commentary()
        if c:
            st.caption(c)
    with col_r:
        st.subheader("Key Releases & FOMC")
        try:
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(
                    snap[["Release", "Next Release", "Latest", "Unit"]]
                    .style.apply(snap_color, axis=1),
                    hide_index=True, use_container_width=True, height=420)
        except Exception:
            st.info("Release data unavailable.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MARKETS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    with st.spinner("Loading equity data…"):
        prices, volumes = fetch_equity()

    period_opts = {
        "Since 2015": "2015-01-01", "Since 2020": "2020-01-01",
        "Since 2025": "2025-01-01", "Past 12M": None
    }

    # ── DAILY POSITIONING FEED ───────────────────────────────────────────────
    st.subheader("Daily Positioning Feed")
    st.caption(
        "Flow Z = residual dollar-volume change (accumulation/distribution) · "
        "Signed Vol Z = directional participation · "
        "Composite = (Flow Z + Signed Vol Z + Return Z) / 3 · "
        "All 63-day rolling, clipped ±3. Sorted by Flow Z desc.")

    regime_cols = st.columns(4)
    try:
        ri = compute_retail_intensity(volumes)
        ri_val = ri.iloc[-1] if len(ri) > 0 else np.nan
        ri_label = ("🟢 Elevated retail" if ri_val > 1.0
                    else "🔴 Low retail" if ri_val < -1.0
                    else "⚪ Normal")
        regime_cols[0].metric("Retail Intensity", f"{ri_val:+.2f}σ", ri_label)
    except Exception:
        regime_cols[0].metric("Retail Intensity", "N/A")

    try:
        br = compute_breadth(prices)
        br_val = br.iloc[-1] if len(br) > 0 else np.nan
        br_ref = br.iloc[-252] if len(br) > 252 else br.iloc[0]
        br_indexed = br_val / br_ref
        br_label = ("Broad" if br_indexed > 1.005
                    else "Concentrated" if br_indexed < 0.995 else "Neutral")
        regime_cols[1].metric("Breadth (RSP/SPY)", f"{br_indexed:.4f}", br_label)
    except Exception:
        regime_cols[1].metric("Breadth (RSP/SPY)", "N/A")

    try:
        rr_pct, rr_raw = compute_rotation_ratio(prices)
        rr_val = rr_pct.iloc[-1] if len(rr_pct) > 0 else np.nan
        rr_label = ("Sector rotation" if rr_val > 0.75
                    else "Stock dispersion" if rr_val < 0.25
                    else "Balanced")
        regime_cols[2].metric("Rotation Pctile", f"{rr_val:.2f}", rr_label)
    except Exception:
        rr_pct, rr_raw = pd.Series(dtype=float), pd.Series(dtype=float)
        regime_cols[2].metric("Rotation Pctile", "N/A")

    try:
        sec_rets_today = prices[list(SECTORS.keys())].pct_change().iloc[-1]
        disp_today = sec_rets_today.std() * 100
        regime_cols[3].metric("Sector Dispersion", f"{disp_today:.2f}%",
                              "Cross-sectional σ today")
    except Exception:
        regime_cols[3].metric("Sector Dispersion", "N/A")

    pos_period = st.radio(
        "Index period", ["1M", "3M", "6M", "YTD"],
        horizontal=True, key="pos_period")
    pos_latest = prices.index.max()
    if pos_period == "YTD":
        pos_start = f"{pos_latest.year}-01-01"
    else:
        m = {"1M": 1, "3M": 3, "6M": 6}[pos_period]
        pos_start = (pos_latest - pd.DateOffset(months=m)).strftime("%Y-%m-%d")

    ptab_sec, ptab_fac = st.columns(2)
    with ptab_sec:
        st.markdown("**Sectors**")
        df_sec = build_positioning_table(prices, volumes, SECTORS, pos_start)
        if not df_sec.empty:
            st.dataframe(style_positioning_table(df_sec),
                         hide_index=True, use_container_width=True, height=400)
    with ptab_fac:
        st.markdown("**Factors**")
        df_fac = build_positioning_table(prices, volumes, FACTORS, pos_start)
        if not df_fac.empty:
            st.dataframe(style_positioning_table(df_fac),
                         hide_index=True, use_container_width=True, height=400)

    # ── REGIME CHARTS ────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Regime Monitor")

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        try:
            if len(rr_pct) > 0:
                rr_t = rr_pct[rr_pct.index >= rr_pct.index.max() - pd.DateOffset(months=12)]
                fig_rr = go.Figure()
                fig_rr.add_trace(go.Scatter(
                    x=rr_t.index, y=rr_t.values, mode="lines",
                    line=dict(color="#1f77b4", width=2), showlegend=False))
                fig_rr.add_hline(y=0.5, line_dash="dash", line_color="gray")
                fig_rr.add_hrect(y0=0.25, y1=0.75, fillcolor="gray",
                                 opacity=0.08, line_width=0)
                fig_rr.update_layout(
                    title=dict(text=(
                        "<b>Rotation Ratio (Percentile)</b><br>"
                        "<span style='font-size:11px;color:#666'>"
                        ">0.75 sector-driven · <0.25 stock-dispersion · "
                        "252d trailing pctile</span>"),
                        font=dict(size=13)),
                    template="plotly_white", height=320,
                    yaxis_title="Percentile", yaxis=dict(range=[0, 1]),
                    margin=dict(b=60, t=70, l=50, r=30),
                    dragmode=False, annotations=[src_ann(-0.18)])
                st.plotly_chart(fig_rr, use_container_width=True,
                                key="fig_rotation", config=PCFG)
        except Exception:
            st.info("Rotation ratio unavailable.")

    with rc2:
        try:
            br = compute_breadth(prices)
            br_t = br[br.index >= br.index.max() - pd.DateOffset(months=12)]
            br_idx = br_t / br_t.iloc[0]
            fig_br = go.Figure()
            fig_br.add_trace(go.Scatter(
                x=br_idx.index, y=br_idx.values, mode="lines",
                line=dict(color="#ff7f0e", width=2), showlegend=False))
            fig_br.add_hline(y=1.0, line_dash="dash", line_color="gray")
            fig_br.update_layout(
                title=dict(text=(
                    "<b>Breadth (RSP / SPY)</b><br>"
                    "<span style='font-size:11px;color:#666'>"
                    "Indexed · rising = broadening · "
                    "falling = concentrated</span>"),
                    font=dict(size=13)),
                template="plotly_white", height=320, yaxis_title="Indexed",
                margin=dict(b=60, t=70, l=50, r=30),
                dragmode=False, annotations=[src_ann(-0.18)])
            st.plotly_chart(fig_br, use_container_width=True,
                            key="fig_breadth", config=PCFG)
        except Exception:
            st.info("Breadth data unavailable.")

    with rc3:
        try:
            ri = compute_retail_intensity(volumes)
            ri_t = ri[ri.index >= ri.index.max() - pd.DateOffset(months=12)]
            fig_ri = go.Figure()
            fig_ri.add_trace(go.Scatter(
                x=ri_t.index, y=ri_t.values, mode="lines",
                line=dict(color="#9467bd", width=2), showlegend=False))
            fig_ri.add_hline(y=0, line_dash="dash", line_color="gray")
            fig_ri.add_hrect(y0=-1, y1=1, fillcolor="gray",
                             opacity=0.08, line_width=0)
            fig_ri.update_layout(
                title=dict(text=(
                    "<b>Retail Intensity</b><br>"
                    "<span style='font-size:11px;color:#666'>"
                    "(TQQQ+SQQQ)/QQQ vol z-score · "
                    ">+1 elevated · <−1 low</span>"),
                    font=dict(size=13)),
                template="plotly_white", height=320, yaxis_title="Z-Score",
                margin=dict(b=60, t=70, l=50, r=30),
                dragmode=False, annotations=[src_ann(-0.18)])
            st.plotly_chart(fig_ri, use_container_width=True,
                            key="fig_retail", config=PCFG)
        except Exception:
            st.info("Retail intensity data unavailable.")

    # ── RELATIVE PERFORMANCE ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Relative Performance")

    pf = st.radio("Period", list(period_opts.keys()), horizontal=True, key="pf")
    base = (period_opts[pf] or
            (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d"))
    rel_f, alpha_f = compute_relative(prices, FACTORS)
    ri_f = reindex_from(rel_f, base)
    al_f = alpha_f[alpha_f.index >= pd.Timestamp(base)]

    fig_f1 = go.Figure()
    for tkr, name in FACTORS.items():
        if tkr in ri_f.columns:
            fig_f1.add_trace(go.Scatter(x=ri_f.index, y=ri_f[tkr], name=name, mode="lines"))
    fig_f1.add_hline(y=1.0, line_dash="dash", line_color="gray")
    fig_f1.update_layout(
        title=chart_title("MSCI Factor Relative Performance",
                          "ETF ÷ SPY, indexed to 1.0 · above = outperforming"),
        template="plotly_white", height=420,
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()])
    st.plotly_chart(fig_f1, use_container_width=True, key="fig_f1", config=PCFG)

    fig_f2 = go.Figure()
    for tkr, name in FACTORS.items():
        if tkr in al_f.columns:
            fig_f2.add_trace(go.Scatter(x=al_f.index, y=al_f[tkr], name=name, mode="lines"))
    fig_f2.add_hline(y=0.0, line_dash="dash", line_color="gray")
    fig_f2.update_layout(
        title=chart_title("MSCI Factor Rolling 6-Month Alpha",
                          "Compounded 126-day return of relative series"),
        template="plotly_white", height=420,
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()])
    st.plotly_chart(fig_f2, use_container_width=True, key="fig_f2", config=PCFG)

    st.divider()

    ps = st.radio("Period", list(period_opts.keys()), horizontal=True, key="ps")
    base_s = (period_opts[ps] or
              (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d"))
    rel_s, alpha_s = compute_relative(prices, SECTORS)
    ri_s = reindex_from(rel_s, base_s)
    al_s = alpha_s[alpha_s.index >= pd.Timestamp(base_s)]
    disp = ri_s.max(axis=1) - ri_s.min(axis=1)
    sec_rets = prices[list(SECTORS.keys())].pct_change().dropna()
    sec_rets_t = sec_rets[sec_rets.index >= pd.Timestamp(base_s)]
    roll_corr = (
        sec_rets_t.rolling(21).corr()
        .groupby(level=0)
        .apply(lambda x: float(np.nanmean(
            x.values[np.triu_indices_from(x.values, k=1)]))))

    fig_s1 = go.Figure()
    for tkr, name in SECTORS.items():
        if tkr in ri_s.columns:
            fig_s1.add_trace(go.Scatter(x=ri_s.index, y=ri_s[tkr], name=name, mode="lines"))
    fig_s1.add_hline(y=1.0, line_dash="dash", line_color="gray")
    fig_s1.update_layout(
        title=chart_title("Sector ETF Relative Performance",
                          "ETF ÷ SPY, indexed to 1.0 · above = outperforming"),
        template="plotly_white", height=420,
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()])
    st.plotly_chart(fig_s1, use_container_width=True, key="fig_s1", config=PCFG)

    fig_s2 = go.Figure()
    for tkr, name in SECTORS.items():
        if tkr in al_s.columns:
            fig_s2.add_trace(go.Scatter(x=al_s.index, y=al_s[tkr], name=name, mode="lines"))
    fig_s2.add_hline(y=0.0, line_dash="dash", line_color="gray")
    fig_s2.update_layout(
        title=chart_title("Sector ETF Rolling 6-Month Alpha",
                          "Compounded 126-day return of relative series"),
        template="plotly_white", height=420,
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()])
    st.plotly_chart(fig_s2, use_container_width=True, key="fig_s2", config=PCFG)

    disp_corr_l, disp_corr_r = st.columns(2)
    with disp_corr_l:
        fig_s3 = go.Figure()
        fig_s3.add_trace(go.Scatter(x=disp.index, y=disp, mode="lines",
                                    line=dict(color="#555", width=2), showlegend=False))
        fig_s3.update_layout(
            title=chart_title("Cross-Sectional Dispersion",
                              "max − min of relative prices"),
            template="plotly_white", height=340,
            margin=dict(b=60, t=60, l=60, r=40),
            dragmode=False, annotations=[src_ann(-0.18)])
        st.plotly_chart(fig_s3, use_container_width=True, key="fig_s3", config=PCFG)

    with disp_corr_r:
        fig_s4 = go.Figure()
        fig_s4.add_trace(go.Scatter(x=roll_corr.index, y=roll_corr.values, mode="lines",
                                    line=dict(color="#e377c2", width=2), showlegend=False))
        fig_s4.update_layout(
            title=chart_title("Avg Pairwise Sector Correlation (21d)",
                              "Higher = macro-driven · lower = sector-specific"),
            template="plotly_white", height=340,
            margin=dict(b=60, t=60, l=60, r=40),
            dragmode=False, annotations=[src_ann(-0.18)])
        st.plotly_chart(fig_s4, use_container_width=True, key="fig_s4", config=PCFG)

    # ── VOLUME Z-SCORE CHARTS ────────────────────────────────────────────────
    st.divider()
    st.subheader("Volume Z-Score & Price (Past 3 Months)")
    st.caption("Price indexed to 1.0 · Vol z-score (63d) bars clipped ±3 · "
               "green = above avg · red = below avg")

    st.markdown("#### Factor ETFs")
    f_cols = st.columns(3)
    for i, (tkr, name) in enumerate(FACTORS.items()):
        fig = build_volume_chart(tkr, name, prices, volumes)
        if fig:
            with f_cols[i % 3]:
                st.plotly_chart(fig, use_container_width=True,
                                key=f"vol_{tkr}", config=PCFG)

    st.markdown("#### Sector ETFs")
    s_cols = st.columns(3)
    for i, (tkr, name) in enumerate(SECTORS.items()):
        fig = build_volume_chart(tkr, name, prices, volumes)
        if fig:
            with s_cols[i % 3]:
                st.plotly_chart(fig, use_container_width=True,
                                key=f"vol_{tkr}", config=PCFG)

    # ── ETF HOLDINGS DRILL-DOWN ──────────────────────────────────────────────
    st.divider()
    st.subheader("Sector ETF Holdings & Daily Attribution")
    st.caption(
        "Expand any sector to see top holdings, weight, daily return, "
        "and contribution (weight × return). Sorted by |contribution|. "
        "Weights sourced live from yfinance when available, otherwise static fallback.")

    exp_cols = st.columns(2)
    for i, (tkr, name) in enumerate(SECTORS.items()):
        with exp_cols[i % 2]:
            with st.expander(f"**{name}** ({tkr})"):
                try:
                    df_attr, etf_ret, is_live = build_holdings_attribution(tkr, prices)
                    src_tag = "🟢 live" if is_live else "⚪ static"
                    if not df_attr.empty:
                        explained = df_attr["Contribution"].sum()
                        if etf_ret and abs(etf_ret) > 0.001:
                            st.caption(
                                f"ETF 1D: **{etf_ret:+.2f}%** · "
                                f"Top holdings explain: **{explained:+.3f}%** "
                                f"({explained/etf_ret*100:.0f}%) · {src_tag}")
                        else:
                            st.caption(f"ETF 1D: **{etf_ret:+.2f}%** · {src_tag}")
                        st.dataframe(
                            style_attribution_table(df_attr),
                            hide_index=True, use_container_width=True,
                            height=min(35 * len(df_attr) + 38, 340))
                    else:
                        st.info("Holdings data unavailable.")
                except Exception:
                    st.info("Holdings data unavailable.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RATES & MACRO
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    rp = st.radio("Period", ["1Y", "3Y", "5Y", "10Y", "Full"],
                  horizontal=True, key="rp")
    rmons = {"1Y": 12, "3Y": 36, "5Y": 60, "10Y": 120, "Full": None}[rp]

    # ── Row 1: Yields + Yield Curve ──
    yld_col, yc_col = st.columns([3, 2])
    with yld_col:
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
        fig_y = go.Figure()
        for i, (sid, lbl) in enumerate(YIELDS.items()):
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_y.add_trace(go.Scatter(
                    x=s.index, y=s.values, name=lbl, mode="lines",
                    line=dict(color=colors[i], width=2)))
            except Exception:
                pass
        fig_y.update_layout(
            title=chart_title("Treasury Yields", "Constant-maturity daily"),
            template="plotly_white", height=380, yaxis_title="Yield (%)",
            margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
            dragmode=False, annotations=[src_ann(-0.22)])
        st.plotly_chart(fig_y, use_container_width=True, key="fig_yields", config=PCFG)

    with yc_col:
        st.plotly_chart(build_yield_curve(), use_container_width=True,
                        key="yc_rates", config=PCFG)
        c = yield_curve_commentary()
        if c:
            st.caption(c)

    # ── Row 2: Spreads + Real Yield/Breakeven + Credit ──
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        fig_sp = go.Figure()
        for sid, lbl in SPREADS.items():
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_sp.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_sp.add_hline(y=0, line_dash="dash", line_color="red", line_width=1)
        fig_sp.update_layout(
            title=chart_title("Curve Spreads", "Below 0 = inverted"),
            template="plotly_white", height=340, yaxis_title="Spread (%)",
            margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
            dragmode=False, annotations=[src_ann(-0.22)])
        st.plotly_chart(fig_sp, use_container_width=True, key="fig_spreads", config=PCFG)

    with r2c2:
        fig_rv = go.Figure()
        for sid, lbl in [("DFII10", "10Y Real Yield"), ("T10YIE", "10Y Breakeven")]:
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_rv.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_rv.update_layout(
            title=chart_title("Real Yield & Breakeven", "TIPS + implied inflation"),
            template="plotly_white", height=340, yaxis_title="%",
            margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
            dragmode=False, annotations=[src_ann(-0.22)])
        st.plotly_chart(fig_rv, use_container_width=True, key="fig_realyield", config=PCFG)

    with r2c3:
        fig_cr = go.Figure()
        for sid, lbl in CREDIT.items():
            try:
                s = trim(fetch_fred_series(sid), rmons) * 100
                fig_cr.add_trace(go.Scatter(
                    x=s.index, y=s.values, name=f"{lbl}", mode="lines"))
            except Exception:
                pass
        try:
            hy = trim(fetch_fred_series("BAMLH0A0HYM2"), rmons)
            ig = trim(fetch_fred_series("BAMLC0A0CM"), rmons)
            gap = (hy - ig).dropna() * 100
            fig_cr.add_trace(go.Scatter(
                x=gap.index, y=gap.values, name="HY–IG Gap",
                mode="lines", line=dict(dash="dot", width=1.5)))
        except Exception:
            pass
        fig_cr.update_layout(
            title=chart_title("Credit Spreads (OAS)", "Wider = risk-off"),
            template="plotly_white", height=340, yaxis_title="bps",
            margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
            dragmode=False, annotations=[src_ann(-0.22)])
        st.plotly_chart(fig_cr, use_container_width=True, key="fig_credit", config=PCFG)

    st.divider()

    # ── Row 3: Inflation ──
    inf_l, inf_r = st.columns(2)
    with inf_l:
        fig_cpi = go.Figure()
        for sid, lbl in [("CPIAUCSL", "CPI"), ("CPILFESL", "Core CPI")]:
            try:
                s = trim(to_yoy(fetch_fred_series(sid)), rmons)
                fig_cpi.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_cpi.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="2%", annotation_position="bottom right")
        fig_cpi.update_layout(
            title=chart_title("CPI & Core CPI", "YoY %"),
            template="plotly_white", height=360, yaxis_title="YoY %",
            margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
            dragmode=False, annotations=[src_ann(-0.22)])
        st.plotly_chart(fig_cpi, use_container_width=True, key="fig_cpi", config=PCFG)

    with inf_r:
        fig_pce = go.Figure()
        for sid, lbl in [("PCEPI", "PCE"), ("PCEPILFE", "Core PCE")]:
            try:
                s = trim(to_yoy(fetch_fred_series(sid)), rmons)
                fig_pce.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_pce.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="2%", annotation_position="bottom right")
        fig_pce.update_layout(
            title=chart_title("PCE & Core PCE", "YoY % · Fed's preferred gauge"),
            template="plotly_white", height=360, yaxis_title="YoY %",
            margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
            dragmode=False, annotations=[src_ann(-0.22)])
        st.plotly_chart(fig_pce, use_container_width=True, key="fig_pce", config=PCFG)

    # ── Row 4: Employment + GDP ──
    emp_col, gdp_col = st.columns(2)
    with emp_col:
        fig_ff = go.Figure()
        for sid, lbl, clr in [("FEDFUNDS", "Fed Funds", "#1f77b4"),
                              ("UNRATE", "Unemployment", "#ff7f0e")]:
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_ff.add_trace(go.Scatter(
                    x=s.index, y=s.values, name=lbl, mode="lines",
                    line=dict(color=clr, width=2)))
            except Exception:
                pass
        fig_ff.update_layout(
            title=chart_title("Fed Funds & Unemployment", "Dual mandate"),
            template="plotly_white", height=360, yaxis_title="%",
            margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
            dragmode=False, annotations=[src_ann(-0.22)])
        st.plotly_chart(fig_ff, use_container_width=True, key="fig_fedfunds", config=PCFG)

    with gdp_col:
        try:
            gdp = trim(fetch_fred_series("A191RL1Q225SBEA"), rmons)
            fig_gdp = go.Figure()
            fig_gdp.add_trace(go.Bar(
                x=gdp.index, y=gdp.values, name="GDP Growth",
                marker_color=["#2ca02c" if v >= 0 else "#d62728" for v in gdp.values]))
            fig_gdp.add_hline(y=0, line_color="black", line_width=1)
            fig_gdp.update_layout(
                title=chart_title("Real GDP Growth", "QoQ annualized %"),
                template="plotly_white", height=360, yaxis_title="% QoQ Ann.",
                margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
                dragmode=False, annotations=[src_ann(-0.22)])
            st.plotly_chart(fig_gdp, use_container_width=True, key="fig_gdp", config=PCFG)
        except Exception:
            st.info("GDP data unavailable.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.subheader("Upcoming Releases")
        st.caption("Next 45 days and past 35 days — all via FRED")
        with st.spinner("Loading…"):
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(
                    snap.style.apply(snap_color, axis=1)
                        .format({"Previous": safe_fmt, "Latest": safe_fmt}, na_rep="—"),
                    hide_index=True, use_container_width=True, height=420)

        st.divider()
        st.subheader("Release Calendar")
        st.caption("All FRED releases — past 35 days and next 45 days "
                   "· yellow = today · gray = past")
        with st.spinner("Loading calendar…"):
            cal = fetch_fred_calendar()
            if cal.empty:
                st.info("No calendar data available.")
            else:
                today_ts = pd.Timestamp.today().normalize()
                def cal_style(row):
                    d = pd.Timestamp(row["Date"])
                    if d.normalize() == today_ts:
                        return ["background-color:#fff3cd;font-weight:bold"] * len(row)
                    if d < today_ts:
                        return ["color:#aaaaaa"] * len(row)
                    return [""] * len(row)
                disp_cal = cal.copy()
                disp_cal["Date"] = disp_cal["Date"].dt.strftime("%b %d, %Y")
                st.dataframe(
                    disp_cal.style.apply(cal_style, axis=1),
                    hide_index=True, use_container_width=True, height=520)

    with col_right:
        st.subheader("FOMC Dates")
        today_d = datetime.today().date()
        for year, meetings in FOMC.items():
            st.caption(f"**{year}**")
            for lbl, d in meetings:
                mtg_d = datetime.strptime(d, "%Y-%m-%d").date()
                days = (mtg_d - today_d).days
                if days > 0:
                    st.markdown(f"🔵 **{lbl}** — *{days}d*")
                elif days == 0:
                    st.markdown(f"🟡 **{lbl}** — *today*")
                else:
                    st.markdown(f"✅ ~~{lbl}~~")
        st.divider()
        st.caption("**Current Fed Funds Rate**")
        try:
            ff = fetch_fred_series("FEDFUNDS")
            st.metric("Fed Funds", f"{ff.iloc[-1]:.2f}%")
        except Exception:
            st.metric("Fed Funds", "N/A")
