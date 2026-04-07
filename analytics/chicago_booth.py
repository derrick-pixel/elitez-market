"""
Corporate Finance (CF) analytics — Chicago Booth research framework.

Covers: CAPM & Jensen's Alpha, Valuation Multiples, WACC, FCF, DCF 3-Stage.
"""

import io
import logging
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd
import requests

from models.stock import StockData
from analytics.base import AnalyticsMethod, registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sector median multiples (hardcoded benchmarks)
# ---------------------------------------------------------------------------
SECTOR_MEDIANS = {
    "Technology":        {"PE": 28, "EV_EBITDA": 18, "PB": 5.0, "PS": 5.0},
    "Healthcare":        {"PE": 22, "EV_EBITDA": 15, "PB": 3.5, "PS": 3.5},
    "Financial Services":{"PE": 13, "EV_EBITDA": 10, "PB": 1.3, "PS": 2.5},
    "Consumer Cyclical":  {"PE": 18, "EV_EBITDA": 12, "PB": 3.0, "PS": 1.5},
    "Consumer Defensive": {"PE": 20, "EV_EBITDA": 14, "PB": 3.0, "PS": 1.8},
    "Industrials":       {"PE": 20, "EV_EBITDA": 13, "PB": 3.0, "PS": 1.8},
    "Energy":            {"PE": 10, "EV_EBITDA": 6,  "PB": 1.5, "PS": 1.0},
    "Utilities":         {"PE": 17, "EV_EBITDA": 11, "PB": 1.8, "PS": 2.0},
    "Real Estate":       {"PE": 35, "EV_EBITDA": 20, "PB": 2.0, "PS": 5.0},
    "Basic Materials":   {"PE": 14, "EV_EBITDA": 8,  "PB": 2.0, "PS": 1.5},
    "Communication Services": {"PE": 18, "EV_EBITDA": 10, "PB": 2.5, "PS": 2.5},
}
DEFAULT_MEDIANS = {"PE": 18, "EV_EBITDA": 12, "PB": 2.5, "PS": 2.0}


# ---------------------------------------------------------------------------
# Helpers: risk-free rate & S&P 500 returns
# ---------------------------------------------------------------------------

def _get_risk_free_rate() -> float:
    """FRED → yfinance ^TNX → hardcoded 4.3%."""
    # Try FRED first (free, no key needed)
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df = df.dropna()
        val = float(df.iloc[-1, 1])
        if 0 < val < 20:
            return val / 100.0
    except Exception as e:
        logger.debug("FRED risk-free rate failed: %s", e)

    # Try yfinance ^TNX
    try:
        import yfinance as yf
        tnx = yf.Ticker("^TNX")
        price = tnx.info.get("regularMarketPrice", 0)
        if price and 0 < price < 20:
            return price / 100.0
    except Exception as e:
        logger.debug("yfinance ^TNX failed: %s", e)

    return 0.043  # hardcoded fallback


def _get_sp500_returns(period: str = "1y") -> Optional[pd.Series]:
    """Stooq ^spx → yfinance ^GSPC fallback."""
    # Try Stooq first
    try:
        url = "https://stooq.com/q/d/l/?s=^spx&i=d"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if not df.empty and "Close" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
            cutoff = pd.Timestamp.now() - pd.DateOffset(years=1)
            df = df[df.index >= cutoff]
            if not df.empty:
                return df["Close"].pct_change().dropna()
    except Exception as e:
        logger.debug("Stooq S&P 500 failed: %s", e)

    # yfinance fallback
    try:
        import yfinance as yf
        spy = yf.Ticker("^GSPC")
        hist = spy.history(period=period)
        if hist is not None and not hist.empty:
            return hist["Close"].pct_change().dropna()
    except Exception as e:
        logger.debug("yfinance ^GSPC failed: %s", e)

    return None


# ---------------------------------------------------------------------------
# CAPM & Jensen's Alpha (Lecture 2B)
# ---------------------------------------------------------------------------

