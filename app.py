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

DISCLAIMER = (
    "*Disclaimer: This dashboard is for educational and informational purposes only. "
    "Nothing contained herein constitutes investment advice, a recommendation, or a solicitation "
    "to buy or sell any securities or financial instruments. The data presented may be delayed, "
    "incomplete, or inaccurate, and should not be relied upon for trading or investment decisions. "
    "Past performance is not indicative of future results. The authors and contributors assume no "
    "liability for any losses or damages arising from the use of this information. "
    "Consult a qualified financial advisor before making any investment decisions.*"
)

SOURCE_HTML = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED · Yahoo Finance</p>'
SOURCE_FRED = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED</p>'
SOURCE_YF = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: Yahoo Finance</p>'

ZSCORE_LOOKBACK = 252
CHART_WINDOW = 63

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
# Actual index tickers for the overview chart (show real index prices on hover)
INDICES_CHART = {
    "^GSPC": "S&P 500", "^IXIC": "Nasdaq",
    "^RUT": "Russell 2000", "^DJI": "Dow 30"
}
EW_SECTORS = {
    "XLK": "RYT", "XLF": "RYF", "XLE": "RYE", "XLV": "RYH",
    "XLI": "RGI", "XLY": "RCD", "XLP": "RHS", "XLB": "RTM",
    "XLU": "RYU", "XLRE": "EWRE"
}
RETAIL_ETFS = ["TQQQ", "SQQQ"]

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

def get_holdings(etf_ticker):
    """Return hardcoded holdings."""
    return HOLDINGS.get(etf_ticker, []), False

SECTORS_CYCLICAL = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLI": "Industrials", "XLY": "Cons. Disc.", "XLB": "Materials"
}
SECTORS_DEFENSIVE = {
    "XLV": "Healthcare", "XLP": "Cons. Staples",
    "XLU": "Utilities", "XLRE": "Real Estate"
}

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
        ("Jan 28–29", "2025-01-29", "Hold (4.25–4.50%)"),
        ("Mar 18–19", "2025-03-19", "Hold (4.25–4.50%)"),
        ("May 6–7",   "2025-05-07", "Hold (4.25–4.50%)"),
        ("Jun 17–18", "2025-06-18", "Hold (4.25–4.50%)"),
        ("Jul 29–30", "2025-07-30", "Hold (4.25–4.50%)"),
        ("Sep 16–17", "2025-09-17", "Cut −25bp (4.00–4.25%)"),
        ("Oct 28–29", "2025-10-29", "Cut −25bp (3.75–4.00%)"),
        ("Dec 9–10",  "2025-12-10", "Cut −25bp (3.50–3.75%)"),
    ],
    "2026": [
        ("Jan 27–28", "2026-01-28", "Hold (3.50–3.75%)"),
        ("Mar 17–18", "2026-03-18", ""),
        ("Apr 28–29", "2026-04-29", ""),
        ("Jun 9–10",  "2026-06-10", ""),
        ("Jul 28–29", "2026-07-29", ""),
        ("Sep 15–16", "2026-09-16", ""),
        ("Oct 27–28", "2026-10-28", ""),
        ("Dec 8–9",   "2026-12-09", ""),
    ]
}

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
               + list(INDICES.keys()) + list(INDICES_CHART.keys())
               + list(EW_SECTORS.values())
               + RETAIL_ETFS + holding_tickers
               + [BENCH, "RSP"])
    tickers = list(set(tickers))
    try:
        raw = yf.download(tickers, start=START, auto_adjust=True,
                          progress=False, threads=True)
        close = raw["Close"]
        volume = raw["Volume"]
    except Exception:
        core = (list(FACTORS.keys()) + list(SECTORS.keys())
                + list(INDICES.keys()) + list(EW_SECTORS.values())
                + RETAIL_ETFS + [BENCH, "RSP"])
        core = list(set(core))
        raw = yf.download(core, start=START, auto_adjust=True,
                          progress=False, threads=True)
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
        text="Source: FRED · Yahoo Finance",
        xref="paper", yref="paper", x=1.0, y=y,
        showarrow=False, font=dict(size=10, color="#888888"), xanchor="right")

