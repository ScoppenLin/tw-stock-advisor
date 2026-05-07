from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MARKET_DATA_DIR = DATA_DIR / "market_data"
REPORTS_DIR = PROJECT_ROOT / "reports"
DAILY_REPORTS_DIR = REPORTS_DIR / "daily"
WEEKLY_REPORTS_DIR = REPORTS_DIR / "weekly"

PORTFOLIO_FILE = DATA_DIR / "portfolio.csv"
ACCOUNT_FILE = DATA_DIR / "account.csv"
WATCHLIST_FILE = DATA_DIR / "watchlist.csv"
LATEST_PRICES_FILE = MARKET_DATA_DIR / "latest_prices.csv"
PRICE_HISTORY_FILE = MARKET_DATA_DIR / "price_history.csv"
MARKET_INDICATORS_FILE = MARKET_DATA_DIR / "market_indicators.csv"

TAIWAN_LOT_SIZE = 1000
TOTAL_CAPITAL_FALLBACK = 1_000_000
