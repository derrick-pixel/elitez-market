"""Configuration for the multi-index Yahoo Finance scraper."""

from pathlib import Path
from datetime import datetime

# Directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_MONTH = datetime.now().strftime("%Y-%m")

# Index sources
SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SGX_URL = "https://stockanalysis.com/list/singapore-exchange/"

AVAILABLE_INDICES = ["sp500", "sgx"]

# Scraping settings
BATCH_SIZE = 10          # tickers per batch
SLEEP_BETWEEN = 1.5      # seconds between batches (avoid rate limits)
MAX_RETRIES = 3          # retries per ticker on failure
PRICE_HISTORY_PERIOD = "1mo"  # monthly snapshot: last month of daily prices