def chart_title(main, sub):
    return f"{main} {sub}"

def safe_fmt(val):
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

# ─── VOLUME & POSITIONING HELPERS ────────────────────────────────────────────

def compute_volume_zscore(vol_series, lookback=ZSCORE_LOOKBACK):
    rm = vol_series.rolling(lookback, min_periods=60).mean()
    rs = vol_series.rolling(lookback, min_periods=60).std()
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
    rm = flow.rolling(lookback, min_periods=60).mean()
    rs = flow.rolling(lookback, min_periods=60).std()
    return ((flow - rm) / rs).clip(-3, 3)

def compute_signed_volume_z(prices, volumes, ticker, lookback=ZSCORE_LOOKBACK):
    if ticker not in prices.columns or ticker not in volumes.columns:
        return pd.Series(dtype=float)
    p = prices[ticker].dropna()
    v = volumes[ticker].dropna()
    common = p.index.intersection(v.index)
    p, v = p.loc[common], v.loc[common]
    sv = v * np.sign(p.pct_change())
    rm = sv.rolling(lookback, min_periods=60).mean()
    rs = sv.rolling(lookback, min_periods=60).std()
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
    rm = ratio.rolling(lookback, min_periods=60).mean()
    rs = ratio.rolling(lookback, min_periods=60).std()
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
        df["_abs_contrib"] = df["Contribution"].abs()
        df = df.sort_values("_abs_contrib", ascending=False).drop(columns=["_abs_contrib"]).reset_index(drop=True)
    return df, etf_ret, is_live

def build_positioning_table(prices, volumes, asset_dict, ret_days):
    rows = []
    for tkr, name in asset_dict.items():
        try:
            p = prices[tkr].dropna()
            if len(p) < 2:
                continue
            if ret_days == 1:
                ret = p.pct_change().iloc[-1] * 100
            elif len(p) > ret_days:
                ret = ((p.iloc[-1] / p.iloc[-ret_days]) - 1) * 100
            else:
                ret = np.nan
            fz = compute_flow_proxy_z(prices, volumes, tkr)
            flow_z = round(fz.iloc[-1], 2) if len(fz) > 0 else np.nan
            svz = compute_signed_volume_z(prices, volumes, tkr)
            svol_z = round(svz.iloc[-1], 2) if len(svz) > 0 else np.nan
            ret_series = p.pct_change()
            ret_rm = ret_series.rolling(ZSCORE_LOOKBACK, min_periods=60).mean()
            ret_rs = ret_series.rolling(ZSCORE_LOOKBACK, min_periods=60).std()
            ret_z_val = float(np.clip(
                (ret_series.iloc[-1] - ret_rm.iloc[-1]) / ret_rs.iloc[-1], -3, 3))
            components = [v for v in [flow_z, svol_z, ret_z_val] if not np.isnan(v)]
            composite = round(np.mean(components), 2) if components else np.nan
            rows.append({
                "Ticker": tkr, "Name": name,
                "Return %": round(ret, 2) if not np.isnan(ret) else np.nan,
                "Flow Z": flow_z, "Signed Vol Z": svol_z, "Composite": composite
            })
        except Exception:
            continue
    df = pd.DataFrame(rows)
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
    for c in ["Return %"]:
        if c in df.columns:
            styler = styler.map(_color_ret, subset=[c])
    fmt = {}
    for c in ["Return %", "Flow Z", "Signed Vol Z", "Composite"]:
        if c in df.columns:
            fmt[c] = "{:+.2f}"
    styler = styler.format(fmt, na_rep="—")
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

