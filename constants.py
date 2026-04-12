import pandas as pd

START = '2015-01-01'
BENCH = 'SPY'
ROLL = 126
CM = dict(b=120, t=60, l=60, r=40)
LEG = dict(orientation='h', yanchor='top', y=-0.25, x=0.5, xanchor='center', font=dict(size=11))
PCFG = dict(displayModeBar=False, scrollZoom=False)

DISCLAIMER = '*Disclaimer: This dashboard is for educational and informational purposes only. Nothing contained herein constitutes investment advice, a recommendation, or a solicitation to buy or sell any securities or financial instruments. The data presented may be delayed, incomplete, or inaccurate, and should not be relied upon for trading or investment decisions. Past performance is not indicative of future results. The authors and contributors assume no liability for any losses or damages arising from the use of this information. Consult a qualified financial advisor before making any investment decisions.*'
SRC_BOTH = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED / Yahoo Finance</p>'
SRC_FRED = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: FRED</p>'
SRC_YF = '<p style="color:#888;font-size:0.625rem;text-align:right;margin-top:0.25rem">Source: Yahoo Finance</p>'

ZSCORE_LOOKBACK = 252
CHART_WINDOW = 63

FACTORS = {'USMV': 'Min Vol', 'MTUM': 'Momentum', 'QUAL': 'Quality', 'SIZE': 'Size', 'VLUE': 'Value', 'HDV': 'Yield'}
SECTORS = {'XLC': 'Comm. Serv.', 'XLY': 'Cons. Disc.', 'XLP': 'Cons. Staples', 'XLE': 'Energy', 'XLF': 'Financials', 'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLK': 'Info. Tech', 'XLB': 'Materials', 'XLRE': 'Real Estate', 'XLU': 'Utilities'}
SECTORS_CYCLICAL = {'XLC': 'Comm. Serv.', 'XLY': 'Cons. Disc.', 'XLE': 'Energy', 'XLF': 'Financials', 'XLI': 'Industrials', 'XLK': 'Info. Tech', 'XLB': 'Materials'}
SECTORS_DEFENSIVE = {'XLP': 'Cons. Staples', 'XLV': 'Healthcare', 'XLRE': 'Real Estate', 'XLU': 'Utilities'}

SECTOR_COLORS = {'XLK': '#5B9BD5', 'XLV': '#70C27A', 'XLC': '#A978DE', 'XLP': '#F0C75E', 'XLY': '#E8725C', 'XLI': '#A3A9B0', 'XLU': '#5EC4D4', 'XLE': '#4AA06D', 'XLF': '#D94F5C', 'XLB': '#C08B5C', 'XLRE': '#D97BA0'}
FACTOR_COLORS = {'MTUM': '#5B9BD5', 'VLUE': '#D94F5C', 'QUAL': '#70C27A', 'SIZE': '#F0A050', 'USMV': '#A3A9B0', 'HDV': '#D4AA4F'}

INDICES = {'SPY': 'S&P 500', 'QQQ': 'Nasdaq 100', 'IWM': 'Russell 2000', 'DIA': 'Dow 30'}
INDICES_CHART = {'^GSPC': 'S&P 500', '^IXIC': 'Nasdaq', '^RUT': 'Russell 2000', '^DJI': 'Dow 30'}
EW_SECTORS = {'XLK': 'RYT', 'XLF': 'RYF', 'XLE': 'RYE', 'XLV': 'RYH', 'XLI': 'RGI', 'XLY': 'RCD', 'XLP': 'RHS', 'XLB': 'RTM', 'XLU': 'RYU', 'XLRE': 'EWRE', 'XLC': 'RSPC'}
RETAIL_ETFS = ['TQQQ', 'SQQQ']