@registry.register("capm_alpha")
class CAPMAlpha(AnalyticsMethod):
    MRP = 0.07  # market risk premium

    def run(self, data: StockData) -> Dict[str, Any]:
        result = {
            "method": "CAPM & Jensen's Alpha",
            "lecture": "Lecture 2B",
        }

        if data.history is None or data.history.empty:
            result["error"] = "No price history available"
            return result

        stock_returns = data.history["Close"].pct_change().dropna()
        market_returns = _get_sp500_returns()

        if market_returns is None or market_returns.empty:
            result["error"] = "Could not fetch S&P 500 data"
            return result

        # Align dates
        combined = pd.DataFrame({
            "stock": stock_returns,
            "market": market_returns,
        }).dropna()

        if len(combined) < 30:
            result["error"] = "Insufficient overlapping data points"
            return result

        # OLS regression: stock = alpha + beta * market
        x = combined["market"].values
        y = combined["stock"].values
        x_mean = x.mean()
        y_mean = y.mean()
        beta = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
        alpha_daily = y_mean - beta * x_mean

        rf = _get_risk_free_rate()
        expected_return = rf + beta * self.MRP
        actual_annual = (1 + stock_returns.mean()) ** 252 - 1
        jensens_alpha = actual_annual - expected_return

        # R-squared
        y_pred = alpha_daily + beta * x
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 0

        result.update({
            "beta": round(beta, 3),
            "risk_free_rate": round(rf, 4),
            "market_risk_premium": self.MRP,
            "expected_return": round(expected_return, 4),
            "actual_annualized_return": round(actual_annual, 4),
            "jensens_alpha": round(jensens_alpha, 4),
            "r_squared": round(r_squared, 4),
            "data_points": len(combined),
        })
        return result


# ---------------------------------------------------------------------------
# Valuation Multiples (Lecture 5B)
# ---------------------------------------------------------------------------

