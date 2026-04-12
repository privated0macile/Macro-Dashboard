import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from constants import *
from helpers import (
    latest_common_window, to_yoy, trim, compute_relative, reindex_from,
    get_negative_spread_ranges, chart_title, safe_fmt, snap_color, add_src,
    compute_flow_proxy_z, compute_signed_volume_z, compute_breadth,
    compute_rotation_ratio, style_attr, build_holdings_attr
)
from data_fetchers import (
    fetch_fred, fetch_equity, fetch_benchmark_ohlc,
    fetch_release_snapshot, fetch_fred_calendar,
    yield_curve_commentary, build_yield_curve
)

st.set_page_config(page_title='Macro Dashboard', layout='wide', page_icon='📊', initial_sidebar_state='collapsed')
st.markdown('\n<style>\n    [data-testid="stMetricValue"] { font-size: 1.1rem; }\n    .block-container { padding-top: 1rem; }\n</style>\n', unsafe_allow_html=True)

st.markdown(f"""\n<div style="display:flex;justify-content:space-between;align-items:baseline">\n    <h1 style="margin:0">Macro Dashboard</h1>\n    <span style="color:#888;font-size:0.85rem">\n        Refreshed: {datetime.now().strftime('%b %d, %Y %H:%M')}\n        &nbsp;/&nbsp; Data: FRED / Yahoo Finance\n    </span>\n</div>\n""", unsafe_allow_html=True)
st.markdown(f"""
<div style="margin:1rem 0 1.5rem;padding:0.9rem 1rem;border-radius:8px;border:1px solid #e6e6e6;background:#fafafa">
  <p style="margin:0 0 0.5rem;font-size:0.95rem;color:#222">
    <strong>Dashboard overview</strong>: This report combines macroeconomic series from FRED with equity and ETF data from Yahoo Finance. Data scope begins {START} and is refreshed hourly from cached calls.
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
        fig_idx.update_layout(title=chart_title('U.S. Major Indices', f'{idx_period} cumulative return'), template='plotly_white', height=220, yaxis_title='Return (%)', margin=dict(b=60, t=40, l=50, r=30), legend=dict(orientation='h', yanchor='top', y=-0.35, x=0.5, xanchor='center', font=dict(size=11)), dragmode=False, font=dict(size=11))
        add_src(fig_idx, -0.35)
        st.plotly_chart(fig_idx, use_container_width=True, key='fig_idx', config=PCFG)
    with hdr_r:
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
            dd = pd.concat([t3, b3], ignore_index=True)
            st.markdown('**Top 3 / Bottom 3 by Composite**')
            st.caption('Composite = (Flow Z + Signed Vol Z + Return Z) / 3 -- all 252-day rolling, clipped +/-3')

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

                def row_border(row):
                    """Row border."""
                    if row.name == 2:
                        return ['border-bottom:2px solid #333'] * len(row)
                    return [''] * len(row)
                s = d.style.apply(row_border, axis=1)
                for c in ['Flow Z', 'Composite']:
                    if c in d.columns:
                        s = s.map(cz, subset=[c])
                for c in ['1D', '5D', '1M', '12M']:
                    if c in d.columns:
                        s = s.map(cr2, subset=[c])
                fmt = {c: '{:+.2f}' for c in ['1D', '5D', '1M', '12M', 'Flow Z', 'Composite'] if c in d.columns}
                return s.format(fmt, na_rep='---')
            st.dataframe(_sty(dd), hide_index=True, use_container_width=True, height=260)
            st.markdown(SRC_BOTH, unsafe_allow_html=True)
    st.divider()
    st.subheader('Benchmark Price Action')
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
    st.subheader('Daily Positioning Feed')
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
    st.subheader('Relative Performance')
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
        st.subheader('Upcoming Releases')
        st.caption('Interactive instructions: scroll the table to compare recent and upcoming releases. Takeaway: this section highlights the latest macro prints and their previous values so the user can see where economic momentum is accelerating or slowing.')
        with st.spinner('Loading...'):
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(snap.style.apply(snap_color, axis=1).format({'Previous': safe_fmt, 'Latest': safe_fmt}, na_rep='---'), hide_index=True, use_container_width=True, height=420)
                st.markdown(SRC_FRED, unsafe_allow_html=True)
        st.divider()
        st.subheader('Release Calendar')
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
