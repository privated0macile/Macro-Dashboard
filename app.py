import streamlit as st
import streamlit.components.v1 as components
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

# ── Tooltip CSS + existing styles ──────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.1rem; }
    .block-container { padding-top: 1rem; }

    /* ── Info-icon tooltip system ── */
    .info-tip {
        position: relative;
        display: inline-block;
        cursor: pointer;
        vertical-align: middle;
        margin-left: 6px;
    }
    .info-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 17px;
        height: 17px;
        border-radius: 50%;
        background: #1a73e8;
        color: #fff;
        font-size: 10px;
        font-weight: 700;
        font-style: italic;
        font-family: Georgia, serif;
        line-height: 1;
        transition: background 0.15s;
    }
    .info-tip:hover .info-icon { background: #1557b0; }
    .info-box {
        visibility: hidden;
        opacity: 0;
        position: absolute;
        z-index: 9999;
        top: 130%;
        left: 0;
        width: min(300px, 80vw);
        padding: 10px 13px;
        background: #2b2b2b;
        color: #eee;
        font-size: 12.5px;
        font-weight: 400;
        font-style: normal;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        line-height: 1.55;
        border-radius: 7px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.25);
        transition: opacity 0.18s;
        pointer-events: none;
    }
    .info-box::after {
        content: "";
        position: absolute;
        bottom: 100%;
        left: 12px;
        border-width: 5px;
        border-style: solid;
        border-color: transparent transparent #2b2b2b transparent;
    }
    .info-tip:hover .info-box,
    .info-tip:focus .info-box {
        visibility: visible;
        opacity: 1;
    }

    /* ── Responsive layout ── */

    /* Tables: always allow horizontal scroll on narrow screens */
    [data-testid="stDataFrame"] { overflow-x: auto !important; }

    /* Metric cards: shrink text on narrow screens */
    @media (max-width: 900px) {
        [data-testid="stMetricValue"] { font-size: 0.9rem !important; }
        [data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    }

    /* Medium screens: tighten padding + start shrinking chart text */
    @media (max-width: 1024px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }

        /* Plotly: shrink legends, axis labels, tick text */
        .js-plotly-plot .legendtext { font-size: 10px !important; }
        .js-plotly-plot .g-xtitle text,
        .js-plotly-plot .g-ytitle text { font-size: 11px !important; }
        .js-plotly-plot .xtick text,
        .js-plotly-plot .ytick text { font-size: 9px !important; }
        .js-plotly-plot .gtitle { font-size: 11px !important; }

        /* Altair / Vega: shrink text */
        .vega-embed text { font-size: 10px !important; }
    }

    /* Narrow / mobile: stack Streamlit columns vertically */
    @media (max-width: 768px) {
        .block-container { padding-left: 0.5rem; padding-right: 0.5rem; }

        /* Force columns to stack */
        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 0 !important;
        }

        /* Section headers: scale down */
        h3 { font-size: 1.1rem !important; }
        h1 { font-size: 1.5rem !important; }

        /* Chart labels: scale down */
        .info-tip { margin-left: 4px; }
        .info-box { width: min(260px, 85vw); font-size: 11.5px; }

        /* Radio buttons: wrap */
        [data-testid="stRadio"] > div {
            flex-wrap: wrap !important;
            gap: 0.25rem !important;
        }

        /* Plotly: further shrink for narrow */
        .js-plotly-plot .legendtext { font-size: 9px !important; }
        .js-plotly-plot .g-xtitle text,
        .js-plotly-plot .g-ytitle text { font-size: 10px !important; }
        .js-plotly-plot .xtick text,
        .js-plotly-plot .ytick text { font-size: 8px !important; }
        .js-plotly-plot .gtitle { font-size: 10px !important; }

        /* Plotly source annotations */
        .js-plotly-plot .annotation-text { font-size: 8px !important; }

        /* Altair */
        .vega-embed text { font-size: 9px !important; }
    }

    /* Very narrow (phone portrait) */
    @media (max-width: 480px) {
        .block-container { padding-left: 0.25rem; padding-right: 0.25rem; }
        h3 { font-size: 1rem !important; }
        .info-box { width: min(240px, 90vw); font-size: 11px; }
        [data-testid="stMetricValue"] { font-size: 0.8rem !important; }

        /* Plotly: smallest */
        .js-plotly-plot .legendtext { font-size: 8px !important; }
        .js-plotly-plot .g-xtitle text,
        .js-plotly-plot .g-ytitle text { font-size: 9px !important; }
        .js-plotly-plot .xtick text,
        .js-plotly-plot .ytick text { font-size: 7px !important; }
        .js-plotly-plot .gtitle { font-size: 9px !important; }
        .js-plotly-plot .annotation-text { font-size: 7px !important; }
    }
</style>
""", unsafe_allow_html=True)

# ── Tooltip helpers ────────────────────────────────────────────────────────

def _esc(text):
    """Escape HTML entities in tooltip text."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def info(tip):
    """Return an inline HTML info-icon with hover tooltip."""
    return (
        f'<span class="info-tip" tabindex="0">'
        f'<span class="info-icon">i</span>'
        f'<span class="info-box">{_esc(tip)}</span>'
        f'</span>'
    )

def hdr(title, tip, tag="h3"):
    """Render a heading with an info tooltip beside it."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:0.25rem">'
        f'<{tag} style="margin:0;padding:0">{title}</{tag}>{info(tip)}'
        f'</div>',
        unsafe_allow_html=True,
    )

def label_info(label, tip):
    """Render a label with an info tooltip, matching section header size."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:0.25rem">'
        f'<h3 style="margin:0;padding:0">{label}</h3>{info(tip)}'
        f'</div>',
        unsafe_allow_html=True,
    )