@registry.register("valuation_multiples")
class ValuationMultiples(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        sector = info.get("sector", "")
        medians = SECTOR_MEDIANS.get(sector, DEFAULT_MEDIANS)

        pe = info.get("trailingPE")
        ev_ebitda = info.get("enterpriseToEbitda")
        pb = info.get("priceToBook")
        ps = info.get("priceToSalesTrailing12Months")

        def _vs(val, med_key):
            med = medians[med_key]
            if val is None or med is None:
                return None
            pct = ((val - med) / med) * 100
            if pct > 20:
                return "Premium"
            elif pct < -20:
                return "Discount"
            return "In-line"

        return {
            "method": "Valuation Multiples",
            "lecture": "Lecture 5B",
            "sector": sector,
            "pe_ratio": round(pe, 2) if pe else None,
            "pe_sector_median": medians["PE"],
            "pe_vs_sector": _vs(pe, "PE"),
            "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else None,
            "ev_ebitda_sector_median": medians["EV_EBITDA"],
            "ev_ebitda_vs_sector": _vs(ev_ebitda, "EV_EBITDA"),
            "pb_ratio": round(pb, 2) if pb else None,
            "pb_sector_median": medians["PB"],
            "pb_vs_sector": _vs(pb, "PB"),
            "ps_ratio": round(ps, 2) if ps else None,
            "ps_sector_median": medians["PS"],
            "ps_vs_sector": _vs(ps, "PS"),
        }


# ---------------------------------------------------------------------------
# WACC (Lecture 4B)
# ---------------------------------------------------------------------------

@registry.register("wacc")
class WACC(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "WACC", "lecture": "Lecture 4B"}

        mkt_cap = info.get("marketCap") or 0
        total_debt = info.get("totalDebt") or 0
        total_capital = mkt_cap + total_debt

        if total_capital == 0:
            result["error"] = "Cannot compute WACC — missing capital data"
            return result

        rf = _get_risk_free_rate()
        beta = info.get("beta") or 1.0
        mrp = 0.07
        cost_equity = rf + beta * mrp

        # Cost of debt: approximate from interest expense / total debt
        interest_expense = 0
        if data.financials is not None and not data.financials.empty:
            for col_name in ["Interest Expense", "InterestExpense"]:
                if col_name in data.financials.index:
                    val = data.financials.loc[col_name].dropna()
                    if not val.empty:
                        interest_expense = abs(float(val.iloc[0]))
                        break

        cost_debt = interest_expense / total_debt if total_debt > 0 else rf + 0.02
        tax_rate = 0.21  # US corporate default

        e_weight = mkt_cap / total_capital
        d_weight = total_debt / total_capital
        wacc = e_weight * cost_equity + d_weight * cost_debt * (1 - tax_rate)

        result.update({
            "market_cap": mkt_cap,
            "total_debt": total_debt,
            "equity_weight": round(e_weight, 4),
            "debt_weight": round(d_weight, 4),
            "cost_of_equity": round(cost_equity, 4),
            "cost_of_debt": round(cost_debt, 4),
            "tax_rate": tax_rate,
            "wacc": round(wacc, 4),
            "risk_free_rate": round(rf, 4),
            "beta": beta,
        })
        return result


# ---------------------------------------------------------------------------
# Free Cash Flow (Lectures 4A/4B)
# ---------------------------------------------------------------------------

@registry.register("free_cash_flow")
class FreeCashFlow(AnalyticsMethod):
    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "Free Cash Flow", "lecture": "Lectures 4A/4B"}

        fcf = info.get("freeCashflow")
        ocf = info.get("operatingCashflow")
        revenue = info.get("totalRevenue")
        mkt_cap = info.get("marketCap")

        # Try to compute from cash flow statement
        if fcf is None and data.cash_flow is not None and not data.cash_flow.empty:
            cf = data.cash_flow
            op_cf = None
            capex = None
            for label in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                if label in cf.index:
                    val = cf.loc[label].dropna()
                    if not val.empty:
                        op_cf = float(val.iloc[0])
                        break
            for label in ["Capital Expenditure", "Capital Expenditures"]:
                if label in cf.index:
                    val = cf.loc[label].dropna()
                    if not val.empty:
                        capex = float(val.iloc[0])
                        break
            if op_cf is not None and capex is not None:
                fcf = op_cf + capex  # capex is typically negative
                ocf = op_cf

        fcf_yield = (fcf / mkt_cap * 100) if fcf and mkt_cap else None
        fcf_margin = (fcf / revenue * 100) if fcf and revenue else None

        result.update({
            "free_cash_flow": fcf,
            "operating_cash_flow": ocf,
            "revenue": revenue,
            "market_cap": mkt_cap,
            "fcf_yield_pct": round(fcf_yield, 2) if fcf_yield else None,
            "fcf_margin_pct": round(fcf_margin, 2) if fcf_margin else None,
        })
        return result


# ---------------------------------------------------------------------------
# DCF 3-Stage Model (Lecture 5B)
# ---------------------------------------------------------------------------

