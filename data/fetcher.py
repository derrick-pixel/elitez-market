"""
Data fetcher with fallback chain: yfinance → Finnhub+Stooq → empty StockData.

yfinance is the primary source. When it fails (common on Streamlit Cloud
shared IPs), the Finnhub+Stooq fallback activates automatically if
FINNHUB_KEY is set in the environment.
"""

import io
import os
import time
import logging
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

from models.stock import StockData
from config import DEFAULT_PERIOD, DEFAULT_INTERVAL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Primary: yfinance (with retry)
# ---------------------------------------------------------------------------

def _fetch_yfinance(ticker: str) -> Optional[StockData]:
    """Fetch all data from yfinance. Retries once on failure (rate-limit recovery)."""
    for attempt in range(2):
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            # yfinance returns partial/empty info on rate-limit
            has_price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            if not has_price and not info.get("shortName"):
                if attempt == 0:
                    logger.info("yfinance returned empty info for %s, retrying...", ticker)
                    time.sleep(2)
                    continue
                return None

            hist = t.history(period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL)
            if hist is None or hist.empty:
                if attempt == 0:
                    time.sleep(2)
                    continue
                # Still return with info if we have it — analytics can work without history
                if has_price:
                    return StockData(ticker=ticker.upper(), info=info)
                return None

            return StockData(
                ticker=ticker.upper(),
                info=info,
                history=hist,
                balance_sheet=_safe_df(t, "balance_sheet"),
                financials=_safe_df(t, "financials"),
                quarterly_balance_sheet=_safe_df(t, "quarterly_balance_sheet"),
                cash_flow=_safe_df(t, "cashflow"),
            )
        except Exception as e:
            logger.warning("yfinance attempt %d failed for %s: %s", attempt + 1, ticker, e)
            if attempt == 0:
                time.sleep(2)
                continue
            return None
    return None


def _safe_df(ticker_obj, attr: str) -> Optional[pd.DataFrame]:
    try:
        df = getattr(ticker_obj, attr, None)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Fallback: Finnhub (fundamentals) + Stooq (historical prices)
# ---------------------------------------------------------------------------

_FINNHUB_BASE = "https://finnhub.io/api/v1"


def _finnhub_get(endpoint: str, params: dict) -> Optional[dict]:
    key = os.environ.get("FINNHUB_KEY", "")
    if not key:
        return None
    params["token"] = key
    try:
        r = requests.get(f"{_FINNHUB_BASE}{endpoint}", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        # Finnhub returns {"error": "..."} on bad requests
        if isinstance(data, dict) and "error" in data:
            logger.warning("Finnhub error: %s", data["error"])
            return None
        return data
    except Exception as e:
        logger.warning("Finnhub request failed: %s", e)
        return None


def _stooq_history(ticker: str) -> Optional[pd.DataFrame]:
    """Download daily price history from Stooq (free, no API key)."""
    symbol = f"{ticker.lower()}.us"
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or "Close" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        # Keep only last ~1 year
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=1)
        df = df[df.index >= cutoff]
        # Rename to yfinance-compatible columns
        df = df.rename(columns={
            "Open": "Open", "High": "High", "Low": "Low",
            "Close": "Close", "Volume": "Volume",
        })
        return df if not df.empty else None
    except Exception as e:
        logger.warning("Stooq history failed for %s: %s", ticker, e)
        return None


