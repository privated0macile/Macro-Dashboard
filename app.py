import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import fredapi

st.set_page_config(page_title="Macro Dashboard", layout="wide", page_icon="📊")
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.1rem; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

FRED_KEY = st.secrets["FRED_API_KEY"]
fred = fredapi.Fred(api_key=FRED_KEY)

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
SRC_BOTH = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED / Yahoo Finance</p>'
SRC_FRED = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED</p>'
SRC_YF = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: Yahoo Finance</p>'
ZSCORE_LOOKBACK = 252
CHART_WINDOW = 63

FACTORS = {"MTUM": "Momentum", "QUAL": "Quality", "SIZE": "Size", "VLUE": "Value", "USMV": "Min Vol", "HDV": "Yield"}
SECTORS = {
    "XLK": "Info. Tech", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Healthcare", "XLI": "Industrials", "XLY": "Cons. Disc.",
    "XLP": "Cons. Staples", "XLB": "Materials", "XLU": "Utilities",
    "XLRE": "Real Estate", "XLC": "Comm. Serv."
}
SECTORS_CYCLICAL = {"XLE": "Energy", "XLB": "Materials", "XLI": "Industrials",
    "XLY": "Cons. Disc.", "XLF": "Financials", "XLK": "Info. Tech", "XLC": "Comm. Serv."}
SECTORS_DEFENSIVE = {"XLP": "Cons. Staples", "XLV": "Healthcare",
    "XLU": "Utilities", "XLRE": "Real Estate"}
INDICES = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "IWM": "Russell 2000", "DIA": "Dow 30"}
INDICES_CHART = {"^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^RUT": "Russell 2000", "^DJI": "Dow 30"}
EW_SECTORS = {"XLK": "RYT", "XLF": "RYF", "XLE": "RYE", "XLV": "RYH", "XLI": "RGI", "XLY": "RCD", "XLP": "RHS", "XLB": "RTM", "XLU": "RYU", "XLRE": "EWRE", "XLC": "RSPC"}
RETAIL_ETFS = ["TQQQ", "SQQQ"]

HOLDINGS = {
    "XLK": [("AAPL","Apple",0.22),("MSFT","Microsoft",0.21),("NVDA","Nvidia",0.11),("AVGO","Broadcom",0.05),("CRM","Salesforce",0.03),("ADBE","Adobe",0.03),("AMD","AMD",0.03),("CSCO","Cisco",0.02)],
    "XLF": [("BRK-B","Berkshire",0.14),("JPM","JPMorgan",0.11),("V","Visa",0.09),("MA","Mastercard",0.07),("BAC","BofA",0.05),("WFC","Wells Fargo",0.04),("GS","Goldman",0.03),("MS","Morgan Stanley",0.03)],
    "XLE": [("XOM","Exxon",0.23),("CVX","Chevron",0.16),("COP","ConocoPhillips",0.08),("WMB","Williams",0.06),("EOG","EOG Resources",0.05),("SLB","Schlumberger",0.05),("PSX","Phillips 66",0.04),("MPC","Marathon Petro",0.04)],
    "XLV": [("LLY","Eli Lilly",0.12),("UNH","UnitedHealth",0.10),("JNJ","J&J",0.07),("ABBV","AbbVie",0.07),("MRK","Merck",0.06),("TMO","Thermo Fisher",0.04),("ABT","Abbott",0.04),("PFE","Pfizer",0.03)],
    "XLI": [("GE","GE Aerospace",0.09),("CAT","Caterpillar",0.06),("RTX","RTX Corp",0.05),("UNP","Union Pacific",0.05),("HON","Honeywell",0.05),("DE","Deere",0.04),("BA","Boeing",0.04),("LMT","Lockheed",0.03)],
    "XLY": [("AMZN","Amazon",0.23),("TSLA","Tesla",0.15),("HD","Home Depot",0.10),("MCD","McDonald's",0.05),("LOW","Lowe's",0.04),("BKNG","Booking",0.04),("TJX","TJX Cos",0.03),("NKE","Nike",0.02)],
    "XLP": [("PG","Procter & Gamble",0.15),("COST","Costco",0.14),("WMT","Walmart",0.10),("KO","Coca-Cola",0.10),("PEP","PepsiCo",0.09),("PM","Philip Morris",0.06),("MDLZ","Mondelez",0.04),("MO","Altria",0.03)],
    "XLB": [("LIN","Linde",0.19),("SHW","Sherwin-Williams",0.09),("FCX","Freeport-McMoRan",0.08),("APD","Air Products",0.06),("ECL","Ecolab",0.06),("NEM","Newmont",0.05),("NUE","Nucor",0.04),("DOW","Dow Inc",0.04)],
    "XLU": [("NEE","NextEra",0.15),("SO","Southern Co",0.10),("DUK","Duke Energy",0.08),("CEG","Constellation",0.07),("SRE","Sempra",0.05),("AEP","AEP",0.05),("D","Dominion",0.04),("PCG","PG&E",0.04)],
    "XLRE": [("PLD","Prologis",0.13),("AMT","American Tower",0.10),("EQIX","Equinix",0.09),("WELL","Welltower",0.07),("SPG","Simon Property",0.06),("DLR","Digital Realty",0.05),("PSA","Public Storage",0.05),("O","Realty Income",0.05)],
    "XLC": [("META","Meta",0.23),("GOOGL","Alphabet A",0.12),("GOOG","Alphabet C",0.11),("NFLX","Netflix",0.08),("T","AT&T",0.05),("CMCSA","Comcast",0.05),("DIS","Disney",0.04),("TMUS","T-Mobile",0.04)],
}

def get_holdings(etf):
    return HOLDINGS.get(etf, []), False