@registry.register("dcf_model")
class DCFModel(AnalyticsMethod):
    TERMINAL_GROWTH = 0.025  # 2.5%

    def run(self, data: StockData) -> Dict[str, Any]:
        info = data.info
        result = {"method": "DCF 3-Stage Model", "lecture": "Lecture 5B"}

        # Get base FCF — normalize using 3-year average if possible
        fcf_list = []
        if data.cash_flow is not None and not data.cash_flow.empty:
            cf = data.cash_flow
            op_row = None
            cx_row = None
            for label in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                if label in cf.index:
                    op_row = cf.loc[label]
                    break
            for label in ["Capital Expenditure", "Capital Expenditures"]:
                if label in cf.index:
                    cx_row = cf.loc[label]
                    break
            if op_row is not None and cx_row is not None:
                for col in cf.columns[:4]:
                    try:
                        o = float(op_row[col])
                        c = float(cx_row[col])
                        fcf_list.append(o + c)
                    except (ValueError, TypeError):
                        pass

        if not fcf_list:
            single_fcf = info.get("freeCashflow")
            if single_fcf:
                fcf_list = [single_fcf]

        if not fcf_list:
            result["error"] = "No FCF data available for DCF"
            return result

        # 3-year average (or whatever we have)
        base_fcf = np.mean(fcf_list[:3])
        if base_fcf <= 0:
            result["error"] = "Negative base FCF — DCF not meaningful"
            result["base_fcf"] = base_fcf
            return result

        # Growth rates
        rev_growth = info.get("revenueGrowth") or 0.05
        near_term_growth = max(min(rev_growth, 0.30), 0.02)  # clamp 2-30%
        fade_growth = (near_term_growth + self.TERMINAL_GROWTH) / 2

        # WACC
        rf = _get_risk_free_rate()
        beta = info.get("beta") or 1.0
        cost_equity = rf + beta * 0.07
        mkt_cap = info.get("marketCap") or 0
        total_debt = info.get("totalDebt") or 0
        total_capital = mkt_cap + total_debt
        if total_capital > 0:
            e_w = mkt_cap / total_capital
            d_w = total_debt / total_capital
        else:
            e_w, d_w = 1.0, 0.0
        cost_debt = rf + 0.02
        wacc = e_w * cost_equity + d_w * cost_debt * 0.79
        wacc = max(wacc, 0.05)  # floor at 5%

        # Stage 1: years 1-5 (near-term growth)
        stage1_cf = []
        cf = base_fcf
        for _ in range(5):
            cf *= (1 + near_term_growth)
            stage1_cf.append(cf)

        # Stage 2: years 6-10 (fade growth)
        stage2_cf = []
        for _ in range(5):
            cf *= (1 + fade_growth)
            stage2_cf.append(cf)

        # Terminal value
        terminal_cf = cf * (1 + self.TERMINAL_GROWTH)
        terminal_value = terminal_cf / (wacc - self.TERMINAL_GROWTH)

        # Discount everything
        all_cfs = stage1_cf + stage2_cf + [terminal_value]
        pv_total = sum(c / (1 + wacc) ** (i + 1) for i, c in enumerate(all_cfs))

        shares = info.get("sharesOutstanding") or 1
        intrinsic_per_share = pv_total / shares
        current_price = data.price or 0
        upside = ((intrinsic_per_share - current_price) / current_price * 100) if current_price else None

        # Sensitivity grid: WACC ±1%, terminal growth ±0.5%
        sensitivity = {}
        for wacc_delta in [-0.01, 0, 0.01]:
            for g_delta in [-0.005, 0, 0.005]:
                w = wacc + wacc_delta
                g = self.TERMINAL_GROWTH + g_delta
                if w <= g:
                    continue
                tv = terminal_cf / (w - g) if (w - g) > 0 else 0
                pvs = sum(c / (1 + w) ** (i + 1) for i, c in enumerate(stage1_cf + stage2_cf + [tv]))
                sensitivity[f"WACC={w:.1%},g={g:.1%}"] = round(pvs / shares, 2)

        result.update({
            "base_fcf": round(base_fcf, 0),
            "near_term_growth": round(near_term_growth, 4),
            "fade_growth": round(fade_growth, 4),
            "terminal_growth": self.TERMINAL_GROWTH,
            "wacc": round(wacc, 4),
            "stage1_pv": round(sum(c / (1 + wacc) ** (i + 1) for i, c in enumerate(stage1_cf)), 0),
            "stage2_pv": round(sum(c / (1 + wacc) ** (i + 6) for i, c in enumerate(stage2_cf)), 0),
            "terminal_value_pv": round(terminal_value / (1 + wacc) ** 10, 0),
            "enterprise_value": round(pv_total, 0),
            "intrinsic_value_per_share": round(intrinsic_per_share, 2),
            "current_price": current_price,
            "upside_pct": round(upside, 2) if upside else None,
            "sensitivity": sensitivity,
            "shares_outstanding": shares,
        })
        return result