def _fetch_finnhub_stooq(ticker: str) -> Optional[StockData]:
    """Build a yfinance-compatible StockData from Finnhub + Stooq."""
    profile = _finnhub_get("/stock/profile2", {"symbol": ticker})
    if not profile or not profile.get("name"):
        return None

    quote = _finnhub_get("/quote", {"symbol": ticker}) or {}
    metrics_resp = _finnhub_get("/stock/metric", {"symbol": ticker, "metric": "all"})
    met = (metrics_resp or {}).get("metric", {})

    shares = (profile.get("shareOutstanding") or 0) * 1e6
    mkt_cap = (profile.get("marketCapitalization") or 0) * 1e6
    price = quote.get("c") or 0

    # Derive revenue / FCF / EBITDA from per-share metrics to avoid unit ambiguity
    rev_per_share = met.get("revenuePerShareAnnual") or 0
    revenue = rev_per_share * shares if shares else 0
    fcf_per_share = met.get("fcfPerShareAnnual") or 0
    fcf = fcf_per_share * shares if shares else 0
    ebitda_per_share = met.get("ebitdaPerShareAnnual") or met.get("ebitdPerShareAnnual") or 0
    ebitda = ebitda_per_share * shares if shares else 0

    # Finnhub returns ratios as percentages — divide by 100
    gross_margin = (met.get("grossMarginAnnual") or 0) / 100.0
    operating_margin = (met.get("operatingMarginAnnual") or 0) / 100.0
    net_margin = (met.get("netProfitMarginAnnual") or 0) / 100.0
    roe_val = (met.get("roeRoa", {}) if isinstance(met.get("roeRoa"), dict) else {})
    roe_annual = (met.get("roeTTM") or 0) / 100.0
    roa_annual = (met.get("roaTTM") or 0) / 100.0

    info = {
        "shortName": profile.get("name", ticker),
        "longName": profile.get("name", ticker),
        "sector": profile.get("finnhubIndustry", ""),
        "industry": profile.get("finnhubIndustry", ""),
        "country": profile.get("country", ""),
        "website": profile.get("weburl", ""),
        "logo_url": profile.get("logo", ""),
        "currentPrice": price,
        "regularMarketPrice": price,
        "previousClose": quote.get("pc"),
        "open": quote.get("o"),
        "dayHigh": quote.get("h"),
        "dayLow": quote.get("l"),
        "marketCap": mkt_cap,
        "sharesOutstanding": shares,
        "trailingPE": met.get("peNormalizedAnnual") or met.get("peTTM"),
        "forwardPE": met.get("peAnnual"),
        "trailingEps": met.get("epsNormalizedAnnual") or met.get("epsTTM"),
        "priceToBook": met.get("pbAnnual") or met.get("pbQuarterly"),
        "priceToSalesTrailing12Months": met.get("psAnnual") or met.get("psTTM"),
        "enterpriseToEbitda": met.get("currentEv/ebitdaAnnual"),
        "dividendYield": (met.get("dividendYieldIndicatedAnnual") or 0) / 100.0,
        "profitMargins": net_margin,
        "grossMargins": gross_margin,
        "operatingMargins": operating_margin,
        "returnOnEquity": roe_annual,
        "returnOnAssets": roa_annual,
        "revenueGrowth": (met.get("revenueGrowthQuarterlyYoy") or 0) / 100.0,
        "earningsGrowth": (met.get("epsGrowthQuarterlyYoy") or 0) / 100.0,
        "debtToEquity": met.get("totalDebt/totalEquityAnnual"),
        "totalRevenue": revenue,
        "ebitda": ebitda,
        "freeCashflow": fcf,
        "totalDebt": met.get("totalDebtCagr5Y"),  # approximate
        "totalCash": None,
        "fiftyTwoWeekHigh": met.get("52WeekHigh"),
        "fiftyTwoWeekLow": met.get("52WeekLow"),
        "beta": met.get("beta"),
        "longBusinessSummary": "",
    }

    history = _stooq_history(ticker)

    return StockData(
        ticker=ticker.upper(),
        info=info,
        history=history,
    ) if history is not None else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_stock_data(ticker: str) -> StockData:
    """
    Fetch stock data with fallback chain:
    yfinance → Finnhub+Stooq → empty StockData.
    """
    ticker = ticker.strip().upper()

    # 1. Try yfinance (primary)
    data = _fetch_yfinance(ticker)
    if data is not None:
        logger.info("Fetched %s from yfinance", ticker)
        return data

    # 2. Try Finnhub + Stooq (fallback)
    data = _fetch_finnhub_stooq(ticker)
    if data is not None:
        logger.info("Fetched %s from Finnhub+Stooq", ticker)
        return data

    # 3. Return empty StockData
    logger.warning("All sources failed for %s, returning empty StockData", ticker)
    return StockData(ticker=ticker)
