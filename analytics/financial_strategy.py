"""
Financial Strategy (FS) analytics — Chicago Booth research framework.

Covers: Capital Structure, Implied Credit Rating, Static Trade-Off,
Payout & Cash Policy, Altman Z-Score, Pecking Order.
"""

import logging
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

from models.stock import StockData
from analytics.base import AnalyticsMethod, registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper: extract financial statement values
# ---------------------------------------------------------------------------

def _get_val(df: Optional[pd.DataFrame], labels: list, col_idx: int = 0) -> Optional[float]:
    """Extract a value from a financial statement DataFrame."""
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


# ---------------------------------------------------------------------------
# Capital Structure Ratios (D1)
# ---------------------------------------------------------------------------

@registry.register("capital_structure")
class CapitalStructure(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Capital Structure Ratios", "lecture": "D1"}

        total_debt = info.get("totalDebt") or 0
        total_cash = info.get("totalCash") or 0
        mkt_cap = info.get("marketCap") or 0
        ebitda = info.get("ebitda") or 0

        # Try balance sheet for more precise values
        bs = data.balance_sheet
        if bs is not None and not bs.empty:
            td = _get_val(bs, ["Total Debt", "Long Term Debt"])
            if td is not None:
                total_debt = td
            tc = _get_val(bs, ["Cash And Cash Equivalents", "Cash"])
            if tc is not None:
                total_cash = tc

        net_debt = total_debt - total_cash
        total_capital = mkt_cap + net_debt

        # FCF for FCF/debt
        fcf = info.get("freeCashflow") or 0

        result.update({
            "total_debt": total_debt,
            "total_cash": total_cash,
            "net_debt": net_debt,
            "market_cap": mkt_cap,
            "net_debt_to_capital": round(net_debt / total_capital, 4) if total_capital else None,
            "net_debt_to_ebitda": round(net_debt / ebitda, 2) if ebitda else None,
            "fcf_to_debt": round(fcf / total_debt, 4) if total_debt else None,
            "debt_to_equity_pct": round(total_debt / mkt_cap * 100, 2) if mkt_cap else None,
        })
        return result


# ---------------------------------------------------------------------------
# Implied S&P Credit Rating (D1)
# ---------------------------------------------------------------------------

CREDIT_RATING_TABLE = [
    ("AAA", 0.0063),
    ("AA+", 0.0078),
    ("AA",  0.0098),
    ("AA-", 0.0108),
    ("A+",  0.0123),
    ("A",   0.0132),
    ("A-",  0.0155),
    ("BBB+",0.0168),
    ("BBB", 0.0195),
    ("BBB-",0.0225),
    ("BB+", 0.0325),
    ("BB",  0.0400),
    ("BB-", 0.0500),
    ("B+",  0.0600),
    ("B",   0.0750),
    ("B-",  0.0900),
    ("CCC+",0.1050),
    ("CCC", 0.1200),
]


@registry.register("credit_rating")
class ImpliedCreditRating(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Implied S&P Credit Rating", "lecture": "D1"}

        ebit = None
        ebitda = info.get("ebitda") or 0
        total_debt = info.get("totalDebt") or 0
        interest_expense = 0
        operating_margin = info.get("operatingMargins") or 0
        fcf = info.get("freeCashflow") or 0
        mkt_cap = info.get("marketCap") or 0

        # Get EBIT from financials
        if data.financials is not None and not data.financials.empty:
            ebit = _get_val(data.financials, ["EBIT", "Operating Income"])
            ie = _get_val(data.financials, ["Interest Expense", "InterestExpense"])
            if ie is not None:
                interest_expense = abs(ie)

        if ebit is None:
            ebit = ebitda * 0.8  # rough approximation

        # Long-term debt / capital
        ltd = total_debt
        bs = data.balance_sheet
        if bs is not None and not bs.empty:
            v = _get_val(bs, ["Long Term Debt"])
            if v is not None:
                ltd = v
        total_capital = mkt_cap + total_debt

        # Score components (higher = better credit)
        scores = []

        # EBIT / Interest
        if interest_expense > 0:
            ebit_int = ebit / interest_expense
            if ebit_int > 15: scores.append(8)
            elif ebit_int > 10: scores.append(7)
            elif ebit_int > 6: scores.append(6)
            elif ebit_int > 4: scores.append(5)
            elif ebit_int > 2.5: scores.append(4)
            elif ebit_int > 1.5: scores.append(3)
            elif ebit_int > 1: scores.append(2)
            else: scores.append(1)
            result["ebit_to_interest"] = round(ebit_int, 2)
        else:
            scores.append(7)  # no debt = good credit

        # EBITDA / Interest
        if interest_expense > 0 and ebitda:
            ebitda_int = ebitda / interest_expense
            if ebitda_int > 20: scores.append(8)
            elif ebitda_int > 12: scores.append(7)
            elif ebitda_int > 8: scores.append(6)
            elif ebitda_int > 5: scores.append(5)
            elif ebitda_int > 3: scores.append(4)
            elif ebitda_int > 2: scores.append(3)
            else: scores.append(2)
            result["ebitda_to_interest"] = round(ebitda_int, 2)

        # FCF / Debt
        if total_debt > 0 and fcf:
            fcf_debt = fcf / total_debt
            if fcf_debt > 0.5: scores.append(8)
            elif fcf_debt > 0.3: scores.append(7)
            elif fcf_debt > 0.2: scores.append(6)
            elif fcf_debt > 0.1: scores.append(5)
            elif fcf_debt > 0.05: scores.append(4)
            elif fcf_debt > 0: scores.append(3)
            else: scores.append(1)

        # LTD / Capital
        if total_capital > 0:
            ltd_cap = ltd / total_capital
            if ltd_cap < 0.1: scores.append(8)
            elif ltd_cap < 0.2: scores.append(7)
            elif ltd_cap < 0.3: scores.append(6)
            elif ltd_cap < 0.4: scores.append(5)
            elif ltd_cap < 0.5: scores.append(4)
            elif ltd_cap < 0.6: scores.append(3)
            else: scores.append(2)

        # Operating Margin
        if operating_margin > 0.30: scores.append(8)
        elif operating_margin > 0.20: scores.append(7)
        elif operating_margin > 0.15: scores.append(6)
        elif operating_margin > 0.10: scores.append(5)
        elif operating_margin > 0.05: scores.append(4)
        elif operating_margin > 0: scores.append(3)
        else: scores.append(1)

        avg_score = np.mean(scores) if scores else 4
        # Map score to rating
        idx = max(0, min(len(CREDIT_RATING_TABLE) - 1, int(18 - avg_score * 2)))
        rating, spread = CREDIT_RATING_TABLE[idx]

        result.update({
            "composite_score": round(avg_score, 2),
            "implied_rating": rating,
            "credit_spread_bps": round(spread * 10000),
            "num_factors": len(scores),
        })
        return result


# ---------------------------------------------------------------------------
# Static Trade-Off (D2/D3/D4)
# ---------------------------------------------------------------------------

@registry.register("static_tradeoff")
class StaticTradeOff(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Static Trade-Off Analysis", "lecture": "D2/D3/D4"}

        total_debt = info.get("totalDebt") or 0
        ebitda = info.get("ebitda") or 0
        interest_expense = 0
        mkt_cap = info.get("marketCap") or 0

        if data.financials is not None and not data.financials.empty:
            ie = _get_val(data.financials, ["Interest Expense", "InterestExpense"])
            if ie is not None:
                interest_expense = abs(ie)

        tax_rate = 0.21

        # PV of tax shield = tax_rate * total_debt (simple perpetuity approx)
        pv_tax_shield = tax_rate * total_debt

        # PV of discipline benefit: debt constrains management
        # Proxy: if FCF is high and payout is low, discipline value is higher
        fcf = info.get("freeCashflow") or 0
        payout = info.get("payoutRatio") or 0
        discipline_score = 0
        if fcf > 0 and mkt_cap > 0:
            fcf_yield = fcf / mkt_cap
            if fcf_yield > 0.05 and payout < 0.3:
                discipline_score = 0.02 * mkt_cap  # ~2% of market cap
            elif fcf_yield > 0.03:
                discipline_score = 0.01 * mkt_cap

        # PV of distress cost: higher leverage & lower interest coverage = more distress
        leverage = total_debt / (mkt_cap + total_debt) if (mkt_cap + total_debt) else 0
        coverage = ebitda / interest_expense if interest_expense > 0 else 99
        if coverage < 2:
            distress_pct = 0.15
        elif coverage < 4:
            distress_pct = 0.08
        elif coverage < 8:
            distress_pct = 0.03
        else:
            distress_pct = 0.01
        pv_distress = distress_pct * (mkt_cap + total_debt) * leverage

        net_benefit = pv_tax_shield + discipline_score - pv_distress

        result.update({
            "total_debt": total_debt,
            "tax_rate": tax_rate,
            "pv_tax_shield": round(pv_tax_shield, 0),
            "pv_discipline_benefit": round(discipline_score, 0),
            "pv_distress_cost": round(pv_distress, 0),
            "net_benefit_of_debt": round(net_benefit, 0),
            "leverage_ratio": round(leverage, 4),
            "interest_coverage": round(coverage, 2) if coverage < 99 else "N/A (no debt)",
            "assessment": "Overleveraged" if net_benefit < 0 else "Debt adds value" if net_benefit > pv_tax_shield * 0.3 else "Near optimal",
        })
        return result


# ---------------------------------------------------------------------------
# Payout & Cash Policy (D4 FANUC)
# ---------------------------------------------------------------------------

@registry.register("payout_policy")
class PayoutPolicy(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Payout & Cash Policy", "lecture": "D4 FANUC"}

        total_cash = info.get("totalCash") or 0
        total_debt = info.get("totalDebt") or 0
        mkt_cap = info.get("marketCap") or 0
        fcf = info.get("freeCashflow") or 0
        div_yield = info.get("dividendYield") or 0
        payout_ratio = info.get("payoutRatio") or 0
        ebitda = info.get("ebitda") or 0

        # Excess cash = cash - (revenue * 5% operational buffer)
        revenue = info.get("totalRevenue") or 0
        operational_cash_need = revenue * 0.05
        excess_cash = max(0, total_cash - operational_cash_need)

        # Tax drag: cash earns ~4% pre-tax, taxed at 21%
        tax_drag = excess_cash * 0.04 * 0.21

        # Net debt position
        net_debt = total_debt - total_cash

        result.update({
            "total_cash": total_cash,
            "total_debt": total_debt,
            "net_debt": net_debt,
            "excess_cash": round(excess_cash, 0),
            "tax_drag_annual": round(tax_drag, 0),
            "dividend_yield": round(div_yield * 100, 2) if div_yield else 0,
            "payout_ratio": round(payout_ratio * 100, 2) if payout_ratio else 0,
            "fcf": fcf,
            "cash_as_pct_of_mktcap": round(total_cash / mkt_cap * 100, 2) if mkt_cap else None,
            "assessment": (
                "Cash-rich, potential return opportunity" if excess_cash > mkt_cap * 0.1
                else "Adequate cash position" if total_cash > operational_cash_need
                else "Cash-constrained"
            ),
        })
        return result


# ---------------------------------------------------------------------------
# Altman Z-Score
# ---------------------------------------------------------------------------

@registry.register("altman_z")
class AltmanZScore(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Altman Z-Score", "lecture": "Bankruptcy Prediction"}

        total_assets = 0
        working_capital = 0
        retained_earnings = 0
        ebit = 0
        revenue = info.get("totalRevenue") or 0
        mkt_cap = info.get("marketCap") or 0
        total_liabilities = 0

        bs = data.balance_sheet
        if bs is not None and not bs.empty:
            ta = _get_val(bs, ["Total Assets"])
            if ta: total_assets = ta
            tl = _get_val(bs, ["Total Liabilities Net Minority Interest", "Total Liab"])
            if tl: total_liabilities = tl
            ca = _get_val(bs, ["Current Assets"]) or 0
            cl = _get_val(bs, ["Current Liabilities"]) or 0
            working_capital = ca - cl
            re = _get_val(bs, ["Retained Earnings"])
            if re: retained_earnings = re

        if data.financials is not None and not data.financials.empty:
            e = _get_val(data.financials, ["EBIT", "Operating Income"])
            if e: ebit = e

        if total_assets == 0:
            result["error"] = "Missing balance sheet data"
            return result

        a = working_capital / total_assets
        b = retained_earnings / total_assets
        c = ebit / total_assets
        d = mkt_cap / total_liabilities if total_liabilities else 0
        e = revenue / total_assets

        z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e

        if z > 2.99:
            zone = "Safe Zone"
        elif z > 1.81:
            zone = "Grey Zone"
        else:
            zone = "Distress Zone"

        result.update({
            "z_score": round(z, 3),
            "zone": zone,
            "wc_ta": round(a, 4),
            "re_ta": round(b, 4),
            "ebit_ta": round(c, 4),
            "mktcap_liab": round(d, 4),
            "rev_ta": round(e, 4),
            "total_assets": total_assets,
        })
        return result


# ---------------------------------------------------------------------------
# Pecking Order (Myers-Majluf 1984)
# ---------------------------------------------------------------------------

@registry.register("pecking_order")
class PeckingOrder(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Pecking Order Theory", "lecture": "Myers-Majluf 1984"}

        fcf = info.get("freeCashflow") or 0
        total_debt = info.get("totalDebt") or 0
        mkt_cap = info.get("marketCap") or 0
        payout_ratio = info.get("payoutRatio") or 0
        retained_earnings = 0

        bs = data.balance_sheet
        if bs is not None and not bs.empty:
            re = _get_val(bs, ["Retained Earnings"])
            if re: retained_earnings = re
            equity = _get_val(bs, ["Total Stockholder Equity", "Stockholders Equity"])
            if equity and equity > 0:
                re_to_equity = retained_earnings / equity
            else:
                re_to_equity = None
        else:
            re_to_equity = None

        # CapEx
        capex = 0
        if data.cash_flow is not None and not data.cash_flow.empty:
            cx = _get_val(data.cash_flow, ["Capital Expenditure", "Capital Expenditures"])
            if cx: capex = abs(cx)

        # Financing hierarchy analysis
        internal_funding = fcf > capex
        debt_level = "Low" if total_debt / mkt_cap < 0.3 else "Moderate" if total_debt / mkt_cap < 0.6 else "High" if mkt_cap else "Unknown"

        result.update({
            "free_cash_flow": fcf,
            "capex": capex,
            "fcf_minus_capex": fcf - capex if fcf else None,
            "internal_funding_sufficient": internal_funding,
            "payout_ratio": round(payout_ratio * 100, 2) if payout_ratio else 0,
            "retained_earnings": retained_earnings,
            "re_to_equity": round(re_to_equity, 4) if re_to_equity else None,
            "debt_level": debt_level,
            "debt_to_mktcap": round(total_debt / mkt_cap * 100, 2) if mkt_cap else None,
            "pecking_order_stage": (
                "Stage 1: Internal Funds" if internal_funding
                else "Stage 2: Debt Financing" if debt_level != "High"
                else "Stage 3: Equity Financing"
            ),
        })
        return result
