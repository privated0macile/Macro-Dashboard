import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta
import fredapi

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Macro Dashboard", layout="wide", page_icon="📊")
st.markdown("""
<style>
div[data-testid="metric-container"] {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    padding: 10px 16px;
    border-radius: 8px;
}
.stTabs [data-baseweb="tab"] { font-size: 15px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ─── SECRETS ───────────────────────────────────────────────────────────────────
FRED_KEY = st.secrets["FRED_API_KEY"]
FMP_KEY  = st.secrets["FMP_API_KEY"]
fred     = fredapi.Fred(api_key=FRED_KEY)

# ─── CONSTANTS ─────────────────────────────────────────────────────────────────
START = "2015-01-01"
BENCH = "SPY"
ROLL  = 126

FACTORS = {
    "MTUM": "Momentum", "QUAL": "Quality", "SIZE": "Size",
    "VLUE": "Value",    "USMV": "Min Vol"
}
SECTORS = {
    "XLK": "Technology",    "XLF": "Financials",      "XLE": "Energy",
    "XLV": "Healthcare",    "XLI": "Industrials",     "XLY": "Cons. Disc.",
    "XLP": "Cons. Staples", "XLB": "Materials",       "XLU": "Utilities",
    "XLRE": "Real Estate"
}
YIELDS  = {"DGS2": "2Y", "DGS5": "5Y", "DGS10": "10Y", "DGS30": "30Y"}
SPREADS = {"T10Y2Y": "10Y–2Y Spread", "T10Y3M": "10Y–3M Spread"}
CREDIT  = {"BAMLH0A0HYM2": "HY OAS", "BAMLC0A0CM": "IG OAS"}

# Key releases to show in macro snapshot table
KEY_RELEASES = [
    ("Nonfarm Payrolls",      "PAYEMS",         "000s MoM",  "diff"),
    ("Unemployment Rate",     "UNRATE",          "%",         "level"),
    ("CPI YoY",               "CPIAUCSL",        "% YoY",     "yoy"),
    ("Core CPI YoY",          "CPILFESL",        "% YoY",     "yoy"),
    ("PCE YoY",               "PCEPI",           "% YoY",     "yoy"),
    ("Core PCE YoY",          "PCEPILFE",        "% YoY",     "yoy"),
    ("GDP Growth QoQ Ann.",   "A191RL1Q225SBEA", "% Ann.",    "level"),
    ("Retail Sales MoM",      "RSAFS",           "% MoM",     "mom"),
    ("Industrial Production", "INDPRO",          "% MoM",     "mom"),
    ("Fed Funds Rate",        "FEDFUNDS",        "%",         "level"),
    ("10Y–2Y Spread",         "T10Y2Y",          "%",         "level"),
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

# ─── DATA FETCHERS ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_fred_series(series_id, start=START):
    s = fred.get_series(series_id, observation_start=start)
    s.index = pd.to_datetime(s.index)
    return s.dropna()

@st.cache_data(ttl=3600)
def fetch_equity():
    tickers = list(FACTORS.keys()) + list(SECTORS.keys()) + [BENCH]
    raw = yf.download(tickers, start=START, auto_adjust=True, progress=False)
    return raw["Close"]

@st.cache_data(ttl=1800)
def fetch_fmp_calendar(date_from, date_to):
    url = (
        f"https://financialmodelingprep.com/api/v3/economic_calendar"
        f"?from={date_from}&to={date_to}&apikey={FMP_KEY}"
    )
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        return pd.DataFrame()
    data = r.json()
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df = df[df.get("country", pd.Series(dtype=str)) == "US"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date")
    return df.reset_index(drop=True)

@st.cache_data(ttl=3600)
def fetch_release_snapshot():
    rows = []
    for name, sid, unit, calc in KEY_RELEASES:
        try:
            s = fetch_fred_series(sid, start="2022-01-01")
            if len(s) < 2:
                continue
            last_val = s.iloc[-1]
            prev_val = s.iloc[-2]
            last_date = s.index[-1].strftime("%b %d, %Y")
            if calc == "yoy":
                sy = s.pct_change(12) * 100
                last_val, prev_val = round(sy.iloc[-1], 2), round(sy.iloc[-2], 2)
            elif calc == "mom":
                sm = s.pct_change() * 100
                last_val, prev_val = round(sm.iloc[-1], 2), round(sm.iloc[-2], 2)
            elif calc == "diff":
                last_val = round(s.diff().iloc[-1], 1)
                prev_val = round(s.diff().iloc[-2], 1)
            else:
                last_val, prev_val = round(last_val, 2), round(prev_val, 2)

            # next release date via FRED API
            next_date = "—"
            try:
                today_str = datetime.today().strftime("%Y-%m-%d")
                to_str    = (datetime.today() + timedelta(days=60)).strftime("%Y-%m-%d")
                rel_r = requests.get(
                    f"https://api.stlouisfed.org/fred/series/release"
                    f"?series_id={sid}&api_key={FRED_KEY}&file_type=json", timeout=5
                )
                if rel_r.status_code == 200:
                    rel_id = rel_r.json()["releases"][0]["id"]
                    dates_r = requests.get(
                        f"https://api.stlouisfed.org/fred/release/dates"
                        f"?release_id={rel_id}&api_key={FRED_KEY}&file_type=json"
                        f"&realtime_start={today_str}&realtime_end={to_str}"
                        f"&include_release_dates_with_no_data=true", timeout=5
                    )
                    if dates_r.status_code == 200:
                        future = [
                            d["date"] for d in dates_r.json().get("release_dates", [])
                            if d["date"] >= today_str
                        ]
                        if future:
                            next_date = pd.Timestamp(future[0]).strftime("%b %d, %Y")
            except Exception:
                pass

            rows.append({
                "Release":      name,
                "Last Updated": last_date,
                "Previous":     prev_val,
                "Latest":       last_val,
                "Unit":         unit,
                "Next Release": next_date,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def to_yoy(s):   return s.pct_change(12) * 100
def to_mom(s):   return s.pct_change() * 100

def trim(s, months):
    return s[s.index >= s.index.max() - pd.DateOffset(months=months)] if months else s

def compute_relative(prices, asset_dict):
    rel   = prices[list(asset_dict.keys())].div(prices[BENCH], axis=0)
    alpha = (1 + rel.pct_change()).rolling(ROLL).apply(np.prod, raw=True) - 1
    return rel, alpha

def reindex_from(df, base_date):
    df = df[df.index >= pd.Timestamp(base_date)]
    return df / df.iloc[0]

def build_yield_curve():
    maturities = {
        "DGS1MO": "1M", "DGS3MO": "3M", "DGS6MO": "6M",
        "DGS1": "1Y",   "DGS2": "2Y",   "DGS5": "5Y",
        "DGS10": "10Y", "DGS20": "20Y", "DGS30": "30Y"
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
    fig.add_trace(go.Scatter(x=labels, y=vals, mode="lines+markers",
                             line=dict(color="#1f77b4", width=2.5), marker=dict(size=8)))
    fig.update_layout(title="<b>Current Yield Curve</b>", template="plotly_white",
                      height=360, yaxis_title="Yield (%)", xaxis_title="Maturity")
    return fig

def beat_miss_color(df):
    """Colour the Beat/Miss column green/red/gray."""
    def _style(row):
        styles = [""] * len(row)
        cols = list(row.index)
        if "Beat / Miss" in cols:
            idx = cols.index("Beat / Miss")
            val = str(row["Beat / Miss"])
            if val == "✅ Beat":
                styles[idx] = "color: #2ca02c; font-weight: bold"
            elif val == "❌ Miss":
                styles[idx] = "color: #d62728; font-weight: bold"
            elif val == "➖ In-line":
                styles[idx] = "color: #888888"
        return styles
    return df.style.apply(_style, axis=1)

# ─── PAGE HEADER ───────────────────────────────────────────────────────────────

st.title("📊 Macro Dashboard")
st.caption(f"Refreshed: {datetime.now().strftime('%b %d, %Y  %H:%M')}  •  Data: FRED · Yahoo Finance · FMP")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏠  Overview", "📈  Markets", "📉  Rates", "🌍  Macro", "📅  Calendar"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.subheader("Key Indicators")
    c = st.columns(6)
    snapshot = [
        ("DGS2",     "2Y Treasury",    True,  "%"),
        ("DGS10",    "10Y Treasury",   True,  "%"),
        ("DGS30",    "30Y Treasury",   True,  "%"),
        ("FEDFUNDS", "Fed Funds Rate", False, "%"),
        ("CPIAUCSL", "CPI YoY",        True,  "%"),
        ("T10Y2Y",   "10Y–2Y Spread",  True,  "%"),
    ]
    for i, (sid, label, show_delta, unit) in enumerate(snapshot):
        try:
            s = to_yoy(fetch_fred_series(sid)) if sid == "CPIAUCSL" else fetch_fred_series(sid)
            cur, prev = s.iloc[-1], s.iloc[-2]
            delta = f"{cur - prev:+.2f}{unit}" if show_delta else None
            c[i].metric(label, f"{cur:.2f}{unit}", delta)
        except Exception:
            c[i].metric(label, "N/A")

    st.divider()

    # ── Credit spread snapshot ──
    st.subheader("Credit Spreads (OAS, bps)")
    cc = st.columns(3)
    credit_snap = [
        ("BAMLH0A0HYM2", "HY OAS"),
        ("BAMLC0A0CM",   "IG OAS"),
    ]
    hy_val, ig_val = None, None
    for i, (sid, label) in enumerate(credit_snap):
        try:
            s = fetch_fred_series(sid)
            cur, prev = s.iloc[-1], s.iloc[-2]
            if label == "HY OAS": hy_val = cur
            if label == "IG OAS": ig_val = cur
            cc[i].metric(label, f"{cur:.0f} bps", f"{cur - prev:+.0f} bps")
        except Exception:
            cc[i].metric(label, "N/A")
    if hy_val and ig_val:
        gap = hy_val - ig_val
        try:
            hy_s = fetch_fred_series("BAMLH0A0HYM2")
            ig_s = fetch_fred_series("BAMLC0A0CM")
            prev_gap = hy_s.iloc[-2] - ig_s.iloc[-2]
            cc[2].metric("HY–IG Gap", f"{gap:.0f} bps", f"{gap - prev_gap:+.0f} bps")
        except Exception:
            cc[2].metric("HY–IG Gap", f"{gap:.0f} bps")

    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        st.plotly_chart(build_yield_curve(), use_container_width=True, key="yc_overview")

    with col_r:
        st.subheader("Upcoming Key Releases")
        try:
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(
                    snap[["Release", "Next Release", "Latest", "Unit"]].head(8),
                    hide_index=True, use_container_width=True
                )
        except Exception:
            st.info("Release data unavailable.")

    st.subheader("Next FOMC Meeting")
    all_fomc = FOMC["2025"] + FOMC["2026"]
    today_d  = datetime.today().date()
    nxt = next(((l, d) for l, d in all_fomc
                if datetime.strptime(d, "%Y-%m-%d").date() >= today_d), None)
    if nxt:
        lbl, d = nxt
        days_away = (datetime.strptime(d, "%Y-%m-%d").date() - today_d).days
        st.info(f"**{lbl}** — {days_away} days away")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MARKETS
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    with st.spinner("Loading equity data…"):
        prices = fetch_equity()

    period_opts = {
        "Since 2015": "2015-01-01", "Since 2020": "2020-01-01",
        "Since 2025": "2025-01-01", "Past 12M":   None
    }

    st.subheader("MSCI Factor Performance vs S&P 500")
    pf   = st.radio("Period", list(period_opts.keys()), horizontal=True, key="pf")
    base = period_opts[pf] or (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d")

    rel_f, alpha_f = compute_relative(prices, FACTORS)
    ri_f = reindex_from(rel_f, base)
    al_f = alpha_f[alpha_f.index >= pd.Timestamp(base)]

    fig_f = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                          subplot_titles=("Relative Performance vs SPY (indexed to 1.0)",
                                          "Rolling 6-Month Relative Alpha"))
    for tkr, name in FACTORS.items():
        if tkr in ri_f.columns:
            fig_f.add_trace(go.Scatter(x=ri_f.index, y=ri_f[tkr], name=name, mode="lines"), row=1, col=1)
        if tkr in al_f.columns:
            fig_f.add_trace(go.Scatter(x=al_f.index, y=al_f[tkr], name=name, mode="lines",
                                       showlegend=False), row=2, col=1)
    fig_f.add_hline(y=1.0, line_dash="dash", line_color="gray", row=1, col=1)
    fig_f.add_hline(y=0.0, line_dash="dash", line_color="gray", row=2, col=1)
    fig_f.update_layout(template="plotly_white", height=580,
                        legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig_f, use_container_width=True, key="fig_factors")

    st.divider()

    st.subheader("Sector ETF Performance vs S&P 500")
    ps     = st.radio("Period", list(period_opts.keys()), horizontal=True, key="ps")
    base_s = period_opts[ps] or (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d")

    rel_s, alpha_s = compute_relative(prices, SECTORS)
    ri_s = reindex_from(rel_s, base_s)
    al_s = alpha_s[alpha_s.index >= pd.Timestamp(base_s)]
    disp = ri_s.max(axis=1) - ri_s.min(axis=1)

    fig_s = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                          subplot_titles=("Relative Performance vs SPY (indexed to 1.0)",
                                          "Rolling 6-Month Relative Alpha",
                                          "Cross-Sectional Dispersion (max − min)"))
    for tkr, name in SECTORS.items():
        if tkr in ri_s.columns:
            fig_s.add_trace(go.Scatter(x=ri_s.index, y=ri_s[tkr], name=name, mode="lines"), row=1, col=1)
        if tkr in al_s.columns:
            fig_s.add_trace(go.Scatter(x=al_s.index, y=al_s[tkr], name=name, mode="lines",
                                       showlegend=False), row=2, col=1)
    fig_s.add_trace(go.Scatter(x=disp.index, y=disp, mode="lines", name="Dispersion",
                               line=dict(color="#888", width=2), showlegend=False), row=3, col=1)
    fig_s.add_hline(y=1.0, line_dash="dash", line_color="gray", row=1, col=1)
    fig_s.add_hline(y=0.0, line_dash="dash", line_color="gray", row=2, col=1)
    fig_s.update_layout(template="plotly_white", height=760,
                        legend=dict(orientation="h", y=-0.1))
    st.plotly_chart(fig_s, use_container_width=True, key="fig_sectors")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RATES
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    rp    = st.radio("Period", ["1Y", "3Y", "5Y", "10Y", "Full"], horizontal=True, key="rp")
    rmons = {"1Y": 12, "3Y": 36, "5Y": 60, "10Y": 120, "Full": None}[rp]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

    st.subheader("Treasury Yields by Maturity")
    fig_y = go.Figure()
    for i, (sid, lbl) in enumerate(YIELDS.items()):
        try:
            s = trim(fetch_fred_series(sid), rmons)
            fig_y.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl,
                                       mode="lines", line=dict(color=colors[i], width=2)))
        except Exception:
            pass
    fig_y.update_layout(template="plotly_white", height=380, yaxis_title="Yield (%)")
    st.plotly_chart(fig_y, use_container_width=True, key="fig_yields")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Yield Curve Spreads")
        fig_sp = go.Figure()
        for sid, lbl in SPREADS.items():
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_sp.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_sp.add_hline(y=0, line_dash="dash", line_color="red", line_width=1)
        fig_sp.update_layout(template="plotly_white", height=360, yaxis_title="Spread (%)")
        st.plotly_chart(fig_sp, use_container_width=True, key="fig_spreads")

    with col2:
        st.subheader("Real Yield & Breakeven Inflation")
        fig_rv = go.Figure()
        for sid, lbl in [("DFII10", "10Y Real Yield"), ("T10YIE", "10Y Breakeven Infl.")]:
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_rv.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_rv.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig_rv.update_layout(template="plotly_white", height=360, yaxis_title="%")
        st.plotly_chart(fig_rv, use_container_width=True, key="fig_realyield")

    st.plotly_chart(build_yield_curve(), use_container_width=True, key="yc_rates")

    st.divider()
    st.subheader("Credit Spreads (OAS, bps)")
    fig_cr = go.Figure()
    for sid, lbl in CREDIT.items():
        try:
            s = trim(fetch_fred_series(sid), rmons)
            fig_cr.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
        except Exception:
            pass
    # HY–IG gap
    try:
        hy = trim(fetch_fred_series("BAMLH0A0HYM2"), rmons)
        ig = trim(fetch_fred_series("BAMLC0A0CM"),   rmons)
        gap = hy - ig
        gap = gap.dropna()
        fig_cr.add_trace(go.Scatter(x=gap.index, y=gap.values, name="HY–IG Gap",
                                    mode="lines", line=dict(dash="dot", width=1.5)))
    except Exception:
        pass
    fig_cr.update_layout(template="plotly_white", height=380,
                         yaxis_title="OAS (bps)",
                         annotations=[dict(
                             text="Source: ICE BofA via FRED",
                             xref="paper", yref="paper",
                             x=1, y=-0.12, showarrow=False,
                             font=dict(size=11, color="#888"), xanchor="right"
                         )])
    st.plotly_chart(fig_cr, use_container_width=True, key="fig_credit")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MACRO
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    mp   = st.radio("Period", ["2Y", "5Y", "10Y", "Full"], horizontal=True, key="mp")
    mmon = {"2Y": 24, "5Y": 60, "10Y": 120, "Full": None}[mp]

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("CPI & Core CPI (YoY %)")
        fig_cpi = go.Figure()
        for sid, lbl in [("CPIAUCSL", "CPI"), ("CPILFESL", "Core CPI")]:
            try:
                s = trim(to_yoy(fetch_fred_series(sid)), mmon)
                fig_cpi.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_cpi.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="Fed 2% target", annotation_position="bottom right")
        fig_cpi.update_layout(template="plotly_white", height=360, yaxis_title="YoY %")
        st.plotly_chart(fig_cpi, use_container_width=True, key="fig_cpi")

    with col_b:
        st.subheader("PCE & Core PCE (YoY %)")
        fig_pce = go.Figure()
        for sid, lbl in [("PCEPI", "PCE"), ("PCEPILFE", "Core PCE")]:
            try:
                s = trim(to_yoy(fetch_fred_series(sid)), mmon)
                fig_pce.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_pce.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="Fed 2% target", annotation_position="bottom right")
        fig_pce.update_layout(template="plotly_white", height=360, yaxis_title="YoY %")
        st.plotly_chart(fig_pce, use_container_width=True, key="fig_pce")

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Fed Funds Rate & Unemployment")
        fig_ff = go.Figure()
        for sid, lbl, col in [("FEDFUNDS", "Fed Funds Rate", "#1f77b4"),
                               ("UNRATE",   "Unemployment",   "#ff7f0e")]:
            try:
                s = trim(fetch_fred_series(sid), mmon)
                fig_ff.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl,
                                            mode="lines", line=dict(color=col, width=2)))
            except Exception:
                pass
        fig_ff.update_layout(template="plotly_white", height=360, yaxis_title="%")
        st.plotly_chart(fig_ff, use_container_width=True, key="fig_fedfunds")

    with col_d:
        st.subheader("Real GDP Growth (QoQ Annualized %)")
        try:
            gdp = trim(fetch_fred_series("A191RL1Q225SBEA"), mmon)
            fig_gdp = go.Figure()
            fig_gdp.add_trace(go.Bar(
                x=gdp.index, y=gdp.values, name="GDP Growth",
                marker_color=["#2ca02c" if v >= 0 else "#d62728" for v in gdp.values]
            ))
            fig_gdp.add_hline(y=0, line_color="black", line_width=1)
            fig_gdp.update_layout(template="plotly_white", height=360, yaxis_title="% QoQ Ann.")
            st.plotly_chart(fig_gdp, use_container_width=True, key="fig_gdp")
        except Exception:
            st.info("GDP data unavailable.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    today      = datetime.today()
    today_str  = today.strftime("%Y-%m-%d")
    past_str   = (today - timedelta(days=35)).strftime("%Y-%m-%d")
    future_str = (today + timedelta(days=45)).strftime("%Y-%m-%d")

    with st.spinner("Loading calendar data…"):
        cal_past   = fetch_fmp_calendar(past_str,  today_str)
        cal_future = fetch_fmp_calendar(today_str, future_str)

    col_left, col_right = st.columns([3, 1])

    with col_left:

        # ── TABLE 1: UPCOMING ──────────────────────────────────────────────
        st.subheader("📅 Upcoming Releases")
        st.caption("Next 45 days  •  Consensus estimates where available")

        if not cal_future.empty:
            up = cal_future.copy()
            up = up[up["actual"].isna() | (up["actual"] == "")]
            up["Date"]      = up["date"].dt.strftime("%b %d, %Y")
            up["Event"]     = up.get("event",    "")
            up["Estimate"]  = up.get("estimate", pd.Series(dtype=float))
            up["Previous"]  = up.get("previous", pd.Series(dtype=float))
            up["Unit"]      = up.get("unit",     "")

            display_up = up[["Date", "Event", "Estimate", "Previous", "Unit"]].copy()
            display_up = display_up[display_up["Event"].str.strip() != ""]
            display_up = display_up.reset_index(drop=True)

            st.dataframe(display_up, hide_index=True, use_container_width=True, height=380)
        else:
            st.info("No upcoming release data available.")

        st.divider()

        # ── TABLE 2: PAST RELEASES ─────────────────────────────────────────
        st.subheader("📋 Past Releases — Last 35 Days")
        st.caption("Actual vs consensus estimate  •  Beat ✅  Miss ❌  In-line ➖")

        if not cal_past.empty:
            ps = cal_past.copy()
            ps = ps[ps["actual"].notna() & (ps["actual"] != "")]
            ps["Date"]     = ps["date"].dt.strftime("%b %d, %Y")
            ps["Event"]    = ps.get("event",    "")
            ps["Actual"]   = pd.to_numeric(ps.get("actual",   None), errors="coerce")
            ps["Estimate"] = pd.to_numeric(ps.get("estimate", None), errors="coerce")
            ps["Previous"] = pd.to_numeric(ps.get("previous", None), errors="coerce")
            ps["Unit"]     = ps.get("unit", "")

            # MoM % change: actual vs previous
            ps["MoM Chg"] = np.where(
                ps["Previous"].notna() & (ps["Previous"] != 0),
                ((ps["Actual"] - ps["Previous"]) / ps["Previous"].abs() * 100).round(2),
                np.nan
            )
            ps["MoM Chg"] = ps["MoM Chg"].apply(
                lambda x: f"{x:+.2f}%" if pd.notna(x) else "—"
            )

            # Beat / Miss vs estimate
            def beat_miss(row):
                try:
                    a, e = float(row["Actual"]), float(row["Estimate"])
                    diff = abs(a - e)
                    threshold = abs(e) * 0.02 if e != 0 else 0.05
                    if diff <= threshold:  return "➖ In-line"
                    return "✅ Beat" if a > e else "❌ Miss"
                except Exception:
                    return "—"
            ps["Beat / Miss"] = ps.apply(beat_miss, axis=1)

            display_ps = ps[["Date", "Event", "Previous", "Estimate",
                              "Actual", "MoM Chg", "Beat / Miss", "Unit"]].copy()
            display_ps = display_ps[display_ps["Event"].str.strip() != ""]
            display_ps = display_ps.sort_values("Date", ascending=False).reset_index(drop=True)

            st.dataframe(
                beat_miss_color(display_ps),
                hide_index=True, use_container_width=True, height=500
            )
        else:
            st.info("No recent release data available.")

    # ── FOMC SIDEBAR ──────────────────────────────────────────────────────
    with col_right:
        st.subheader("FOMC Dates")
        today_d = datetime.today().date()
        for year, meetings in FOMC.items():
            st.caption(f"**{year}**")
            for lbl, d in meetings:
                mtg_d = datetime.strptime(d, "%Y-%m-%d").date()
                days  = (mtg_d - today_d).days
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