YIELDS = {"DGS2": "2Y", "DGS5": "5Y", "DGS10": "10Y", "DGS30": "30Y"}
SPREADS = {"T10Y2Y": "10Y-2Y Spread", "T10Y3M": "10Y-3M Spread"}
CREDIT = {"BAMLH0A0HYM2": "HY OAS", "BAMLC0A0CM": "IG OAS"}
KEY_RELEASES = [
    ("Nonfarm Payrolls","PAYEMS","000s MoM","diff"),("Unemployment Rate","UNRATE","%","level"),
    ("CPI YoY","CPIAUCSL","% YoY","yoy"),("Core CPI YoY","CPILFESL","% YoY","yoy"),
    ("PCE YoY","PCEPI","% YoY","yoy"),("Core PCE YoY","PCEPILFE","% YoY","yoy"),
    ("GDP Growth QoQ Ann.","A191RL1Q225SBEA","% Ann.","level"),("Retail Sales MoM","RSAFS","% MoM","mom"),
    ("Industrial Production","INDPRO","% MoM","mom"),("Fed Funds Rate","FEDFUNDS","%","level"),
    ("10Y-2Y Spread","T10Y2Y","%","level"),
]
FOMC = {
    "2025": [
        ("Jan 28-29","2025-01-29","Hold (4.25-4.50%)"),("Mar 18-19","2025-03-19","Hold (4.25-4.50%)"),
        ("May 6-7","2025-05-07","Hold (4.25-4.50%)"),("Jun 17-18","2025-06-18","Hold (4.25-4.50%)"),
        ("Jul 29-30","2025-07-30","Hold (4.25-4.50%)"),("Sep 16-17","2025-09-17","Cut -25bp (4.00-4.25%)"),
        ("Oct 28-29","2025-10-29","Cut -25bp (3.75-4.00%)"),("Dec 9-10","2025-12-10","Cut -25bp (3.50-3.75%)"),
    ],
    "2026": [
        ("Jan 27-28","2026-01-28","Hold (3.50-3.75%)"),("Mar 17-18","2026-03-18",""),
        ("Apr 28-29","2026-04-29",""),("Jun 9-10","2026-06-10",""),
        ("Jul 28-29","2026-07-29",""),("Sep 15-16","2026-09-16",""),
        ("Oct 27-28","2026-10-28",""),("Dec 8-9","2026-12-09",""),
    ]
}

# ─── DATA FETCHERS ───────────────────────────────────────────────────────────
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
        + list(EW_SECTORS.values()) + RETAIL_ETFS + ht + [BENCH, "RSP"]
    ))
    try:
        raw = yf.download(tks, start=START, auto_adjust=True, progress=False, threads=True)
        return raw["Close"], raw["Volume"]
    except Exception:
        core = list(set(list(FACTORS) + list(SECTORS) + list(INDICES) + list(INDICES_CHART)
                        + list(EW_SECTORS.values()) + RETAIL_ETFS + [BENCH, "RSP"]))
        raw = yf.download(core, start=START, auto_adjust=True, progress=False, threads=True)
        return raw["Close"], raw["Volume"]

@st.cache_data(ttl=3600)
def fetch_release_snapshot():
    rows = []
    for name, sid, unit, calc in KEY_RELEASES:
        try:
            s = fetch_fred(sid, start="2022-01-01")
            if len(s) < 2: continue
            lv, pv = s.iloc[-1], s.iloc[-2]
            ld = s.index[-1].strftime("%b %d, %Y")
            if calc == "yoy":
                sy = s.pct_change(12)*100; lv, pv = round(sy.iloc[-1],2), round(sy.iloc[-2],2)
            elif calc == "mom":
                sm = s.pct_change()*100; lv, pv = round(sm.iloc[-1],2), round(sm.iloc[-2],2)
            elif calc == "diff":
                lv, pv = round(s.diff().iloc[-1],2), round(s.diff().iloc[-2],2)
            else:
                lv, pv = round(lv,2), round(pv,2)
            nd = "---"
            try:
                ts = datetime.today().strftime("%Y-%m-%d")
                te = (datetime.today()+timedelta(days=60)).strftime("%Y-%m-%d")
                rr = requests.get(f"https://api.stlouisfed.org/fred/series/release?series_id={sid}&api_key={FRED_KEY}&file_type=json", timeout=5)
                if rr.status_code == 200:
                    rid = rr.json()["releases"][0]["id"]
                    dr = requests.get(f"https://api.stlouisfed.org/fred/release/dates?release_id={rid}&api_key={FRED_KEY}&file_type=json&realtime_start={ts}&realtime_end={te}&include_release_dates_with_no_data=true", timeout=5)
                    if dr.status_code == 200:
                        fu = [d["date"] for d in dr.json().get("release_dates",[]) if d["date"] >= ts]
                        if fu: nd = pd.Timestamp(fu[0]).strftime("%b %d, %Y")
            except Exception: pass
            rows.append({"Release":name,"Last Updated":ld,"Previous":pv,"Latest":lv,"Unit":unit,"Next Release":nd})
        except Exception: continue
    return pd.DataFrame(rows)

@st.cache_data(ttl=1800)
def fetch_fred_calendar():
    today = datetime.today()
    ps = (today-timedelta(days=35)).strftime("%Y-%m-%d")
    fs = (today+timedelta(days=45)).strftime("%Y-%m-%d")
    try:
        r = requests.get(f"https://api.stlouisfed.org/fred/releases/dates?api_key={FRED_KEY}&file_type=json&realtime_start={ps}&realtime_end={fs}&include_release_dates_with_no_data=true", timeout=10)
        if r.status_code != 200: return pd.DataFrame()
        df = pd.DataFrame(r.json().get("release_dates",[]))
        if df.empty: return df
        df = df.rename(columns={"release_name":"Release","date":"Date"})
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df[["Date","Release"]].sort_values("Date").reset_index(drop=True)
    except Exception: return pd.DataFrame()

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def to_yoy(s): return s.pct_change(12)*100
def trim(s, m): return s[s.index >= s.index.max()-pd.DateOffset(months=m)] if m else s
def compute_relative(p, d):
    avail = [k for k in d.keys() if k in p.columns]
    if not avail or BENCH not in p.columns: return pd.DataFrame(), pd.DataFrame()
    rel = p[avail].div(p[BENCH], axis=0)
    alpha = (1+rel.pct_change()).rolling(ROLL).apply(np.prod, raw=True)-1
    return rel, alpha
def reindex_from(df, bd):
    df = df[df.index >= pd.Timestamp(bd)]
    return df / df.iloc[0]

