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
INDICES = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "IWM": "Russell 2000"}
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
    tickers = (list(FACTORS.keys()) + list(SECTORS.keys())
               + list(INDICES.keys()) + [BENCH])
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

def compute_volume_zscore(vol_series, lookback=ZSCORE_LOOKBACK):
    rm = vol_series.rolling(lookback, min_periods=20).mean()
    rs = vol_series.rolling(lookback, min_periods=20).std()
    z = (vol_series - rm) / rs
    return z.clip(-3, 3)

def build_volume_chart(ticker, label, prices, volumes, window=CHART_WINDOW):
    if ticker not in prices.columns or ticker not in volumes.columns:
        return None
    p = prices[ticker].dropna()
    v = volumes[ticker].dropna()
    cutoff = p.index[-1] - pd.tseries.offsets.BDay(window)
    p = p[p.index >= cutoff]
    v = v[v.index >= cutoff]
    if len(p) < 10:
        return None
    p_idx = p / p.iloc[0]
    v_full = volumes[ticker].dropna()
    z_full = compute_volume_zscore(v_full)
    z = z_full[z_full.index >= cutoff]
    common = p_idx.index.intersection(z.index)
    p_idx, z = p_idx.loc[common], z.loc[common]
    bar_colors = ["#2ca02c" if val >= 0 else "#d62728" for val in z.values]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=z.index, y=z.values, name="Vol Z-Score",
               marker_color=bar_colors, opacity=0.35, showlegend=True),
        secondary_y=True
    )
    fig.add_trace(
        go.Scatter(x=p_idx.index, y=p_idx.values, name=f"{label} Price",
                   mode="lines", line=dict(color="#1f77b4", width=2.5)),
        secondary_y=False
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="gray", line_width=1,
                  secondary_y=False)
    fig.update_layout(
        title=dict(
            text=(f"<b>{label}</b> ({ticker})<br>"
                  f"<span style='font-size:12px;color:#666'>"
                  f"Price indexed to 1.0 · Volume z-score (63d) clipped ±3</span>"),
            font=dict(size=14)
        ),
        template="plotly_white", height=340,
        margin=dict(b=60, t=70, l=55, r=45),
        legend=dict(orientation="h", yanchor="top", y=-0.18,
                    x=0.5, xanchor="center", font=dict(size=10)),
        dragmode=False, bargap=0.1,
        annotations=[src_ann(-0.25)]
    )
    fig.update_yaxes(title_text="Indexed Price", secondary_y=False)
    fig.update_yaxes(title_text="Vol Z-Score", secondary_y=True,
                     range=[-3.5, 3.5], dtick=1, showgrid=False)
    return fig

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
        line=dict(color="#1f77b4", width=2.5),
        marker=dict(size=8), showlegend=False
    ))
    fig.update_layout(
        title=chart_title("Current Yield Curve",
                          "Spot rates 1M–30Y as of latest FRED data"),
        template="plotly_white", height=400,
        yaxis_title="Yield (%)", xaxis_title="Maturity",
        margin=dict(b=70, t=60, l=60, r=40),
        dragmode=False, annotations=[src_ann(-0.18)]
    )
    return fig

def credit_spread_df():
    hy_s = fetch_fred_series("BAMLH0A0HYM2")
    ig_s = fetch_fred_series("BAMLC0A0CM")
    t10_s = fetch_fred_series("DGS10")
    hy_oas, hy_prev = hy_s.iloc[-1], hy_s.iloc[-2]
    ig_oas, ig_prev = ig_s.iloc[-1], ig_s.iloc[-2]
    t10 = t10_s.iloc[-1]
    gap, gap_prev = hy_oas - ig_oas, hy_prev - ig_prev
    rows = [
        ("HY OAS",    f"{hy_oas*100:.0f} bps",       f"{(hy_oas-hy_prev)*100:+.0f} bps DoD"),
        ("HY Yield",  f"{(hy_oas+t10):.2f}%",        f"{(hy_oas-hy_prev)*100:+.0f} bps DoD"),
        ("IG OAS",    f"{ig_oas*100:.0f} bps",        f"{(ig_oas-ig_prev)*100:+.0f} bps DoD"),
        ("IG Yield",  f"{(ig_oas+t10):.2f}%",         f"{(ig_oas-ig_prev)*100:+.0f} bps DoD"),
        ("HY–IG Gap", f"{gap*100:.0f} bps",           f"{(gap-gap_prev)*100:+.0f} bps DoD"),
    ]
    df = pd.DataFrame(rows, columns=["", "Value", "DoD"])
    return df, hy_oas, hy_prev, ig_oas, ig_prev, gap, gap_prev

