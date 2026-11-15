"""Asset universe: 31 assets (10 CA equities, 10 US equities, 9 ETFs, 2 crypto).

Mirrors the composition of the official starter set (alphaforge_starter/assets_universe.csv).
Selection rule: large, liquid, well-known names across sectors so that each persona has
realistic options (growth tech for Amira, ESG-screened funds for Mateo, bonds/dividend payers
for Robert, plus a "hyped" high-volatility name to test the off-profile challenge).
Known selection bias: survivors only (all assets still trade today), large caps only.
"""

# ticker, name, asset_class, market, currency, sector, sec_cik (US filers only)
ASSETS = [
    # --- Canadian equities (TSX, CAD) ---
    ("RY.TO", "Royal Bank of Canada", "equity", "TSX", "CAD", "Financials", None),
    ("TD.TO", "Toronto-Dominion Bank", "equity", "TSX", "CAD", "Financials", None),
    ("ENB.TO", "Enbridge Inc.", "equity", "TSX", "CAD", "Energy", None),
    ("SU.TO", "Suncor Energy Inc.", "equity", "TSX", "CAD", "Energy", None),
    ("CNR.TO", "Canadian National Railway", "equity", "TSX", "CAD", "Industrials", None),
    ("SHOP.TO", "Shopify Inc.", "equity", "TSX", "CAD", "Information Technology", None),
    ("CSU.TO", "Constellation Software Inc.", "equity", "TSX", "CAD", "Information Technology", None),
    ("BCE.TO", "BCE Inc.", "equity", "TSX", "CAD", "Communication Services", None),
    ("ATD.TO", "Alimentation Couche-Tard Inc.", "equity", "TSX", "CAD", "Consumer Staples", None),
    ("FTS.TO", "Fortis Inc.", "equity", "TSX", "CAD", "Utilities", None),
    # --- US equities (NYSE/NASDAQ, USD) ---
    ("AAPL", "Apple Inc.", "equity", "NASDAQ", "USD", "Information Technology", 320193),
    ("MSFT", "Microsoft Corp.", "equity", "NASDAQ", "USD", "Information Technology", 789019),
    ("NVDA", "NVIDIA Corp.", "equity", "NASDAQ", "USD", "Information Technology", 1045810),
    ("AMZN", "Amazon.com Inc.", "equity", "NASDAQ", "USD", "Consumer Discretionary", 1018724),
    ("GOOGL", "Alphabet Inc. (Class A)", "equity", "NASDAQ", "USD", "Communication Services", 1652044),
    ("TSLA", "Tesla Inc.", "equity", "NASDAQ", "USD", "Consumer Discretionary", 1318605),
    ("JNJ", "Johnson & Johnson", "equity", "NYSE", "USD", "Health Care", 200406),
    ("PG", "Procter & Gamble Co.", "equity", "NYSE", "USD", "Consumer Staples", 80424),
    ("JPM", "JPMorgan Chase & Co.", "equity", "NYSE", "USD", "Financials", 19617),
    ("XOM", "Exxon Mobil Corp.", "equity", "NYSE", "USD", "Energy", 34088),
    # --- ETFs ---
    ("XIU.TO", "iShares S&P/TSX 60 Index ETF", "etf_equity", "TSX", "CAD", "Broad market (Canada)", None),
    ("VFV.TO", "Vanguard S&P 500 Index ETF (CAD)", "etf_equity", "TSX", "CAD", "Broad market (US)", None),
    ("XEF.TO", "iShares Core MSCI EAFE IMI Index ETF", "etf_equity", "TSX", "CAD", "Broad market (International)", None),
    ("XEC.TO", "iShares Core MSCI Emerging Markets IMI ETF", "etf_equity", "TSX", "CAD", "Broad market (Emerging)", None),
    ("QQQ", "Invesco QQQ Trust (Nasdaq-100)", "etf_equity", "NASDAQ", "USD", "Growth / Technology", None),
    ("XESG.TO", "iShares ESG Aware MSCI Canada Index ETF", "etf_equity", "TSX", "CAD", "ESG screened (Canada)", None),
    ("XBB.TO", "iShares Core Canadian Universe Bond ETF", "etf_bond", "TSX", "CAD", "Bonds (Canada aggregate)", None),
    ("XSB.TO", "iShares Core Canadian Short Term Bond ETF", "etf_bond", "TSX", "CAD", "Bonds (Canada short term)", None),
    ("GLD", "SPDR Gold Shares", "etf_gold", "NYSE Arca", "USD", "Gold", None),
    # --- Crypto (24/7, USD) ---
    ("BTC-USD", "Bitcoin", "crypto", "Crypto (24/7)", "USD", "Crypto-asset", None),
    ("ETH-USD", "Ether", "crypto", "Crypto (24/7)", "USD", "Crypto-asset", None),
]

START = "2021-11-12"
END = "2026-11-12"

# Macro series kept identical to the starter set (series ids used by the front Markets page).
BOC_SERIES = {
    "V39079": ("Target for the overnight rate (Bank of Canada)", "percent", "daily"),
    "BD.CDN.2YR.DQ.YLD": ("Government of Canada 2-year benchmark bond yield", "percent", "daily"),
    "BD.CDN.10YR.DQ.YLD": ("Government of Canada 10-year benchmark bond yield", "percent", "daily"),
    "STATIC_TOTALCPICHANGE": ("Canada CPI, 12-month change", "percent", "monthly"),
}
FRED_SERIES = {
    "DFF": ("US effective federal funds rate", "percent", "daily"),
    "DGS2": ("US Treasury 2-year constant maturity yield", "percent", "daily"),
    "DGS10": ("US Treasury 10-year constant maturity yield", "percent", "daily"),
    "CPIAUCSL": ("US CPI-U, all items (index 1982-84=100)", "index", "monthly"),
    "UNRATE": ("US unemployment rate", "percent", "monthly"),
}

# SEC XBRL concepts (first available tag wins), annual 10-K values only.
SEC_CONCEPTS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"],
    "stockholders_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
}