HOLDINGS = {'XLK': [('AAPL', 'Apple', 0.22), ('MSFT', 'Microsoft', 0.21), ('NVDA', 'Nvidia', 0.11), ('AVGO', 'Broadcom', 0.05), ('CRM', 'Salesforce', 0.03), ('ADBE', 'Adobe', 0.03), ('AMD', 'AMD', 0.03), ('CSCO', 'Cisco', 0.02)], 'XLF': [('BRK-B', 'Berkshire', 0.14), ('JPM', 'JPMorgan', 0.11), ('V', 'Visa', 0.09), ('MA', 'Mastercard', 0.07), ('BAC', 'BofA', 0.05), ('WFC', 'Wells Fargo', 0.04), ('GS', 'Goldman', 0.03), ('MS', 'Morgan Stanley', 0.03)], 'XLE': [('XOM', 'Exxon', 0.23), ('CVX', 'Chevron', 0.16), ('COP', 'ConocoPhillips', 0.08), ('WMB', 'Williams', 0.06), ('EOG', 'EOG Resources', 0.05), ('SLB', 'Schlumberger', 0.05), ('PSX', 'Phillips 66', 0.04), ('MPC', 'Marathon Petro', 0.04)], 'XLV': [('LLY', 'Eli Lilly', 0.12), ('UNH', 'UnitedHealth', 0.1), ('JNJ', 'J&J', 0.07), ('ABBV', 'AbbVie', 0.07), ('MRK', 'Merck', 0.06), ('TMO', 'Thermo Fisher', 0.04), ('ABT', 'Abbott', 0.04), ('PFE', 'Pfizer', 0.03)], 'XLI': [('GE', 'GE Aerospace', 0.09), ('CAT', 'Caterpillar', 0.06), ('RTX', 'RTX Corp', 0.05), ('UNP', 'Union Pacific', 0.05), ('HON', 'Honeywell', 0.05), ('DE', 'Deere', 0.04), ('BA', 'Boeing', 0.04), ('LMT', 'Lockheed', 0.03)], 'XLY': [('AMZN', 'Amazon', 0.23), ('TSLA', 'Tesla', 0.15), ('HD', 'Home Depot', 0.1), ('MCD', "McDonald's", 0.05), ('LOW', "Lowe's", 0.04), ('BKNG', 'Booking', 0.04), ('TJX', 'TJX Cos', 0.03), ('NKE', 'Nike', 0.02)], 'XLP': [('PG', 'Procter & Gamble', 0.15), ('COST', 'Costco', 0.14), ('WMT', 'Walmart', 0.1), ('KO', 'Coca-Cola', 0.1), ('PEP', 'PepsiCo', 0.09), ('PM', 'Philip Morris', 0.06), ('MDLZ', 'Mondelez', 0.04), ('MO', 'Altria', 0.03)], 'XLB': [('LIN', 'Linde', 0.19), ('SHW', 'Sherwin-Williams', 0.09), ('FCX', 'Freeport-McMoRan', 0.08), ('APD', 'Air Products', 0.06), ('ECL', 'Ecolab', 0.06), ('NEM', 'Newmont', 0.05), ('NUE', 'Nucor', 0.04), ('DOW', 'Dow Inc', 0.04)], 'XLU': [('NEE', 'NextEra', 0.15), ('SO', 'Southern Co', 0.1), ('DUK', 'Duke Energy', 0.08), ('CEG', 'Constellation', 0.07), ('SRE', 'Sempra', 0.05), ('AEP', 'AEP', 0.05), ('D', 'Dominion', 0.04), ('PCG', 'PG&E', 0.04)], 'XLRE': [('PLD', 'Prologis', 0.13), ('AMT', 'American Tower', 0.1), ('EQIX', 'Equinix', 0.09), ('WELL', 'Welltower', 0.07), ('SPG', 'Simon Property', 0.06), ('DLR', 'Digital Realty', 0.05), ('PSA', 'Public Storage', 0.05), ('O', 'Realty Income', 0.05)], 'XLC': [('META', 'Meta', 0.23), ('GOOGL', 'Alphabet A', 0.12), ('GOOG', 'Alphabet C', 0.11), ('NFLX', 'Netflix', 0.08), ('T', 'AT&T', 0.05), ('CMCSA', 'Comcast', 0.05), ('DIS', 'Disney', 0.04), ('TMUS', 'T-Mobile', 0.04)]}

YIELDS = {'DGS2': '2Y', 'DGS5': '5Y', 'DGS10': '10Y', 'DGS30': '30Y'}
SPREADS = {'T10Y2Y': '10Y-2Y Spread', 'T10Y3M': '10Y-3M Spread'}
CREDIT = {'BAMLH0A0HYM2': 'HY OAS', 'BAMLC0A0CM': 'IG OAS'}
KEY_RELEASES = [('Nonfarm Payrolls', 'PAYEMS', '000s MoM', 'diff'), ('Unemployment Rate', 'UNRATE', '%', 'level'), ('CPI YoY', 'CPIAUCSL', '% YoY', 'yoy'), ('Core CPI YoY', 'CPILFESL', '% YoY', 'yoy'), ('PCE YoY', 'PCEPI', '% YoY', 'yoy'), ('Core PCE YoY', 'PCEPILFE', '% YoY', 'yoy'), ('GDP Growth QoQ Ann.', 'A191RL1Q225SBEA', '% Ann.', 'level'), ('Retail Sales MoM', 'RSAFS', '% MoM', 'mom'), ('Industrial Production', 'INDPRO', '% MoM', 'mom'), ('Fed Funds Rate', 'FEDFUNDS', '%', 'level'), ('10Y-2Y Spread', 'T10Y2Y', '%', 'level')]
FOMC = {'2025': [('Jan 28-29', '2025-01-29', 'Hold (4.25-4.50%)'), ('Mar 18-19', '2025-03-19', 'Hold (4.25-4.50%)'), ('May 6-7', '2025-05-07', 'Hold (4.25-4.50%)'), ('Jun 17-18', '2025-06-18', 'Hold (4.25-4.50%)'), ('Jul 29-30', '2025-07-30', 'Hold (4.25-4.50%)'), ('Sep 16-17', '2025-09-17', 'Cut -25bp (4.00-4.25%)'), ('Oct 28-29', '2025-10-29', 'Cut -25bp (3.75-4.00%)'), ('Dec 9-10', '2025-12-10', 'Cut -25bp (3.50-3.75%)')], '2026': [('Jan 27-28', '2026-01-28', 'Hold (3.50-3.75%)'), ('Mar 17-18', '2026-03-18', ''), ('Apr 28-29', '2026-04-29', ''), ('Jun 9-10', '2026-06-10', ''), ('Jul 28-29', '2026-07-29', ''), ('Sep 15-16', '2026-09-16', ''), ('Oct 27-28', '2026-10-28', ''), ('Dec 8-9', '2026-12-09', '')]}
