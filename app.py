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
FRED_KEY    = st.secrets["FRED_API_KEY"]
FINNHUB_KEY = st.secrets["FINNHUB_API_KEY"]
fred        = fredapi.Fred(api_key=FRED_KEY)

# ─── CONSTANTS ─────────────────────────────────────────────────────────────────
START = "2015-01-01"
BENCH = "SPY"
ROLL  = 126  # 6-month rolling window

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

# FOMC meeting dates — update annually
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
def fetch_fred(series_id, start=START):
    s = fred.get_series(series_id, observation_start=start)
    s.index = pd.to_datetime(s.index)
    return s.dropna()

@st.cache_data(ttl=3600)
def fetch_equity():
    tickers = list(FACTORS.keys()) + list(SECTORS.keys()) + [BENCH]
    raw = yf.download(tickers, start=START, auto_adjust=True, progress=False)
    return raw["Close"]

@st.cache_data(ttl=3600)
def fetch_calendar():
    today = datetime.today()
    params = {
        "token": FINNHUB_KEY,
        "from":  (today - timedelta(days=7)).strftime("%Y-%m-%d"),
        "to":    (today + timedelta(days=45)).strftime("%Y-%m-%d"),
    }
    r = requests.get("https://finnhub.io/api/v1/calendar/economic", params=params, timeout=10)
    if r.status_code != 200:
        return pd.DataFrame()
    events = r.json().get("economicCalendar", [])
    df = pd.DataFrame(events)
    if df.empty:
        return df
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df[df.get("country", pd.Series(dtype=str)) == "US"].sort_values("time")
    return df[["time", "event", "estimate", "prev", "actual", "unit"]].reset_index(drop=True)

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def to_yoy(s):
    return s.pct_change(12) * 100

def trim(s, months):
    if months:
        return s[s.index >= s.index.max() - pd.DateOffset(months=months)]
    return s

def compute_relative(prices, asset_dict):
    rel   = prices[list(asset_dict.keys())].div(prices[BENCH], axis=0)
    alpha = (1 + rel.pct_change()).rolling(ROLL).apply(np.prod, raw=True) - 1
    return rel, alpha

def reindex_from(df, base_date):
    df = df[df.index >= pd.Timestamp(base_date)]
    return df / df.iloc[0]

def yield_curve_fig():
    maturities = {
        "DGS1MO": "1M", "DGS3MO": "3M", "DGS6MO": "6M",
        "DGS1": "1Y", "DGS2": "2Y", "DGS5": "5Y",
        "DGS10": "10Y", "DGS20": "20Y", "DGS30": "30Y"
    }
    vals, labels = [], []
    for sid, lbl in maturities.items():
        try:
            s = fetch_fred(sid, start="2020-01-01")
            vals.append(round(s.iloc[-1], 3))
            labels.append(lbl)
        except Exception:
            pass
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=vals, mode="lines+markers",
                             line=dict(color="#1f77b4", width=2.5),
                             marker=dict(size=8)))
    fig.update_layout(title="<b>Current Yield Curve</b>", template="plotly_white",
                      height=360, yaxis_title="Yield (%)", xaxis_title="Maturity")
    return fig

# ─── PAGE HEADER ───────────────────────────────────────────────────────────────