def snap_color(row):
    styles = [""] * len(row)
    try:
        cols = list(row.index)
        l, p = float(row["Latest"]), float(row["Previous"])
        idx = cols.index("Latest")
        styles[idx] = ("color: #2ca02c; font-weight:bold" if l > p
                       else "color: #d62728; font-weight:bold" if l < p else "")
    except Exception:
        pass
    return styles

def cred_color(row):
    styles = ["", "", ""]
    try:
        val = row["DoD"]
        num = float(val.replace("bps DoD", "").replace("+", "").strip())
        color = "#2ca02c" if num > 0 else "#d62728" if num < 0 else "#888"
        styles[2] = f"color:{color}"
    except Exception:
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Markets", "Rates", "Macro", "Calendar"]
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
            horizontal=True, key="idx_period"
        )
        with st.spinner("Loading index data…"):
            prices, volumes = fetch_equity()
            latest = prices.index.max()
            if idx_period == "YTD":
                idx_start = pd.Timestamp(f"{latest.year}-01-01")
            else:
                months = {"1M": 1, "3M": 3, "6M": 6, "1Y": 12}[idx_period]
                idx_start = latest - pd.DateOffset(months=months)

            idx_colors = {"SPY": "#1f77b4", "QQQ": "#ff7f0e", "IWM": "#2ca02c"}
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
                            line=dict(color=idx_colors.get(tkr, "#999"), width=2.5)
                        ))
            fig_idx.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
            fig_idx.update_layout(
                title=chart_title("Index Returns",
                                  f"{idx_period} cumulative % return"),
                template="plotly_white", height=340,
                yaxis_title="Return (%)",
                margin=dict(b=80, t=60, l=55, r=40),
                legend=dict(orientation="h", yanchor="top", y=-0.22,
                            x=0.5, xanchor="center"),
                dragmode=False,
                annotations=[src_ann(-0.28)]
            )
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
        today_d = datetime.today().date()
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
        prices, volumes = fetch_equity()

    period_opts = {
        "Since 2015": "2015-01-01", "Since 2020": "2020-01-01",
        "Since 2025": "2025-01-01", "Past 12M": None
    }

    # ── Factors ──
    pf = st.radio("Period", list(period_opts.keys()), horizontal=True, key="pf")
    base = (period_opts[pf] or
            (prices.index.max() - pd.DateOffset(months=12)).strftime("%Y-%m-%d"))
    rel_f, alpha_f = compute_relative(prices, FACTORS)
    ri_f = reindex_from(rel_f, base)
    al_f = alpha_f[alpha_f.index >= pd.Timestamp(base)]

    fig_f1 = go.Figure()
    for tkr, name in FACTORS.items():
        if tkr in ri_f.columns:
            fig_f1.add_trace(go.Scatter(
                x=ri_f.index, y=ri_f[tkr], name=name, mode="lines"))
    fig_f1.add_hline(y=1.0, line_dash="dash", line_color="gray")
    fig_f1.update_layout(
        title=chart_title("MSCI Factor Relative Performance",
                          "ETF ÷ SPY, indexed to 1.0 · above 1.0 = outperforming"),
        template="plotly_white", height=420,
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
    )
    st.plotly_chart(fig_f1, use_container_width=True, key="fig_f1", config=PCFG)

    fig_f2 = go.Figure()
    for tkr, name in FACTORS.items():
        if tkr in al_f.columns:
            fig_f2.add_trace(go.Scatter(
                x=al_f.index, y=al_f[tkr], name=name, mode="lines"))
    fig_f2.add_hline(y=0.0, line_dash="dash", line_color="gray")
    fig_f2.update_layout(
        title=chart_title("MSCI Factor Rolling 6-Month Alpha",
                          "Compounded 126-day return of relative series · positive = outperforming"),
        template="plotly_white", height=420,
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
    )
    st.plotly_chart(fig_f2, use_container_width=True, key="fig_f2", config=PCFG)

    st.divider()

    # ── Sectors ──
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
            x.values[np.triu_indices_from(x.values, k=1)]
        )))
    )

    fig_s1 = go.Figure()
    for tkr, name in SECTORS.items():
        if tkr in ri_s.columns:
            fig_s1.add_trace(go.Scatter(
                x=ri_s.index, y=ri_s[tkr], name=name, mode="lines"))
    fig_s1.add_hline(y=1.0, line_dash="dash", line_color="gray")
    fig_s1.update_layout(
        title=chart_title("Sector ETF Relative Performance",
                          "ETF ÷ SPY, indexed to 1.0 at start · above 1.0 = outperforming"),
        template="plotly_white", height=420,
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
    )
    st.plotly_chart(fig_s1, use_container_width=True, key="fig_s1", config=PCFG)

    fig_s2 = go.Figure()
    for tkr, name in SECTORS.items():
        if tkr in al_s.columns:
            fig_s2.add_trace(go.Scatter(
                x=al_s.index, y=al_s[tkr], name=name, mode="lines"))
    fig_s2.add_hline(y=0.0, line_dash="dash", line_color="gray")
    fig_s2.update_layout(
        title=chart_title("Sector ETF Rolling 6-Month Alpha",
                          "Compounded 126-day return of relative series"),
        template="plotly_white", height=420,
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
    )
    st.plotly_chart(fig_s2, use_container_width=True, key="fig_s2", config=PCFG)

    fig_s3 = go.Figure()
    fig_s3.add_trace(go.Scatter(
        x=disp.index, y=disp, mode="lines",
        line=dict(color="#555", width=2), showlegend=False))
    fig_s3.update_layout(
        title=chart_title("Cross-Sectional Dispersion",
                          "max − min of relative prices · higher = more between-sector divergence"),
        template="plotly_white", height=360,
        margin=dict(b=70, t=60, l=60, r=40),
        dragmode=False, annotations=[src_ann(-0.18)]
    )
    st.plotly_chart(fig_s3, use_container_width=True, key="fig_s3", config=PCFG)

    fig_s4 = go.Figure()
    fig_s4.add_trace(go.Scatter(
        x=roll_corr.index, y=roll_corr.values, mode="lines",
        line=dict(color="#e377c2", width=2), showlegend=False))
    fig_s4.update_layout(
        title=chart_title("Avg Pairwise Sector Correlation (21-day)",
                          "Higher = sectors moving together (macro-driven) · lower = sector-specific moves"),
        template="plotly_white", height=360,
        margin=dict(b=70, t=60, l=60, r=40),
        dragmode=False, annotations=[src_ann(-0.18)]
    )
    st.plotly_chart(fig_s4, use_container_width=True, key="fig_s4", config=PCFG)

    # ── Volume Z-Score Charts ──
    st.divider()
    st.subheader("Volume Z-Score & Price (Past 3 Months)")
    st.caption(
        "Each chart shows price indexed to 1.0 at the start of the window, "
        "with a volume z-score bar overlay (63-day rolling). "
        "Green bars = above-average volume; red = below-average."
    )

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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — RATES
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    rp = st.radio("Period", ["1Y", "3Y", "5Y", "10Y", "Full"],
                  horizontal=True, key="rp")
    rmons = {"1Y": 12, "3Y": 36, "5Y": 60, "10Y": 120, "Full": None}[rp]

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
        title=chart_title("Treasury Yields by Maturity",
                          "Daily constant-maturity yields — absolute rate levels"),
        template="plotly_white", height=420, yaxis_title="Yield (%)",
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
    )
    st.plotly_chart(fig_y, use_container_width=True, key="fig_yields", config=PCFG)

    col1, col2 = st.columns(2)
    with col1:
        fig_sp = go.Figure()
        for sid, lbl in SPREADS.items():
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_sp.add_trace(go.Scatter(
                    x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_sp.add_hline(y=0, line_dash="dash", line_color="red", line_width=1)
        fig_sp.update_layout(
            title=chart_title("Yield Curve Spreads",
                              "10Y–2Y: recession signal · below 0 = inverted"),
            template="plotly_white", height=420, yaxis_title="Spread (%)",
            margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
        )
        st.plotly_chart(fig_sp, use_container_width=True,
                        key="fig_spreads", config=PCFG)

    with col2:
        fig_rv = go.Figure()
        for sid, lbl in [("DFII10", "10Y Real Yield"),
                         ("T10YIE", "10Y Breakeven Infl.")]:
            try:
                s = trim(fetch_fred_series(sid), rmons)
                fig_rv.add_trace(go.Scatter(
                    x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_rv.update_layout(
            title=chart_title("Real Yield & Breakeven Inflation",
                              "Real yield = 10Y TIPS · Breakeven = market-implied inflation"),
            template="plotly_white", height=420, yaxis_title="%",
            yaxis=dict(rangemode="normal", autorange=True),
            margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
        )
        st.plotly_chart(fig_rv, use_container_width=True,
                        key="fig_realyield", config=PCFG)

    st.plotly_chart(build_yield_curve(), use_container_width=True,
                    key="yc_rates", config=PCFG)
    c = yield_curve_commentary()
    if c:
        st.caption(c)

    fig_cr = go.Figure()
    for sid, lbl in CREDIT.items():
        try:
            s = trim(fetch_fred_series(sid), rmons) * 100
            fig_cr.add_trace(go.Scatter(
                x=s.index, y=s.values, name=f"{lbl} (bps)", mode="lines"))
        except Exception:
            pass
    try:
        hy = trim(fetch_fred_series("BAMLH0A0HYM2"), rmons)
        ig = trim(fetch_fred_series("BAMLC0A0CM"), rmons)
        gap = (hy - ig).dropna() * 100
        fig_cr.add_trace(go.Scatter(
            x=gap.index, y=gap.values, name="HY–IG Gap (bps)",
            mode="lines", line=dict(dash="dot", width=1.5)))
    except Exception:
        pass
    fig_cr.update_layout(
        title=chart_title("Credit Spreads (OAS)",
                          "ICE BofA OAS over Treasuries · wider = risk-off"),
        template="plotly_white", height=420, yaxis_title="bps",
        margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
    )
    st.plotly_chart(fig_cr, use_container_width=True,
                    key="fig_credit", config=PCFG)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MACRO
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    mp = st.radio("Period", ["2Y", "5Y", "10Y", "Full"],
                  horizontal=True, key="mp")
    mmon = {"2Y": 24, "5Y": 60, "10Y": 120, "Full": None}[mp]

    col_a, col_b = st.columns(2)
    with col_a:
        fig_cpi = go.Figure()
        for sid, lbl in [("CPIAUCSL", "CPI"), ("CPILFESL", "Core CPI")]:
            try:
                s = trim(to_yoy(fetch_fred_series(sid)), mmon)
                fig_cpi.add_trace(go.Scatter(
                    x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_cpi.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="2% target",
                          annotation_position="bottom right")
        fig_cpi.update_layout(
            title=chart_title("CPI & Core CPI",
                              "YoY % · Core excludes food & energy"),
            template="plotly_white", height=420, yaxis_title="YoY %",
            margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
        )
        st.plotly_chart(fig_cpi, use_container_width=True,
                        key="fig_cpi", config=PCFG)

    with col_b:
        fig_pce = go.Figure()
        for sid, lbl in [("PCEPI", "PCE"), ("PCEPILFE", "Core PCE")]:
            try:
                s = trim(to_yoy(fetch_fred_series(sid)), mmon)
                fig_pce.add_trace(go.Scatter(
                    x=s.index, y=s.values, name=lbl, mode="lines"))
            except Exception:
                pass
        fig_pce.add_hline(y=2.0, line_dash="dash", line_color="red",
                          annotation_text="2% target",
                          annotation_position="bottom right")
        fig_pce.update_layout(
            title=chart_title("PCE & Core PCE",
                              "YoY % · Fed's preferred inflation gauge"),
            template="plotly_white", height=420, yaxis_title="YoY %",
            margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
        )
        st.plotly_chart(fig_pce, use_container_width=True,
                        key="fig_pce", config=PCFG)

    col_c, col_d = st.columns(2)
    with col_c:
        fig_ff = go.Figure()
        for sid, lbl, clr in [("FEDFUNDS", "Fed Funds Rate", "#1f77b4"),
                              ("UNRATE", "Unemployment", "#ff7f0e")]:
            try:
                s = trim(fetch_fred_series(sid), mmon)
                fig_ff.add_trace(go.Scatter(
                    x=s.index, y=s.values, name=lbl, mode="lines",
                    line=dict(color=clr, width=2)))
            except Exception:
                pass
        fig_ff.update_layout(
            title=chart_title("Fed Funds Rate & Unemployment",
                              "Policy rate vs U-3 unemployment — dual mandate"),
            template="plotly_white", height=420, yaxis_title="%",
            margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
        )
        st.plotly_chart(fig_ff, use_container_width=True,
                        key="fig_fedfunds", config=PCFG)

    with col_d:
        try:
            gdp = trim(fetch_fred_series("A191RL1Q225SBEA"), mmon)
            fig_gdp = go.Figure()
            fig_gdp.add_trace(go.Bar(
                x=gdp.index, y=gdp.values, name="GDP Growth",
                marker_color=["#2ca02c" if v >= 0 else "#d62728"
                              for v in gdp.values]
            ))
            fig_gdp.add_hline(y=0, line_color="black", line_width=1)
            fig_gdp.update_layout(
                title=chart_title("Real GDP Growth",
                                  "QoQ annualized % (SAAR) · two negative = technical recession"),
                template="plotly_white", height=420, yaxis_title="% QoQ Ann.",
                margin=CM, legend=LEG, dragmode=False, annotations=[src_ann()]
            )
            st.plotly_chart(fig_gdp, use_container_width=True,
                            key="fig_gdp", config=PCFG)
        except Exception:
            st.info("GDP data unavailable.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.subheader("Upcoming Releases")
        st.caption("Next 45 days and past 35 days — all via FRED")
        with st.spinner("Loading…"):
            snap = fetch_release_snapshot()
            if not snap.empty:
                fmt = {"Previous": "{:.2f}", "Latest": "{:.2f}"}
                st.dataframe(
                    snap.style.apply(snap_color, axis=1).format(fmt),
                    hide_index=True, use_container_width=True, height=420
                )

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
                    hide_index=True, use_container_width=True, height=520
                )

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