def src_ann(y=-0.30):
    return dict(text="Source: FRED / Yahoo Finance", xref="paper", yref="paper",
                x=1.0, y=y, showarrow=False, font=dict(size=10, color="#888888"), xanchor="right")

def chart_title(m, s): return f"{m} {s}"

def safe_fmt(v):
    try: return f"{float(v):.2f}"
    except (ValueError, TypeError): return str(v)

def snap_color(row):
    st_ = [""]*len(row)
    try:
        l, p = float(row["Latest"]), float(row["Previous"])
        i = list(row.index).index("Latest")
        st_[i] = "color:#2ca02c;font-weight:bold" if l > p else "color:#d62728;font-weight:bold" if l < p else ""
    except (ValueError, TypeError): pass
    return st_

def add_src(fig, y=-0.25):
    fig.add_annotation(text="Source: FRED / Yahoo Finance", xref="paper", yref="paper",
                       x=1.0, y=y, showarrow=False, font=dict(size=10, color="#888888"), xanchor="right")

# ─── Z-SCORE HELPERS ─────────────────────────────────────────────────────────
def compute_volume_zscore(v, lb=ZSCORE_LOOKBACK):
    rm = v.rolling(lb, min_periods=60).mean()
    rs = v.rolling(lb, min_periods=60).std()
    return ((v-rm)/rs).clip(-3,3)

def compute_flow_proxy_z(P, V, t, lb=ZSCORE_LOOKBACK):
    if t not in P.columns or t not in V.columns: return pd.Series(dtype=float)
    p, v = P[t].dropna(), V[t].dropna()
    c = p.index.intersection(v.index); p, v = p.loc[c], v.loc[c]
    dv = p*v; ret = p.pct_change(); flow = dv.diff()-(ret*dv.shift(1))
    rm = flow.rolling(lb, min_periods=60).mean()
    rs = flow.rolling(lb, min_periods=60).std()
    return ((flow-rm)/rs).clip(-3,3)

def compute_signed_volume_z(P, V, t, lb=ZSCORE_LOOKBACK):
    if t not in P.columns or t not in V.columns: return pd.Series(dtype=float)
    p, v = P[t].dropna(), V[t].dropna()
    c = p.index.intersection(v.index); p, v = p.loc[c], v.loc[c]
    sv = v*np.sign(p.pct_change())
    rm = sv.rolling(lb, min_periods=60).mean()
    rs = sv.rolling(lb, min_periods=60).std()
    return ((sv-rm)/rs).clip(-3,3)

def compute_breadth(P):
    if "RSP" not in P.columns or "SPY" not in P.columns: return pd.Series(dtype=float)
    r, s = P["RSP"].dropna(), P["SPY"].dropna()
    c = r.index.intersection(s.index)
    return r.loc[c]/s.loc[c]

def compute_rotation_ratio(P, smooth=21, nw=252):
    sr = P[list(SECTORS.keys())].pct_change().dropna()
    bw = sr.std(axis=1)
    wp = []
    for cw, ew in EW_SECTORS.items():
        if cw in P.columns and ew in P.columns:
            wp.append((P[ew].pct_change()-P[cw].pct_change()).abs())
    if not wp: return pd.Series(dtype=float), pd.Series(dtype=float)
    wi = pd.concat(wp, axis=1).mean(axis=1).dropna()
    c = bw.index.intersection(wi.index); bw, wi = bw.loc[c], wi.loc[c]
    wi = wi.replace(0, np.nan); raw = bw/wi
    sm = raw.rolling(smooth, min_periods=10).mean()
    pr = sm.rolling(nw, min_periods=60).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    return pr.dropna(), sm.dropna()

def build_positioning_table(P, V, d, rd):
    rows = []
    for t, n in d.items():
        try:
            p = P[t].dropna()
            if len(p) < 2: continue
            ret = p.pct_change().iloc[-1]*100 if rd == 1 else ((p.iloc[-1]/p.iloc[-rd])-1)*100 if len(p) > rd else np.nan
            fz = compute_flow_proxy_z(P, V, t); fzv = round(fz.iloc[-1],2) if len(fz) > 0 else np.nan
            svz = compute_signed_volume_z(P, V, t); svzv = round(svz.iloc[-1],2) if len(svz) > 0 else np.nan
            rs = p.pct_change(); rm = rs.rolling(ZSCORE_LOOKBACK, min_periods=60).mean()
            rsd = rs.rolling(ZSCORE_LOOKBACK, min_periods=60).std()
            rzv = float(np.clip((rs.iloc[-1]-rm.iloc[-1])/rsd.iloc[-1],-3,3))
            comp = [v for v in [fzv, svzv, rzv] if not np.isnan(v)]
            cv = round(np.mean(comp),2) if comp else np.nan
            rows.append({"Ticker":t,"Name":n,"Return %":round(ret,2) if not np.isnan(ret) else np.nan,
                         "Flow Z":fzv,"Signed Vol Z":svzv,"Composite":cv})
        except Exception: continue
    return pd.DataFrame(rows)

def style_pos(df):
    def cz(v):
        if pd.isna(v): return ""
        if v >= 2: return "color:#2ca02c;font-weight:bold"
        if v <= -2: return "color:#d62728;font-weight:bold"
        if v >= 1: return "color:#2ca02c"
        if v <= -1: return "color:#d62728"
        return ""
    def cr(v):
        if pd.isna(v): return ""
        return "color:#2ca02c" if v > 0 else "color:#d62728" if v < 0 else ""
    s = df.style
    for c in ["Flow Z","Signed Vol Z","Composite"]:
        if c in df.columns: s = s.map(cz, subset=[c])
    for c in ["Return %"]:
        if c in df.columns: s = s.map(cr, subset=[c])
    fmt = {c: "{:+.2f}" for c in ["Return %","Flow Z","Signed Vol Z","Composite"] if c in df.columns}
    return s.format(fmt, na_rep="---")