st.title("📊 Macro Dashboard")
st.caption(f"Refreshed: {datetime.now().strftime('%b %d, %Y  %H:%M')}  •  Data: FRED · Yahoo Finance · Finnhub")

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
        ("DGS2",      "2Y Treasury",    True,  "%"),
        ("DGS10",     "10Y Treasury",   True,  "%"),
        ("DGS30",     "30Y Treasury",   True,  "%"),
        ("FEDFUNDS",  "Fed Funds Rate", False, "%"),
        ("CPIAUCSL",  "CPI YoY",        True,  "%"),   # converted below
        ("T10Y2Y",    "10Y–2Y Spread",  True,  "%"),
    ]
    for i, (sid, label, show_delta, unit) in enumerate(snapshot):
        try:
            s = to_yoy(fetch_fred(sid)) if sid == "CPIAUCSL" else fetch_fred(sid)
            cur, prev = s.iloc[-1], s.iloc[-2]
            delta = f"{cur - prev:+.2f}{unit}" if show_delta else None
            c[i].metric(label, f"{cur:.2f}{unit}", delta)
        except Exception:
            c[i].metric(label, "N/A")

    st.divider()
    col_l, col_r = st.columns(2)

    with col_l:
        st.plotly_chart(yield_curve_fig(), use_container_width=True)

    with col_r:
        st.subheader("Upcoming Releases")
        try:
            cal = fetch_calendar()
            today_ts = pd.Timestamp.today().normalize()
            upcoming = cal[cal["time"] >= today_ts].head(10)
            if not upcoming.empty:
                disp = upcoming.copy()
                disp["Date"]  = disp["time"].dt.strftime("%b %d")
                disp = disp.rename(columns={"event": "Event", "estimate": "Est.",
                                             "prev": "Prev", "actual": "Actual"})
                st.dataframe(disp[["Date", "Event", "Prev", "Est.", "Actual"]],
                             hide_index=True, use_container_width=True)
        except Exception:
            st.info("Calendar unavailable.")

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

    # ── Factors ──
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
    st.plotly_chart(fig_f, use_container_width=True)

    st.divider()

    # ── Sectors ──
    st.subheader("Sector ETF Performance vs S&P 500")
    ps   = st.radio("Period", list(period_opts.keys()), horizontal=True, key="ps")
    base_s = period_opts[ps] or (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d")

    rel_s, alpha_s = compute_relative(prices, SECTORS)
    ri_s  = reindex_from(rel_s, base_s)
    al_s  = alpha_s[alpha_s.index >= pd.Timestamp(base_s)]
    disp  = ri_s.max(axis=1) - ri_s.min(axis=1)

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
    st.plotly_chart(fig_s, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RATES
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    rp    = st.radio("Period", ["1Y", "3Y", "5Y", "10Y", "Full"], horizontal=True)
    rmons = {"1Y": 12, "3Y": 36, "5Y": 60, "10Y": 120, "Full": None}[rp]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

    # Treasury yield lines
    st.subheader("Treasury Yields by Maturity")
    fig_y = go.Figure()
    for i, (sid, lbl) in enumerate(YIELDS.items()):
        try:
            s = trim(fetch_fred(sid), rmons)
            fig_y.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl,
                                       mode="lines", line=dict(color=colors[i], width=2)))
        except Exception:
            pass
    fig_y.update_layout(template="plotly_white", height=380, yaxis_title="Yield (%)")
    st.plotly_chart(fig_y, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Yield Curve Spreads")
        fig_sp = go.Figure()
        for sid, lbl in SPREADS.items():
            try:
                s = trim(fetch_fred(sid), rmons)
                fig_sp.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_sp.add_hline(y=0, line_dash="dash", line_color="red", line_width=1)
        fig_sp.update_layout(template="plotly_white", height=360, yaxis_title="Spread (%)")
        st.plotly_chart(fig_sp, use_container_width=True)

    with col2:
        st.subheader("Real Yield & Breakeven Inflation")
        fig_rv = go.Figure()
        for sid, lbl in [("DFII10", "10Y Real Yield"), ("T10YIE", "10Y Breakeven Infl.")]:
            try:
                s = trim(fetch_fred(sid), rmons)
                fig_rv.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_rv.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig_rv.update_layout(template="plotly_white", height=360, yaxis_title="%")
        st.plotly_chart(fig_rv, use_container_width=True)

    st.plotly_chart(yield_curve_fig(), use_container_width=True)

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
                s = trim(to_yoy(fetch_fred(sid)), mmon)
                fig_cpi.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_cpi.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="Fed 2% target", annotation_position="bottom right")
        fig_cpi.update_layout(template="plotly_white", height=360, yaxis_title="YoY %")
        st.plotly_chart(fig_cpi, use_container_width=True)

    with col_b:
        st.subheader("PCE & Core PCE (YoY %)")
        fig_pce = go.Figure()
        for sid, lbl in [("PCEPI", "PCE"), ("PCEPILFE", "Core PCE")]:
            try:
                s = trim(to_yoy(fetch_fred(sid)), mmon)
                fig_pce.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_pce.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="Fed 2% target", annotation_position="bottom right")
        fig_pce.update_layout(template="plotly_white", height=360, yaxis_title="YoY %")
        st.plotly_chart(fig_pce, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.subheader("Fed Funds Rate & Unemployment")
        fig_ff = go.Figure()
        for sid, lbl, col in [("FEDFUNDS", "Fed Funds Rate", "#1f77b4"),
                               ("UNRATE",   "Unemployment",   "#ff7f0e")]:
            try:
                s = trim(fetch_fred(sid), mmon)
                fig_ff.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl,
                                            mode="lines", line=dict(color=col, width=2)))
            except Exception:
                pass
        fig_ff.update_layout(template="plotly_white", height=360, yaxis_title="%")
        st.plotly_chart(fig_ff, use_container_width=True)

    with col_d:
        st.subheader("Real GDP Growth (QoQ Annualized %)")
        try:
            # A191RL1Q225SBEA = real GDP growth rate, SAAR
            gdp = trim(fetch_fred("A191RL1Q225SBEA"), mmon)
            fig_gdp = go.Figure()
            fig_gdp.add_trace(go.Bar(
                x=gdp.index, y=gdp.values, name="GDP Growth",
                marker_color=["#2ca02c" if v >= 0 else "#d62728" for v in gdp.values]
            ))
            fig_gdp.add_hline(y=0, line_color="black", line_width=1)
            fig_gdp.update_layout(template="plotly_white", height=360, yaxis_title="% QoQ Ann.")
            st.plotly_chart(fig_gdp, use_container_width=True)
        except Exception:
            st.info("GDP data unavailable.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    col_cal, col_fomc = st.columns([3, 1])

    with col_cal:
        st.subheader("US Economic Releases")
        st.caption("Past 7 days and next 45 days  •  Yellow = today  •  Gray = past")
        try:
            cal = fetch_calendar()
            if not cal.empty:
                today_ts = pd.Timestamp.today().normalize()

                def row_style(row):
                    if row["time"].normalize() == today_ts:
                        return ["background-color: #fff3cd"] * len(row)
                    if row["time"] < today_ts:
                        return ["color: #aaaaaa"]        * len(row)
                    return [""] * len(row)

                disp = cal.copy()
                disp["Date"] = disp["time"].dt.strftime("%b %d, %Y")
                disp["Time"] = disp["time"].dt.strftime("%H:%M")
                disp = disp.rename(columns={"event": "Event", "estimate": "Estimate",
                                             "prev": "Previous", "actual": "Actual",
                                             "unit": "Unit"})
                st.dataframe(
                    disp[["Date", "Time", "Event", "Previous", "Estimate", "Actual", "Unit"]]
                    .style.apply(row_style, axis=1),
                    hide_index=True, use_container_width=True, height=600
                )
            else:
                st.info("No calendar data returned. Check your Finnhub API key.")
        except Exception as e:
            st.error(f"Calendar error: {e}")

    with col_fomc:
        st.subheader("FOMC Dates")
        today_d = datetime.today().date()
        for year, meetings in FOMC.items():
            st.caption(f"**{year}**")
            for lbl, d in meetings:
                mtg_d  = datetime.strptime(d, "%Y-%m-%d").date()
                days   = (mtg_d - today_d).days
                if days > 0:
                    st.markdown(f"🔵 **{lbl}** — *{days}d*")
                elif days == 0:
                    st.markdown(f"🟡 **{lbl}** — *today*")
                else:
                    st.markdown(f"✅ ~~{lbl}~~")

        st.divider()
        st.caption("**Current Fed Funds Rate**")
        try:
            ff = fetch_fred("FEDFUNDS")
            st.metric("Fed Funds", f"{ff.iloc[-1]:.2f}%")
        except Exception:
            st.metric("Fed Funds", "N/A")