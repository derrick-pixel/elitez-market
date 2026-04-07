"""
Competitive Strategy (CS) analytics — Chicago Booth research framework.

Covers: Competitive Moat, Disruption Risk, Market Position.
"""

import logging
from typing import Dict, Any, Optional, List

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
    if df is None or df.empty:
        return []
    for label in labels:
        if label in df.index:
            row = df.loc[label].dropna()
            return [float(row.iloc[i]) for i in range(min(n, len(row)))]
    return []


# High-margin sectors that typically have stronger moats
_MOAT_SECTORS = {
    "Technology", "Healthcare", "Communication Services",
    "Consumer Defensive", "Financial Services",
}


# ---------------------------------------------------------------------------
# Competitive Moat (Session 2/6)
# ---------------------------------------------------------------------------

@registry.register("competitive_moat")
class CompetitiveMoat(AnalyticsMethod):
    """
    0-10 moat score across five dimensions:
    switching costs, network effects, cost advantage, intangible assets, efficient scale.
    Proxy-scored from financial metrics.
    """

    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Competitive Moat Analysis", "lecture": "Session 2/6"}

        gm = info.get("grossMargins") or 0
        om = info.get("operatingMargins") or 0
        roe_val = info.get("returnOnEquity") or 0
        roa_val = info.get("returnOnAssets") or 0
        revenue = info.get("totalRevenue") or 0
        mkt_cap = info.get("marketCap") or 0
        sector = info.get("sector", "")
        rev_growth = info.get("revenueGrowth") or 0

        # R&D intensity
        rd = 0
        if data.financials is not None and not data.financials.empty:
            r = _get_val(data.financials, ["Research Development", "Research And Development"])
            if r: rd = abs(r)
        rd_pct = rd / revenue if revenue else 0

        scores = {}

        # 1. Switching Costs (proxy: high GM + recurring revenue signals)
        sc = 0
        if gm > 0.6: sc += 4
        elif gm > 0.4: sc += 3
        elif gm > 0.25: sc += 2
        else: sc += 1
        if sector in _MOAT_SECTORS: sc += 1
        scores["switching_costs"] = min(10, sc)

        # 2. Network Effects (proxy: large market cap + high margins + growth)
        ne = 0
        if mkt_cap > 100e9: ne += 3
        elif mkt_cap > 10e9: ne += 2
        else: ne += 1
        if om > 0.25: ne += 2
        elif om > 0.15: ne += 1
        if rev_growth > 0.15: ne += 2
        elif rev_growth > 0.05: ne += 1
        scores["network_effects"] = min(10, ne)

        # 3. Cost Advantage (proxy: above-average margins for sector)
        ca = 0
        if om > 0.25: ca += 4
        elif om > 0.15: ca += 3
        elif om > 0.08: ca += 2
        else: ca += 1
        if roa_val > 0.10: ca += 2
        elif roa_val > 0.05: ca += 1
        scores["cost_advantage"] = min(10, ca)

        # 4. Intangible Assets (proxy: R&D intensity + brand value from margins)
        ia = 0
        if rd_pct > 0.15: ia += 4
        elif rd_pct > 0.08: ia += 3
        elif rd_pct > 0.03: ia += 2
        else: ia += 1
        if gm > 0.5: ia += 2  # brand pricing power
        elif gm > 0.35: ia += 1
        scores["intangible_assets"] = min(10, ia)

        # 5. Efficient Scale (proxy: market dominance indicators)
        es = 0
        if mkt_cap > 50e9: es += 3
        elif mkt_cap > 10e9: es += 2
        else: es += 1
        if om > 0.20: es += 2
        if roe_val > 0.15: es += 1
        scores["efficient_scale"] = min(10, es)

        total = sum(scores.values())
        avg = total / len(scores)

        if avg >= 7:
            width = "Wide Moat"
        elif avg >= 4.5:
            width = "Narrow Moat"
        else:
            width = "No Moat"

        result.update({
            "scores": scores,
            "total_score": total,
            "average_score": round(avg, 1),
            "moat_width": width,
            "gross_margin": round(gm * 100, 2),
            "operating_margin": round(om * 100, 2),
            "rd_intensity_pct": round(rd_pct * 100, 2),
            "roe": round(roe_val * 100, 2) if roe_val else None,
            "roa": round(roa_val * 100, 2) if roa_val else None,
        })
        return result


# ---------------------------------------------------------------------------
# Disruption Risk (Session 7) — Henderson & Clark Framework
# ---------------------------------------------------------------------------

