"""
Elitez Asia's Analytics — Market Tracker
Two-page Streamlit app: Dashboard + CB Analysis
"""

import os
import re
import logging

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf

# ---------------------------------------------------------------------------
# Secrets → environment (must happen before any analytics import)
# ---------------------------------------------------------------------------
for _k in ("ANTHROPIC_API_KEY", "FINNHUB_KEY"):
    os.environ[_k] = st.secrets.get(_k, "")

from tracker import (
    run_booth_analysis,
    run_fs_analysis,
    run_om_analysis,
    run_cs_analysis,
    get_stock_info,
    get_stock_data,
)
from guest_limit import check_rate_limit, remaining
from pdf_report import generate_pdf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Market Tracker — Elitez Asia",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

MAROON = "#9B1B30"
GREY = "#94a3b8"

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
    .main-header {{
        font-size: 2rem;
        font-weight: 700;
        color: {MAROON};
        margin-bottom: 0.2rem;
    }}
    .sub-header {{
        font-size: 1rem;
        color: {GREY};
        margin-bottom: 1.5rem;
    }}
    .metric-card {{
        background: #ffffff;
        border-left: 4px solid {MAROON};
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .metric-card h4 {{
        margin: 0 0 0.3rem 0;
        color: {MAROON};
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .metric-card .value {{
        font-size: 1.6rem;
        font-weight: 700;
        color: #1e293b;
    }}
    .booth-card {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    .booth-card h3 {{
        color: {MAROON};
        border-bottom: 2px solid {MAROON};
        padding-bottom: 0.4rem;
        margin-bottom: 0.8rem;
    }}
    .booth-card table {{
        width: 100%;
        border-collapse: collapse;
    }}
    .booth-card table td {{
        padding: 0.35rem 0.5rem;
        border-bottom: 1px solid #f1f5f9;
    }}
    .booth-card table td:first-child {{
        color: {GREY};
        font-weight: 500;
    }}
    .booth-card table td:last-child {{
        text-align: right;
        font-weight: 600;
    }}
    .ai-narrative {{
        background: linear-gradient(135deg, #fdf2f4 0%, #fff 100%);
        border-left: 4px solid {MAROON};
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        line-height: 1.7;
    }}
    .company-header {{
        background: linear-gradient(135deg, {MAROON} 0%, #7d1526 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }}
    .company-header h1 {{
        margin: 0;
        font-size: 1.8rem;
    }}
    .company-header .sector {{
        opacity: 0.85;
        font-size: 0.95rem;
    }}
    .tag-good {{ color: #16a34a; font-weight: 600; }}
    .tag-warn {{ color: #d97706; font-weight: 600; }}
    .tag-bad {{ color: #dc2626; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper: Markdown → HTML for AI narratives
# ---------------------------------------------------------------------------

def _md(text: str) -> str:
    """Convert markdown (bold, italic, headings, newlines) to HTML."""
    if not text:
        return ""
    # Headings
    text = re.sub(r'^### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    # Bold and italic
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Newlines
    text = text.replace('\n', '<br>')
    return text


# ---------------------------------------------------------------------------
# Helper: format numbers
# ---------------------------------------------------------------------------

def _fmt(val, fmt_type="number"):
    if val is None:
        return "N/A"
    try:
        val = float(val)
    except (ValueError, TypeError):
        return str(val)
    if fmt_type == "currency":
        if abs(val) >= 1e12:
            return f"${val/1e12:.2f}T"
        if abs(val) >= 1e9:
            return f"${val/1e9:.2f}B"
        if abs(val) >= 1e6:
            return f"${val/1e6:.2f}M"
        return f"${val:,.0f}"
    if fmt_type == "pct":
        return f"{val:.2f}%"
    if fmt_type == "price":
        return f"${val:,.2f}"
    return f"{val:,.2f}"


# ---------------------------------------------------------------------------
# AI Narrative Generation
# ---------------------------------------------------------------------------

def _get_ai_narrative(prompt: str, data: dict) -> str:
    """Generate AI narrative using Claude API."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "*AI narrative unavailable — set ANTHROPIC_API_KEY in secrets.*"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"{prompt}\n\nData:\n{data}",
            }],
        )
        return message.content[0].text
    except Exception as e:
        logger.error("AI narrative failed: %s", e)
        return f"*AI narrative generation failed: {e}*"


# ---------------------------------------------------------------------------
# Cached analysis calls (TTL 1 hour)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def _cached_booth(ticker):
    return run_booth_analysis(ticker)

@st.cache_data(ttl=3600)
def _cached_fs(ticker):
    return run_fs_analysis(ticker)

@st.cache_data(ttl=3600)
def _cached_om(ticker):
    return run_om_analysis(ticker)

@st.cache_data(ttl=3600)
def _cached_cs(ticker):
    return run_cs_analysis(ticker)


# ===================================================================
# PAGE 1: DASHBOARD
# ===================================================================

def page_dashboard():
    st.markdown('<div class="main-header">Market Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Elitez Asia\'s Analytics — Global Market Overview</div>', unsafe_allow_html=True)

    # --- Major Indices ---
    st.subheader("Major Indices")
    indices = {
        "^GSPC": "S&P 500",
        "^DJI": "Dow Jones",
        "^IXIC": "NASDAQ",
        "^FTSE": "FTSE 100",
        "^N225": "Nikkei 225",
        "^HSI": "Hang Seng",
    }

    try:
        tickers_str = " ".join(indices.keys())
        idx_data = yf.download(tickers_str, period="5d", interval="1d", group_by="ticker", progress=False)
    except Exception:
        idx_data = None

    cols = st.columns(len(indices))
    for i, (symbol, name) in enumerate(indices.items()):
        with cols[i]:
            try:
                if idx_data is not None and not idx_data.empty:
                    if len(indices) > 1:
                        close = idx_data[symbol]["Close"].dropna()
                    else:
                        close = idx_data["Close"].dropna()
                    if len(close) >= 2:
                        last = float(close.iloc[-1])
                        prev = float(close.iloc[-2])
                        chg = (last - prev) / prev * 100
                        st.metric(name, f"{last:,.0f}", f"{chg:+.2f}%")
                    else:
                        st.metric(name, "N/A")
                else:
                    st.metric(name, "N/A")
            except Exception:
                st.metric(name, "N/A")

    st.divider()

    # --- Sector Heatmap ---
    st.subheader("Sector Performance Heatmap")
    sector_etfs = {
        "XLK": "Technology", "XLV": "Healthcare", "XLF": "Financials",
        "XLY": "Cons. Disc.", "XLP": "Cons. Staples", "XLE": "Energy",
        "XLI": "Industrials", "XLU": "Utilities", "XLRE": "Real Estate",
        "XLB": "Materials", "XLC": "Communication",
    }

    try:
        etf_data = yf.download(" ".join(sector_etfs.keys()), period="5d", interval="1d", group_by="ticker", progress=False)
        sector_perf = {}
        for sym, name in sector_etfs.items():
            try:
                close = etf_data[sym]["Close"].dropna()
                if len(close) >= 2:
                    chg = (float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2]) * 100
                    sector_perf[name] = chg
            except Exception:
                pass

        if sector_perf:
            df_heat = pd.DataFrame({
                "Sector": list(sector_perf.keys()),
                "Change %": list(sector_perf.values()),
            })
            # Simple treemap-style heatmap
            fig = px.treemap(
                df_heat,
                path=["Sector"],
                values=[abs(v) + 0.1 for v in df_heat["Change %"]],
                color="Change %",
                color_continuous_scale=["#dc2626", "#fbbf24", "#16a34a"],
                color_continuous_midpoint=0,
            )
            fig.update_layout(margin=dict(t=10, l=10, r=10, b=10), height=350)
            fig.update_traces(textinfo="label+text", texttemplate="%{label}<br>%{color:+.2f}%")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load sector data: {e}")

    st.divider()

    # --- Portfolio Tracker ---
    st.subheader("Quick Portfolio Tracker")
    portfolio_input = st.text_input(
        "Enter tickers (comma-separated)",
        value="AAPL, MSFT, GOOGL, AMZN, NVDA",
        key="portfolio_input",
    )
    if portfolio_input:
        tickers = [t.strip().upper() for t in portfolio_input.split(",") if t.strip()]
        if tickers:
            try:
                port_data = yf.download(" ".join(tickers), period="1mo", interval="1d", group_by="ticker", progress=False)
                if not port_data.empty:
                    # Normalized chart
                    fig = go.Figure()
                    for t in tickers:
                        try:
                            if len(tickers) > 1:
                                close = port_data[t]["Close"].dropna()
                            else:
                                close = port_data["Close"].dropna()
                            if not close.empty:
                                normalized = close / close.iloc[0] * 100
                                fig.add_trace(go.Scatter(
                                    x=normalized.index, y=normalized.values,
                                    name=t, mode="lines",
                                ))
                        except Exception:
                            pass
                    fig.update_layout(
                        title="1-Month Relative Performance (Base = 100)",
                        yaxis_title="Normalized Price",
                        height=400,
                        margin=dict(t=40, l=40, r=20, b=40),
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not load portfolio data: {e}")


# ===================================================================
# PAGE 2: CB ANALYSIS
# ===================================================================

def page_cb_analysis():
    st.markdown('<div class="main-header">CB Research Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Chicago Booth Research Framework — Deep Single-Ticker Analysis</div>', unsafe_allow_html=True)

    # Rate limit check
    session_id = st.session_state.get("session_id", "guest")
    if "session_id" not in st.session_state:
        import uuid
        st.session_state["session_id"] = str(uuid.uuid4())
        session_id = st.session_state["session_id"]

    ticker = st.text_input("Enter Ticker Symbol", value="", placeholder="e.g. AAPL, MSFT, NVDA").strip().upper()

    if not ticker:
        st.info("Enter a ticker symbol above to begin analysis.")
        return

    if not check_rate_limit(session_id):
        st.error(f"Rate limit reached. Please try again later. ({remaining(session_id)} requests remaining)")
        return

    with st.spinner(f"Analyzing {ticker}..."):
        # --- Company Header ---
        info = get_stock_info(ticker)
        if not info:
            st.error(f"Could not fetch data for {ticker}. Please check the ticker symbol.")
            return

        name = info.get("longName") or info.get("shortName") or ticker
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        mkt_cap = info.get("marketCap")
        pe = info.get("trailingPE")
        fwd_pe = info.get("forwardPE")
        eps_val = info.get("trailingEps")
        div_yield = info.get("dividendYield")
        high52 = info.get("fiftyTwoWeekHigh")
        low52 = info.get("fiftyTwoWeekLow")
        description = info.get("longBusinessSummary", "")

        st.markdown(f"""
        <div class="company-header">
            <h1>{name} ({ticker})</h1>
            <div class="sector">{sector} | {industry}</div>
        </div>
        """, unsafe_allow_html=True)

        # Key stats row
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.markdown(f'<div class="metric-card"><h4>Price</h4><div class="value">{_fmt(price, "price")}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><h4>Market Cap</h4><div class="value">{_fmt(mkt_cap, "currency")}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><h4>PE Ratio</h4><div class="value">{_fmt(pe)}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-card"><h4>Forward PE</h4><div class="value">{_fmt(fwd_pe)}</div></div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="metric-card"><h4>EPS</h4><div class="value">{_fmt(eps_val, "price")}</div></div>', unsafe_allow_html=True)
        with c6:
            div_display = f"{div_yield*100:.2f}%" if div_yield else "N/A"
            st.markdown(f'<div class="metric-card"><h4>Div Yield</h4><div class="value">{div_display}</div></div>', unsafe_allow_html=True)

        c7, c8 = st.columns(2)
        with c7:
            st.markdown(f'<div class="metric-card"><h4>52W High</h4><div class="value">{_fmt(high52, "price")}</div></div>', unsafe_allow_html=True)
        with c8:
            st.markdown(f'<div class="metric-card"><h4>52W Low</h4><div class="value">{_fmt(low52, "price")}</div></div>', unsafe_allow_html=True)

        if description:
            with st.expander("Company Description"):
                st.write(description)

        st.divider()

        # --- Run all 4 analyses ---
        booth = _cached_booth(ticker)
        fs = _cached_fs(ticker)
        om = _cached_om(ticker)
        cs = _cached_cs(ticker)

        # ====== CORPORATE FINANCE (CF) ======
        st.markdown(f'## Corporate Finance (CF)')

        _render_cf(booth)

        # ====== FINANCIAL STRATEGY (FS) ======
        st.markdown(f'## Financial Strategy (FS)')

        _render_fs(fs)

        # --- AI Investment Thesis (CF + FS) ---
        st.markdown("### AI Investment Thesis")
        with st.spinner("Generating investment thesis..."):
            thesis = _get_ai_narrative(
                "You are an equity research analyst trained at Chicago Booth. "
                "Write a concise investment thesis (3-4 paragraphs) covering valuation, "
                "financial health, capital structure, and risk factors. Use bullet points for key metrics.",
                {"corporate_finance": booth, "financial_strategy": fs},
            )
        if thesis:
            st.markdown(f'<div class="ai-narrative">{_md(thesis)}</div>', unsafe_allow_html=True)

        st.divider()

        # ====== OPERATIONS MANAGEMENT (OM) ======
        st.markdown(f'## Operations Management (OM)')

        _render_om(om)

        st.markdown("### AI Operations Narrative")
        with st.spinner("Generating operations narrative..."):
            om_narrative = _get_ai_narrative(
                "You are an operations management consultant trained at Chicago Booth. "
                "Analyze the supply chain efficiency, operational throughput, process quality, "
                "and demand variability. Provide actionable insights in 2-3 paragraphs.",
                om,
            )
        if om_narrative:
            st.markdown(f'<div class="ai-narrative">{_md(om_narrative)}</div>', unsafe_allow_html=True)

        st.divider()

        # ====== COMPETITIVE STRATEGY (CS) ======
        st.markdown(f'## Competitive Strategy (CS)')

        _render_cs(cs)

        st.markdown("### AI Strategy Narrative")
        with st.spinner("Generating strategy narrative..."):
            cs_narrative = _get_ai_narrative(
                "You are a competitive strategy analyst trained at Chicago Booth. "
                "Assess the company's competitive moat, disruption risk, and market position. "
                "Reference Porter's Five Forces and Henderson & Clark where relevant. 2-3 paragraphs.",
                cs,
            )
        if cs_narrative:
            st.markdown(f'<div class="ai-narrative">{_md(cs_narrative)}</div>', unsafe_allow_html=True)

        # --- PDF Download ---
        st.divider()
        st.markdown("### Download Report")
        try:
            pdf_bytes = generate_pdf(
                ticker=ticker,
                info=info,
                booth=booth,
                fs=fs,
                om=om,
                cs=cs,
                thesis=thesis if thesis else "",
                om_narrative=om_narrative if om_narrative else "",
                cs_narrative=cs_narrative if cs_narrative else "",
            )
            st.download_button(
                "Download PDF Report",
                data=pdf_bytes,
                file_name=f"{ticker}_CB_Analysis.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.warning(f"PDF generation unavailable: {e}")


# ---------------------------------------------------------------------------
# Render helpers for each framework
# ---------------------------------------------------------------------------

def _render_card(title: str, rows: list):
    """Render a booth-card with table rows. rows = [(label, value), ...]."""
    table_rows = "".join(f"<tr><td>{label}</td><td>{val}</td></tr>" for label, val in rows if val is not None)
    if not table_rows:
        return
    html = f'<div class="booth-card"><h3>{title}</h3><table>{table_rows}</table></div>'
    st.markdown(html, unsafe_allow_html=True)


def _tag(val, good_threshold, bad_threshold, higher_is_better=True, fmt_fn=None):
    """Return colored HTML tag."""
    if val is None:
        return "N/A"
    display = fmt_fn(val) if fmt_fn else f"{val}"
    if higher_is_better:
        if val >= good_threshold:
            return f'<span class="tag-good">{display}</span>'
        if val <= bad_threshold:
            return f'<span class="tag-bad">{display}</span>'
    else:
        if val <= good_threshold:
            return f'<span class="tag-good">{display}</span>'
        if val >= bad_threshold:
            return f'<span class="tag-bad">{display}</span>'
    return f'<span class="tag-warn">{display}</span>'


def _render_cf(booth: dict):
    # CAPM
    d = booth.get("capm_alpha", {})
    if d and "error" not in d:
        _render_card("CAPM & Jensen's Alpha (Lecture 2B)", [
            ("Beta", f"{d.get('beta', 'N/A')}"),
            ("Risk-Free Rate", f"{d.get('risk_free_rate', 0)*100:.2f}%"),
            ("Expected Return (CAPM)", f"{d.get('expected_return', 0)*100:.2f}%"),
            ("Actual Annualized Return", f"{d.get('actual_annualized_return', 0)*100:.2f}%"),
            ("Jensen's Alpha", _tag(d.get('jensens_alpha', 0)*100, 2, -2, True, lambda v: f"{v:.2f}%")),
            ("R-squared", f"{d.get('r_squared', 0):.4f}"),
        ])

    # Multiples
    d = booth.get("valuation_multiples", {})
    if d:
        _render_card("Valuation Multiples (Lecture 5B)", [
            ("Sector", d.get("sector", "N/A")),
            ("PE Ratio", f"{d.get('pe_ratio', 'N/A')} (Median: {d.get('pe_sector_median', 'N/A')}) — {d.get('pe_vs_sector', 'N/A')}"),
            ("EV/EBITDA", f"{d.get('ev_ebitda', 'N/A')} (Median: {d.get('ev_ebitda_sector_median', 'N/A')}) — {d.get('ev_ebitda_vs_sector', 'N/A')}"),
            ("P/B Ratio", f"{d.get('pb_ratio', 'N/A')} (Median: {d.get('pb_sector_median', 'N/A')}) — {d.get('pb_vs_sector', 'N/A')}"),
            ("P/S Ratio", f"{d.get('ps_ratio', 'N/A')} (Median: {d.get('ps_sector_median', 'N/A')}) — {d.get('ps_vs_sector', 'N/A')}"),
        ])

    # WACC
    d = booth.get("wacc", {})
    if d and "error" not in d:
        _render_card("WACC (Lecture 4B)", [
            ("WACC", f"{d.get('wacc', 0)*100:.2f}%"),
            ("Cost of Equity", f"{d.get('cost_of_equity', 0)*100:.2f}%"),
            ("Cost of Debt", f"{d.get('cost_of_debt', 0)*100:.2f}%"),
            ("Equity Weight", f"{d.get('equity_weight', 0)*100:.1f}%"),
            ("Debt Weight", f"{d.get('debt_weight', 0)*100:.1f}%"),
            ("Beta", f"{d.get('beta', 'N/A')}"),
        ])

    # FCF
    d = booth.get("free_cash_flow", {})
    if d:
        _render_card("Free Cash Flow (Lectures 4A/4B)", [
            ("Free Cash Flow", _fmt(d.get("free_cash_flow"), "currency")),
            ("Operating Cash Flow", _fmt(d.get("operating_cash_flow"), "currency")),
            ("FCF Yield", _tag(d.get("fcf_yield_pct"), 5, 0, True, lambda v: f"{v:.2f}%") if d.get("fcf_yield_pct") else "N/A"),
            ("FCF Margin", f"{d.get('fcf_margin_pct', 'N/A')}%" if d.get("fcf_margin_pct") else "N/A"),
        ])

    # DCF
    d = booth.get("dcf_model", {})
    if d and "error" not in d:
        _render_card("DCF 3-Stage Model (Lecture 5B)", [
            ("Intrinsic Value / Share", _fmt(d.get("intrinsic_value_per_share"), "price")),
            ("Current Price", _fmt(d.get("current_price"), "price")),
            ("Upside / Downside", _tag(d.get("upside_pct"), 10, -10, True, lambda v: f"{v:+.1f}%") if d.get("upside_pct") is not None else "N/A"),
            ("WACC Used", f"{d.get('wacc', 0)*100:.2f}%"),
            ("Near-term Growth (Yr 1-5)", f"{d.get('near_term_growth', 0)*100:.1f}%"),
            ("Fade Growth (Yr 6-10)", f"{d.get('fade_growth', 0)*100:.1f}%"),
            ("Terminal Growth", f"{d.get('terminal_growth', 0)*100:.1f}%"),
        ])
        # Sensitivity table
        sens = d.get("sensitivity", {})
        if sens:
            with st.expander("DCF Sensitivity Table"):
                rows_data = []
                for k, v in sens.items():
                    parts = k.split(",")
                    wacc_str = parts[0].replace("WACC=", "")
                    g_str = parts[1].replace("g=", "") if len(parts) > 1 else ""
                    rows_data.append({"WACC": wacc_str, "Terminal g": g_str, "Value/Share": f"${v:,.2f}"})
                st.table(pd.DataFrame(rows_data))


def _render_fs(fs: dict):
    # Capital Structure
    d = fs.get("capital_structure", {})
    if d:
        _render_card("Capital Structure (D1)", [
            ("Total Debt", _fmt(d.get("total_debt"), "currency")),
            ("Total Cash", _fmt(d.get("total_cash"), "currency")),
            ("Net Debt", _fmt(d.get("net_debt"), "currency")),
            ("Net Debt / Capital", f"{d.get('net_debt_to_capital', 0)*100:.1f}%" if d.get("net_debt_to_capital") else "N/A"),
            ("Net Debt / EBITDA", f"{d.get('net_debt_to_ebitda', 'N/A')}x"),
            ("FCF / Debt", f"{d.get('fcf_to_debt', 0)*100:.1f}%" if d.get("fcf_to_debt") else "N/A"),
        ])

    # Credit Rating
    d = fs.get("credit_rating", {})
    if d:
        _render_card("Implied S&P Credit Rating (D1)", [
            ("Implied Rating", f"<strong>{d.get('implied_rating', 'N/A')}</strong>"),
            ("Composite Score", f"{d.get('composite_score', 'N/A')} / 8"),
            ("Credit Spread", f"{d.get('credit_spread_bps', 'N/A')} bps"),
            ("EBIT / Interest", f"{d.get('ebit_to_interest', 'N/A')}x"),
            ("EBITDA / Interest", f"{d.get('ebitda_to_interest', 'N/A')}x"),
        ])

    # Static Trade-Off
    d = fs.get("static_tradeoff", {})
    if d:
        _render_card("Static Trade-Off (D2/D3/D4)", [
            ("PV Tax Shield", _fmt(d.get("pv_tax_shield"), "currency")),
            ("PV Discipline Benefit", _fmt(d.get("pv_discipline_benefit"), "currency")),
            ("PV Distress Cost", _fmt(d.get("pv_distress_cost"), "currency")),
            ("Net Benefit of Debt", _fmt(d.get("net_benefit_of_debt"), "currency")),
            ("Assessment", f"<strong>{d.get('assessment', 'N/A')}</strong>"),
        ])

    # Payout Policy
    d = fs.get("payout_policy", {})
    if d:
        _render_card("Payout & Cash Policy (D4)", [
            ("Excess Cash", _fmt(d.get("excess_cash"), "currency")),
            ("Tax Drag (Annual)", _fmt(d.get("tax_drag_annual"), "currency")),
            ("Dividend Yield", f"{d.get('dividend_yield', 0):.2f}%"),
            ("Payout Ratio", f"{d.get('payout_ratio', 0):.1f}%"),
            ("Cash as % of Mkt Cap", f"{d.get('cash_as_pct_of_mktcap', 'N/A')}%"),
            ("Assessment", f"<strong>{d.get('assessment', 'N/A')}</strong>"),
        ])

    # Altman Z
    d = fs.get("altman_z", {})
    if d and "error" not in d:
        z = d.get("z_score", 0)
        zone = d.get("zone", "")
        z_tag = _tag(z, 2.99, 1.81, True, lambda v: f"{v:.3f}")
        _render_card("Altman Z-Score", [
            ("Z-Score", f"{z_tag} — {zone}"),
            ("WC/TA (×1.2)", f"{d.get('wc_ta', 0):.4f}"),
            ("RE/TA (×1.4)", f"{d.get('re_ta', 0):.4f}"),
            ("EBIT/TA (×3.3)", f"{d.get('ebit_ta', 0):.4f}"),
            ("MktCap/Liabilities (×0.6)", f"{d.get('mktcap_liab', 0):.4f}"),
            ("Revenue/TA (×1.0)", f"{d.get('rev_ta', 0):.4f}"),
        ])

    # Pecking Order
    d = fs.get("pecking_order", {})
    if d:
        _render_card("Pecking Order (Myers-Majluf 1984)", [
            ("Stage", f"<strong>{d.get('pecking_order_stage', 'N/A')}</strong>"),
            ("FCF", _fmt(d.get("free_cash_flow"), "currency")),
            ("CapEx", _fmt(d.get("capex"), "currency")),
            ("Internal Funding Sufficient", "Yes" if d.get("internal_funding_sufficient") else "No"),
            ("Debt Level", d.get("debt_level", "N/A")),
            ("RE / Equity", f"{d.get('re_to_equity', 0):.4f}" if d.get("re_to_equity") else "N/A"),
        ])


def _render_om(om: dict):
    # Supply Chain
    d = om.get("supply_chain", {})
    if d:
        _render_card("Supply Chain Efficiency (S1/S6/S7)", [
            ("Cash Conversion Cycle", _tag(d.get("cash_conversion_cycle"), 30, 90, False, lambda v: f"{v:.1f} days") if d.get("cash_conversion_cycle") else "N/A"),
            ("Days Inventory (DIO)", f"{d.get('dio_days', 'N/A')} days"),
            ("Days Sales (DSO)", f"{d.get('dso_days', 'N/A')} days"),
            ("Days Payables (DPO)", f"{d.get('dpo_days', 'N/A')} days"),
            ("Inventory Turnover", f"{d.get('inventory_turnover', 'N/A')}x"),
            ("Assessment", f"<strong>{d.get('assessment', 'N/A')}</strong>"),
        ])

    # Throughput
    d = om.get("operational_throughput", {})
    if d:
        _render_card("Operational Throughput (S2/S4)", [
            ("Fixed Asset Turnover", f"{d.get('fixed_asset_turnover', 'N/A')}x"),
            ("Revenue Growth", f"{d.get('revenue_growth', 0)*100:.1f}%" if d.get("revenue_growth") else "N/A"),
            ("CapEx (Current)", _fmt(d.get("capex_current"), "currency")),
            ("CapEx Growth", f"{d.get('capex_growth', 0)*100:.1f}%" if d.get("capex_growth") is not None else "N/A"),
            ("Assessment", f"<strong>{d.get('assessment', 'N/A')}</strong>"),
        ])

    # Process Quality
    d = om.get("process_quality", {})
    if d:
        _render_card("Process Quality & Lean (S5 TQM/TPS)", [
            ("Gross Margin", f"{d.get('gross_margin', 0):.2f}%"),
            ("Operating Margin", f"{d.get('operating_margin', 0):.2f}%"),
            ("Overhead Gap (GM − OM)", f"{d.get('overhead_gap_pct', 0):.2f}%"),
            ("ROA", f"{d.get('roa', 'N/A')}%"),
            ("Gross Margin Trend", d.get("gross_margin_trend", "N/A")),
            ("WC / Revenue", f"{d.get('wc_to_revenue', 'N/A')}%"),
            ("Assessment", f"<strong>{d.get('assessment', 'N/A')}</strong>"),
        ])

    # Demand Variability
    d = om.get("demand_variability", {})
    if d:
        _render_card("Demand Variability & Bullwhip (S7/S8)", [
            ("Revenue CV", f"{d.get('revenue_cv', 'N/A')}"),
            ("Inventory Growth", f"{d.get('inventory_growth', 0)*100:.1f}%" if d.get("inventory_growth") is not None else "N/A"),
            ("Revenue Growth", f"{d.get('revenue_growth', 0)*100:.1f}%" if d.get("revenue_growth") is not None else "N/A"),
            ("Bullwhip Ratio", _tag(d.get("bullwhip_ratio"), 1.0, 1.5, False, lambda v: f"{v:.3f}") if d.get("bullwhip_ratio") else "N/A"),
            ("Assessment", f"<strong>{d.get('assessment', 'N/A')}</strong>"),
        ])


def _render_cs(cs: dict):
    # Moat
    d = cs.get("competitive_moat", {})
    if d:
        scores = d.get("scores", {})
        score_rows = [(k.replace("_", " ").title(), f"{v}/10") for k, v in scores.items()]
        _render_card("Competitive Moat (Session 2/6)", [
            ("Moat Width", f"<strong>{d.get('moat_width', 'N/A')}</strong> (Avg: {d.get('average_score', 0)}/10)"),
            *score_rows,
            ("Gross Margin", f"{d.get('gross_margin', 0):.1f}%"),
            ("R&D Intensity", f"{d.get('rd_intensity_pct', 0):.1f}%"),
        ])

    # Disruption Risk
    d = cs.get("disruption_risk", {})
    if d:
        risk = d.get("disruption_risk_score", 0)
        _render_card("Disruption Risk (Session 7)", [
            ("Risk Score", _tag(risk, 3, 7, False, lambda v: f"{v}/10")),
            ("Risk Level", f"<strong>{d.get('risk_level', 'N/A')}</strong>"),
            ("Innovation Type", d.get("innovation_type", "N/A")),
            ("R&D Intensity", f"{d.get('rd_intensity_pct', 0):.1f}%"),
            ("Revenue Growth", f"{d.get('revenue_growth', 'N/A')}%"),
            ("Gross Margin Trend", d.get("gross_margin_trend", "N/A")),
        ])

    # Market Position
    d = cs.get("market_position", {})
    if d:
        _render_card("Market Position (Session 2/3)", [
            ("Position", f"<strong>{d.get('market_position', 'N/A')}</strong>"),
            ("Detail", d.get("position_detail", "")),
            ("Cap Tier", d.get("cap_tier", "N/A")),
            ("Risk Profile", d.get("risk_profile", "N/A")),
            ("Operating Margin", f"{d.get('operating_margin_pct', 0):.1f}%"),
            ("ROE", f"{d.get('roe_pct', 'N/A')}%"),
            ("Beta", f"{d.get('beta', 'N/A')}"),
        ])


# ===================================================================
# SIDEBAR NAV + MAIN
# ===================================================================

with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:1rem 0;">
        <div style="font-size:1.3rem; font-weight:700; color:{MAROON};">Elitez Asia's Analytics</div>
        <div style="font-size:0.8rem; color:{GREY};">Powered by CB Research Framework</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("Navigation", ["Dashboard", "CB Analysis"], label_visibility="collapsed")

if page == "Dashboard":
    page_dashboard()
else:
    page_cb_analysis()