def chart_label(title, tip):
    """Render a chart-level title with inline tooltip above a Plotly/Altair chart."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:5px">'
        f'<span style="font-weight:700;font-size:0.9rem">{title}</span>'
        f'{info(tip)}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Tooltip text constants ─────────────────────────────────────────────────

TIP_INDICES = (
    "Tracks cumulative returns of the four main U.S. stock benchmarks. "
    "S&P 500 = 500 large companies, Nasdaq = tech-heavy, "
    "Russell 2000 = small companies, Dow 30 = 30 blue-chip stocks. "
    "A rising line means the index has gained value over the chosen period."
)
TIP_COMPOSITE = (
    "Ranks sectors by a Composite score that blends three signals: "
    "Flow Z (are investors putting money in or pulling it out?), "
    "Signed Volume Z (is trading volume heavier on up-days or down-days?), "
    "and Return Z (how unusual is the latest daily move vs the past year?). "
    "Green/positive = bullish signals; red/negative = bearish signals."
)
TIP_CANDLE = (
    "A candlestick chart shows each day's open, high, low, and close price. "
    "Green candles = price went up that day; red = price went down. "
    "The blue line is the 20-day moving average, which smooths out noise "
    "and shows the short-term trend."
)
TIP_POSITIONING = (
    "Four quick-look gauges that together describe the current market regime -- "
    "whether moves are driven by big-picture sector rotation or individual stocks, "
    "whether gains are broad or concentrated in a few names, whether investors "
    "favor riskier or safer sectors, and whether trading volume is unusually high or low."
)
TIP_MACRO_MICRO = (
    "Compares how much sectors move relative to each other (macro) versus "
    "how much individual stocks diverge within each sector (micro). "
    "Above 0.75 means sector bets dominate; below 0.25 means stock-pickers "
    "are driving returns. Measured as a percentile rank over the past year."
)
TIP_BREADTH = (
    "Compares the equal-weight S&P 500 (RSP, every stock counts the same) "
    "to the cap-weight S&P 500 (SPY, bigger companies count more). "
    "A rising line means gains are spread across many stocks (healthy). "
    "A falling line means only a few large stocks are driving the index."
)
TIP_CYC_DEF = (
    "Tracks cyclical sectors (tech, financials, energy, industrials -- "
    "these do well when the economy grows) versus defensive sectors "
    "(utilities, healthcare, staples -- these hold up in downturns). "
    "Rising = investors favor growth and risk. Falling = investors seek safety."
)
TIP_SPY_VOL = (
    "Shows today's SPY trading volume compared to its one-year median, "
    "expressed as a z-score. 0 = normal volume, +2 = very heavy, -2 = very light. "
    "Spikes often accompany big market moves or news events."
)
TIP_RELATIVE = (
    "Each line shows how an ETF has performed relative to SPY (the S&P 500). "
    "A rising line means that ETF is beating the broad market; falling means "
    "it is lagging. Indexed to 1.0 at the start of the chosen period."
)
TIP_ALPHA = (
    "Rolling 6-month alpha measures an ETF's compounded outperformance "
    "versus SPY over a trailing half-year window. Positive = outperforming, "
    "negative = underperforming. Useful for spotting sustained trends."
)
TIP_FLOW_SECTION = (
    "Each chart overlays an ETF's price return (blue line) with a flow z-score "
    "(green/red bars). The flow proxy estimates whether money is flowing into "
    "(green, accumulation) or out of (red, distribution) the ETF, based on "
    "price and volume patterns over the past year."
)
TIP_HEATMAP = (
    "A color grid showing each sector's return over two windows: "
    "5 trading days and 1 month. Green = positive return, red = negative. "
    "Useful for spotting which sectors are hot or cold at a glance."
)
TIP_MACRO_PULSE = (
    "Three key macro series plotted together: the 10-year minus 2-year Treasury "
    "spread (negative = inverted yield curve, a recession signal), the Fed Funds "
    "rate (the interest rate the Fed sets), and the unemployment rate."
)
TIP_HOLDINGS = (
    "Expand any sector to see its top holdings, their approximate weight in the ETF, "
    "and how much each stock contributed to the ETF's daily move. "
    "Contribution = weight x stock return. Sorted by absolute contribution so the "
    "biggest movers appear first."
)
TIP_FI_METRICS = (
    "Snapshot of key fixed-income and macro levels. Treasury yields show the annual "
    "return you earn for lending money to the U.S. government at each maturity. "
    "Fed Funds is the overnight rate set by the Federal Reserve. CPI YoY is the "
    "yearly inflation rate. 10Y-2Y is the yield curve slope."
)
TIP_YIELD_CURVE = (
    "The yield curve plots Treasury yields from 1-month to 30-year maturities. "
    "A normal curve slopes upward (longer = higher yield). An inverted curve "
    "(short rates above long rates) has historically preceded recessions."
)
TIP_YIELDS_HIST = (
    "Historical paths of key Treasury yields. When yields rise, bond prices fall "
    "(and vice versa). Comparing maturities shows how the curve shape has evolved."
)
TIP_SPREADS = (
    "The 10Y-2Y and 10Y-3M spreads measure the gap between long and short Treasury "
    "yields. When the line goes below zero (shaded red), the curve is inverted -- "
    "meaning short-term rates exceed long-term rates. This is a widely watched "
    "recession indicator."
)
TIP_REAL_YIELD = (
    "Real yield = the return on TIPS (inflation-protected bonds) after removing "
    "expected inflation. Breakeven = the market's implied inflation expectation. "
    "Together they decompose nominal yields into a real return and an inflation premium."
)
TIP_CREDIT = (
    "Credit spreads measure the extra yield investors demand to hold corporate bonds "
    "over risk-free Treasuries. HY OAS = high-yield (junk) bonds, IG OAS = "
    "investment-grade bonds. Wider spreads signal fear or stress; tighter spreads "
    "signal confidence. Measured in basis points (1 bp = 0.01%)."
)
TIP_CPI = (
    "CPI (Consumer Price Index) measures the year-over-year change in prices for "
    "a basket of goods and services. Core CPI strips out volatile food and energy. "
    "The dashed line at 2% is the Fed's inflation target."
)
TIP_PCE = (
    "PCE (Personal Consumption Expenditures) is the Fed's preferred inflation gauge. "
    "It covers a broader basket than CPI and adjusts for substitution effects. "
    "Core PCE excludes food and energy. The 2% line is the Fed's target."
)
TIP_FF_UNEMP = (
    "The Fed's dual mandate: keep prices stable and maximize employment. "
    "Fed Funds rate is the Fed's main policy lever -- higher rates cool the economy. "
    "The unemployment rate shows the percentage of workers actively looking for jobs."
)
TIP_GDP = (
    "Real GDP growth, reported quarterly, measures how fast the economy is expanding "
    "or contracting after removing inflation. Annualized means the quarterly change "
    "is scaled to show what a full year at that pace would look like. "
    "Negative bars indicate economic contraction."
)
TIP_SNAPSHOT = (
    "Key macro data releases with their latest and previous values, plus the next "
    "scheduled release date. Green = latest reading higher than previous; "
    "red = lower. Useful for tracking whether the economy is accelerating or slowing."
)
TIP_CALENDAR = (
    "FRED release schedule showing upcoming and recent data publications. "
    "Yellow-highlighted rows are today's releases. Gray rows are past releases."
)
TIP_FOMC = (
    "Federal Open Market Committee meeting dates -- this is when the Fed decides "
    "whether to raise, lower, or hold interest rates. These decisions move every "
    "asset class. Past meetings show their outcomes; future dates show days remaining."
)

SECTOR_TIPS = {
    'XLK': 'Info Tech: Apple, Microsoft, Nvidia, etc. Largest sector by weight. Sensitive to interest rates and growth expectations.',
    'XLF': 'Financials: Banks, insurers, payment networks. Benefits from higher rates and steeper yield curves.',
    'XLE': 'Energy: Oil majors, drillers, pipelines. Tied to oil/gas prices and global demand.',
    'XLV': 'Healthcare: Pharma, biotech, insurers. Defensive -- demand is steady regardless of the economy.',
    'XLI': 'Industrials: Aerospace, machinery, railroads. Cyclical -- rises with economic expansion and capex.',
    'XLY': 'Consumer Discretionary: Amazon, Tesla, Home Depot. Spending on wants, not needs -- sensitive to consumer confidence.',
    'XLP': 'Consumer Staples: Procter & Gamble, Costco, Coca-Cola. Essentials people buy in any economy. Defensive.',
    'XLB': 'Materials: Chemicals, mining, steel. Tied to commodity prices and industrial demand.',
    'XLU': 'Utilities: Electric, gas, water companies. Bond-like, dividend-heavy. Outperforms when rates fall.',
    'XLRE': 'Real Estate: REITs -- warehouses, towers, malls. Sensitive to interest rates and property values.',
    'XLC': 'Comm Services: Meta, Alphabet, Netflix, Disney. Mix of social media, streaming, and telecom.',
}
FACTOR_TIPS = {
    'USMV': 'Min Vol: Stocks with the lowest historical volatility. Tends to outperform in choppy or falling markets.',
    'MTUM': 'Momentum: Stocks that have been rising recently. Bets that winners keep winning in the short term.',
    'QUAL': 'Quality: Companies with high ROE, low debt, stable earnings. Tends to hold up well in downturns.',
    'SIZE': 'Size (Small-Cap): Smaller companies that may grow faster but carry more risk than large-caps.',
    'VLUE': 'Value: Stocks trading at low price-to-earnings or price-to-book. Bets that cheap stocks will revert to fair value.',
    'HDV': 'High Dividend Yield: Companies paying above-average dividends. Popular for income, tends to be defensive.',
}

# ── Config ─────────────────────────────────────────────────────────────────

FRED_KEY = st.secrets['FRED_API_KEY']
fred = fredapi.Fred(api_key=FRED_KEY)
START = '2015-01-01'
BENCH = 'SPY'
ROLL = 126
CM = dict(b=120, t=60, l=60, r=40)
LEG = dict(orientation='h', yanchor='top', y=-0.15, x=0.5, xanchor='center', font=dict(size=11))
PCFG = dict(displayModeBar=False, scrollZoom=False)
DISCLAIMER = '*Disclaimer: This dashboard is for educational and informational purposes only. Nothing contained herein constitutes investment advice, a recommendation, or a solicitation to buy or sell any securities or financial instruments. The data presented may be delayed, incomplete, or inaccurate, and should not be relied upon for trading or investment decisions. Past performance is not indicative of future results. The authors and contributors assume no liability for any losses or damages arising from the use of this information. Consult a qualified financial advisor before making any investment decisions.*'

# Last trading day (previous business day)
_today = pd.Timestamp.today().normalize()
LAST_TRADE = (_today - pd.tseries.offsets.BDay(1))
LAST_TRADE_STR = LAST_TRADE.strftime('%b %d, %Y')

SRC_BOTH = f'<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED / Yahoo Finance, data as of {LAST_TRADE_STR}</p>'
SRC_FRED = f'<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED, data as of {LAST_TRADE_STR}</p>'
SRC_YF = f'<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: Yahoo Finance, data as of {LAST_TRADE_STR}</p>'
ZSCORE_LOOKBACK = 252
CHART_WINDOW = 63

FACTORS = {'USMV': 'Min Vol', 'MTUM': 'Momentum', 'QUAL': 'Quality', 'SIZE': 'Size', 'VLUE': 'Value', 'HDV': 'Yield'}
SECTORS = {'XLC': 'Comm. Serv.', 'XLY': 'Cons. Disc.', 'XLP': 'Cons. Staples', 'XLE': 'Energy', 'XLF': 'Financials', 'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLK': 'Info. Tech', 'XLB': 'Materials', 'XLRE': 'Real Estate', 'XLU': 'Utilities'}
SECTORS_CYCLICAL = {'XLC': 'Comm. Serv.', 'XLY': 'Cons. Disc.', 'XLE': 'Energy', 'XLF': 'Financials', 'XLI': 'Industrials', 'XLK': 'Info. Tech', 'XLB': 'Materials'}
SECTORS_DEFENSIVE = {'XLP': 'Cons. Staples', 'XLV': 'Healthcare', 'XLRE': 'Real Estate', 'XLU': 'Utilities'}
SECTOR_COLORS = {'XLK': '#5B9BD5', 'XLV': '#70C27A', 'XLC': '#A978DE', 'XLP': '#F0C75E', 'XLY': '#E8725C', 'XLI': '#A3A9B0', 'XLU': '#5EC4D4', 'XLE': '#4AA06D', 'XLF': '#D94F5C', 'XLB': '#C08B5C', 'XLRE': '#D97BA0'}
FACTOR_COLORS = {'MTUM': '#5B9BD5', 'VLUE': '#D94F5C', 'QUAL': '#70C27A', 'SIZE': '#F0A050', 'USMV': '#A3A9B0', 'HDV': '#D4AA4F'}
INDICES = {'SPY': 'S&P 500', 'QQQ': 'Nasdaq 100', 'IWM': 'Russell 2000', 'DIA': 'Dow 30'}

EW_SECTORS = {'XLK': 'RYT', 'XLF': 'RYF', 'XLE': 'RYE', 'XLV': 'RYH', 'XLI': 'RGI', 'XLY': 'RCD', 'XLP': 'RHS', 'XLB': 'RTM', 'XLU': 'RYU', 'XLRE': 'EWRE', 'XLC': 'RSPC'}
RETAIL_ETFS = ['TQQQ', 'SQQQ']
HOLDINGS = {
    'XLK': [('AAPL', 'Apple', 0.22), ('MSFT', 'Microsoft', 0.21), ('NVDA', 'Nvidia', 0.11), ('AVGO', 'Broadcom', 0.05), ('CRM', 'Salesforce', 0.03), ('ADBE', 'Adobe', 0.03), ('AMD', 'AMD', 0.03), ('CSCO', 'Cisco', 0.02)],
    'XLF': [('BRK-B', 'Berkshire', 0.14), ('JPM', 'JPMorgan', 0.11), ('V', 'Visa', 0.09), ('MA', 'Mastercard', 0.07), ('BAC', 'BofA', 0.05), ('WFC', 'Wells Fargo', 0.04), ('GS', 'Goldman', 0.03), ('MS', 'Morgan Stanley', 0.03)],
    'XLE': [('XOM', 'Exxon', 0.23), ('CVX', 'Chevron', 0.16), ('COP', 'ConocoPhillips', 0.08), ('WMB', 'Williams', 0.06), ('EOG', 'EOG Resources', 0.05), ('SLB', 'Schlumberger', 0.05), ('PSX', 'Phillips 66', 0.04), ('MPC', 'Marathon Petro', 0.04)],
    'XLV': [('LLY', 'Eli Lilly', 0.12), ('UNH', 'UnitedHealth', 0.1), ('JNJ', 'J&J', 0.07), ('ABBV', 'AbbVie', 0.07), ('MRK', 'Merck', 0.06), ('TMO', 'Thermo Fisher', 0.04), ('ABT', 'Abbott', 0.04), ('PFE', 'Pfizer', 0.03)],
    'XLI': [('GE', 'GE Aerospace', 0.09), ('CAT', 'Caterpillar', 0.06), ('RTX', 'RTX Corp', 0.05), ('UNP', 'Union Pacific', 0.05), ('HON', 'Honeywell', 0.05), ('DE', 'Deere', 0.04), ('BA', 'Boeing', 0.04), ('LMT', 'Lockheed', 0.03)],
    'XLY': [('AMZN', 'Amazon', 0.23), ('TSLA', 'Tesla', 0.15), ('HD', 'Home Depot', 0.1), ('MCD', "McDonald's", 0.05), ('LOW', "Lowe's", 0.04), ('BKNG', 'Booking', 0.04), ('TJX', 'TJX Cos', 0.03), ('NKE', 'Nike', 0.02)],
    'XLP': [('PG', 'Procter & Gamble', 0.15), ('COST', 'Costco', 0.14), ('WMT', 'Walmart', 0.1), ('KO', 'Coca-Cola', 0.1), ('PEP', 'PepsiCo', 0.09), ('PM', 'Philip Morris', 0.06), ('MDLZ', 'Mondelez', 0.04), ('MO', 'Altria', 0.03)],
    'XLB': [('LIN', 'Linde', 0.19), ('SHW', 'Sherwin-Williams', 0.09), ('FCX', 'Freeport-McMoRan', 0.08), ('APD', 'Air Products', 0.06), ('ECL', 'Ecolab', 0.06), ('NEM', 'Newmont', 0.05), ('NUE', 'Nucor', 0.04), ('DOW', 'Dow Inc', 0.04)],
    'XLU': [('NEE', 'NextEra', 0.15), ('SO', 'Southern Co', 0.1), ('DUK', 'Duke Energy', 0.08), ('CEG', 'Constellation', 0.07), ('SRE', 'Sempra', 0.05), ('AEP', 'AEP', 0.05), ('D', 'Dominion', 0.04), ('PCG', 'PG&E', 0.04)],
    'XLRE': [('PLD', 'Prologis', 0.13), ('AMT', 'American Tower', 0.1), ('EQIX', 'Equinix', 0.09), ('WELL', 'Welltower', 0.07), ('SPG', 'Simon Property', 0.06), ('DLR', 'Digital Realty', 0.05), ('PSA', 'Public Storage', 0.05), ('O', 'Realty Income', 0.05)],
    'XLC': [('META', 'Meta', 0.23), ('GOOGL', 'Alphabet A', 0.12), ('GOOG', 'Alphabet C', 0.11), ('NFLX', 'Netflix', 0.08), ('T', 'AT&T', 0.05), ('CMCSA', 'Comcast', 0.05), ('DIS', 'Disney', 0.04), ('TMUS', 'T-Mobile', 0.04)],
}


# ── Utility functions ──────────────────────────────────────────────────────

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


# ── FRED / Yield config ───────────────────────────────────────────────────

YIELDS = {'DGS2': '2Y', 'DGS5': '5Y', 'DGS10': '10Y', 'DGS30': '30Y'}
SPREADS = {'T10Y2Y': '10Y-2Y Spread', 'T10Y3M': '10Y-3M Spread'}
CREDIT = {'BAMLH0A0HYM2': 'HY OAS', 'BAMLC0A0CM': 'IG OAS'}
KEY_RELEASES = [
    ('Nonfarm Payrolls', 'PAYEMS', '000s MoM', 'diff'),
    ('Unemployment Rate', 'UNRATE', '%', 'level'),
    ('CPI YoY', 'CPIAUCSL', '% YoY', 'yoy'),
    ('Core CPI YoY', 'CPILFESL', '% YoY', 'yoy'),
    ('PCE YoY', 'PCEPI', '% YoY', 'yoy'),
    ('Core PCE YoY', 'PCEPILFE', '% YoY', 'yoy'),
    ('GDP Growth QoQ Ann.', 'A191RL1Q225SBEA', '% Ann.', 'level'),
    ('Retail Sales MoM', 'RSAFS', '% MoM', 'mom'),
    ('Industrial Production', 'INDPRO', '% MoM', 'mom'),
    ('Fed Funds Rate', 'FEDFUNDS', '%', 'level'),
    ('10Y-2Y Spread', 'T10Y2Y', '%', 'level'),
]
FOMC = {
    '2025': [
        ('Jan 28-29', '2025-01-29', 'Hold (4.25-4.50%)'),
        ('Mar 18-19', '2025-03-19', 'Hold (4.25-4.50%)'),
        ('May 6-7', '2025-05-07', 'Hold (4.25-4.50%)'),
        ('Jun 17-18', '2025-06-18', 'Hold (4.25-4.50%)'),
        ('Jul 29-30', '2025-07-30', 'Hold (4.25-4.50%)'),
        ('Sep 16-17', '2025-09-17', 'Cut -25bp (4.00-4.25%)'),
        ('Oct 28-29', '2025-10-29', 'Cut -25bp (3.75-4.00%)'),
        ('Dec 9-10', '2025-12-10', 'Cut -25bp (3.50-3.75%)'),
    ],
    '2026': [
        ('Jan 27-28', '2026-01-28', 'Hold (3.50-3.75%)'),
        ('Mar 17-18', '2026-03-18', ''),
        ('Apr 28-29', '2026-04-29', ''),
        ('Jun 9-10', '2026-06-10', ''),
        ('Jul 28-29', '2026-07-29', ''),
        ('Sep 15-16', '2026-09-16', ''),
        ('Oct 27-28', '2026-10-28', ''),
        ('Dec 8-9', '2026-12-09', ''),
    ],
}


# ── Data-fetching functions ────────────────────────────────────────────────

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
        list(FACTORS) + list(SECTORS) + list(INDICES)
        + list(EW_SECTORS.values()) + RETAIL_ETFS + ht + [BENCH, "RSP"]
    ))
    try:
        raw = yf.download(tks, start=START, auto_adjust=True, progress=False, threads=True)
        close_df = normalize_yf_panel(raw, "Close")
        volume_df = normalize_yf_panel(raw, "Volume")
        if close_df.empty:
            raise ValueError("No close data returned from Yahoo Finance.")
        return close_df, volume_df
    except Exception:
        core = list(set(
            list(FACTORS) + list(SECTORS) + list(INDICES)
            + list(EW_SECTORS.values()) + RETAIL_ETFS + [BENCH, "RSP"]
        ))
        raw = yf.download(core, start=START, auto_adjust=True, progress=False, threads=True)
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
                rr = requests.get(
                    f'https://api.stlouisfed.org/fred/series/release?series_id={sid}&api_key={FRED_KEY}&file_type=json',
                    timeout=5,
                )
                if rr.status_code == 200:
                    releases = rr.json().get('releases', [])
                    if not releases:
                        raise ValueError('No release metadata')
                    rid = releases[0]['id']
                    dr = requests.get(
                        f'https://api.stlouisfed.org/fred/release/dates?release_id={rid}&api_key={FRED_KEY}&file_type=json&realtime_start={ts}&realtime_end={te}&include_release_dates_with_no_data=true',
                        timeout=5,
                    )
                    if dr.status_code == 200:
                        fu = [d['date'] for d in dr.json().get('release_dates', []) if d['date'] >= ts]
                        if fu:
                            nd = pd.Timestamp(fu[0]).strftime('%b %d, %Y')
            except Exception:
                pass
            rows.append({
                'Release': name, 'Last Updated': ld, 'Previous': pv,
                'Latest': lv, 'Unit': unit, 'Next Release': nd,
            })
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
        r = requests.get(
            f'https://api.stlouisfed.org/fred/releases/dates?api_key={FRED_KEY}&file_type=json&realtime_start={ps}&realtime_end={fs}&include_release_dates_with_no_data=true',
            timeout=10,
        )
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


# ── Computation helpers ────────────────────────────────────────────────────

def to_yoy(s):
    s = s.dropna()
    return s.pct_change(12) * 100

def trim(s, m):
    s = s.dropna()
    if s.empty or not m:
        return s
    return s[s.index >= s.index.max() - pd.DateOffset(months=m)]

def compute_relative(p, d):
    if p.empty or BENCH not in p.columns:
        return (pd.DataFrame(), pd.DataFrame())
    avail = [k for k in d.keys() if k in p.columns]
    if not avail:
        return (pd.DataFrame(), pd.DataFrame())
    rel = p[avail].div(p[BENCH], axis=0).dropna(how='all')
    alpha = (1 + rel.pct_change()).rolling(ROLL).apply(np.prod, raw=True) - 1
    return (rel, alpha)

def reindex_from(df, bd):
    if df.empty:
        return df
    df = df[df.index >= pd.Timestamp(bd)].dropna(how='all')
    if df.empty:
        return df
    base = df.iloc[0].replace(0, np.nan)
    return df.div(base, axis=1)

def src_ann(y=-0.3):
    return dict(text='Source: FRED / Yahoo Finance', xref='paper', yref='paper', x=1.0, y=y, showarrow=False, font=dict(size=10, color='#888888'), xanchor='right')

def get_negative_spread_ranges(s):
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
    return f'{m} {s}'

def safe_fmt(v):
    try:
        if pd.isna(v):
            return '---'
        return f'{float(v):.2f}'
    except (ValueError, TypeError):
        return str(v)

def snap_color(row):
    st_ = [''] * len(row)
    try:
        l, p = (float(row['Latest']), float(row['Previous']))
        i = list(row.index).index('Latest')
        st_[i] = 'color:#2ca02c;font-weight:bold' if l > p else 'color:#d62728;font-weight:bold' if l < p else ''
    except (ValueError, TypeError):
        pass
    return st_

def add_src(fig, y=-0.40):
    fig.add_annotation(text=f'Source: FRED / Yahoo Finance, data as of {LAST_TRADE_STR}', xref='paper', yref='paper', x=1.0, y=y, showarrow=False, font=dict(size=10, color='#888888'), xanchor='right')

def compute_volume_zscore(v, lb=ZSCORE_LOOKBACK):
    v = v.dropna()
    if v.empty:
        return pd.Series(dtype=float)
    rm = v.rolling(lb, min_periods=60).mean()
    rs = v.rolling(lb, min_periods=60).std().replace(0, np.nan)
    return ((v - rm) / rs).clip(-3, 3).dropna()

def compute_flow_proxy_z(P, V, t, lb=ZSCORE_LOOKBACK):
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
    if P.empty or 'RSP' not in P.columns or 'SPY' not in P.columns:
        return pd.Series(dtype=float)
    r, s = (P['RSP'].dropna(), P['SPY'].dropna())
    c = r.index.intersection(s.index)
    if len(c) == 0:
        return pd.Series(dtype=float)
    return (r.loc[c] / s.loc[c]).dropna()

def compute_rotation_ratio(P, smooth=21, nw=252):
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
    def cz(v):
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
    def c(v):
        if pd.isna(v):
            return ''
        return 'color:#2ca02c' if v > 0 else 'color:#d62728' if v < 0 else ''
    s = df.style
    for col in [x for x in ['1D Ret %', 'Contribution', '5D Ret %', '1M Ret %'] if x in df.columns]:
        s = s.map(c, subset=[col])
    return s.format({'1D Ret %': '{:+.2f}', 'Contribution': '{:+.3f}', '5D Ret %': '{:+.2f}', '1M Ret %': '{:+.2f}'}, na_rep='---')

def build_holdings_attr(etf, P):
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
        rows.append({
            'Ticker': t, 'Name': n, 'Weight': f'{w:.0%}',
            '1D Ret %': round(sr, 2), 'Contribution': round(co, 3),
            '5D Ret %': round(r5, 2) if not np.isnan(r5) else np.nan,
            '1M Ret %': round(r1m, 2) if not np.isnan(r1m) else np.nan,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df['_ac'] = df['Contribution'].abs()
        df = df.sort_values('_ac', ascending=False).drop(columns=['_ac']).reset_index(drop=True)
    return (df, er, live)

def yield_curve_commentary():
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
    fig.update_layout(title=chart_title('Current Yield Curve', 'Spot rates 1M-30Y'), template='plotly_white', height=380, yaxis_title='Yield (%)', xaxis_title='Maturity', margin=dict(b=120, t=60, l=60, r=40), dragmode=False)
    add_src(fig, -0.40)
    return fig


# ══════════════════════════════════════════════════════════════════════════
# DASHBOARD LAYOUT
# ══════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:baseline">
    <h1 style="margin:0">Macro Dashboard</h1>
    <span style="color:#888;font-size:0.85rem">
        Data as of {LAST_TRADE_STR}
        &nbsp;/&nbsp; Source: FRED / Yahoo Finance
    </span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="margin:1rem 0 1.5rem;padding:0.9rem 1rem;border-radius:8px;border:1px solid #e6e6e6;background:#fafafa">
  <p style="margin:0 0 0.5rem;font-size:0.95rem;color:#222"><strong>Dashboard overview</strong>: This report combines macroeconomic series from FRED with equity and ETF data from Yahoo Finance. All data reflects the last trading day close ({LAST_TRADE_STR}) and is cached daily.</p>
  <p style="margin:0 0 0.5rem;font-size:0.85rem;color:#555">Use hover details and legend clicks to inspect each series. Hover over the <span style="display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border-radius:50%;background:#1a73e8;color:#fff;font-size:9px;font-weight:700;font-style:italic;font-family:Georgia,serif;vertical-align:middle">i</span> icons next to each chart title for definitions and reading guides.</p>
  <p style="margin:0;font-size:0.85rem;color:#555">See the <strong>Guide & Analysis</strong> tab for a walkthrough of how to interpret the dashboard, including a worked example.</p>
</div>
""", unsafe_allow_html=True)

