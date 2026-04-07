"""
Tracker: central orchestrator that auto-registers analytics and provides
a module-level fetch cache (TTL 5min) so all 4 analytics calls share one fetch.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from models.stock import StockData
from data.fetcher import fetch_stock_data
from analytics.base import registry

# Auto-register all analytics modules by importing them
import analytics.fundamental
import analytics.chicago_booth
import analytics.financial_strategy
import analytics.operations_management
import analytics.competitive_strategy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level fetch cache (TTL 5 minutes)
# ---------------------------------------------------------------------------
_fetch_cache: Dict[str, tuple] = {}  # ticker -> (StockData, timestamp)
_CACHE_TTL = 300  # 5 minutes


def _cached_fetch(ticker: str) -> StockData:
    """Fetch stock data with module-level caching (5min TTL)."""
    ticker = ticker.strip().upper()
    now = time.time()

    if ticker in _fetch_cache:
        data, ts = _fetch_cache[ticker]
        if now - ts < _CACHE_TTL:
            logger.debug("Cache hit for %s", ticker)
            return data

    data = fetch_stock_data(ticker)
    _fetch_cache[ticker] = (data, now)
    return data


def get_stock_data(ticker: str) -> StockData:
    """Public accessor — reuses the module-level cache."""
    return _cached_fetch(ticker)


def get_stock_info(ticker: str) -> dict:
    """Get stock info dict — reuses the cached fetch (NOT a separate yf.Ticker call)."""
    return _cached_fetch(ticker).info


# ---------------------------------------------------------------------------
# Analysis runners
# ---------------------------------------------------------------------------

def _run_methods(data: StockData, method_names: List[str]) -> Dict[str, Any]:
    """Run selected methods, catching individual failures."""
    results = {}
    for name in method_names:
        try:
            method = registry.get(name)
            results[name] = method.run(data)
        except Exception as e:
            logger.error("Method %s failed for %s: %s", name, data.ticker, e)
            results[name] = {"method": name, "error": str(e)}
    return results


def analyze(ticker: str, methods: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run analytics on a ticker.
    Uses _cached_fetch() so all calls in a session share one data fetch.
    """
    data = _cached_fetch(ticker)
    if methods is None:
        methods = registry.names()
    return _run_methods(data, methods)


# Convenience runners for the four CB frameworks

def run_booth_analysis(ticker: str) -> Dict[str, Any]:
    """Corporate Finance (CF) analysis."""
    data = _cached_fetch(ticker)
    return _run_methods(data, [
        "capm_alpha", "valuation_multiples", "wacc", "free_cash_flow", "dcf_model",
    ])


def run_fs_analysis(ticker: str) -> Dict[str, Any]:
    """Financial Strategy (FS) analysis."""
    data = _cached_fetch(ticker)
    return _run_methods(data, [
        "capital_structure", "credit_rating", "static_tradeoff",
        "payout_policy", "altman_z", "pecking_order",
    ])


def run_om_analysis(ticker: str) -> Dict[str, Any]:
    """Operations Management (OM) analysis."""
    data = _cached_fetch(ticker)
    return _run_methods(data, [
        "supply_chain", "operational_throughput", "process_quality", "demand_variability",
    ])


def run_cs_analysis(ticker: str) -> Dict[str, Any]:
    """Competitive Strategy (CS) analysis."""
    data = _cached_fetch(ticker)
    return _run_methods(data, [
        "competitive_moat", "disruption_risk", "market_position",
    ])