def style_attr(df):
    def c(v):
        if pd.isna(v): return ""
        return "color:#2ca02c" if v > 0 else "color:#d62728" if v < 0 else ""
    s = df.style
    for col in [x for x in ["1D Ret %","Contribution","5D Ret %","1M Ret %"] if x in df.columns]:
        s = s.map(c, subset=[col])
    return s.format({"1D Ret %":"{:+.2f}","Contribution":"{:+.3f}","5D Ret %":"{:+.2f}","1M Ret %":"{:+.2f}"}, na_rep="---")

def build_holdings_attr(etf, P):
    h, live = get_holdings(etf)
    if not h: return pd.DataFrame(), np.nan, False
    er = P[etf].pct_change().iloc[-1]*100 if etf in P.columns else np.nan
    rows = []
    for t, n, w in h:
        if t not in P.columns: continue
        p = P[t].dropna()
        if len(p) < 2: continue
        sr = p.pct_change().iloc[-1]*100; co = w*sr
        r5 = ((p.iloc[-1]/p.iloc[-5])-1)*100 if len(p) >= 5 else np.nan
        r1m = ((p.iloc[-1]/p.iloc[-21])-1)*100 if len(p) >= 21 else np.nan
        rows.append({"Ticker":t,"Name":n,"Weight":f"{w:.0%}","1D Ret %":round(sr,2),
                     "Contribution":round(co,3),"5D Ret %":round(r5,2) if not np.isnan(r5) else np.nan,
                     "1M Ret %":round(r1m,2) if not np.isnan(r1m) else np.nan})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["_ac"] = df["Contribution"].abs()
        df = df.sort_values("_ac", ascending=False).drop(columns=["_ac"]).reset_index(drop=True)
    return df, er, live

def yield_curve_commentary():
    try:
        y2, y10, y30 = fetch_fred("DGS2").iloc[-1], fetch_fred("DGS10").iloc[-1], fetch_fred("DGS30").iloc[-1]
        sp = (fetch_fred("DGS10")-fetch_fred("DGS2")).dropna()
        sn = sp.iloc[-1]; sp2 = sp.iloc[-63] if len(sp) > 63 else sp.iloc[0]; ch = sn-sp2
        sh = "inverted" if sn < -0.1 else ("flat" if sn < 0.1 else "upward sloping")
        tr = "steepening" if ch > 0.1 else ("flattening" if ch < -0.1 else "unchanged")
        return f"Currently **{sh}** -- 2Y {y2:.2f}% / 10Y {y10:.2f}% / 30Y {y30:.2f}% / 10Y-2Y {sn:+.2f}% / {tr} over 3M"
    except Exception: return ""

def build_yield_curve():
    mats = {"DGS1MO":"1M","DGS3MO":"3M","DGS6MO":"6M","DGS1":"1Y","DGS2":"2Y","DGS5":"5Y","DGS10":"10Y","DGS20":"20Y","DGS30":"30Y"}
    vs, ls = [], []
    for sid, lbl in mats.items():
        try: s = fetch_fred(sid, start="2020-01-01"); vs.append(round(s.iloc[-1],3)); ls.append(lbl)
        except Exception: pass
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ls, y=vs, mode="lines+markers", line=dict(color="#1f77b4", width=2.5), marker=dict(size=8), showlegend=False))
    fig.update_layout(title=chart_title("Current Yield Curve","Spot rates 1M-30Y"), template="plotly_white", height=380,
                      yaxis_title="Yield (%)", xaxis_title="Maturity", margin=dict(b=70,t=60,l=60,r=40), dragmode=False)
    add_src(fig, -0.18)
    return fig

