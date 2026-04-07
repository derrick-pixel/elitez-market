"""Basic fundamental analysis."""

from typing import Dict, Any

from models.stock import StockData
from analytics.base import AnalyticsMethod, registry


@registry.register("fundamental")
class FundamentalAnalysis(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        return {
            "ticker": data.ticker,
            "price": data.price,
            "pe_ratio": data.pe_ratio,
            "forward_pe": data.forward_pe,
            "eps": data.eps,
            "market_cap": data.market_cap,
            "pb_ratio": data.pb_ratio,
            "ps_ratio": data.ps_ratio,
            "ev_ebitda": data.ev_ebitda,
            "dividend_yield": info.get("dividendYield"),
            "profit_margin": data.profit_margin,
            "roe": data.roe,
            "debt_to_equity": data.debt_to_equity,
            "revenue_growth": data.revenue_growth,
            "earnings_growth": data.earnings_growth,
        }
