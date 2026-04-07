"""
Data fetcher with fallback chain:
  1. yfinance (library)
  2. Yahoo Finance direct JSON (bypasses yfinance library issues)
  3. Finnhub+Stooq (if FINNHUB_KEY set)
  4. Empty StockData

On Streamlit Cloud, yfinance often fails due to shared IP rate-limiting.
The Yahoo JSON fallback uses a different endpoint that is more reliable.
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
# Source 1: yfinance library (with retry)
# ---------------------------------------------------------------------------

def _fetch_yfinance(ticker: str) -> Optional[StockData]:
    """Fetch all data from yfinance. Retries once on failure."""
    for attempt in range(2):
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            has_price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            if not has_price and not info.get("shortName"):
                if attempt == 0:
                    logger.info("yfinance empty for %s, retrying...", ticker)
                    time.sleep(1)
                    continue
                return None

            hist = t.history(period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL)
            if hist is None or hist.empty:
                if attempt == 0:
                    time.sleep(1)
                    continue
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
                time.sleep(1)
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
# Source 2: Yahoo Finance direct JSON with crumb authentication
# ---------------------------------------------------------------------------

_YF_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
_YF_SUMMARY_URL = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
_YF_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

# Module-level crumb cache
_yf_crumb: Optional[str] = None
_yf_cookies: Optional[dict] = None


def _get_yahoo_crumb() -> tuple:
    """Get Yahoo Finance crumb + cookies for authenticated requests."""
    global _yf_crumb, _yf_cookies
    if _yf_crumb and _yf_cookies:
        return _yf_crumb, _yf_cookies
    try:
        sess = requests.Session()
        sess.headers["User-Agent"] = _YF_UA
        # Get cookie from Yahoo
        sess.get("https://fc.yahoo.com", timeout=5)
        # Get crumb
        r = sess.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=5)
        r.raise_for_status()
        _yf_crumb = r.text.strip()
        _yf_cookies = dict(sess.cookies)
        return _yf_crumb, _yf_cookies
    except Exception as e:
        logger.warning("Yahoo crumb auth failed: %s", e)
        return None, None


def _fetch_yahoo_direct(ticker: str) -> Optional[StockData]:
    """Fetch from Yahoo Finance quoteSummary API with crumb auth."""
    try:
        crumb, cookies = _get_yahoo_crumb()
        if not crumb:
            return None

        modules = "price,summaryProfile,summaryDetail,defaultKeyStatistics,financialData"
        url = _YF_SUMMARY_URL.format(ticker=ticker)
        r = requests.get(
            url,
            params={"modules": modules, "crumb": crumb},
            cookies=cookies,
            headers={"User-Agent": _YF_UA},
            timeout=10,
        )
        if r.status_code == 401:
            # Crumb expired, reset and retry once
            global _yf_crumb, _yf_cookies
            _yf_crumb, _yf_cookies = None, None
            crumb, cookies = _get_yahoo_crumb()
            if not crumb:
                return None
            r = requests.get(
                url,
                params={"modules": modules, "crumb": crumb},
                cookies=cookies,
                headers={"User-Agent": _YF_UA},
                timeout=10,
            )
        r.raise_for_status()
        data = r.json()
        result = data.get("quoteSummary", {}).get("result", [])
        if not result:
            return None

        # Extract from modules
        price_mod = result[0].get("price", {})
        profile = result[0].get("summaryProfile", {})
        detail = result[0].get("summaryDetail", {})
        stats = result[0].get("defaultKeyStatistics", {})
        fin = result[0].get("financialData", {})

        def _raw(d, key):
            """Extract raw value from Yahoo's {raw: X, fmt: Y} format."""
            v = d.get(key, {})
            if isinstance(v, dict):
                return v.get("raw")
            return v

        price_val = _raw(price_mod, "regularMarketPrice")
        if not price_val:
            return None

        info = {
            "shortName": price_mod.get("shortName", ticker),
            "longName": price_mod.get("longName") or price_mod.get("shortName", ticker),
            "sector": profile.get("sector", ""),
            "industry": profile.get("industry", ""),
            "currentPrice": price_val,
            "regularMarketPrice": price_val,
            "previousClose": _raw(detail, "previousClose"),
            "marketCap": _raw(price_mod, "marketCap"),
            "sharesOutstanding": _raw(stats, "sharesOutstanding"),
            "trailingPE": _raw(detail, "trailingPE"),
            "forwardPE": _raw(detail, "forwardPE") or _raw(stats, "forwardPE"),
            "trailingEps": _raw(stats, "trailingEps"),
            "dividendYield": _raw(detail, "dividendYield"),
            "priceToBook": _raw(stats, "priceToBook"),
            "priceToSalesTrailing12Months": _raw(detail, "priceToSalesTrailing12Months"),
            "enterpriseToEbitda": _raw(stats, "enterpriseToEbitda"),
            "fiftyTwoWeekHigh": _raw(detail, "fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": _raw(detail, "fiftyTwoWeekLow"),
            "beta": _raw(detail, "beta") or _raw(stats, "beta"),
            "profitMargins": _raw(stats, "profitMargins") or _raw(fin, "profitMargins"),
            "grossMargins": _raw(fin, "grossMargins"),
            "operatingMargins": _raw(fin, "operatingMargins"),
            "returnOnEquity": _raw(fin, "returnOnEquity"),
            "returnOnAssets": _raw(fin, "returnOnAssets"),
            "revenueGrowth": _raw(fin, "revenueGrowth"),
            "earningsGrowth": _raw(fin, "earningsGrowth"),
            "debtToEquity": _raw(fin, "debtToEquity"),
            "totalRevenue": _raw(fin, "totalRevenue"),
            "ebitda": _raw(fin, "ebitda"),
            "freeCashflow": _raw(fin, "freeCashflow"),
            "totalDebt": _raw(fin, "totalDebt"),
            "totalCash": _raw(fin, "totalCash"),
            "operatingCashflow": _raw(fin, "operatingCashflow"),
            "longBusinessSummary": profile.get("longBusinessSummary", ""),
        }

        # Chart data for price history (v8 works without auth)
        history = _fetch_yahoo_chart(ticker)

        return StockData(
            ticker=ticker.upper(),
            info=info,
            history=history,
        )
    except Exception as e:
        logger.warning("Yahoo direct failed for %s: %s", ticker, e)
        return None


def _fetch_yahoo_chart(ticker: str) -> Optional[pd.DataFrame]:
    """Fetch 1-year daily chart from Yahoo v8 API (no auth needed)."""
    try:
        url = _YF_CHART_URL.format(ticker=ticker)
        r = requests.get(
            url,
            params={"range": "1y", "interval": "1d"},
            headers={"User-Agent": _YF_UA},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None

        ts = result[0].get("timestamp", [])
        quotes = result[0].get("indicators", {}).get("quote", [{}])[0]
        if not ts or not quotes.get("close"):
            return None

        df = pd.DataFrame({
            "Open": quotes.get("open", []),
            "High": quotes.get("high", []),
            "Low": quotes.get("low", []),
            "Close": quotes.get("close", []),
            "Volume": quotes.get("volume", []),
        }, index=pd.to_datetime(ts, unit="s"))
        df.index.name = "Date"
        df = df.dropna(subset=["Close"])
        return df if not df.empty else None
    except Exception as e:
        logger.warning("Yahoo chart failed for %s: %s", ticker, e)
        return None


# ---------------------------------------------------------------------------
# Source 3: Finnhub (fundamentals) + Stooq (historical prices)
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
        cutoff = pd.Timestamp.now() - pd.DateOffset(years=1)
        df = df[df.index >= cutoff]
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

    rev_per_share = met.get("revenuePerShareAnnual") or 0
    revenue = rev_per_share * shares if shares else 0
    fcf_per_share = met.get("fcfPerShareAnnual") or 0
    fcf = fcf_per_share * shares if shares else 0
    ebitda_per_share = met.get("ebitdaPerShareAnnual") or met.get("ebitdPerShareAnnual") or 0
    ebitda = ebitda_per_share * shares if shares else 0

    gross_margin = (met.get("grossMarginAnnual") or 0) / 100.0
    operating_margin = (met.get("operatingMarginAnnual") or 0) / 100.0
    net_margin = (met.get("netProfitMarginAnnual") or 0) / 100.0
    roe_annual = (met.get("roeTTM") or 0) / 100.0
    roa_annual = (met.get("roaTTM") or 0) / 100.0

    info = {
        "shortName": profile.get("name", ticker),
        "longName": profile.get("name", ticker),
        "sector": profile.get("finnhubIndustry", ""),
        "industry": profile.get("finnhubIndustry", ""),
        "country": profile.get("country", ""),
        "website": profile.get("weburl", ""),
        "currentPrice": price,
        "regularMarketPrice": price,
        "previousClose": quote.get("pc"),
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
        "totalDebt": met.get("totalDebtCagr5Y"),
        "totalCash": None,
        "fiftyTwoWeekHigh": met.get("52WeekHigh"),
        "fiftyTwoWeekLow": met.get("52WeekLow"),
        "beta": met.get("beta"),
        "longBusinessSummary": "",
    }

    history = _stooq_history(ticker)

    # Return even without history — analytics can still work with fundamentals
    return StockData(
        ticker=ticker.upper(),
        info=info,
        history=history,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_stock_data(ticker: str) -> StockData:
    """
    Fetch stock data with fallback chain:
    yfinance → Yahoo direct JSON → Finnhub+Stooq → empty StockData.
    """
    ticker = ticker.strip().upper()

    # 1. Try yfinance library
    data = _fetch_yfinance(ticker)
    if data is not None:
        logger.info("Fetched %s from yfinance", ticker)
        return data

    # 2. Try Yahoo Finance direct JSON endpoint
    data = _fetch_yahoo_direct(ticker)
    if data is not None:
        logger.info("Fetched %s from Yahoo direct JSON", ticker)
        return data

    # 3. Try Finnhub + Stooq (requires FINNHUB_KEY)
    data = _fetch_finnhub_stooq(ticker)
    if data is not None:
        logger.info("Fetched %s from Finnhub+Stooq", ticker)
        return data

    # 4. Return empty StockData
    logger.warning("All sources failed for %s, returning empty StockData", ticker)
    return StockData(ticker=ticker)
