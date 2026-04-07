"""
Operations Management (OM) analytics — Chicago Booth research framework.

Covers: Supply Chain Efficiency, Operational Throughput, Process Quality & Lean,
Demand Variability & Bullwhip.
"""

import logging
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

from models.stock import StockData
from analytics.base import AnalyticsMethod, registry

logger = logging.getLogger(__name__)


def _get_val(df: Optional[pd.DataFrame], labels: list, col_idx: int = 0) -> Optional[float]:
    if df is None or df.empty:
        return None
    for label in labels:
        if label in df.index:
            row = df.loc[label].dropna()
            if not row.empty and col_idx < len(row):
                try:
                    return float(row.iloc[col_idx])
                except (ValueError, TypeError):
                    pass
    return None


def _get_multi_year(df: Optional[pd.DataFrame], labels: list, n: int = 4) -> list:
    """Get up to n years of a line item."""
    if df is None or df.empty:
        return []
    for label in labels:
        if label in df.index:
            row = df.loc[label].dropna()
            return [float(row.iloc[i]) for i in range(min(n, len(row)))]
    return []


# ---------------------------------------------------------------------------
# Supply Chain Efficiency (S1/S6/S7)
# ---------------------------------------------------------------------------

@registry.register("supply_chain")
class SupplyChainEfficiency(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Supply Chain Efficiency", "lecture": "S1/S6/S7"}

        revenue = info.get("totalRevenue") or 0
        cogs = 0
        inventory = 0
        receivables = 0
        payables = 0

        # Get from financial statements
        if data.financials is not None and not data.financials.empty:
            c = _get_val(data.financials, ["Cost Of Revenue", "Cost Of Goods Sold"])
            if c: cogs = abs(c)

        bs = data.balance_sheet
        if bs is not None and not bs.empty:
            inv = _get_val(bs, ["Inventory", "Net Inventory"])
            if inv: inventory = inv
            ar = _get_val(bs, ["Accounts Receivable", "Net Receivables"])
            if ar: receivables = ar
            ap = _get_val(bs, ["Accounts Payable"])
            if ap: payables = ap

        # Calculate days
        dio = (inventory / cogs * 365) if cogs else None
        dso = (receivables / revenue * 365) if revenue else None
        dpo = (payables / cogs * 365) if cogs else None

        ccc = None
        if dio is not None and dso is not None and dpo is not None:
            ccc = dio + dso - dpo

        inv_turnover = (cogs / inventory) if inventory else None

        result.update({
            "revenue": revenue,
            "cogs": cogs,
            "inventory": inventory,
            "receivables": receivables,
            "payables": payables,
            "dio_days": round(dio, 1) if dio else None,
            "dso_days": round(dso, 1) if dso else None,
            "dpo_days": round(dpo, 1) if dpo else None,
            "cash_conversion_cycle": round(ccc, 1) if ccc else None,
            "inventory_turnover": round(inv_turnover, 2) if inv_turnover else None,
            "assessment": (
                "Excellent" if ccc is not None and ccc < 30
                else "Good" if ccc is not None and ccc < 60
                else "Average" if ccc is not None and ccc < 90
                else "Needs improvement" if ccc is not None
                else "Insufficient data"
            ),
        })
        return result


# ---------------------------------------------------------------------------
# Operational Throughput (S2/S4)
# ---------------------------------------------------------------------------

@registry.register("operational_throughput")
class OperationalThroughput(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Operational Throughput", "lecture": "S2/S4"}

        revenue = info.get("totalRevenue") or 0
        revenue_growth = info.get("revenueGrowth")

        # Fixed asset turnover
        fixed_assets = 0
        bs = data.balance_sheet
        if bs is not None and not bs.empty:
            fa = _get_val(bs, ["Net PPE", "Property Plant Equipment Net", "Property Plant And Equipment Net"])
            if fa: fixed_assets = fa

        fat = revenue / fixed_assets if fixed_assets else None

        # CapEx growth
        capex_list = _get_multi_year(data.cash_flow, ["Capital Expenditure", "Capital Expenditures"])
        capex_growth = None
        if len(capex_list) >= 2:
            c0, c1 = abs(capex_list[0]), abs(capex_list[1])
            if c1 > 0:
                capex_growth = (c0 - c1) / c1

        # Revenue multi-year
        rev_list = _get_multi_year(data.financials, ["Total Revenue", "Revenue"])

        result.update({
            "revenue": revenue,
            "revenue_growth": round(revenue_growth, 4) if revenue_growth else None,
            "fixed_assets": fixed_assets,
            "fixed_asset_turnover": round(fat, 2) if fat else None,
            "capex_current": abs(capex_list[0]) if capex_list else None,
            "capex_growth": round(capex_growth, 4) if capex_growth is not None else None,
            "revenue_trend": [round(r, 0) for r in rev_list] if rev_list else None,
            "assessment": (
                "High throughput" if fat and fat > 3
                else "Moderate throughput" if fat and fat > 1.5
                else "Capital-intensive" if fat
                else "Insufficient data"
            ),
        })
        return result


# ---------------------------------------------------------------------------
# Process Quality & Lean (S5 TQM/TPS)
# ---------------------------------------------------------------------------

@registry.register("process_quality")
class ProcessQuality(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Process Quality & Lean", "lecture": "S5 TQM/TPS"}

        gross_margin = info.get("grossMargins") or 0
        operating_margin = info.get("operatingMargins") or 0
        roa = info.get("returnOnAssets") or 0
        revenue = info.get("totalRevenue") or 0

        # Gross margin trend (multi-year)
        gm_values = []
        if data.financials is not None and not data.financials.empty:
            rev_list = _get_multi_year(data.financials, ["Total Revenue", "Revenue"])
            gp_list = _get_multi_year(data.financials, ["Gross Profit"])
            if rev_list and gp_list and len(rev_list) == len(gp_list):
                gm_values = [gp / r if r else 0 for gp, r in zip(gp_list, rev_list)]

        gm_trend = None
        if len(gm_values) >= 2:
            gm_trend = "Improving" if gm_values[0] > gm_values[-1] else "Declining"

        # Overhead gap = Gross Margin - Operating Margin (SGA overhead)
        overhead_gap = gross_margin - operating_margin

        # Working capital efficiency
        wc = 0
        bs = data.balance_sheet
        if bs is not None and not bs.empty:
            ca = _get_val(bs, ["Current Assets"]) or 0
            cl = _get_val(bs, ["Current Liabilities"]) or 0
            wc = ca - cl
        wc_to_rev = wc / revenue if revenue else None

        result.update({
            "gross_margin": round(gross_margin * 100, 2),
            "operating_margin": round(operating_margin * 100, 2),
            "overhead_gap_pct": round(overhead_gap * 100, 2),
            "roa": round(roa * 100, 2) if roa else None,
            "gross_margin_trend": gm_trend,
            "gross_margin_history": [round(g * 100, 2) for g in gm_values] if gm_values else None,
            "working_capital": wc,
            "wc_to_revenue": round(wc_to_rev * 100, 2) if wc_to_rev else None,
            "assessment": (
                "Lean operations" if overhead_gap < 0.15 and operating_margin > 0.15
                else "Moderate efficiency" if operating_margin > 0.10
                else "High overhead" if overhead_gap > 0.30
                else "Needs improvement"
            ),
        })
        return result


# ---------------------------------------------------------------------------
# Demand Variability & Bullwhip (S7/S8)
# ---------------------------------------------------------------------------

@registry.register("demand_variability")
class DemandVariability(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        result = {"method": "Demand Variability & Bullwhip", "lecture": "S7/S8"}

        # Revenue volatility from multi-year data
        rev_list = _get_multi_year(data.financials, ["Total Revenue", "Revenue"])
        inv_list = []
        if data.balance_sheet is not None and not data.balance_sheet.empty:
            for i in range(4):
                v = _get_val(data.balance_sheet, ["Inventory", "Net Inventory"], i)
                if v is not None:
                    inv_list.append(v)

        # Revenue CV (coefficient of variation)
        rev_cv = None
        if len(rev_list) >= 2:
            arr = np.array(rev_list)
            mean = arr.mean()
            if mean > 0:
                rev_cv = arr.std() / mean

        # Inventory growth vs revenue growth
        inv_growth = None
        rev_growth_calc = None
        if len(inv_list) >= 2:
            inv_growth = (inv_list[0] - inv_list[-1]) / abs(inv_list[-1]) if inv_list[-1] else None
        if len(rev_list) >= 2:
            rev_growth_calc = (rev_list[0] - rev_list[-1]) / abs(rev_list[-1]) if rev_list[-1] else None

        # Bullwhip ratio = inventory growth / revenue growth
        bullwhip = None
        if inv_growth is not None and rev_growth_calc is not None and rev_growth_calc != 0:
            bullwhip = abs(inv_growth / rev_growth_calc)

        result.update({
            "revenue_cv": round(rev_cv, 4) if rev_cv else None,
            "revenue_trend": [round(r, 0) for r in rev_list] if rev_list else None,
            "inventory_trend": [round(i, 0) for i in inv_list] if inv_list else None,
            "inventory_growth": round(inv_growth, 4) if inv_growth is not None else None,
            "revenue_growth": round(rev_growth_calc, 4) if rev_growth_calc is not None else None,
            "bullwhip_ratio": round(bullwhip, 3) if bullwhip is not None else None,
            "assessment": (
                "High variability (bullwhip risk)" if bullwhip and bullwhip > 1.5
                else "Moderate variability" if bullwhip and bullwhip > 1.0
                else "Well-managed demand" if bullwhip
                else "Insufficient data"
            ),
        })
        return result
