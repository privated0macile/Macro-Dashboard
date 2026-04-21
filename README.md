# Macro Dashboard

**DS4200 Final Project — Northeastern University**

Live Streamlit dashboard connecting macroeconomic conditions with equity market behavior using data from [FRED](https://fred.stlouisfed.org/) and [Yahoo Finance](https://finance.yahoo.com/).

🔗 **[dliu-macro.streamlit.app](https://dliu-macro.streamlit.app/)**

## Overview

The dashboard helps users interpret how inflation, interest rates, growth expectations, market breadth, and ETF positioning interact — rather than viewing each signal in isolation.

**Tabs:**
- **Guide & Analysis** — project overview, how-to, and a worked interpretation example (March 2026 Strait of Hormuz sell-off) with static snapshot charts
- **Equities** — index returns, daily positioning feed, sector/factor relative performance, ETF flow proxies, holdings attribution
- **Fixed Income & Macro** — Treasury yields, yield curve, credit spreads, CPI/PCE inflation, Fed Funds, GDP
- **Calendar** — FRED release schedule, macro snapshot table, FOMC dates with outcomes and countdowns

## Tech Stack

| Component | Tool |
|---|---|
| Platform | Streamlit, deployed on Streamlit Cloud |
| Charts | Plotly (line, bar, candlestick, dual-axis), Altair (heatmap, multi-line) |
| Data | FRED API (`fredapi`), Yahoo Finance (`yfinance`) |
| Computation | pandas, numpy — rolling z-scores, flow proxies, rotation ratios |

## Repo Structure

```
app.py              # Single-file dashboard (deployed)
config.toml         # Streamlit theme (light mode)
requirements.txt    # Python dependencies
.gitignore
README.md
```

## Running Locally

```bash
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
FRED_API_KEY = "your_key_here"
```

```bash
streamlit run app.py
```

## Team

Dominic Liu, Ryan Devlin, Aidan Allajbej

Northeastern University — DS4200, Spring 2026