tab0, tab1, tab2, tab3 = st.tabs(['Guide & Analysis', 'Equities', 'Fixed Income & Macro', 'Calendar'])

# Default to Equities tab on first load
if 'tab_init' not in st.session_state:
    st.session_state.tab_init = True
    components.html("""
    <script>
        const tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
        if (tabs.length > 1) tabs[1].click();
    </script>
    """, height=0)

# ── TAB 0: Guide & Analysis ────────────────────────────────────────────────
with tab0:
    st.title("Guide & Analysis")

    st.markdown("""
### About This Dashboard
This dashboard connects macroeconomic conditions with equity market behavior using data from **FRED** and **Yahoo Finance**. It is designed to help users interpret how inflation, interest rates, growth expectations, market breadth, and ETF positioning interact -- rather than viewing each signal in isolation.

### How to Use It
- **Tabs** across the top organize the dashboard into Equities, Fixed Income & Macro, and Calendar views.
- **Radio buttons and dropdowns** on each tab control the time horizon. Different charts work best at different windows: flow z-scores and candlesticks are most useful at 3-6 months, while yield curves and inflation need 3-5+ years of context.
- **Hover** over any chart for exact values. **Click legend items** to isolate or hide individual series.
- **Blue ⓘ icons** next to each chart title contain definitions and reading guides. Hover over them for a quick explanation of what each visualization shows and how to interpret it.
- **Expanders** in the Holdings section let you drill into individual stocks within each sector ETF.

### What Each Tab Covers
- **Equities**: index returns, market breadth, sector/factor relative performance, ETF flow proxies, and holdings-level attribution.
- **Fixed Income & Macro**: Treasury yields, yield curve shape, credit spreads, inflation (CPI/PCE), Fed Funds, unemployment, and GDP growth.
- **Calendar**: upcoming and recent FRED data releases, and FOMC meeting dates with outcomes and countdowns.

The dashboard is meant to be read as a **connected system**. The strongest interpretive signals come from confluence across multiple sections, not from any single chart.
""")

    st.divider()

    st.markdown("""
### Worked Example: Reading the Dashboard During the March 2026 Sell-Off

To demonstrate how to read across tabs, this section walks through what the dashboard showed during the week of March 17-21, 2026, when the Strait of Hormuz crisis escalated and Iranian forces declared the strait closed to all shipping. Brent crude surged past $100/bbl for the first time in four years, and the S&P 500 broke below its 200-day moving average near 6,620, finishing Q1 down roughly 4.3%.

Each step below includes a static chart anchored to that week so the visual always matches the narrative.
""")

    # ── Snapshot date range constants ──
    SNAP_END = pd.Timestamp('2026-03-21')
    SNAP_1M = SNAP_END - pd.DateOffset(months=1)
    SNAP_3M = SNAP_END - pd.DateOffset(months=3)
    SNAP_6M = SNAP_END - pd.DateOffset(months=6)
    SNAP_12M = SNAP_END - pd.DateOffset(months=12)

    # Load data once for all snapshot charts
    try:
        snap_prices, snap_volumes = fetch_equity()
    except Exception:
        snap_prices, snap_volumes = pd.DataFrame(), pd.DataFrame()

    # ── Step 1: Index Returns ──
    st.markdown("""
**Step 1 — U.S. Major Indices (Equities tab).** The index chart showed all four benchmarks turning sharply negative over the 1M window. Russell 2000 underperformed the most, consistent with small-caps bearing the brunt of growth scares. The Dow held up slightly better, reflecting its heavier weighting toward industrials and energy names that benefited from the oil spike.
""")
    try:
        fig_snap_idx = go.Figure()
        snap_idx_colors = {'SPY': '#1f77b4', 'QQQ': '#ff7f0e', 'IWM': '#2ca02c', 'DIA': '#d62728'}
        for t, n in INDICES.items():
            if t in snap_prices.columns:
                s = snap_prices[t].dropna()
                s = s[(s.index >= SNAP_1M) & (s.index <= SNAP_END)]
                if len(s) > 1:
                    ix = (s / s.iloc[0] - 1) * 100
                    fig_snap_idx.add_trace(go.Scatter(x=ix.index, y=np.round(ix.values, 2), name=n, mode='lines', line=dict(color=snap_idx_colors.get(t, '#999'), width=2.5)))
        fig_snap_idx.add_hline(y=0, line_dash='dash', line_color='gray', line_width=1)
        fig_snap_idx.update_layout(title='U.S. Major Indices — 1M cumulative return (as of Mar 21, 2026)', template='plotly_white', height=340, yaxis_title='Return (%)', margin=dict(b=80, t=40, l=50, r=30), legend=dict(orientation='h', yanchor='top', y=-0.18, x=0.5, xanchor='center', font=dict(size=11)), dragmode=False)
        st.plotly_chart(fig_snap_idx, use_container_width=True, config=PCFG)
    except Exception:
        st.info('Snapshot chart unavailable.')

    # ── Step 2: Positioning ──
    st.markdown("""
**Step 2 — Daily Positioning Feed (Equities tab).** The Macro vs Micro chart spiked above 0.90, signaling that cross-sector dispersion dominated over stock-level moves. This confirmed the sell-off was macro-driven (geopolitical shock) rather than an idiosyncratic earnings event. The Breadth indicator fell, indicating the decline was concentrating in mega-cap growth names rather than spreading evenly. The Cyclical/Defensive ratio dropped sharply as investors rotated out of cyclicals and into safer sectors.
""")
    snap_pos_l, snap_pos_r = st.columns(2)
    with snap_pos_l:
        try:
            rr_pct_snap, _ = compute_rotation_ratio(snap_prices)
            rt_snap = rr_pct_snap[(rr_pct_snap.index >= SNAP_12M) & (rr_pct_snap.index <= SNAP_END)]
            fig_snap_rot = go.Figure()
            fig_snap_rot.add_trace(go.Scatter(x=rt_snap.index, y=rt_snap.values, mode='lines', line=dict(color='#1f77b4', width=2), showlegend=False))
            fig_snap_rot.add_hline(y=0.5, line_dash='dash', line_color='gray')
            fig_snap_rot.add_hrect(y0=0.25, y1=0.75, fillcolor='gray', opacity=0.08, line_width=0)
            fig_snap_rot.update_layout(title='Macro vs Micro — 12M (as of Mar 21)', template='plotly_white', height=300, yaxis_title='%-tile', yaxis=dict(range=[0, 1], dtick=0.25), margin=dict(b=50, t=40, l=45, r=25), dragmode=False)
            st.plotly_chart(fig_snap_rot, use_container_width=True, config=PCFG)
        except Exception:
            st.info('Snapshot chart unavailable.')
    with snap_pos_r:
        try:
            cy_snap = snap_prices[list(SECTORS_CYCLICAL.keys())].pct_change().mean(axis=1)
            de_snap = snap_prices[list(SECTORS_DEFENSIVE.keys())].pct_change().mean(axis=1)
            ratio_snap = (1 + cy_snap).cumprod() / (1 + de_snap).cumprod()
            rt2_snap = ratio_snap[(ratio_snap.index >= SNAP_12M) & (ratio_snap.index <= SNAP_END)]
            ri2_snap = rt2_snap / rt2_snap.iloc[0]
            fig_snap_cd = go.Figure()
            fig_snap_cd.add_trace(go.Scatter(x=ri2_snap.index, y=ri2_snap.values, mode='lines', line=dict(color='#2ca02c', width=2), showlegend=False))
            fig_snap_cd.add_hline(y=1.0, line_dash='dash', line_color='gray')
            fig_snap_cd.update_layout(title='Cyclical / Defensive — 12M (as of Mar 21)', template='plotly_white', height=300, yaxis_title='Ratio', margin=dict(b=50, t=40, l=45, r=25), dragmode=False)
            st.plotly_chart(fig_snap_cd, use_container_width=True, config=PCFG)
        except Exception:
            st.info('Snapshot chart unavailable.')

    # ── Step 3: Composite ──
    st.markdown("""
**Step 3 — Sector Composite Table (Equities tab).** Energy (XLE) surged to the top of the Composite ranking with strongly positive flow z-scores, reflecting the oil price spike. Defensive sectors like Consumer Staples (XLP) and Utilities (XLU) also showed positive or neutral composites. Meanwhile, Info Tech (XLK) and Consumer Discretionary (XLY) fell to the bottom, with negative flow z-scores indicating distribution.
""")

    # ── Step 4: ETF Flows ──
    st.markdown("""
**Step 4 — Individual ETF Flows (Equities tab).** Switching to the 3M window, the flow charts for XLE showed a clear accumulation pattern: rising prices confirmed by positive (green) flow z bars. Tech and discretionary charts showed the opposite: price declines accompanied by red flow bars, suggesting investors were actively reducing exposure rather than passively riding losses.
""")

    def _snap_flow(t, lbl, snap_start, snap_end):
        """Build a snapshot flow chart for one ETF."""
        if snap_prices.empty or snap_volumes.empty or t not in snap_prices.columns or t not in snap_volumes.columns:
            return None
        p = snap_prices[t].dropna()
        p = p[(p.index >= snap_start) & (p.index <= snap_end)]
        if len(p) < 10:
            return None
        pi = (p / p.iloc[0] - 1) * 100
        fz = compute_flow_proxy_z(snap_prices, snap_volumes, t)
        if fz.empty:
            return None
        fz = fz[(fz.index >= snap_start) & (fz.index <= snap_end)]
        cm = pi.index.intersection(fz.index)
        if len(cm) < 5:
            return None
        pi, fz = pi.loc[cm], fz.loc[cm]
        bc = ['#2ca02c' if v >= 0 else '#d62728' for v in fz.values]
        fig = make_subplots(specs=[[{'secondary_y': True}]])
        fig.add_trace(go.Bar(x=fz.index, y=fz.values, name='Flow Z', marker_color=bc, opacity=0.35, showlegend=False), secondary_y=True)
        fig.add_trace(go.Scatter(x=pi.index, y=pi.values, name='Return %', mode='lines', line=dict(color='#1f77b4', width=2.5)), secondary_y=False)
        fig.add_hline(y=0, line_dash='dash', line_color='gray', line_width=0.8, secondary_y=False)
        fig.update_layout(title=f'{lbl} ({t}) — 3M (as of Mar 21, 2026)', template='plotly_white', height=300, margin=dict(b=50, t=40, l=50, r=40), showlegend=False, dragmode=False, bargap=0.1)
        fig.update_yaxes(title_text='Return %', secondary_y=False)
        fig.update_yaxes(title_text='Flow Z', secondary_y=True, range=[-3.5, 3.5], dtick=1, showgrid=False)
        return fig

    snap_flow_l, snap_flow_r = st.columns(2)
    with snap_flow_l:
        f = _snap_flow('XLE', 'Energy', SNAP_3M, SNAP_END)
        if f:
            st.plotly_chart(f, use_container_width=True, config=PCFG)
        else:
            st.info('XLE snapshot unavailable.')
    with snap_flow_r:
        f = _snap_flow('XLK', 'Info. Tech', SNAP_3M, SNAP_END)
        if f:
            st.plotly_chart(f, use_container_width=True, config=PCFG)
        else:
            st.info('XLK snapshot unavailable.')

    # ── Step 5: Holdings ──
    st.markdown("""
**Step 5 — Holdings Attribution (Equities tab).** Expanding XLE revealed that Exxon (XOM, ~23% weight) and Chevron (CVX, ~16%) together explained the majority of the ETF's daily gains. Expanding XLK showed that despite Apple and Microsoft holding up relatively well, Nvidia and AMD dragged the sector down, consistent with higher-beta semiconductor names leading losses during risk-off episodes.
""")

    # ── Step 6: Fixed Income ──
    st.markdown("""
**Step 6 — Fixed Income & Macro tab.** Treasury yields fell as investors sought safety, with the 10Y dropping and the 2Y-10Y spread steepening. Credit spreads (HY OAS) widened, confirming a broad risk-off move. The CPI and PCE charts showed inflation still above the 2% target, which meant the Fed had limited room to cut rates in response to the shock. The Fed Funds rate held steady, and the yield curve commentary confirmed a steepening trend over the prior three months.
""")
    snap_fi_l, snap_fi_r = st.columns(2)
    with snap_fi_l:
        try:
            fig_snap_yld = go.Figure()
            for sid, lbl, clr in [('DGS2', '2Y', '#1f77b4'), ('DGS10', '10Y', '#ff7f0e'), ('DGS30', '30Y', '#2ca02c')]:
                s = fetch_fred(sid)
                s = s[(s.index >= SNAP_6M) & (s.index <= SNAP_END)]
                fig_snap_yld.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines', line=dict(color=clr, width=2)))
            fig_snap_yld.update_layout(title='Treasury Yields — 6M (as of Mar 21)', template='plotly_white', height=300, yaxis_title='Yield (%)', margin=dict(b=60, t=40, l=50, r=30), legend=dict(orientation='h', yanchor='top', y=-0.18, x=0.5, xanchor='center', font=dict(size=11)), dragmode=False)
            st.plotly_chart(fig_snap_yld, use_container_width=True, config=PCFG)
        except Exception:
            st.info('Snapshot chart unavailable.')
    with snap_fi_r:
        try:
            fig_snap_cr = go.Figure()
            for sid, lbl in CREDIT.items():
                s = fetch_fred(sid)
                s = s[(s.index >= SNAP_6M) & (s.index <= SNAP_END)] * 100
                fig_snap_cr.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            fig_snap_cr.update_layout(title='Credit Spreads (OAS) — 6M (as of Mar 21)', template='plotly_white', height=300, yaxis_title='bps', margin=dict(b=60, t=40, l=50, r=30), legend=dict(orientation='h', yanchor='top', y=-0.18, x=0.5, xanchor='center', font=dict(size=11)), dragmode=False)
            st.plotly_chart(fig_snap_cr, use_container_width=True, config=PCFG)
        except Exception:
            st.info('Snapshot chart unavailable.')

    # ── Step 7: Calendar ──
    st.markdown("""
**Step 7 — Calendar tab.** The FOMC was scheduled for March 18-19, adding a policy catalyst directly into the sell-off window. The release calendar showed CPI and retail sales prints landing in the same week. This confluence of geopolitical shock, inflation data, and a Fed decision created the conditions for elevated volatility.

**Synthesis.** No single chart told this story. The index chart showed something was wrong. The positioning feed confirmed it was macro-driven and concentrated. The sector table identified who was winning and losing. The flow charts confirmed active reallocation, not just passive drawdowns. The FI tab explained why the Fed was boxed in. And the calendar revealed why that particular week was so volatile. This is how the dashboard is designed to be read: as connected layers that build toward a narrative, not as isolated metrics.
""")

    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>', unsafe_allow_html=True)
    st.caption("This worked example is anchored to March 17-21, 2026 for illustration purposes. The snapshot charts above are frozen to that date window. The live dashboard tabs reflect current conditions. The analytical framework — moving from indices to positioning to sectors to flows to macro to catalysts — applies regardless of the date.")

