from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class StockData:
    ticker: str
    info: dict = field(default_factory=dict)
    history: Optional[pd.DataFrame] = None
    balance_sheet: Optional[pd.DataFrame] = None
    financials: Optional[pd.DataFrame] = None
    quarterly_balance_sheet: Optional[pd.DataFrame] = None
    cash_flow: Optional[pd.DataFrame] = None

    # --------------- convenience properties ---------------

    @property
    def price(self) -> Optional[float]:
        return self.info.get("currentPrice") or self.info.get("regularMarketPrice")

    @property
    def pe_ratio(self) -> Optional[float]:
        return self.info.get("trailingPE")

    @property
    def forward_pe(self) -> Optional[float]:
        return self.info.get("forwardPE")

    @property
    def eps(self) -> Optional[float]:
        return self.info.get("trailingEps")

    @property
    def market_cap(self) -> Optional[float]:
        return self.info.get("marketCap")

    @property
    def pb_ratio(self) -> Optional[float]:
        return self.info.get("priceToBook")

    @property
    def ps_ratio(self) -> Optional[float]:
        return self.info.get("priceToSalesTrailing12Months")

    @property
    def ev_ebitda(self) -> Optional[float]:
        return self.info.get("enterpriseToEbitda")

    @property
    def revenue_growth(self) -> Optional[float]:
        return self.info.get("revenueGrowth")

    @property
    def earnings_growth(self) -> Optional[float]:
        return self.info.get("earningsGrowth")

    @property
    def profit_margin(self) -> Optional[float]:
        return self.info.get("profitMargins")

    @property
    def debt_to_equity(self) -> Optional[float]:
        return self.info.get("debtToEquity")

    @property
    def roe(self) -> Optional[float]:
        return self.info.get("returnOnEquity")

    @property
    def sector(self) -> Optional[str]:
        return self.info.get("sector")

    @property
    def industry(self) -> Optional[str]:
        return self.info.get("industry")
