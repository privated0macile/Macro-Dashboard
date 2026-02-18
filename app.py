import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests, json
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

KEY_RELEASES = [
    ("Nonfarm Payrolls",      "PAYEMS",          "000s MoM", "diff"),
    ("Unemployment Rate",     "UNRATE",          "%",        "level"),
    ("CPI YoY",               "CPIAUCSL",        "% YoY",    "yoy"),
    ("Core CPI YoY",          "CPILFESL",        "% YoY",    "yoy"),
    ("PCE YoY",               "PCEPI",           "% YoY",    "yoy"),
    ("Core PCE YoY",          "PCEPILFE",        "% YoY",    "yoy"),
    ("GDP Growth QoQ Ann.",   "A191RL1Q225SBEA", "% Ann.",   "level"),
    ("Retail Sales MoM",      "RSAFS",           "% MoM",    "mom"),
    ("Industrial Production", "INDPRO",          "% MoM",    "mom"),
    ("Fed Funds Rate",        "FEDFUNDS",        "%",        "level"),
    ("10Y–2Y Spread",         "T10Y2Y",          "%",        "level"),
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
                last_val = round(s.diff().iloc[-1], 1)
                prev_val = round(s.diff().iloc[-2], 1)
            else:
                last_val, prev_val = round(last_val, 2), round(prev_val, 2)
            next_date = "—"
            try:
                today_str = datetime.today().strftime("%Y-%m-%d")
                to_str    = (datetime.today() + timedelta(days=60)).strftime("%Y-%m-%d")
                rel_r = requests.get(
                    f"https://api.stlouisfed.org/fred/series/release"
                    f"?series_id={sid}&api_key={FRED_KEY}&file_type=json", timeout=5)
                if rel_r.status_code == 200:
                    rel_id = rel_r.json()["releases"][0]["id"]
                    dates_r = requests.get(
                        f"https://api.stlouisfed.org/fred/release/dates"
                        f"?release_id={rel_id}&api_key={FRED_KEY}&file_type=json"
                        f"&realtime_start={today_str}&realtime_end={to_str}"
                        f"&include_release_dates_with_no_data=true", timeout=5)
                    if dates_r.status_code == 200:
                        future = [d["date"] for d in dates_r.json().get("release_dates", [])
                                  if d["date"] >= today_str]
                        if future:
                            next_date = pd.Timestamp(future[0]).strftime("%b %d, %Y")
            except Exception:
                pass
            rows.append({"Release": name, "Last Updated": last_date,
                         "Previous": prev_val, "Latest": last_val,
                         "Unit": unit, "Next Release": next_date})
        except Exception:
            continue
    return pd.DataFrame(rows)

@st.cache_data(ttl=1800)
def fetch_fred_calendar():
    """Pull upcoming + recent release dates directly from FRED."""
    today    = datetime.today()
    past_str = (today - timedelta(days=35)).strftime("%Y-%m-%d")
    fut_str  = (today + timedelta(days=45)).strftime("%Y-%m-%d")
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

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def to_yoy(s): return s.pct_change(12) * 100

def trim(s, months):
    return s[s.index >= s.index.max() - pd.DateOffset(months=months)] if months else s

def compute_relative(prices, asset_dict):
    rel   = prices[list(asset_dict.keys())].div(prices[BENCH], axis=0)
    alpha = (1 + rel.pct_change()).rolling(ROLL).apply(np.prod, raw=True) - 1
    return rel, alpha

def reindex_from(df, base_date):
    df = df[df.index >= pd.Timestamp(base_date)]
    return df / df.iloc[0]

def src_ann(y=-0.13):
    """Italic source annotation bottom-right with extra padding."""
    return dict(
        text="<i>Source: FRED / Yahoo Finance</i>",
        xref="paper", yref="paper",
        x=1.0, y=y, showarrow=False,
        font=dict(size=10, color="#888888"), xanchor="right"
    )

def chart_title(main, sub):
    """Returns a plotly-formatted two-line title string."""
    return f"<b>{main}</b><br><sup style='color:#888;font-weight:normal'>{sub}</sup>"

def yield_curve_commentary():
    try:
        y2  = fetch_fred_series("DGS2").iloc[-1]
        y10 = fetch_fred_series("DGS10").iloc[-1]
        y30 = fetch_fred_series("DGS30").iloc[-1]
        sp  = (fetch_fred_series("DGS10") - fetch_fred_series("DGS2")).dropna()
        spread_now  = sp.iloc[-1]
        spread_prev = sp.iloc[-63] if len(sp) > 63 else sp.iloc[0]
        change = spread_now - spread_prev
        shape  = "inverted" if spread_now < -0.1 else ("flat" if spread_now < 0.1 else "upward sloping")
        trend  = "steepening" if change > 0.1 else ("flattening" if change < -0.1 else "unchanged")
        return (f"Currently **{shape}** — 2Y {y2:.2f}%  ·  10Y {y10:.2f}%  ·  "
                f"30Y {y30:.2f}%  ·  10Y–2Y {spread_now:+.2f}%  ·  {trend} over 3M")
    except Exception:
        return ""

def build_yield_curve():
    maturities = {
        "DGS1MO": "1M", "DGS3MO": "3M", "DGS6MO": "6M",
        "DGS1": "1Y", "DGS2": "2Y", "DGS5": "5Y",
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
    fig.update_layout(
        title=chart_title("Current Yield Curve", "Spot rates 1M–30Y as of latest FRED data"),
        template="plotly_white", height=380,
        yaxis_title="Yield (%)", xaxis_title="Maturity",
        margin=dict(b=70), annotations=[src_ann()]
    )
    return fig

def beat_miss_color(df):
    def _style(row):
        styles = [""] * len(row)
        cols = list(row.index)
        if "Beat / Miss" in cols:
            idx = cols.index("Beat / Miss")
            val = str(row["Beat / Miss"])
            if "Beat"  in val: styles[idx] = "color: #2ca02c; font-weight: bold"
            elif "Miss" in val: styles[idx] = "color: #d62728; font-weight: bold"
            elif "line" in val: styles[idx] = "color: #888888"
        return styles
    return df.style.apply(_style, axis=1)

# ─── PAGE HEADER ───────────────────────────────────────────────────────────────

st.title("📊 Macro Dashboard")
st.caption(f"Refreshed: {datetime.now().strftime('%b %d, %Y  %H:%M')}  •  Data: FRED · Yahoo Finance")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🏠  Overview", "📈  Markets", "📉  Rates", "🌍  Macro", "📅  Calendar"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    ind_col, cred_col = st.columns([3, 1])

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
                s = to_yoy(fetch_fred_series(sid)) if sid == "CPIAUCSL" else fetch_fred_series(sid)
                cur, prev = s.iloc[-1], s.iloc[-2]
                delta = f"{cur - prev:+.2f}{unit} DoD" if show_delta else None
                col.metric(label, f"{cur:.2f}{unit}", delta)
            except Exception:
                col.metric(label, "N/A")

    with cred_col:
        st.subheader("Credit Spreads")
        try:
            hy_s  = fetch_fred_series("BAMLH0A0HYM2")
            ig_s  = fetch_fred_series("BAMLC0A0CM")
            t10_s = fetch_fred_series("DGS10")
            hy_oas, hy_prev = hy_s.iloc[-1], hy_s.iloc[-2]
            ig_oas, ig_prev = ig_s.iloc[-1], ig_s.iloc[-2]
            t10 = t10_s.iloc[-1]
            gap, gap_prev = hy_oas - ig_oas, hy_prev - ig_prev
            st.metric("HY OAS",    f"{hy_oas * 100:.0f} bps",
                      f"{(hy_oas - hy_prev) * 100:+.0f} bps DoD")
            st.metric("HY Yield",  f"{hy_oas + t10:.2f}%",
                      f"{(hy_oas - hy_prev) * 100:+.0f} bps DoD")
            st.metric("IG OAS",    f"{ig_oas * 100:.0f} bps",
                      f"{(ig_oas - ig_prev) * 100:+.0f} bps DoD")
            st.metric("IG Yield",  f"{ig_oas + t10:.2f}%",
                      f"{(ig_oas - ig_prev) * 100:+.0f} bps DoD")
            st.metric("HY–IG Gap", f"{gap * 100:.0f} bps",
                      f"{(gap - gap_prev) * 100:+.0f} bps DoD")
            st.caption("Yield ≈ OAS + 10Y Treasury")
        except Exception:
            st.info("Credit data unavailable.")

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(build_yield_curve(), use_container_width=True, key="yc_overview")
        c = yield_curve_commentary()
        if c: st.caption(c)
    with col_r:
        st.subheader("Upcoming Key Releases")
        try:
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(snap[["Release", "Next Release", "Latest", "Unit"]].head(8),
                             hide_index=True, use_container_width=True)
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
        "Since 2025": "2025-01-01", "Past 12M": None
    }

    # ── Factors ──
    st.subheader("MSCI Factors vs S&P 500")
    pf   = st.radio("Period", list(period_opts.keys()), horizontal=True, key="pf")
    base = period_opts[pf] or (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d")

    rel_f, alpha_f = compute_relative(prices, FACTORS)
    ri_f = reindex_from(rel_f, base)
    al_f = alpha_f[alpha_f.index >= pd.Timestamp(base)]

    fig_f = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.16,
                          subplot_titles=[
                              chart_title("Relative Performance vs SPY",
                                          "ETF price ÷ SPY price, indexed to 1.0 at start · above 1.0 = outperforming"),
                              chart_title("Rolling 6-Month Alpha",
                                          "Compounded 126-day return of relative series · positive = outperforming on rolling basis")
                          ])
    for tkr, name in FACTORS.items():
        if tkr in ri_f.columns:
            fig_f.add_trace(go.Scatter(x=ri_f.index, y=ri_f[tkr], name=name, mode="lines"), row=1, col=1)
        if tkr in al_f.columns:
            fig_f.add_trace(go.Scatter(x=al_f.index, y=al_f[tkr], name=name, mode="lines",
                                       showlegend=False), row=2, col=1)
    fig_f.add_hline(y=1.0, line_dash="dash", line_color="gray", row=1, col=1)
    fig_f.add_hline(y=0.0, line_dash="dash", line_color="gray", row=2, col=1)
    for r in [1, 2]:
        fig_f.update_xaxes(showticklabels=True, row=r, col=1)
    fig_f.update_layout(template="plotly_white", height=640,
                        legend=dict(orientation="h", y=-0.06),
                        margin=dict(b=80), annotations=[src_ann(-0.09)])
    st.plotly_chart(fig_f, use_container_width=True, key="fig_factors")

    st.divider()

    # ── Sectors ──
    st.subheader("Sector ETFs vs S&P 500")
    ps     = st.radio("Period", list(period_opts.keys()), horizontal=True, key="ps")
    base_s = period_opts[ps] or (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d")

    rel_s, alpha_s = compute_relative(prices, SECTORS)
    ri_s = reindex_from(rel_s, base_s)
    al_s = alpha_s[alpha_s.index >= pd.Timestamp(base_s)]
    disp = ri_s.max(axis=1) - ri_s.min(axis=1)

    sec_rets   = prices[list(SECTORS.keys())].pct_change().dropna()
    sec_rets_t = sec_rets[sec_rets.index >= pd.Timestamp(base_s)]
    roll_corr  = (
        sec_rets_t.rolling(21).corr()
        .groupby(level=0)
        .apply(lambda x: float(np.nanmean(
            x.values[np.triu_indices_from(x.values, k=1)]
        )))
    )

    fig_s = make_subplots(rows=4, cols=1, shared_xaxes=False, vertical_spacing=0.1,
                          subplot_titles=[
                              chart_title("Relative Performance vs SPY",
                                          "ETF price ÷ SPY price, indexed to 1.0 at start"),
                              chart_title("Rolling 6-Month Alpha",
                                          "Compounded 126-day return of relative series"),
                              chart_title("Cross-Sectional Dispersion",
                                          "max − min of relative prices · higher = more between-sector divergence"),
                              chart_title("Avg Pairwise Sector Correlation (21-day)",
                                          "Higher = sectors moving together (macro-driven) · lower = sector-specific moves")
                          ])
    for tkr, name in SECTORS.items():
        if tkr in ri_s.columns:
            fig_s.add_trace(go.Scatter(x=ri_s.index, y=ri_s[tkr], name=name, mode="lines"), row=1, col=1)
        if tkr in al_s.columns:
            fig_s.add_trace(go.Scatter(x=al_s.index, y=al_s[tkr], name=name, mode="lines",
                                       showlegend=False), row=2, col=1)
    fig_s.add_trace(go.Scatter(x=disp.index, y=disp, mode="lines", showlegend=False,
                               line=dict(color="#555", width=2)), row=3, col=1)
    fig_s.add_trace(go.Scatter(x=roll_corr.index, y=roll_corr.values, mode="lines", showlegend=False,
                               line=dict(color="#e377c2", width=2)), row=4, col=1)
    fig_s.add_hline(y=1.0, line_dash="dash", line_color="gray", row=1, col=1)
    fig_s.add_hline(y=0.0, line_dash="dash", line_color="gray", row=2, col=1)
    for r in [1, 2, 3, 4]:
        fig_s.update_xaxes(showticklabels=True, row=r, col=1)
    fig_s.update_layout(template="plotly_white", height=1020,
                        legend=dict(orientation="h", y=-0.04),
                        margin=dict(b=80), annotations=[src_ann(-0.06)])
    st.plotly_chart(fig_s, use_container_width=True, key="fig_sectors")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RATES
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    rp    = st.radio("Period", ["1Y", "3Y", "5Y", "10Y", "Full"], horizontal=True, key="rp")
    rmons = {"1Y": 12, "3Y": 36, "5Y": 60, "10Y": 120, "Full": None}[rp]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

    fig_y = go.Figure()
    for i, (sid, lbl) in enumerate(YIELDS.items()):
        try:
            s = trim(fetch_fred_series(sid), rmons)
            fig_y.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl,
                                       mode="lines", line=dict(color=colors[i], width=2)))
        except Exception:
            pass
    fig_y.update_layout(
        title=chart_title("Treasury Yields by Maturity", "Daily constant-maturity yields — absolute rate levels"),
        template="plotly_white", height=400, yaxis_title="Yield (%)",
        margin=dict(b=70), annotations=[src_ann()]
    )
    st.plotly_chart(fig_y, use_container_width=True, key="fig_yields")

    col1, col2 = st.columns(2)
    with col1:
        fig_sp = go.Figure()
        for sid, lbl in SPREADS.items():
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_sp.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_sp.add_hline(y=0, line_dash="dash", line_color="red", line_width=1)
        fig_sp.update_layout(
            title=chart_title("Yield Curve Spreads",
                              "10Y–2Y: recession signal · 10Y–3M: Fed preferred · below 0 = inverted"),
            template="plotly_white", height=380, yaxis_title="Spread (%)",
            margin=dict(b=70), annotations=[src_ann()]
        )
        st.plotly_chart(fig_sp, use_container_width=True, key="fig_spreads")

    with col2:
        fig_rv = go.Figure()
        for sid, lbl in [("DFII10", "10Y Real Yield"), ("T10YIE", "10Y Breakeven Infl.")]:
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_rv.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_rv.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
        fig_rv.update_layout(
            title=chart_title("Real Yield & Breakeven Inflation",
                              "Real yield = 10Y TIPS · Breakeven = market-implied inflation expectation"),
            template="plotly_white", height=380, yaxis_title="%",
            margin=dict(b=70), annotations=[src_ann()]
        )
        st.plotly_chart(fig_rv, use_container_width=True, key="fig_realyield")

    c = yield_curve_commentary()
    if c: st.caption(c)
    st.plotly_chart(build_yield_curve(), use_container_width=True, key="yc_rates")

    fig_cr = go.Figure()
    for sid, lbl in CREDIT.items():
        try:
            s = trim(fetch_fred_series(sid), rmons) * 100
            fig_cr.add_trace(go.Scatter(x=s.index, y=s.values, name=f"{lbl} (bps)", mode="lines"))
        except Exception:
            pass
    try:
        hy  = trim(fetch_fred_series("BAMLH0A0HYM2"), rmons)
        ig  = trim(fetch_fred_series("BAMLC0A0CM"),   rmons)
        gap = (hy - ig).dropna() * 100
        fig_cr.add_trace(go.Scatter(x=gap.index, y=gap.values, name="HY–IG Gap (bps)",
                                    mode="lines", line=dict(dash="dot", width=1.5)))
    except Exception:
        pass
    fig_cr.update_layout(
        title=chart_title("Credit Spreads (OAS)",
                          "ICE BofA option-adjusted spread over Treasuries · wider = risk-off"),
        template="plotly_white", height=400, yaxis_title="bps",
        margin=dict(b=70), annotations=[src_ann()]
    )
    st.plotly_chart(fig_cr, use_container_width=True, key="fig_credit")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MACRO
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    mp   = st.radio("Period", ["2Y", "5Y", "10Y", "Full"], horizontal=True, key="mp")
    mmon = {"2Y": 24, "5Y": 60, "10Y": 120, "Full": None}[mp]

    col_a, col_b = st.columns(2)
    with col_a:
        fig_cpi = go.Figure()
        for sid, lbl in [("CPIAUCSL", "CPI"), ("CPILFESL", "Core CPI")]:
            try:
                s = trim(to_yoy(fetch_fred_series(sid)), mmon)
                fig_cpi.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_cpi.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="2% target", annotation_position="bottom right")
        fig_cpi.update_layout(
            title=chart_title("CPI & Core CPI", "YoY % · Core excludes food & energy"),
            template="plotly_white", height=380, yaxis_title="YoY %",
            margin=dict(b=70), annotations=[src_ann()]
        )
        st.plotly_chart(fig_cpi, use_container_width=True, key="fig_cpi")

    with col_b:
        fig_pce = go.Figure()
        for sid, lbl in [("PCEPI", "PCE"), ("PCEPILFE", "Core PCE")]:
            try:
                s = trim(to_yoy(fetch_fred_series(sid)), mmon)
                fig_pce.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_pce.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="2% target", annotation_position="bottom right")
        fig_pce.update_layout(
            title=chart_title("PCE & Core PCE", "YoY % · Fed's preferred inflation gauge"),
            template="plotly_white", height=380, yaxis_title="YoY %",
            margin=dict(b=70), annotations=[src_ann()]
        )
        st.plotly_chart(fig_pce, use_container_width=True, key="fig_pce")

    col_c, col_d = st.columns(2)
    with col_c:
        fig_ff = go.Figure()
        for sid, lbl, col in [("FEDFUNDS", "Fed Funds Rate", "#1f77b4"),
                               ("UNRATE",   "Unemployment",   "#ff7f0e")]:
            try:
                s = trim(fetch_fred_series(sid), mmon)
                fig_ff.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl,
                                            mode="lines", line=dict(color=col, width=2)))
            except Exception:
                pass
        fig_ff.update_layout(
            title=chart_title("Fed Funds Rate & Unemployment", "FOMC policy rate vs U-3 unemployment · dual mandate"),
            template="plotly_white", height=380, yaxis_title="%",
            margin=dict(b=70), annotations=[src_ann()]
        )
        st.plotly_chart(fig_ff, use_container_width=True, key="fig_fedfunds")

    with col_d:
        try:
            gdp = trim(fetch_fred_series("A191RL1Q225SBEA"), mmon)
            fig_gdp = go.Figure()
            fig_gdp.add_trace(go.Bar(
                x=gdp.index, y=gdp.values, name="GDP Growth",
                marker_color=["#2ca02c" if v >= 0 else "#d62728" for v in gdp.values]
            ))
            fig_gdp.add_hline(y=0, line_color="black", line_width=1)
            fig_gdp.update_layout(
                title=chart_title("Real GDP Growth", "QoQ annualized % (SAAR) · two negative quarters = technical recession"),
                template="plotly_white", height=380, yaxis_title="% QoQ Ann.",
                margin=dict(b=70), annotations=[src_ann()]
            )
            st.plotly_chart(fig_gdp, use_container_width=True, key="fig_gdp")
        except Exception:
            st.info("GDP data unavailable.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    col_left, col_right = st.columns([3, 1])

    with col_left:

        # ── Key Release Snapshot ──────────────────────────────────────────
        st.subheader("Key Release Snapshot")
        st.caption("Latest actuals and next scheduled release dates — all via FRED")
        with st.spinner("Loading…"):
            snap = fetch_release_snapshot()
        if not snap.empty:
            def snap_color(row):
                styles = [""] * len(row)
                try:
                    cols = list(row.index)
                    l, p = float(row["Latest"]), float(row["Previous"])
                    idx  = cols.index("Latest")
                    styles[idx] = ("color: #2ca02c; font-weight:bold" if l > p
                                   else "color: #d62728; font-weight:bold" if l < p else "")
                except Exception:
                    pass
                return styles
            st.dataframe(
                snap.style.apply(snap_color, axis=1),
                hide_index=True, use_container_width=True, height=420
            )

        st.divider()

        # ── FRED Release Calendar ─────────────────────────────────────────
        st.subheader("Release Calendar")
        st.caption("All FRED data releases — past 35 days and next 45 days")
        with st.spinner("Loading calendar…"):
            cal = fetch_fred_calendar()

        if cal.empty:
            st.info("No calendar data available.")
        else:
            today_ts = pd.Timestamp.today().normalize()

            def cal_style(row):
                d = row["Date"]
                if pd.Timestamp(d).normalize() == today_ts:
                    return ["background-color: #fff3cd; font-weight:bold"] * len(row)
                if pd.Timestamp(d) < today_ts:
                    return ["color: #aaaaaa"] * len(row)
                return [""] * len(row)

            disp = cal.copy()
            disp["Date"] = disp["Date"].dt.strftime("%b %d, %Y")
            st.dataframe(
                disp.style.apply(cal_style, axis=1),
                hide_index=True, use_container_width=True, height=520
            )

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