# ── TAB 1: Equities ───────────────────────────────────────────────────────
with tab1:
    with st.spinner('Loading equity data...'):
        prices, volumes = fetch_equity()

    period_opts = {'Past 12M': None, 'Since 2015': '2015-01-01', 'Since 2020': '2020-01-01', 'Since 2025': '2025-01-01'}

    hdr_l, hdr_r = st.columns(2)

    with hdr_l:
        label_info('U.S. Major Indices', TIP_INDICES)
        idx_period = st.radio('Period', ['1M', '3M', '6M', 'YTD', '1Y'], horizontal=True, key='idx_period')
        latest = prices.index.max()
        idx_start = pd.Timestamp(f'{latest.year}-01-01') if idx_period == 'YTD' else latest - pd.DateOffset(months={'1M': 1, '3M': 3, '6M': 6, '1Y': 12}[idx_period])
        idx_colors = {'SPY': '#1f77b4', 'QQQ': '#ff7f0e', 'IWM': '#2ca02c', 'DIA': '#d62728'}
        fig_idx = go.Figure()
        for t, n in INDICES.items():
            if t in prices.columns:
                s = prices[t].dropna()
                s = s[s.index >= idx_start]
                if len(s) > 1:
                    ix = (s / s.iloc[0] - 1) * 100
                    fig_idx.add_trace(go.Scatter(
                        x=ix.index, y=np.round(ix.values, 2), name=n, mode='lines',
                        line=dict(color=idx_colors.get(t, '#999'), width=2.5),
                        customdata=np.round(s.values, 2),
                        hovertemplate=f'<b>{n}</b><br>Date: %{{x|%b %d, %Y}}<br>Return: %{{y:+.2f}}%<br>Level: %{{customdata:,.2f}}<extra></extra>',
                    ))
        fig_idx.add_hline(y=0, line_dash='dash', line_color='gray', line_width=1)
        fig_idx.update_layout(
            title=chart_title('U.S. Major Indices', f'{idx_period} cumulative return'),
            template='plotly_white', height=460, yaxis_title='Return (%)',
            margin=dict(b=130, t=40, l=50, r=30),
            legend=dict(orientation='h', yanchor='top', y=-0.15, x=0.5, xanchor='center', font=dict(size=11)),
            dragmode=False, font=dict(size=11),
        )
        add_src(fig_idx, -0.42)
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
                rows.append({
                    'Ticker': t, 'Name': n, '1D': round(r1, 2),
                    '5D': round(r5, 2) if not np.isnan(r5) else np.nan,
                    '1M': round(r1m, 2) if not np.isnan(r1m) else np.nan,
                    '12M': round(r12m, 2) if not np.isnan(r12m) else np.nan,
                    'Flow Z': fzv, 'Composite': cv,
                })
            except Exception:
                continue

        df_pos = pd.DataFrame(rows)
        if not df_pos.empty and 'Composite' in df_pos.columns:
            df_pos = df_pos.dropna(subset=['Composite']).sort_values('Composite', ascending=False).reset_index(drop=True)
            t3, b3 = (df_pos.head(3), df_pos.tail(3))

            def _sty(d):
                def cz(v):
                    if pd.isna(v): return ''
                    if v >= 2: return 'color:#2ca02c;font-weight:bold'
                    if v <= -2: return 'color:#d62728;font-weight:bold'
                    if v >= 1: return 'color:#2ca02c'
                    if v <= -1: return 'color:#d62728'
                    return ''
                def cr2(v):
                    if pd.isna(v): return ''
                    return 'color:#2ca02c' if v > 0 else 'color:#d62728' if v < 0 else ''
                s = d.style
                for c in ['Flow Z', 'Composite']:
                    if c in d.columns: s = s.map(cz, subset=[c])
                for c in ['1D', '5D', '1M', '12M']:
                    if c in d.columns: s = s.map(cr2, subset=[c])
                fmt = {c: '{:+.2f}' for c in ['1D', '5D', '1M', '12M', 'Flow Z', 'Composite'] if c in d.columns}
                return s.format(fmt, na_rep='---')

            label_info('Sector Positioning by Composite', TIP_COMPOSITE)
            st.caption('Composite = (Flow Z + Signed Vol Z + Return Z) / 3 -- all 252-day rolling, clipped +/-3')
            st.markdown('**Top 3 by Composite**')
            st.dataframe(_sty(t3.reset_index(drop=True)), hide_index=True, use_container_width=True, height=152)
            st.markdown('**Bottom 3 by Composite**')
            st.dataframe(_sty(b3.reset_index(drop=True)), hide_index=True, use_container_width=True, height=152)
            st.markdown(SRC_BOTH, unsafe_allow_html=True)

    st.divider()

    # ── Benchmark Price Action ─────────────────────────────────────────────
    hdr('Benchmark Price Action', TIP_CANDLE)
    st.caption('Candlestick plot for SPY showing recent price action; hover for OHLC details and use legend controls to isolate series.')
    spy_window = st.selectbox('SPY candlestick window', ['3M', '6M', '1Y', 'Since 2015'], key='spy_window', index=1)
    spy_start = {
        '3M': prices.index.max() - pd.DateOffset(months=3),
        '6M': prices.index.max() - pd.DateOffset(months=6),
        '1Y': prices.index.max() - pd.DateOffset(years=1),
        'Since 2015': pd.Timestamp(START),
    }[spy_window]
    spy_ohlc = fetch_benchmark_ohlc(start=spy_start.strftime('%Y-%m-%d'))
    if not spy_ohlc.empty:
        fig_spy = go.Figure()
        fig_spy.add_trace(go.Candlestick(
            x=spy_ohlc.index, open=spy_ohlc['Open'], high=spy_ohlc['High'],
            low=spy_ohlc['Low'], close=spy_ohlc['Close'],
            increasing_line_color='#2ca02c', decreasing_line_color='#d62728', name=BENCH,
        ))
        fig_spy.add_trace(go.Scatter(
            x=spy_ohlc.index, y=spy_ohlc['Close'].rolling(20).mean(),
            mode='lines', line=dict(color='#1f77b4', width=1.8), name='20D MA',
        ))
        fig_spy.update_layout(
            title=chart_title('SPY Candlestick', 'Price action with 20-day moving average'),
            template='plotly_white', height=460, margin=dict(b=160, t=60, l=60, r=40),
            legend=LEG, dragmode=False,
        )
        fig_spy.update_yaxes(title_text='Price ($)')
        add_src(fig_spy, -0.52)
        st.plotly_chart(fig_spy, use_container_width=True, key='fig_spy_candle', config=PCFG)
    else:
        st.info('SPY candlestick data unavailable.')

    # ── Daily Positioning Feed ─────────────────────────────────────────────
    hdr('Daily Positioning Feed', TIP_POSITIONING)
    st.caption('Macro vs Micro = between-sector vs within-sector dispersion (252d percentile rank) / Breadth = RSP/SPY ratio (equal-weight vs cap-weight) / Cyclical/Defensive = equal-weight basket ratio / SPY Volume = volume z-scored against 1Y median.')
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
                chart_label(f'Macro vs Micro -- {rv:.2f} ({rl})', TIP_MACRO_MICRO)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=rt.index, y=rt.values, mode='lines', line=dict(color='#1f77b4', width=2), showlegend=False))
                fig.add_hline(y=0.5, line_dash='dash', line_color='gray')
                fig.add_hrect(y0=0.25, y1=0.75, fillcolor='gray', opacity=0.08, line_width=0)
                fig.update_layout(
                    title=dict(text=f"<span style='font-size:11px;color:#666'>>0.75 sector-driven / <0.25 stock-driven</span>", font=dict(size=12)),
                    template='plotly_white', height=380, yaxis_title='%-tile',
                    yaxis=dict(range=[0, 1], dtick=0.25),
                    margin=dict(b=65, t=35, l=45, r=25), dragmode=False,
                )
                add_src(fig, -0.15)
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
                chart_label(f'Breadth -- {bn:.4f} ({bl})', TIP_BREADTH)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=bi.index, y=bi.values, mode='lines', line=dict(color='#ff7f0e', width=2), showlegend=False))
                fig.add_hline(y=1.0, line_dash='dash', line_color='gray')
                fig.update_layout(
                    title=dict(text=f"<span style='font-size:11px;color:#666'>RSP/SPY / rising = broadening</span>", font=dict(size=12)),
                    template='plotly_white', height=380, yaxis_title='Indexed',
                    margin=dict(b=65, t=35, l=45, r=25), dragmode=False,
                )
                add_src(fig, -0.15)
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
            chart_label(f'Cyclical / Defensive -- {cn:.4f} ({cl})', TIP_CYC_DEF)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ri2.index, y=ri2.values, mode='lines', line=dict(color='#2ca02c', width=2), showlegend=False))
            fig.add_hline(y=1.0, line_dash='dash', line_color='gray')
            fig.update_layout(
                title=dict(text=f"<span style='font-size:11px;color:#666'>Rising = risk-on / falling = risk-off</span>", font=dict(size=12)),
                template='plotly_white', height=380, yaxis_title='Ratio',
                margin=dict(b=65, t=35, l=45, r=25), dragmode=False,
            )
            add_src(fig, -0.15)
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
            chart_label(f'SPY Volume -- {szn:+.2f}σ today', TIP_SPY_VOL)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=sz.index, y=sz.values, marker_color=bc, opacity=0.7, showlegend=False))
            fig.add_hline(y=0, line_dash='dash', line_color='gray', line_width=1)
            fig.add_hline(y=2, line_dash='dot', line_color='#2ca02c', line_width=0.8)
            fig.add_hline(y=-2, line_dash='dot', line_color='#d62728', line_width=0.8)
            fig.update_layout(
                title=dict(text=f"<span style='font-size:11px;color:#666'>0 = 1Y median / 3M window / +/-3</span>", font=dict(size=12)),
                template='plotly_white', height=380, yaxis_title='Z-Score',
                yaxis=dict(range=[-3.5, 3.5], dtick=1),
                margin=dict(b=65, t=35, l=45, r=25), bargap=0.15, dragmode=False,
            )
            add_src(fig, -0.15)
            st.plotly_chart(fig, use_container_width=True, key='fig_spy_vol', config=PCFG)
        except Exception:
            st.info('SPY volume unavailable.')

    st.divider()

    # ── Relative Performance ───────────────────────────────────────────────
    hdr('Relative Performance', TIP_RELATIVE)
    pf = st.radio('Period', list(period_opts.keys()), horizontal=True, key='pf')
    base = period_opts[pf] or (prices.index.max() - pd.DateOffset(months=12)).strftime('%Y-%m-%d')

    def _build_pair(ad, gl, bd, ks):
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
            fig.update_layout(
                title=chart_title(f'{gl} Relative Performance', 'ETF / SPY, indexed to 1.0'),
                template='plotly_white', height=380, margin=dict(b=110, t=50, l=55, r=30),
                legend=LEG, dragmode=False,
            )
            add_src(fig, -0.38)
            st.plotly_chart(fig, use_container_width=True, key=f'rel_{ks}', config=PCFG)
        with cr2:
            fig = go.Figure()
            for t, n in ad.items():
                if t in al.columns:
                    c = SECTOR_COLORS.get(t) or FACTOR_COLORS.get(t)
                    fig.add_trace(go.Scatter(x=al.index, y=al[t], name=n, mode='lines', line=dict(color=c, width=2) if c else dict(width=2)))
            fig.add_hline(y=0.0, line_dash='dash', line_color='gray')
            fig.update_layout(
                title=chart_title(f'{gl} Rolling 6M Alpha', 'Compounded 126-day relative return'),
                template='plotly_white', height=380, margin=dict(b=110, t=50, l=55, r=30),
                legend=LEG, dragmode=False,
            )
            add_src(fig, -0.38)
            st.plotly_chart(fig, use_container_width=True, key=f'alpha_{ks}', config=PCFG)

    label_info('Factors', "Factor ETFs isolate specific investment styles. Min Vol = low-volatility stocks, Momentum = recent winners, Quality = profitable companies, Size = small-caps, Value = cheap stocks, Yield = high-dividend payers. Relative performance shows which style is beating the broad market.")
    _build_pair(FACTORS, 'Factor', base, 'factors')
    label_info('Cyclical-Tilt Sectors', "Cyclical sectors tend to rise and fall with economic growth. Tech, Financials, Energy, Industrials, and Materials are sensitive to business cycles. When these outperform, it usually signals economic optimism.")
    _build_pair(SECTORS_CYCLICAL, 'Cyclical-Tilt', base, 'cyclical')
    label_info('Defensive-Tilt Sectors', "Defensive sectors provide essential goods and services people buy regardless of the economy -- utilities, healthcare, staples, real estate. When these outperform, it often signals investors are seeking safety.")
    _build_pair(SECTORS_DEFENSIVE, 'Defensive-Tilt', base, 'defensive')

    st.divider()

    # ── Individual ETF Flow & Price ────────────────────────────────────────
    hdr('Individual ETF -- Flow & Price', TIP_FLOW_SECTION)
    st.caption('Return % from window start / flow z-score (252d rolling, clipped +/-3) / green = accumulation, red = distribution')
    cwopt = st.radio('Chart window', ['3M', '6M', '1Y'], horizontal=True, key='etf_cw', index=1)
    cbd = {'3M': 63, '6M': 126, '1Y': 252}[cwopt]

    def build_flow_chart(t, lbl, P, V, w):
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
        fig.update_layout(
            title=dict(
                text=f"<b>{lbl}</b> ({t})<br><span style='font-size:11px;color:#666'>Return % / Flow z (252d) / green = accumulation</span>",
                font=dict(size=13),
            ),
            template='plotly_white', height=350, margin=dict(b=110, t=65, l=50, r=40),
            legend=dict(orientation='h', yanchor='top', y=-0.15, x=0.5, xanchor='center', font=dict(size=11)),
            dragmode=False, bargap=0.1,
        )
        fig.update_yaxes(title_text='Return %', secondary_y=False)
        fig.update_yaxes(title_text='Flow Z', secondary_y=True, range=[-3.5, 3.5], dtick=1, showgrid=False)
        add_src(fig, -0.38)
        return fig

    chart_label('Sector ETFs', 'Each chart shows one of the 11 S&P 500 sector ETFs. Sectors group companies by industry -- Tech, Financials, Energy, Healthcare, etc. Comparing sectors reveals which parts of the economy are attracting or losing investor interest.')
    sc = st.columns(3)
    for i, (t, n) in enumerate(SECTORS.items()):
        f = build_flow_chart(t, n, prices, volumes, cbd)
        if f:
            with sc[i % 3]:
                st.plotly_chart(f, use_container_width=True, key=f'flow_{t}', config=PCFG)

    chart_label('Factor ETFs', 'Factors are investment styles like Momentum (recent winners), Value (cheap stocks), Quality (profitable companies), Min Vol (low volatility), Size (small-caps), and Yield (high dividends). Factor rotation shows which styles are in or out of favor.')
    fc = st.columns(3)
    for i, (t, n) in enumerate(FACTORS.items()):
        f = build_flow_chart(t, n, prices, volumes, cbd)
        if f:
            with fc[i % 3]:
                st.plotly_chart(f, use_container_width=True, key=f'flow_{t}', config=PCFG)

    st.divider()

    # ── Altair Views ───────────────────────────────────────────────────────
    st.subheader('Altair Views')
    st.caption('A pair of lighter-weight Altair visuals to make the cross-section easier to scan.')

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
                chart_label('Sector Return Heatmap', TIP_HEATMAP)
                heat = alt.Chart(alt_df).mark_rect(cornerRadius=4).encode(
                    x=alt.X('Ticker:N', sort=list(SECTORS.keys()), title=None),
                    y=alt.Y('Metric:N', title=None),
                    color=alt.Color('Value:Q', scale=alt.Scale(scheme='redyellowgreen'), title='Return %'),
                    tooltip=['Sector:N', 'Ticker:N', 'Metric:N', alt.Tooltip('Value:Q', format='.2f')],
                ).transform_fold(['1M Return', '5D Return'], as_=['Metric', 'Value']).properties(height=160)
                st.altair_chart(heat, use_container_width=True)
                st.markdown(f'<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:-0.5rem">Source: FRED / Yahoo Finance, data as of {LAST_TRADE_STR}</p>', unsafe_allow_html=True)
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
                chart_label('Macro Pulse', TIP_MACRO_PULSE)
                long_macro = macro_df.melt(id_vars='Date', var_name='Series', value_name='Value')
                line = alt.Chart(long_macro).mark_line(point=False).encode(
                    x=alt.X('Date:T', title=None),
                    y=alt.Y('Value:Q', title=None),
                    color=alt.Color('Series:N', legend=alt.Legend(orient='bottom')),
                    tooltip=[alt.Tooltip('Date:T'), 'Series:N', alt.Tooltip('Value:Q', format='.2f')],
                ).properties(height=220)
                st.altair_chart(line, use_container_width=True)
                st.markdown(f'<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:-0.5rem">Source: FRED, data as of {LAST_TRADE_STR}</p>', unsafe_allow_html=True)
            else:
                st.info('Not enough macro data for the Altair line chart.')
        except Exception:
            st.info('Altair macro chart unavailable.')

    st.divider()

    # ── Sector ETF Holdings & Daily Attribution ────────────────────────────
    hdr('Sector ETF Holdings & Daily Attribution', TIP_HOLDINGS)
    st.caption('Expand any sector to see top holdings, weight, daily return, and contribution (weight x return). Sorted by contribution. Weights are hardcoded and updated biannually -- minor drift expected between updates.')

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