# ─── PAGE HEADER ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:baseline">
    <h1 style="margin:0">Macro Dashboard</h1>
    <span style="color:#888;font-size:0.85rem">
        Refreshed: {datetime.now().strftime('%b %d, %Y %H:%M')}
        &nbsp;/&nbsp; Data: FRED / Yahoo Finance
    </span>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Equities", "Fixed Income & Macro", "Calendar"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 -- EQUITIES
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    with st.spinner("Loading equity data..."):
        prices, volumes = fetch_equity()

    period_opts = {"Past 12M": None, "Since 2015": "2015-01-01", "Since 2020": "2020-01-01", "Since 2025": "2025-01-01"}

    # ── Header: Indices + Top/Bottom table ──
    hdr_l, hdr_r = st.columns(2)
    with hdr_l:
        idx_period = st.radio("Period", ["1M","3M","6M","YTD","1Y"], horizontal=True, key="idx_period")
        latest = prices.index.max()
        idx_start = pd.Timestamp(f"{latest.year}-01-01") if idx_period == "YTD" else latest - pd.DateOffset(months={"1M":1,"3M":3,"6M":6,"1Y":12}[idx_period])
        idx_colors = {"^GSPC":"#1f77b4","^IXIC":"#ff7f0e","^RUT":"#2ca02c","^DJI":"#d62728"}
        fig_idx = go.Figure()
        for t, n in INDICES_CHART.items():
            if t in prices.columns:
                s = prices[t].dropna(); s = s[s.index >= idx_start]
                if len(s) > 1:
                    ix = (s/s.iloc[0]-1)*100
                    fig_idx.add_trace(go.Scatter(x=ix.index, y=np.round(ix.values,2), name=n, mode="lines",
                        line=dict(color=idx_colors.get(t,"#999"), width=2.5), customdata=np.round(s.values,2),
                        hovertemplate=f"<b>{n}</b><br>Date: %{{x|%b %d, %Y}}<br>Return: %{{y:+.2f}}%<br>Level: %{{customdata:,.2f}}<extra></extra>"))
        fig_idx.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig_idx.update_layout(title=chart_title("U.S. Major Indices", f"{idx_period} cumulative return"),
            template="plotly_white", height=260, yaxis_title="Return (%)",
            margin=dict(b=70,t=50,l=55,r=40), legend=dict(orientation="h",yanchor="top",y=-0.28,x=0.5,xanchor="center"),
            dragmode=False)
        add_src(fig_idx, -0.35)
        st.plotly_chart(fig_idx, use_container_width=True, key="fig_idx", config=PCFG)

    with hdr_r:
        # Build multi-period positioning for sectors
        rows = []
        for t, n in SECTORS.items():
            try:
                p = prices[t].dropna()
                if len(p) < 2: continue
                r1 = p.pct_change().iloc[-1]*100
                r5 = ((p.iloc[-1]/p.iloc[-5])-1)*100 if len(p) >= 5 else np.nan
                r1m = ((p.iloc[-1]/p.iloc[-21])-1)*100 if len(p) >= 21 else np.nan
                r12m = ((p.iloc[-1]/p.iloc[-252])-1)*100 if len(p) >= 252 else np.nan
                fz = compute_flow_proxy_z(prices, volumes, t)
                fzv = round(fz.iloc[-1],2) if len(fz) > 0 else np.nan
                svz = compute_signed_volume_z(prices, volumes, t)
                svzv = round(svz.iloc[-1],2) if len(svz) > 0 else np.nan
                rs = p.pct_change()
                rm = rs.rolling(ZSCORE_LOOKBACK, min_periods=60).mean()
                rsd = rs.rolling(ZSCORE_LOOKBACK, min_periods=60).std()
                rzv = float(np.clip((rs.iloc[-1]-rm.iloc[-1])/rsd.iloc[-1],-3,3))
                comp = [v for v in [fzv, svzv, rzv] if not np.isnan(v)]
                cv = round(np.mean(comp),2) if comp else np.nan
                rows.append({"Ticker":t,"Name":n,
                    "1D":round(r1,2),"5D":round(r5,2) if not np.isnan(r5) else np.nan,
                    "1M":round(r1m,2) if not np.isnan(r1m) else np.nan,
                    "12M":round(r12m,2) if not np.isnan(r12m) else np.nan,
                    "Flow Z":fzv,"Composite":cv})
            except Exception: continue
        df_pos = pd.DataFrame(rows)
        if not df_pos.empty and "Composite" in df_pos.columns:
            df_pos = df_pos.dropna(subset=["Composite"]).sort_values("Composite", ascending=False).reset_index(drop=True)
            t3, b3 = df_pos.head(3), df_pos.tail(3)
            dd = pd.concat([t3, b3], ignore_index=True)
            st.markdown("**Top 3 / Bottom 3 by Composite**")
            st.caption("Composite = (Flow Z + Signed Vol Z + Return Z) / 3 -- all 252-day rolling, clipped +/-3")
            def _sty(d):
                def cz(v):
                    if pd.isna(v): return ""
                    if v >= 2: return "color:#2ca02c;font-weight:bold"
                    if v <= -2: return "color:#d62728;font-weight:bold"
                    if v >= 1: return "color:#2ca02c"
                    if v <= -1: return "color:#d62728"
                    return ""
                def cr2(v):
                    if pd.isna(v): return ""
                    return "color:#2ca02c" if v > 0 else "color:#d62728" if v < 0 else ""
                def row_border(row):
                    if row.name == 2:
                        return ["border-bottom:2px solid #333"]*len(row)
                    return [""]*len(row)
                s = d.style.apply(row_border, axis=1)
                for c in ["Flow Z","Composite"]:
                    if c in d.columns: s = s.map(cz, subset=[c])
                for c in ["1D","5D","1M","12M"]:
                    if c in d.columns: s = s.map(cr2, subset=[c])
                fmt = {c: "{:+.2f}" for c in ["1D","5D","1M","12M","Flow Z","Composite"] if c in d.columns}
                return s.format(fmt, na_rep="---")
            st.dataframe(_sty(dd), hide_index=True, use_container_width=True, height=260)
            st.markdown(SRC_BOTH, unsafe_allow_html=True)

    st.divider()

    # ── Daily Positioning Feed ──
    st.subheader("Daily Positioning Feed")
    st.caption("Macro vs Micro = between-sector vs within-sector dispersion (252d percentile rank) / "
               "Breadth = RSP/SPY ratio (equal-weight vs cap-weight) / "
               "Cyclical/Defensive = equal-weight basket ratio / "
               "SPY Volume = volume z-scored against 1Y median.")

    # ── Regime charts ──
    regime_window = st.radio("Regime window", ["3M","6M","12M"], horizontal=True, key="regime_window", index=2)
    regime_months = {"3M":3,"6M":6,"12M":12}[regime_window]
    regime_cutoff = prices.index.max() - pd.DateOffset(months=regime_months)

    rc1, rc2, rc3, rc4 = st.columns(4)

    with rc1:
        try:
            rr_pct, rr_raw = compute_rotation_ratio(prices)
            if len(rr_pct) > 0:
                rv = rr_pct.iloc[-1]
                rl = "Sector rotation" if rv > 0.75 else "Stock dispersion" if rv < 0.25 else "Balanced"
                rt = rr_pct[rr_pct.index >= regime_cutoff]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=rt.index, y=rt.values, mode="lines", line=dict(color="#1f77b4",width=2), showlegend=False))
                fig.add_hline(y=0.5, line_dash="dash", line_color="gray")
                fig.add_hrect(y0=0.25, y1=0.75, fillcolor="gray", opacity=0.08, line_width=0)
                fig.update_layout(title=dict(text=f"<b>Macro vs Micro</b> -- {rv:.2f} ({rl})<br><span style='font-size:11px;color:#666'>>0.75 sector-driven / <0.25 stock-driven</span>", font=dict(size=12)),
                    template="plotly_white", height=380, yaxis_title="%-tile", yaxis=dict(range=[0,1],dtick=0.25),
                    margin=dict(b=70,t=65,l=45,r=25), dragmode=False)
                add_src(fig, -0.25)
                st.plotly_chart(fig, use_container_width=True, key="fig_rotation", config=PCFG)
            else: st.info("Rotation ratio unavailable.")
        except Exception:
            rr_pct, rr_raw = pd.Series(dtype=float), pd.Series(dtype=float)
            st.info("Rotation ratio unavailable.")

    with rc2:
        try:
            br = compute_breadth(prices)
            if len(br) > 0:
                bt = br[br.index >= regime_cutoff]; bi = bt/bt.iloc[0]; bn = bi.iloc[-1]
                bl = "Broad" if bn > 1.005 else "Concentrated" if bn < 0.995 else "Neutral"
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=bi.index, y=bi.values, mode="lines", line=dict(color="#ff7f0e",width=2), showlegend=False))
                fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
                fig.update_layout(title=dict(text=f"<b>Breadth</b> -- {bn:.4f} ({bl})<br><span style='font-size:11px;color:#666'>RSP/SPY / rising = broadening</span>", font=dict(size=12)),
                    template="plotly_white", height=380, yaxis_title="Indexed", margin=dict(b=70,t=65,l=45,r=25), dragmode=False)
                add_src(fig, -0.25)
                st.plotly_chart(fig, use_container_width=True, key="fig_breadth", config=PCFG)
        except Exception: st.info("Breadth data unavailable.")

    with rc3:
        try:
            cy = prices[list(SECTORS_CYCLICAL.keys())].pct_change().mean(axis=1)
            de = prices[list(SECTORS_DEFENSIVE.keys())].pct_change().mean(axis=1)
            cc, dc = (1+cy).cumprod(), (1+de).cumprod()
            ratio = cc/dc; rt2 = ratio[ratio.index >= regime_cutoff]; ri2 = rt2/rt2.iloc[0]
            cn = ri2.iloc[-1]; cl = "Risk-on" if cn > 1.005 else "Risk-off" if cn < 0.995 else "Neutral"
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ri2.index, y=ri2.values, mode="lines", line=dict(color="#2ca02c",width=2), showlegend=False))
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
            fig.update_layout(title=dict(text=f"<b>Cyclical / Defensive</b> -- {cn:.4f} ({cl})<br><span style='font-size:11px;color:#666'>Rising = risk-on / falling = risk-off</span>", font=dict(size=12)),
                template="plotly_white", height=380, yaxis_title="Ratio", margin=dict(b=70,t=65,l=45,r=25), dragmode=False)
            add_src(fig, -0.25)
            st.plotly_chart(fig, use_container_width=True, key="fig_cyc_def", config=PCFG)
        except Exception: st.info("Cyclical/Defensive unavailable.")

    with rc4:
        try:
            sv = volumes["SPY"].dropna()
            s1y = sv[sv.index >= sv.index.max()-pd.DateOffset(months=12)]
            sm, ss = s1y.median(), s1y.std()
            szf = ((sv-sm)/ss).clip(-3,3)
            c3m = sv.index.max()-pd.DateOffset(months=3)
            sz = szf[szf.index >= c3m]; szn = sz.iloc[-1]
            bc = ["#2ca02c" if v >= 0 else "#d62728" for v in sz.values]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=sz.index, y=sz.values, marker_color=bc, opacity=0.7, showlegend=False))
            fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
            fig.add_hline(y=2, line_dash="dot", line_color="#2ca02c", line_width=0.8)
            fig.add_hline(y=-2, line_dash="dot", line_color="#d62728", line_width=0.8)
            fig.update_layout(title=dict(text=f"<b>SPY Volume</b> -- {szn:+.2f}s today<br><span style='font-size:11px;color:#666'>0 = 1Y median / 3M window / +/-3</span>", font=dict(size=12)),
                template="plotly_white", height=380, yaxis_title="Z-Score", yaxis=dict(range=[-3.5,3.5],dtick=1),
                margin=dict(b=70,t=65,l=45,r=25), bargap=0.15, dragmode=False)
            add_src(fig, -0.25)
            st.plotly_chart(fig, use_container_width=True, key="fig_spy_vol", config=PCFG)
        except Exception: st.info("SPY volume unavailable.")

    # ── Relative Performance ──
    st.divider()
    st.subheader("Relative Performance")
    pf = st.radio("Period", list(period_opts.keys()), horizontal=True, key="pf")
    base = period_opts[pf] or (prices.index.max()-pd.DateOffset(months=12)).strftime("%Y-%m-%d")

    def _build_pair(ad, gl, bd, ks):
        rel, alpha = compute_relative(prices, ad)
        ri = reindex_from(rel, bd); al = alpha[alpha.index >= pd.Timestamp(bd)]
        cl, cr2 = st.columns(2)
        with cl:
            fig = go.Figure()
            for t, n in ad.items():
                if t in ri.columns: fig.add_trace(go.Scatter(x=ri.index, y=ri[t], name=n, mode="lines"))
            fig.add_hline(y=1.0, line_dash="dash", line_color="gray")
            fig.update_layout(title=chart_title(f"{gl} Relative Performance","ETF / SPY, indexed to 1.0"),
                template="plotly_white", height=380, margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
            add_src(fig, -0.22)
            st.plotly_chart(fig, use_container_width=True, key=f"rel_{ks}", config=PCFG)
        with cr2:
            fig = go.Figure()
            for t, n in ad.items():
                if t in al.columns: fig.add_trace(go.Scatter(x=al.index, y=al[t], name=n, mode="lines"))
            fig.add_hline(y=0.0, line_dash="dash", line_color="gray")
            fig.update_layout(title=chart_title(f"{gl} Rolling 6M Alpha","Compounded 126-day relative return"),
                template="plotly_white", height=380, margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
            add_src(fig, -0.22)
            st.plotly_chart(fig, use_container_width=True, key=f"alpha_{ks}", config=PCFG)

    st.markdown("#### Factors")
    _build_pair(FACTORS, "Factor", base, "factors")
    st.markdown("#### Cyclical-Tilt Sectors")
    _build_pair(SECTORS_CYCLICAL, "Cyclical-Tilt", base, "cyclical")
    st.markdown("#### Defensive-Tilt Sectors")
    _build_pair(SECTORS_DEFENSIVE, "Defensive-Tilt", base, "defensive")

    # ── Individual ETF Flow Charts ──
    st.divider()
    st.subheader("Individual ETF -- Flow & Price")
    st.caption("Price indexed / flow z-score (252d rolling, clipped +/-3) / green = accumulation, red = distribution")
    cwopt = st.radio("Chart window", ["3M","6M","1Y"], horizontal=True, key="etf_cw", index=1)
    cbd = {"3M":63,"6M":126,"1Y":252}[cwopt]

    def build_flow_chart(t, lbl, P, V, w):
        if t not in P.columns: return None
        p = P[t].dropna(); co = p.index[-1]-pd.tseries.offsets.BDay(w); p = p[p.index >= co]
        if len(p) < 10: return None
        pi = p/p.iloc[0]; fz = compute_flow_proxy_z(P, V, t); fz = fz[fz.index >= co]
        cm = pi.index.intersection(fz.index); pi, fz = pi.loc[cm], fz.loc[cm]
        if len(cm) < 5: return None
        bc = ["#2ca02c" if v >= 0 else "#d62728" for v in fz.values]
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=fz.index, y=fz.values, name="Flow Z", marker_color=bc, opacity=0.35, showlegend=False), secondary_y=True)
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
            name="\U0001f7e9\U0001f7e5 Flow Z", marker=dict(size=0, color="rgba(0,0,0,0)")))
        fig.add_trace(go.Scatter(x=pi.index, y=pi.values, name=lbl, mode="lines", line=dict(color="#1f77b4",width=2.5)), secondary_y=False)
        fig.add_hline(y=1.0, line_dash="dash", line_color="gray", line_width=0.8, secondary_y=False)
        fig.update_layout(title=dict(text=f"<b>{lbl}</b> ({t})<br><span style='font-size:11px;color:#666'>Price indexed / Flow z (252d) / green = accumulation</span>", font=dict(size=13)),
            template="plotly_white", height=320, margin=dict(b=55,t=65,l=50,r=40),
            legend=dict(orientation="h",yanchor="top",y=-0.18,x=0.5,xanchor="center",font=dict(size=9)),
            dragmode=False, bargap=0.1)
        fig.update_yaxes(title_text="Indexed", secondary_y=False)
        fig.update_yaxes(title_text="Flow Z", secondary_y=True, range=[-3.5,3.5], dtick=1, showgrid=False)
        add_src(fig, -0.22)
        return fig

    st.markdown("#### Sector ETFs")
    sc = st.columns(3)
    for i, (t, n) in enumerate(SECTORS.items()):
        f = build_flow_chart(t, n, prices, volumes, cbd)
        if f:
            with sc[i%3]: st.plotly_chart(f, use_container_width=True, key=f"flow_{t}", config=PCFG)

    st.markdown("#### Factor ETFs")
    fc = st.columns(3)
    for i, (t, n) in enumerate(FACTORS.items()):
        f = build_flow_chart(t, n, prices, volumes, cbd)
        if f:
            with fc[i%3]: st.plotly_chart(f, use_container_width=True, key=f"flow_{t}", config=PCFG)

    # ── Holdings ──
    st.divider()
    st.subheader("Sector ETF Holdings & Daily Attribution")
    st.caption("Expand any sector to see top holdings, weight, daily return, "
               "and contribution (weight x return). Sorted by contribution. "
               "Weights are hardcoded and updated biannually -- minor drift expected between updates.")
    ec = st.columns(2)
    for i, (t, n) in enumerate(SECTORS.items()):
        with ec[i%2]:
            with st.expander(f"**{n}** ({t})"):
                try:
                    da, er, il = build_holdings_attr(t, prices)
                    st2 = "live" if il else "static"
                    if not da.empty:
                        ex = da["Contribution"].sum()
                        if er and abs(er) > 0.001:
                            st.caption(f"ETF 1D: **{er:+.2f}%** / Top holdings explain: **{ex:+.3f}%** ({ex/er*100:.0f}%) / {st2}")
                        else:
                            st.caption(f"ETF 1D: **{er:+.2f}%** / {st2}")
                        st.dataframe(style_attr(da), hide_index=True, use_container_width=True, height=min(35*len(da)+38,340))
                    else: st.info("Holdings data unavailable.")
                except Exception: st.info("Holdings data unavailable.")
    st.markdown(SRC_YF, unsafe_allow_html=True)

    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 -- FIXED INCOME & MACRO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    ri1, ri2, ri3, ri4, ri5, ri6 = st.columns(6)
    for col, sid, lbl, sd, u in [(ri1,"DGS2","2Y Treasury",True,"%"),(ri2,"DGS10","10Y Treasury",True,"%"),
        (ri3,"DGS30","30Y Treasury",True,"%"),(ri4,"FEDFUNDS","Fed Funds",False,"%"),
        (ri5,"CPIAUCSL","CPI YoY",True,"%"),(ri6,"T10Y2Y","10Y-2Y",True,"%")]:
        try:
            s = to_yoy(fetch_fred(sid)) if sid == "CPIAUCSL" else fetch_fred(sid)
            c, p = s.iloc[-1], s.iloc[-2]
            d = f"{c-p:+.2f}{u}" if sd else None
            col.metric(lbl, f"{c:.2f}{u}", d)
        except Exception: col.metric(lbl, "N/A")
    st.markdown(SRC_FRED, unsafe_allow_html=True)
    st.divider()

    rp = st.radio("Period", ["1Y","3Y","5Y","10Y","Full"], horizontal=True, key="rp")
    rmons = {"1Y":12,"3Y":36,"5Y":60,"10Y":120,"Full":None}[rp]

    yc_col, yld_col = st.columns(2)
    with yc_col:
        st.plotly_chart(build_yield_curve(), use_container_width=True, key="yc_rates", config=PCFG)
        c = yield_curve_commentary()
        if c: st.caption(c)
    with yld_col:
        colors = ["#1f77b4","#ff7f0e","#2ca02c","#d62728"]
        fig = go.Figure()
        for i, (sid, lbl) in enumerate(YIELDS.items()):
            try:
                s = trim(fetch_fred(sid), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines", line=dict(color=colors[i],width=2)))
            except Exception: pass
        fig.update_layout(title=chart_title("Treasury Yields","Constant-maturity daily"), template="plotly_white", height=380,
            yaxis_title="Yield (%)", margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key="fig_yields", config=PCFG)

    r2a, r2b, r2c = st.columns(3)
    with r2a:
        fig = go.Figure()
        for sid, lbl in SPREADS.items():
            try: s = trim(fetch_fred(sid), rmons); fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception: pass
        fig.add_hline(y=0, line_dash="dash", line_color="red", line_width=1)
        fig.update_layout(title=chart_title("Curve Spreads","Below 0 = inverted"), template="plotly_white", height=340,
            yaxis_title="Spread (%)", margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key="fig_spreads", config=PCFG)
    with r2b:
        fig = go.Figure()
        for sid, lbl in [("DFII10","10Y Real Yield"),("T10YIE","10Y Breakeven")]:
            try: s = trim(fetch_fred(sid), rmons); fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception: pass
        fig.update_layout(title=chart_title("Real Yield & Breakeven","TIPS + implied inflation"), template="plotly_white", height=340,
            yaxis_title="%", margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key="fig_realyield", config=PCFG)
    with r2c:
        fig = go.Figure()
        for sid, lbl in CREDIT.items():
            try: s = trim(fetch_fred(sid), rmons)*100; fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception: pass
        try:
            hy = trim(fetch_fred("BAMLH0A0HYM2"), rmons); ig = trim(fetch_fred("BAMLC0A0CM"), rmons)
            gap = (hy-ig).dropna()*100
            fig.add_trace(go.Scatter(x=gap.index, y=gap.values, name="HY-IG Gap", mode="lines", line=dict(dash="dot",width=1.5)))
        except Exception: pass
        fig.update_layout(title=chart_title("Credit Spreads (OAS)","Wider = risk-off"), template="plotly_white", height=340,
            yaxis_title="bps", margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key="fig_credit", config=PCFG)

    st.divider()
    il, ir = st.columns(2)
    with il:
        fig = go.Figure()
        for sid, lbl in [("CPIAUCSL","CPI"),("CPILFESL","Core CPI")]:
            try: s = trim(to_yoy(fetch_fred(sid)), rmons); fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception: pass
        fig.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="2%", annotation_position="bottom right")
        fig.update_layout(title=chart_title("CPI & Core CPI","YoY %"), template="plotly_white", height=360,
            yaxis_title="YoY %", margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key="fig_cpi", config=PCFG)
    with ir:
        fig = go.Figure()
        for sid, lbl in [("PCEPI","PCE"),("PCEPILFE","Core PCE")]:
            try: s = trim(to_yoy(fetch_fred(sid)), rmons); fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception: pass
        fig.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="2%", annotation_position="bottom right")
        fig.update_layout(title=chart_title("PCE & Core PCE","YoY % / Fed's preferred gauge"), template="plotly_white", height=360,
            yaxis_title="YoY %", margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key="fig_pce", config=PCFG)

    el, gl = st.columns(2)
    with el:
        fig = go.Figure()
        for sid, lbl, clr in [("FEDFUNDS","Fed Funds","#1f77b4"),("UNRATE","Unemployment","#ff7f0e")]:
            try: s = trim(fetch_fred(sid), rmons); fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines", line=dict(color=clr,width=2)))
            except Exception: pass
        fig.update_layout(title=chart_title("Fed Funds & Unemployment","Dual mandate"), template="plotly_white", height=360,
            yaxis_title="%", margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
        add_src(fig, -0.22)
        st.plotly_chart(fig, use_container_width=True, key="fig_ff", config=PCFG)
    with gl:
        try:
            gdp = trim(fetch_fred("A191RL1Q225SBEA"), rmons)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=gdp.index, y=gdp.values, name="GDP Growth",
                marker_color=["#2ca02c" if v >= 0 else "#d62728" for v in gdp.values]))
            fig.add_hline(y=0, line_color="black", line_width=1)
            fig.update_layout(title=chart_title("Real GDP Growth","QoQ annualized %"), template="plotly_white", height=360,
                yaxis_title="% QoQ Ann.", margin=dict(b=90,t=50,l=55,r=30), legend=LEG, dragmode=False)
            add_src(fig, -0.22)
            st.plotly_chart(fig, use_container_width=True, key="fig_gdp", config=PCFG)
        except Exception: st.info("GDP data unavailable.")

    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 -- CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    cl, cr3 = st.columns([3, 1])
    with cl:
        st.subheader("Upcoming Releases")
        st.caption("FRED releases -- next 45 days and past 35 days")
        with st.spinner("Loading..."):
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(snap.style.apply(snap_color, axis=1).format({"Previous":safe_fmt,"Latest":safe_fmt}, na_rep="---"),
                    hide_index=True, use_container_width=True, height=420)
                st.markdown(SRC_FRED, unsafe_allow_html=True)
        st.divider()
        st.subheader("Release Calendar")
        st.caption("FRED release schedule -- past 35 days and next 45 days / yellow = today / gray = past")
        with st.spinner("Loading calendar..."):
            cal = fetch_fred_calendar()
            if cal.empty: st.info("No calendar data available.")
            else:
                tts = pd.Timestamp.today().normalize()
                def cs(row):
                    d = pd.Timestamp(row["Date"])
                    if d.normalize() == tts: return ["background-color:#fff3cd;font-weight:bold"]*len(row)
                    if d < tts: return ["color:#aaaaaa"]*len(row)
                    return [""]*len(row)
                dc = cal.copy(); dc["Date"] = dc["Date"].dt.strftime("%b %d, %Y")
                st.dataframe(dc.style.apply(cs, axis=1), hide_index=True, use_container_width=True, height=520)
                st.markdown(SRC_FRED, unsafe_allow_html=True)
    with cr3:
        st.subheader("FOMC Dates")
        td = datetime.today().date()
        for yr, mtgs in FOMC.items():
            st.caption(f"**{yr}**")
            for lbl, d, res in mtgs:
                md = datetime.strptime(d, "%Y-%m-%d").date(); days = (md-td).days
                if days > 0: st.markdown(f"🔵 **{lbl}** -- *{days}d*")
                elif days == 0: st.markdown(f"🟡 **{lbl}** -- *today*")
                else:
                    note = f" / {res}" if res else ""
                    st.markdown(f"✅ ~~{lbl}~~{note}")
        st.divider()
        st.caption("**Current Fed Funds Rate**")
        try: ff = fetch_fred("FEDFUNDS"); st.metric("Fed Funds", f"{ff.iloc[-1]:.2f}%")
        except Exception: st.metric("Fed Funds", "N/A")

    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>', unsafe_allow_html=True)