tab1, tab2, tab3 = st.tabs(
    ["Equities", "Fixed Income & Macro", "Calendar"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MARKETS
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    with st.spinner("Loading equity data…"):
        prices, volumes = fetch_equity()

    # ── Header: Indices + Top/Bottom positioning ────────────────────────────
    hdr_l, hdr_r = st.columns([3, 2])

    with hdr_l:
        idx_period = st.radio(
            "Period", ["1M", "3M", "6M", "YTD", "1Y"],
            horizontal=True, key="idx_period")
        latest = prices.index.max()
        if idx_period == "YTD":
            idx_start = pd.Timestamp(f"{latest.year}-01-01")
        else:
            months = {"1M": 1, "3M": 3, "6M": 6, "1Y": 12}[idx_period]
            idx_start = latest - pd.DateOffset(months=months)
        idx_colors = {
            "^GSPC": "#1f77b4", "^IXIC": "#ff7f0e",
            "^RUT": "#2ca02c", "^DJI": "#d62728"
        }
        fig_idx = go.Figure()
        for tkr, name in INDICES_CHART.items():
            if tkr in prices.columns:
                s = prices[tkr].dropna()
                s = s[s.index >= idx_start]
                if len(s) > 1:
                    indexed = (s / s.iloc[0] - 1) * 100
                    fig_idx.add_trace(go.Scatter(
                        x=indexed.index, y=indexed.values,
                        name=name, mode="lines",
                        line=dict(color=idx_colors.get(tkr, "#999"), width=2.5),
                        customdata=s.values,
                        hovertemplate=(
                            f"<b>{name}</b><br>"
                            "Date: %{x|%b %d, %Y}<br>"
                            "Return: %{y:+.2f}%<br>"
                            "Level: %{customdata:,.2f}"
                            "<extra></extra>"
                        )))
        fig_idx.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig_idx.update_layout(
            title=chart_title("U.S. Major Indices", f"{idx_period} cumulative return"),
            template="plotly_white", height=340,
            yaxis_title="Return (%)",
            margin=dict(b=80, t=60, l=55, r=40),
            legend=dict(orientation="h", yanchor="top", y=-0.22,
                        x=0.5, xanchor="center"),
            dragmode=False, annotations=[src_ann(-0.28)])
        st.plotly_chart(fig_idx, use_container_width=True,
                        key="fig_idx_overview", config=PCFG)

    with hdr_r:
        pos_freq = st.radio(
            "Return period", ["1D", "5D", "1M", "12M"],
            horizontal=True, key="pos_freq")
        ret_days = {"1D": 1, "5D": 5, "1M": 21, "12M": 252}[pos_freq]
        df_sec = build_positioning_table(prices, volumes, SECTORS, ret_days)

        if not df_sec.empty and "Composite" in df_sec.columns:
            df_ranked = df_sec.dropna(subset=["Composite"]).sort_values(
                "Composite", ascending=False).reset_index(drop=True)
            top3 = df_ranked.head(3)
            bot3 = df_ranked.tail(3)
            df_display = pd.concat([top3, bot3], ignore_index=True)
            df_display = df_display.rename(columns={"Return %": f"{pos_freq} Ret %"})
            st.markdown(f"**Top 3 / Bottom 3 by Composite** — {pos_freq} return")
            def _style_topbot(df_d):
                def _cz(val):
                    if pd.isna(val): return ""
                    if val >= 2:  return "color:#2ca02c;font-weight:bold"
                    if val <= -2: return "color:#d62728;font-weight:bold"
                    if val >= 1:  return "color:#2ca02c"
                    if val <= -1: return "color:#d62728"
                    return ""
                def _cr(val):
                    if pd.isna(val): return ""
                    return "color:#2ca02c" if val > 0 else "color:#d62728" if val < 0 else ""
                s = df_d.style
                for c in ["Flow Z", "Signed Vol Z", "Composite"]:
                    if c in df_d.columns:
                        s = s.map(_cz, subset=[c])
                ret_col = f"{pos_freq} Ret %"
                if ret_col in df_d.columns:
                    s = s.map(_cr, subset=[ret_col])
                fmt = {}
                for c in [ret_col, "Flow Z", "Signed Vol Z", "Composite"]:
                    if c in df_d.columns:
                        fmt[c] = "{:+.2f}"
                s = s.format(fmt, na_rep="—")
                return s
            st.dataframe(_style_topbot(df_display),
                         hide_index=True, use_container_width=True, height=248)
            st.markdown(SOURCE_HTML, unsafe_allow_html=True)

    st.divider()

    period_opts = {
        "Past 12M": None, "Since 2015": "2015-01-01",
        "Since 2020": "2020-01-01", "Since 2025": "2025-01-01"
    }

    # ── DAILY POSITIONING FEED ───────────────────────────────────────────────
    st.subheader("Daily Positioning Feed")
    st.caption(
        "Flow Z = residual dollar-volume change (accumulation/distribution) · "
        "Signed Vol Z = directional participation · "
        "Composite = (Flow Z + Signed Vol Z + Return Z) / 3 · "
        "All 252-day rolling, clipped ±3.")

    # ── Regime charts ──
    rc1, rc2, rc3, rc4 = st.columns(4)

    with rc1:
        try:
            rr_pct, rr_raw = compute_rotation_ratio(prices)
            if len(rr_pct) > 0:
                rr_val = rr_pct.iloc[-1]
                rr_label = ("Sector rotation" if rr_val > 0.75
                            else "Stock dispersion" if rr_val < 0.25
                            else "Balanced")
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
                        f"<b>Macro vs Micro</b> — {rr_val:.2f} ({rr_label})<br>"
                        f"<span style='font-size:11px;color:#666'>"
                        f">0.75 sector-driven · <0.25 stock-driven</span>"),
                        font=dict(size=12)),
                    template="plotly_white", height=280,
                    yaxis_title="%-tile", yaxis=dict(range=[0, 1], dtick=0.25),
                    margin=dict(b=45, t=65, l=45, r=25),
                    dragmode=False, annotations=[src_ann(-0.12)])
                st.plotly_chart(fig_rr, use_container_width=True,
                                key="fig_rotation", config=PCFG)
            else:
                st.info("Rotation ratio unavailable.")
        except Exception:
            rr_pct, rr_raw = pd.Series(dtype=float), pd.Series(dtype=float)
            st.info("Rotation ratio unavailable.")

    with rc2:
        try:
            br = compute_breadth(prices)
            if len(br) > 0:
                br_t = br[br.index >= br.index.max() - pd.DateOffset(months=12)]
                br_idx = br_t / br_t.iloc[0]
                br_now = br_idx.iloc[-1]
                br_label = ("Broad" if br_now > 1.005
                            else "Concentrated" if br_now < 0.995 else "Neutral")
                fig_br = go.Figure()
                fig_br.add_trace(go.Scatter(
                    x=br_idx.index, y=br_idx.values, mode="lines",
                    line=dict(color="#ff7f0e", width=2), showlegend=False))
                fig_br.add_hline(y=1.0, line_dash="dash", line_color="gray")
                fig_br.update_layout(
                    title=dict(text=(
                        f"<b>Breadth</b> — {br_now:.4f} ({br_label})<br>"
                        f"<span style='font-size:11px;color:#666'>"
                        f"RSP/SPY · rising = broadening</span>"),
                        font=dict(size=12)),
                    template="plotly_white", height=280, yaxis_title="Indexed",
                    margin=dict(b=45, t=65, l=45, r=25),
                    dragmode=False, annotations=[src_ann(-0.12)])
                st.plotly_chart(fig_br, use_container_width=True,
                                key="fig_breadth", config=PCFG)
        except Exception:
            st.info("Breadth data unavailable.")

    with rc3:
        try:
            cyc_rets = prices[list(SECTORS_CYCLICAL.keys())].pct_change().mean(axis=1)
            def_rets = prices[list(SECTORS_DEFENSIVE.keys())].pct_change().mean(axis=1)
            cyc_cum = (1 + cyc_rets).cumprod()
            def_cum = (1 + def_rets).cumprod()
            ratio = cyc_cum / def_cum
            ratio_12m = ratio[ratio.index >= ratio.index.max() - pd.DateOffset(months=12)]
            ratio_idx = ratio_12m / ratio_12m.iloc[0]
            cd_now = ratio_idx.iloc[-1]
            cd_label = ("Risk-on" if cd_now > 1.005
                        else "Risk-off" if cd_now < 0.995 else "Neutral")
            fig_cd = go.Figure()
            fig_cd.add_trace(go.Scatter(
                x=ratio_idx.index, y=ratio_idx.values, mode="lines",
                line=dict(color="#2ca02c", width=2), showlegend=False))
            fig_cd.add_hline(y=1.0, line_dash="dash", line_color="gray")
            fig_cd.update_layout(
                title=dict(text=(
                    f"<b>Cyclical / Defensive</b> — {cd_now:.4f} ({cd_label})<br>"
                    f"<span style='font-size:11px;color:#666'>"
                    f"Rising = risk-on · falling = risk-off</span>"),
                    font=dict(size=12)),
                template="plotly_white", height=280, yaxis_title="Ratio",
                margin=dict(b=45, t=65, l=45, r=25),
                dragmode=False)
            st.plotly_chart(fig_cd, use_container_width=True,
                            key="fig_cyc_def_regime", config=PCFG)
        except Exception:
            st.info("Cyclical/Defensive unavailable.")

    with rc4:
        try:
            spy_vol = volumes["SPY"].dropna()
            sv_1y = spy_vol[spy_vol.index >= spy_vol.index.max() - pd.DateOffset(months=12)]
            sv_med = sv_1y.median()
            sv_std = sv_1y.std()
            sv_z_full = ((spy_vol - sv_med) / sv_std).clip(-3, 3)
            cutoff_3m = spy_vol.index.max() - pd.DateOffset(months=3)
            sv_z = sv_z_full[sv_z_full.index >= cutoff_3m]
            sv_z_now = sv_z.iloc[-1]
            bar_colors = ["#2ca02c" if v >= 0 else "#d62728" for v in sv_z.values]
            fig_sv = go.Figure()
            fig_sv.add_trace(go.Bar(
                x=sv_z.index, y=sv_z.values,
                marker_color=bar_colors, opacity=0.7, showlegend=False))
            fig_sv.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
            fig_sv.add_hline(y=2, line_dash="dot", line_color="#2ca02c", line_width=0.8)
            fig_sv.add_hline(y=-2, line_dash="dot", line_color="#d62728", line_width=0.8)
            fig_sv.update_layout(
                title=dict(text=(
                    f"<b>SPY Volume</b> — {sv_z_now:+.2f}σ today<br>"
                    f"<span style='font-size:11px;color:#666'>"
                    f"0 = 1Y median · 3M window · ±3</span>"),
                    font=dict(size=12)),
                template="plotly_white", height=280, yaxis_title="Z-Score",
                yaxis=dict(range=[-3.5, 3.5], dtick=1),
                margin=dict(b=45, t=65, l=45, r=25),
                bargap=0.15, dragmode=False, annotations=[src_ann(-0.12)])
            st.plotly_chart(fig_sv, use_container_width=True,
                            key="fig_spy_vol", config=PCFG)
        except Exception:
            st.info("SPY volume unavailable.")

    # ── RELATIVE PERFORMANCE ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Relative Performance")

    pf = st.radio("Period", list(period_opts.keys()), horizontal=True, key="pf")
    base = (period_opts[pf] or
            (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d"))

    def _build_pair(asset_dict, group_label, base_date, key_suffix):
        """Build relative perf (left) + rolling alpha (right) side by side."""
        rel, alpha = compute_relative(prices, asset_dict)
        ri = reindex_from(rel, base_date)
        al = alpha[alpha.index >= pd.Timestamp(base_date)]

        cl, cr = st.columns(2)
        with cl:
            fig = go.Figure()
            for tkr, name in asset_dict.items():
                if tkr in ri.columns:
                    fig.add_trace(go.Scatter(
                        x=ri.index, y=ri[tkr], name=name, mode="lines"))
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
            fig.update_layout(
                title=chart_title(f"{group_label} Relative Performance",
                                  "ETF ÷ SPY, indexed to 1.0"),
                template="plotly_white", height=380,
                margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
                dragmode=False, annotations=[src_ann(-0.22)])
            st.plotly_chart(fig, use_container_width=True,
                            key=f"rel_{key_suffix}", config=PCFG)
        with cr:
            fig = go.Figure()
            for tkr, name in asset_dict.items():
                if tkr in al.columns:
                    fig.add_trace(go.Scatter(
                        x=al.index, y=al[tkr], name=name, mode="lines"))
            fig.add_hline(y=0.0, line_dash="dash", line_color="gray")
            fig.update_layout(
                title=chart_title(f"{group_label} Rolling 6M Alpha",
                                  "Compounded 126-day relative return"),
                template="plotly_white", height=380,
                margin=dict(b=90, t=50, l=55, r=30), legend=LEG,
                dragmode=False, annotations=[src_ann(-0.22)])
            st.plotly_chart(fig, use_container_width=True,
                            key=f"alpha_{key_suffix}", config=PCFG)

    st.markdown("#### Factors")
    _build_pair(FACTORS, "Factor", base, "factors")

    st.markdown("#### Cyclical-Tilt Sectors")
    _build_pair(SECTORS_CYCLICAL, "Cyclical-Tilt", base, "cyclical")

    st.markdown("#### Defensive-Tilt Sectors")
    _build_pair(SECTORS_DEFENSIVE, "Defensive-Tilt", base, "defensive")

    # ── INDIVIDUAL ETF CHARTS — Flow only ────────────────────────────────────
    st.divider()
    st.subheader("Individual ETF — Flow & Price")
    st.caption("Price return % + flow z-score (252d rolling, clipped ±3)")

    chart_window_opt = st.radio(
        "Chart window", ["3M", "6M", "1Y"],
        horizontal=True, key="etf_chart_window", index=1)
    chart_bdays = {"3M": 63, "6M": 126, "1Y": 252}[chart_window_opt]

    def build_flow_chart(ticker, label, prices, volumes, window):
        if ticker not in prices.columns:
            return None
        p = prices[ticker].dropna()
        cutoff = p.index[-1] - pd.tseries.offsets.BDay(window)
        p = p[p.index >= cutoff]
        if len(p) < 10:
            return None
        p_idx = p / p.iloc[0]
        fz = compute_flow_proxy_z(prices, volumes, ticker)
        fz = fz[fz.index >= cutoff]
        common = p_idx.index.intersection(fz.index)
        p_idx, fz = p_idx.loc[common], fz.loc[common]
        if len(common) < 5:
            return None
        bar_colors = ["#2ca02c" if v >= 0 else "#d62728" for v in fz.values]
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=fz.index, y=fz.values, name="Flow Z",
                   marker_color=bar_colors, opacity=0.35), secondary_y=True)
        fig.add_trace(
            go.Scatter(x=p_idx.index, y=p_idx.values, name=label,
                       mode="lines", line=dict(color="#1f77b4", width=2.5)),
            secondary_y=False)
        fig.add_hline(y=1.0, line_dash="dash", line_color="gray", line_width=0.8,
                      secondary_y=False)
        fig.update_layout(
            title=dict(text=(
                f"<b>{label}</b> ({ticker})<br>"
                f"<span style='font-size:11px;color:#666'>"
                f"Price indexed · Flow z (252d) · green = accumulation</span>"),
                font=dict(size=13)),
            template="plotly_white", height=320,
            margin=dict(b=55, t=65, l=50, r=40),
            legend=dict(orientation="h", yanchor="top", y=-0.18,
                        x=0.5, xanchor="center", font=dict(size=9)),
            dragmode=False, bargap=0.1, annotations=[src_ann(-0.22)])
        fig.update_yaxes(title_text="Indexed", secondary_y=False)
        fig.update_yaxes(title_text="Flow Z", secondary_y=True,
                         range=[-3.5, 3.5], dtick=1, showgrid=False)
        return fig

    st.markdown("#### Sector ETFs")
    sec_flow_cols = st.columns(3)
    for i, (tkr, name) in enumerate(SECTORS.items()):
        fig = build_flow_chart(tkr, name, prices, volumes, chart_bdays)
        if fig:
            with sec_flow_cols[i % 3]:
                st.plotly_chart(fig, use_container_width=True,
                                key=f"flow_{tkr}", config=PCFG)

    st.markdown("#### Factor ETFs")
    fac_flow_cols = st.columns(3)
    for i, (tkr, name) in enumerate(FACTORS.items()):
        fig = build_flow_chart(tkr, name, prices, volumes, chart_bdays)
        if fig:
            with fac_flow_cols[i % 3]:
                st.plotly_chart(fig, use_container_width=True,
                                key=f"flow_{tkr}", config=PCFG)

    # ── ETF HOLDINGS DRILL-DOWN ──────────────────────────────────────────────
    st.divider()
    st.subheader("Sector ETF Holdings & Daily Attribution")
    st.caption(
        "Expand any sector to see top holdings, weight, daily return, "
        "and contribution (weight × return). Sorted by contribution. "
        "Weights are hardcoded and updated biannually — minor drift expected between updates.")

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
    st.markdown(SOURCE_YF, unsafe_allow_html=True)

    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>',
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — FIXED INCOME & MACRO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    # ── Header: Key rate indicators ──
    ri1, ri2, ri3, ri4, ri5, ri6 = st.columns(6)
    rate_snap = [
        (ri1, "DGS2",     "2Y Treasury",   True,  "%"),
        (ri2, "DGS10",    "10Y Treasury",  True,  "%"),
        (ri3, "DGS30",    "30Y Treasury",  True,  "%"),
        (ri4, "FEDFUNDS", "Fed Funds",     False, "%"),
        (ri5, "CPIAUCSL", "CPI YoY",       True,  "%"),
        (ri6, "T10Y2Y",   "10Y–2Y",        True,  "%"),
    ]
    for col, sid, label, show_delta, unit in rate_snap:
        try:
            s = (to_yoy(fetch_fred_series(sid)) if sid == "CPIAUCSL"
                 else fetch_fred_series(sid))
            cur, prev = s.iloc[-1], s.iloc[-2]
            delta = f"{cur - prev:+.2f}{unit}" if show_delta else None
            col.metric(label, f"{cur:.2f}{unit}", delta)
        except Exception:
            col.metric(label, "N/A")

    st.markdown(SOURCE_FRED, unsafe_allow_html=True)
    st.divider()

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

    # ── Row 2: Spreads + Real Yield + Credit ──
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
                    x=s.index, y=s.values, name=lbl, mode="lines"))
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

    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>',
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.subheader("Upcoming Releases")
        st.caption("FRED releases — next 45 days and past 35 days")
        with st.spinner("Loading…"):
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(
                    snap.style.apply(snap_color, axis=1)
                        .format({"Previous": safe_fmt, "Latest": safe_fmt}, na_rep="—"),
                    hide_index=True, use_container_width=True, height=420)
                st.markdown(SOURCE_FRED, unsafe_allow_html=True)

        st.divider()
        st.subheader("Release Calendar")
        st.caption("FRED release schedule — past 35 days and next 45 days "
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
                st.markdown(SOURCE_FRED, unsafe_allow_html=True)

    with col_right:
        st.subheader("FOMC Dates")
        today_d = datetime.today().date()
        for year, meetings in FOMC.items():
            st.caption(f"**{year}**")
            for lbl, d, result in meetings:
                mtg_d = datetime.strptime(d, "%Y-%m-%d").date()
                days = (mtg_d - today_d).days
                if days > 0:
                    st.markdown(f"🔵 **{lbl}** — *{days}d*")
                elif days == 0:
                    st.markdown(f"🟡 **{lbl}** — *today*")
                else:
                    note = f" · {result}" if result else ""
                    st.markdown(f"✅ ~~{lbl}~~{note}")
        st.divider()
        st.caption("**Current Fed Funds Rate**")
        try:
            ff = fetch_fred_series("FEDFUNDS")
            st.metric("Fed Funds", f"{ff.iloc[-1]:.2f}%")
        except Exception:
            st.metric("Fed Funds", "N/A")

    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>',
                unsafe_allow_html=True)