@registry.register("disruption_risk")
class DisruptionRisk(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Disruption Risk Assessment", "lecture": "Session 7 — Henderson & Clark"}

        revenue = info.get("totalRevenue") or 0
        rev_growth = info.get("revenueGrowth") or 0
        gm = info.get("grossMargins") or 0

        # R&D intensity
        rd = 0
        if data.financials is not None and not data.financials.empty:
            r = _get_val(data.financials, ["Research Development", "Research And Development"])
            if r: rd = abs(r)
        rd_pct = rd / revenue if revenue else 0

        # Gross margin trend (declining GM = potential disruption)
        gm_values = []
        if data.financials is not None and not data.financials.empty:
            rev_list = _get_multi_year(data.financials, ["Total Revenue", "Revenue"])
            gp_list = _get_multi_year(data.financials, ["Gross Profit"])
            if rev_list and gp_list and len(rev_list) == len(gp_list):
                gm_values = [gp / r if r else 0 for gp, r in zip(gp_list, rev_list)]

        gm_trend = "Stable"
        if len(gm_values) >= 2:
            if gm_values[0] < gm_values[-1] - 0.02:
                gm_trend = "Declining"
            elif gm_values[0] > gm_values[-1] + 0.02:
                gm_trend = "Improving"

        # Disruption score (0-10, higher = more at risk)
        risk_score = 0

        # Low R&D = vulnerable to disruption
        if rd_pct < 0.02: risk_score += 3
        elif rd_pct < 0.05: risk_score += 2
        elif rd_pct < 0.10: risk_score += 1

        # Declining revenue growth
        if rev_growth < 0: risk_score += 3
        elif rev_growth < 0.05: risk_score += 2
        elif rev_growth < 0.10: risk_score += 1

        # Declining gross margins
        if gm_trend == "Declining": risk_score += 2
        elif gm_trend == "Stable": risk_score += 1

        # Henderson & Clark classification
        if rd_pct > 0.10 and rev_growth > 0.15:
            innovation_type = "Radical Innovation Leader"
        elif rd_pct > 0.05 and rev_growth > 0.05:
            innovation_type = "Incremental Innovator"
        elif rd_pct > 0.05:
            innovation_type = "Architectural Innovation"
        else:
            innovation_type = "Modular / Component Innovation"

        result.update({
            "disruption_risk_score": min(10, risk_score),
            "risk_level": "High" if risk_score >= 7 else "Moderate" if risk_score >= 4 else "Low",
            "innovation_type": innovation_type,
            "rd_intensity_pct": round(rd_pct * 100, 2),
            "revenue_growth": round(rev_growth * 100, 2) if rev_growth else None,
            "gross_margin_trend": gm_trend,
            "gross_margin_history": [round(g * 100, 2) for g in gm_values] if gm_values else None,
        })
        return result


# ---------------------------------------------------------------------------
# Market Position (Session 2/3)
# ---------------------------------------------------------------------------

@registry.register("market_position")
class MarketPosition(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Market Position Analysis", "lecture": "Session 2/3"}

        gm = info.get("grossMargins") or 0
        om = info.get("operatingMargins") or 0
        rev_growth = info.get("revenueGrowth") or 0
        mkt_cap = info.get("marketCap") or 0
        pb = info.get("priceToBook") or 0
        beta = info.get("beta") or 1.0
        roe_val = info.get("returnOnEquity") or 0

        # Classify market position
        if om > 0.20 and gm > 0.40:
            position = "Pricing Leader"
            position_detail = "High margins indicate strong pricing power and differentiation"
        elif om > 0.10 and rev_growth > 0.10:
            position = "Growth Challenger"
            position_detail = "Solid margins with strong growth trajectory"
        elif om > 0.10:
            position = "Stable Competitor"
            position_detail = "Decent margins but limited growth"
        elif om > 0 and rev_growth > 0:
            position = "Margin-Challenged"
            position_detail = "Low margins suggest competitive pressure on pricing"
        else:
            position = "Turnaround Candidate"
            position_detail = "Negative margins require strategic reassessment"

        # Market cap tier
        if mkt_cap > 200e9:
            cap_tier = "Mega-Cap"
        elif mkt_cap > 10e9:
            cap_tier = "Large-Cap"
        elif mkt_cap > 2e9:
            cap_tier = "Mid-Cap"
        elif mkt_cap > 300e6:
            cap_tier = "Small-Cap"
        else:
            cap_tier = "Micro-Cap"

        # Risk profile
        if beta < 0.8:
            risk_profile = "Defensive"
        elif beta < 1.2:
            risk_profile = "Market-Neutral"
        else:
            risk_profile = "Aggressive"

        result.update({
            "market_position": position,
            "position_detail": position_detail,
            "cap_tier": cap_tier,
            "market_cap": mkt_cap,
            "gross_margin_pct": round(gm * 100, 2),
            "operating_margin_pct": round(om * 100, 2),
            "revenue_growth_pct": round(rev_growth * 100, 2) if rev_growth else None,
            "price_to_book": round(pb, 2) if pb else None,
            "beta": round(beta, 2) if beta else None,
            "roe_pct": round(roe_val * 100, 2) if roe_val else None,
            "risk_profile": risk_profile,
        })
        return result