# ── TAB 2: Fixed Income & Macro ───────────────────────────────────────────
with tab2:
    label_info('Key Rates & Macro Snapshot', TIP_FI_METRICS)
    ri1, ri2, ri3, ri4, ri5, ri6 = st.columns(6)
    for col, sid, lbl, sd, u in [
        (ri1, 'DGS2', '2Y Treasury', True, '%'),
        (ri2, 'DGS10', '10Y Treasury', True, '%'),
        (ri3, 'DGS30', '30Y Treasury', True, '%'),
        (ri4, 'FEDFUNDS', 'Fed Funds', False, '%'),
        (ri5, 'CPIAUCSL', 'CPI YoY', True, '%'),
        (ri6, 'T10Y2Y', '10Y-2Y', True, '%'),
    ]:
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
        chart_label('Current Yield Curve', TIP_YIELD_CURVE)
        st.plotly_chart(build_yield_curve(), use_container_width=True, key='yc_rates', config=PCFG)
        c = yield_curve_commentary()
        if c:
            st.caption(c)

    with yld_col:
        chart_label('Treasury Yields', TIP_YIELDS_HIST)
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        fig = go.Figure()
        for i, (sid, lbl) in enumerate(YIELDS.items()):
            try:
                s = trim(fetch_fred(sid), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines', line=dict(color=colors[i], width=2)))
            except Exception:
                pass
        fig.update_layout(
            title=dict(text="<span style='font-size:11px;color:#888'>Constant-maturity daily</span>", font=dict(size=12)),
            template='plotly_white', height=380, yaxis_title='Yield (%)',
            margin=dict(b=110, t=35, l=55, r=30), legend=LEG, dragmode=False,
        )
        add_src(fig, -0.38)
        st.plotly_chart(fig, use_container_width=True, key='fig_yields', config=PCFG)

    r2a, r2b, r2c = st.columns(3)
    with r2a:
        chart_label('Curve Spreads', TIP_SPREADS)
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
        fig.update_layout(
            title=dict(text="<span style='font-size:11px;color:#888'>Below 0 = inverted / shaded = contiguous inversion</span>", font=dict(size=12)),
            template='plotly_white', height=340, yaxis_title='Spread (%)',
            margin=dict(b=110, t=35, l=55, r=30), legend=LEG, dragmode=False,
        )
        add_src(fig, -0.38)
        st.plotly_chart(fig, use_container_width=True, key='fig_spreads', config=PCFG)

    with r2b:
        chart_label('Real Yield & Breakeven', TIP_REAL_YIELD)
        fig = go.Figure()
        for sid, lbl in [('DFII10', '10Y Real Yield'), ('T10YIE', '10Y Breakeven')]:
            try:
                s = trim(fetch_fred(sid), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            except Exception:
                pass
        fig.update_layout(
            title=dict(text="<span style='font-size:11px;color:#888'>TIPS + implied inflation</span>", font=dict(size=12)),
            template='plotly_white', height=340, yaxis_title='%',
            margin=dict(b=110, t=35, l=55, r=30), legend=LEG, dragmode=False,
        )
        add_src(fig, -0.38)
        st.plotly_chart(fig, use_container_width=True, key='fig_realyield', config=PCFG)

    with r2c:
        chart_label('Credit Spreads (OAS)', TIP_CREDIT)
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
        fig.update_layout(
            title=dict(text="<span style='font-size:11px;color:#888'>Wider = risk-off</span>", font=dict(size=12)),
            template='plotly_white', height=340, yaxis_title='bps',
            margin=dict(b=110, t=35, l=55, r=30), legend=LEG, dragmode=False,
        )
        add_src(fig, -0.38)
        st.plotly_chart(fig, use_container_width=True, key='fig_credit', config=PCFG)

    st.divider()

    il, ir = st.columns(2)
    with il:
        chart_label('CPI & Core CPI', TIP_CPI)
        fig = go.Figure()
        for sid, lbl in [('CPIAUCSL', 'CPI'), ('CPILFESL', 'Core CPI')]:
            try:
                s = trim(to_yoy(fetch_fred(sid)), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            except Exception:
                pass
        fig.add_hline(y=2.0, line_dash='dash', line_color='red', annotation_text='2%', annotation_position='bottom right')
        fig.update_layout(
            title=dict(text="<span style='font-size:11px;color:#888'>YoY %</span>", font=dict(size=12)),
            template='plotly_white', height=360, yaxis_title='YoY %',
            margin=dict(b=110, t=35, l=55, r=30), legend=LEG, dragmode=False,
        )
        add_src(fig, -0.38)
        st.plotly_chart(fig, use_container_width=True, key='fig_cpi', config=PCFG)

    with ir:
        chart_label('PCE & Core PCE', TIP_PCE)
        fig = go.Figure()
        for sid, lbl in [('PCEPI', 'PCE'), ('PCEPILFE', 'Core PCE')]:
            try:
                s = trim(to_yoy(fetch_fred(sid)), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines'))
            except Exception:
                pass
        fig.add_hline(y=2.0, line_dash='dash', line_color='red', annotation_text='2%', annotation_position='bottom right')
        fig.update_layout(
            title=dict(text="<span style='font-size:11px;color:#888'>YoY % / Fed's preferred gauge</span>", font=dict(size=12)),
            template='plotly_white', height=360, yaxis_title='YoY %',
            margin=dict(b=110, t=35, l=55, r=30), legend=LEG, dragmode=False,
        )
        add_src(fig, -0.38)
        st.plotly_chart(fig, use_container_width=True, key='fig_pce', config=PCFG)

    el, gl = st.columns(2)
    with el:
        chart_label('Fed Funds & Unemployment', TIP_FF_UNEMP)
        fig = go.Figure()
        for sid, lbl, clr in [('FEDFUNDS', 'Fed Funds', '#1f77b4'), ('UNRATE', 'Unemployment', '#ff7f0e')]:
            try:
                s = trim(fetch_fred(sid), rmons)
                fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lbl, mode='lines', line=dict(color=clr, width=2)))
            except Exception:
                pass
        fig.update_layout(
            title=dict(text="<span style='font-size:11px;color:#888'>Dual mandate</span>", font=dict(size=12)),
            template='plotly_white', height=360, yaxis_title='%',
            margin=dict(b=110, t=35, l=55, r=30), legend=LEG, dragmode=False,
        )
        add_src(fig, -0.38)
        st.plotly_chart(fig, use_container_width=True, key='fig_ff', config=PCFG)

    with gl:
        try:
            chart_label('Real GDP Growth', TIP_GDP)
            gdp = trim(fetch_fred('A191RL1Q225SBEA'), rmons)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=gdp.index, y=gdp.values, name='GDP Growth',
                marker_color=['#2ca02c' if v >= 0 else '#d62728' for v in gdp.values],
            ))
            fig.add_hline(y=0, line_color='black', line_width=1)
            fig.update_layout(
                title=dict(text="<span style='font-size:11px;color:#888'>QoQ annualized %</span>", font=dict(size=12)),
                template='plotly_white', height=360, yaxis_title='% QoQ Ann.',
                margin=dict(b=110, t=35, l=55, r=30), legend=LEG, dragmode=False,
            )
            add_src(fig, -0.38)
            st.plotly_chart(fig, use_container_width=True, key='fig_gdp', config=PCFG)
        except Exception:
            st.info('GDP data unavailable.')

    st.divider()
    st.markdown(f'<p style="color:#999;font-size:0.75rem;font-style:italic">{DISCLAIMER}</p>', unsafe_allow_html=True)


# ── TAB 3: Calendar ───────────────────────────────────────────────────────
with tab3:
    cl, cr3 = st.columns([3, 1])

    with cl:
        hdr('Upcoming Releases', TIP_SNAPSHOT)
        st.caption('FRED releases -- next 45 days and past 35 days')
        with st.spinner('Loading...'):
            snap = fetch_release_snapshot()
            if not snap.empty:
                st.dataframe(
                    snap.style.apply(snap_color, axis=1).format({'Previous': safe_fmt, 'Latest': safe_fmt}, na_rep='---'),
                    hide_index=True, use_container_width=True, height=420,
                )
                st.markdown(SRC_FRED, unsafe_allow_html=True)

        st.divider()

        hdr('Release Calendar', TIP_CALENDAR)
        st.caption('FRED release schedule -- past 35 days and next 45 days / yellow = today / gray = past')
        with st.spinner('Loading calendar...'):
            cal = fetch_fred_calendar()
            if cal.empty:
                st.info('No calendar data available.')
            else:
                tts = pd.Timestamp.today().normalize()
                def cs(row):
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
        hdr('FOMC Dates', TIP_FOMC, tag="h3")
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
