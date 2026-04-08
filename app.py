"""
Adept Academy — Market Tracker
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
    page_title="Market Tracker — Adept Academy",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

MAROON = "#4A2811"  # Dark Brown (was "#9B1B30" maroon)
GREY = "#53565A"

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(f"""
<style>
    .main-header {{
        font-size: 1.6rem;
        font-weight: 700;
        color: {MAROON};
        margin-bottom: 0.1rem;
        letter-spacing: 1px;
    }}
    .sub-header {{
        font-size: 0.8rem;
        color: {GREY};
        margin-bottom: 1.2rem;
        letter-spacing: 2px;
        text-transform: uppercase;
    }}
    .metric-card {{
        background: #ffffff;
        border-left: 3px solid {MAROON};
        border-radius: 3px;
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
        border: 1px solid #d1d5db;
        border-radius: 3px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
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
        padding: 0.25rem 0.5rem;
        border-bottom: 1px solid #f1f5f9;
        font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
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
        background: #fdf8f0;
        border-left: 3px solid {MAROON};
        border-top: 2px solid {MAROON};
        border-radius: 0px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        line-height: 1.7;
    }}
    .company-header {{
        background: {MAROON};
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 4px;
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

    /* --- CB Analysis PDF-style CSS --- */
    .section-bar {{
        background: {MAROON};
        color: white;
        padding: 0.5rem 1rem;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 3px;
        text-transform: uppercase;
        border-radius: 2px;
        margin: 1.5rem 0 1rem 0;
    }}
    .card-title {{
        text-transform: uppercase;
        letter-spacing: 2.5px;
        font-size: 0.7rem;
        color: {MAROON};
        font-weight: 600;
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #e2e8f0;
    }}
    .signal-pos {{
        border-left: 3px solid #16a34a;
        padding: 0.25rem 0.6rem;
        margin-top: 0.4rem;
        border-radius: 0;
        background: none;
    }}
    .signal-neg {{
        border-left: 3px solid #dc2626;
        padding: 0.25rem 0.6rem;
        margin-top: 0.4rem;
        border-radius: 0;
        background: none;
    }}
    .signal-warn {{
        border-left: 3px solid #d97706;
        padding: 0.25rem 0.6rem;
        margin-top: 0.4rem;
        border-radius: 0;
        background: none;
    }}
    .card-note {{
        font-size: 0.65rem;
        color: #6b7280;
        line-height: 1.4;
        margin-top: 0.5rem;
    }}
    .pill {{
        display: inline-block;
        background: rgba(255,255,255,0.2);
        padding: 0.15rem 0.65rem;
        border-radius: 999px;
        font-size: 0.75rem;
        margin-right: 0.4rem;
        border: 1px solid rgba(255,255,255,0.3);
    }}
    .exec-box {{
        background: #ffffff;
        border: 1px solid #D4A017;
        border-radius: 2px;
        padding: 1rem 1.2rem;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        height: 100%;
    }}
    .exec-box .exec-label {{
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #53565A;
        margin-bottom: 0.3rem;
    }}
    .exec-box .exec-value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
    }}
    .exec-box .exec-sub {{
        font-size: 0.75rem;
        color: #53565A;
        margin-top: 0.15rem;
    }}
    .ai-header {{
        background: {MAROON};
        color: white;
        padding: 0.45rem 1rem;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 2px;
        text-transform: uppercase;
        border-radius: 4px 4px 0 0;
        margin-top: 1.5rem;
        margin-bottom: 0;
    }}
    .ai-body {{
        background: #fdf8f0;
        border: 1px solid #e2e8f0;
        border-top: none;
        border-radius: 0 0 2px 2px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        line-height: 1.7;
    }}
    .data-table {{
        width: 100%;
        border-collapse: collapse;
    }}
    .data-table td {{
        padding: 0.25rem 0.5rem;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.85rem;
    }}
    .data-table td:first-child {{
        color: #53565A;
        font-weight: 500;
    }}
    .data-table td:last-child {{
        text-align: right;
        font-weight: 600;
        color: #1e293b;
        font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    }}
    .mono-val {{
        font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
    }}
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
    st.markdown('<div class="sub-header">Adept Academy — Global Market Overview</div>', unsafe_allow_html=True)

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
# PAGE 2: CB ANALYSIS — PDF-style render helpers
# ===================================================================

def _render_card(title, rows, signal=None, note=None):
    """Render a styled analysis card.

    Args:
        title: card heading (small-caps maroon)
        rows: list of (label, value) tuples
        signal: optional tuple (type, text) where type is
                'pos'/'positive' | 'neg'/'negative' | 'warn'/'amber'
        note: optional annotation string
    """
    table_rows = "".join(
        f"<tr><td>{label}</td><td>{val}</td></tr>"
        for label, val in rows if val is not None
    )
    if not table_rows:
        return

    signal_html = ""
    if signal:
        stype, stext = signal
        # Normalise type names
        if stype in ("pos", "positive"):
            signal_html = f'<div style="border-left:3px solid #16a34a; padding:0.25rem 0.6rem; margin-top:0.4rem;"><span style="color:#16a34a; font-size:0.75rem; font-weight:600;">\u25b2 {stext}</span></div>'
        elif stype in ("neg", "negative"):
            signal_html = f'<div style="border-left:3px solid #dc2626; padding:0.25rem 0.6rem; margin-top:0.4rem;"><span style="color:#dc2626; font-size:0.75rem; font-weight:600;">\u25bc {stext}</span></div>'
        elif stype in ("warn", "amber"):
            signal_html = f'<div style="border-left:3px solid #d97706; padding:0.25rem 0.6rem; margin-top:0.4rem;"><span style="color:#d97706; font-size:0.75rem; font-weight:600;">\u25b3 {stext}</span></div>'

    note_html = ""
    if note:
        note_html = f'<div style="font-size:0.65rem; color:#6b7280; line-height:1.4; margin-top:0.4rem;">{note}</div>'

    html = (
        f'<div class="booth-card">'
        f'<div class="card-title">{title}</div>'
        f'<table class="data-table">{table_rows}</table>'
        f'{signal_html}{note_html}'
        f'</div>'
    )
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


def _section_bar(text):
    """Full-width maroon section header bar."""
    st.markdown(f'<div class="section-bar">{text}</div>', unsafe_allow_html=True)


def _ai_block(header_text, body_html):
    """Render AI narrative with maroon header + body card."""
    st.markdown(
        f'<div class="ai-header">{header_text}</div>'
        f'<div class="ai-body">{body_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Executive Summary helpers
# ---------------------------------------------------------------------------

def _exec_metric_box(label, value_html, sub_html=""):
    """Return HTML for a single executive summary metric box."""
    sub = f'<div class="exec-sub">{sub_html}</div>' if sub_html else ""
    return (
        f'<div class="exec-box">'
        f'<div class="exec-label">{label}</div>'
        f'<div class="exec-value">{value_html}</div>'
        f'{sub}'
        f'</div>'
    )


def _render_executive_summary(booth, fs):
    """Render the 2x3 executive summary grid."""
    # --- Gather data ---
    dcf = booth.get("dcf_model", {})
    cr = fs.get("credit_rating", {})
    az = fs.get("altman_z", {})
    fcf_d = booth.get("free_cash_flow", {})
    capm = booth.get("capm_alpha", {})
    po = fs.get("pecking_order", {})

    # DCF upside
    upside = dcf.get("upside_pct")
    iv = dcf.get("intrinsic_value_per_share")
    if upside is not None:
        color = "#16a34a" if upside >= 0 else "#dc2626"
        dcf_val = f'<span style="color:{color}">{upside:+.1f}%</span>'
        dcf_sub = f"Intrinsic value {_fmt(iv, 'price')}" if iv else ""
    else:
        dcf_val = "N/A"
        dcf_sub = ""

    # Implied rating
    rating = cr.get("implied_rating", "N/A")
    score = cr.get("composite_score")
    if score is not None:
        grade_label = "Investment Grade" if score >= 4 else "High Yield"
        grade_color = "#16a34a" if score >= 4 else "#d97706"
        rating_sub = f'<span style="color:{grade_color}">{grade_label}</span>'
    else:
        rating_sub = ""

    # Altman Z
    z = az.get("z_score")
    zone = az.get("zone", "")
    if z is not None:
        if z >= 2.99:
            z_color = "#16a34a"
        elif z >= 1.81:
            z_color = "#53565A"
        else:
            z_color = "#dc2626"
        z_val = f'<span style="color:{z_color}">{z:.2f}</span>'
        z_sub = zone
    else:
        z_val = "N/A"
        z_sub = ""

    # FCF Yield
    fcf_yield = fcf_d.get("fcf_yield_pct")
    if fcf_yield is not None:
        fy_color = "#16a34a" if fcf_yield > 0 else "#dc2626"
        fcf_val = f'<span style="color:{fy_color}">{fcf_yield:.2f}%</span>'
    else:
        fcf_val = "N/A"

    # Jensen's Alpha
    alpha = capm.get("jensens_alpha")
    if alpha is not None and "error" not in capm:
        a_pct = alpha * 100
        a_color = "#16a34a" if a_pct > 0 else "#dc2626"
        alpha_val = f'<span style="color:{a_color}">{a_pct:+.2f}%</span>'
    else:
        alpha_val = "N/A"

    # Pecking Order
    po_stage = po.get("pecking_order_stage", "N/A") if po else "N/A"
    po_score_val = ""
    if po:
        # Build a rough net score from boolean checks
        checks = 0
        total = 5
        if po.get("internal_funding_sufficient"):
            checks += 1
        if po.get("payout_ratio") is not None and po.get("payout_ratio", 100) < 60:
            checks += 1
        if po.get("re_to_equity") is not None and po.get("re_to_equity", 0) > 0.3:
            checks += 1
        if po.get("debt_level") in ("low", "Low", "moderate", "Moderate"):
            checks += 1
        if po.get("debt_to_mktcap") is not None and po.get("debt_to_mktcap", 1) < 0.5:
            checks += 1
        po_score_val = f"{checks}/{total}"

    # --- Render 2x3 grid ---
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.markdown(_exec_metric_box("DCF UPSIDE / DOWNSIDE", dcf_val, dcf_sub), unsafe_allow_html=True)
    with r1c2:
        st.markdown(_exec_metric_box("IMPLIED S&P RATING", f"<strong>{rating}</strong>", rating_sub), unsafe_allow_html=True)
    with r1c3:
        st.markdown(_exec_metric_box("ALTMAN Z-SCORE", z_val, z_sub), unsafe_allow_html=True)

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        st.markdown(_exec_metric_box("FCF YIELD", fcf_val), unsafe_allow_html=True)
    with r2c2:
        st.markdown(_exec_metric_box("JENSEN'S ALPHA (\u03b1)", alpha_val), unsafe_allow_html=True)
    with r2c3:
        st.markdown(_exec_metric_box("PECKING ORDER", po_stage, f"Net score: {po_score_val}" if po_score_val else ""), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# CF column render
# ---------------------------------------------------------------------------

def _render_cf_column(booth):
    """Render all Corporate Finance cards inside a column."""

    # 1. CAPM & Jensen's Alpha
    d = booth.get("capm_alpha", {})
    if d and "error" not in d:
        alpha = d.get("jensens_alpha")
        alpha_pct = alpha * 100 if alpha is not None else None
        if alpha_pct is not None:
            sig = ("pos", f"Jensen's \u03b1 = {alpha_pct:+.2f}% — genuine operational outperformance") if alpha_pct > 0 else ("neg", f"Jensen's \u03b1 = {alpha_pct:+.2f}% — underperformance vs CAPM benchmark")
        else:
            sig = None
        _render_card(
            "CAPM & JENSEN'S ALPHA \u00b7 LECTURE 2B",
            [
                ("Beta (\u03b2)", f"{d.get('beta', 'N/A')}"),
                ("Risk-Free Rate (r\u1da0)", f"{d.get('risk_free_rate', 0)*100:.2f}%"),
                ("Market Risk Premium", f"{d.get('market_risk_premium', 0.07)*100:.1f}%"),
                ("CAPM Expected Return", f"{d.get('expected_return', 0)*100:.2f}%"),
                ("Actual Return (ann.)", f"{d.get('actual_annualized_return', 0)*100:.2f}%"),
                ("Jensen's Alpha (\u03b1)", _tag(alpha_pct, 2, -2, True, lambda v: f"{v:+.2f}%") if alpha_pct is not None else "N/A"),
                ("R\u00b2", f"{d.get('r_squared', 0):.4f}"),
            ],
            signal=sig,
            note="r\u1da0 + \u03b2(r\u2098 \u2212 r\u1da0) = CAPM expected return; \u03b1 = actual \u2212 expected.",
        )

    # 2. Valuation Multiples — paired format (value + vs Sector)
    d = booth.get("valuation_multiples", {})
    if d:
        pe = d.get("pe_ratio")
        pe_med = d.get("pe_sector_median")
        ev = d.get("ev_ebitda")
        ev_med = d.get("ev_ebitda_sector_median")
        pb = d.get("pb_ratio")
        pb_med = d.get("pb_sector_median")
        ps = d.get("ps_ratio")
        ps_med = d.get("ps_sector_median")

        def _pct_diff(val, med):
            """Return (pct, label) — negative = discount, positive = premium."""
            if val is None or med is None or med == 0:
                return None, ""
            pct = (val - med) / med * 100
            word = "discount" if pct < 0 else "premium"
            return pct, word

        mult_rows = []
        disc_count = 0
        prem_count = 0
        for label, val, med, med_label in [
            ("P/E (TTM)", pe, pe_med, "P/E"),
            ("EV/EBITDA", ev, ev_med, "EV/EBITDA"),
            ("P/B", pb, pb_med, "P/B"),
            ("P/S", ps, ps_med, "P/S"),
        ]:
            if val is not None:
                mult_rows.append((label, f"{val:.2f}x"))
                pct, word = _pct_diff(val, med)
                if pct is not None:
                    mult_rows.append(("vs Sector", f"{abs(pct):.0f}% {word} vs sector median {med_label} of {med:.1f}x"))
                    if word == "discount":
                        disc_count += 1
                    else:
                        prem_count += 1
            else:
                mult_rows.append((label, "N/A"))

        if disc_count > prem_count:
            sig = ("pos", "cheap vs peers")
        elif prem_count > disc_count:
            sig = ("neg", "expensive vs peers")
        else:
            sig = ("amber", "Mixed valuation signals vs sector medians")

        _render_card(
            "VALUATION MULTIPLES \u00b7 LECTURE 5B",
            mult_rows,
            signal=sig,
            note=f"Sector: {d.get('sector', 'N/A')}. Multiples compared to sector medians.",
        )

    # 3. WACC
    d = booth.get("wacc", {})
    if d and "error" not in d:
        _render_card(
            "WACC \u00b7 LECTURE 4B",
            [
                ("Beta (\u03b2)", f"{d.get('beta', 'N/A')}"),
                ("Cost of Equity (r\u1d31)", f"{d.get('cost_of_equity', 0)*100:.2f}%"),
                ("Tax Rate", f"{d.get('tax_rate', 0)*100:.1f}%"),
                ("E / (E+D)", f"{d.get('equity_weight', 0)*100:.1f}%"),
                ("D / (E+D)", f"{d.get('debt_weight', 0)*100:.1f}%"),
                ("WACC", f"<strong>{d.get('wacc', 0)*100:.2f}%</strong>"),
            ],
            note="WACC = (E/V)\u00b7r\u1d31 + (D/V)\u00b7r\u1d48\u00b7(1\u2212t). Used as discount rate in DCF.",
        )

    # 4. Free Cash Flow
    d = booth.get("free_cash_flow", {})
    if d:
        fcf_y = d.get("fcf_yield_pct")
        if fcf_y is not None and fcf_y > 4:
            sig = ("pos", "strong cash generator")
        elif fcf_y is not None and fcf_y > 0:
            sig = ("amber", f"FCF yield {fcf_y:.2f}%")
        elif fcf_y is not None:
            sig = ("neg", f"FCF yield {fcf_y:.2f}% \u2014 weak cash conversion")
        else:
            sig = None

        fcf_val = d.get("free_cash_flow")
        ocf_val = d.get("operating_cash_flow")
        rev = d.get("revenue")
        mktcap = d.get("market_cap")
        fcf_margin = d.get("fcf_margin_pct")
        pfcf = None
        if fcf_val and mktcap and fcf_val > 0:
            pfcf = mktcap / fcf_val

        _render_card(
            "FREE CASH FLOW \u00b7 LECTURES 4A/4B",
            [
                ("Operating Cash Flow", _fmt(ocf_val, "currency")),
                ("Free Cash Flow", _fmt(fcf_val, "currency")),
                ("FCF Yield", f"{fcf_y:.2f}%" if fcf_y is not None else "N/A"),
                ("FCF Margin", f"{fcf_margin:.2f}%" if fcf_margin is not None else "N/A"),
                ("P/FCF", f"{pfcf:.1f}x" if pfcf else "N/A"),
            ],
            signal=sig,
            note="FCF = Operating CF \u2212 CapEx | FCF Yield > 4% = strong cash generator",
        )

    # 5. DCF
    d = booth.get("dcf_model", {})
    if d and "error" not in d:
        upside = d.get("upside_pct")
        iv = d.get("intrinsic_value_per_share")
        cp = d.get("current_price")
        terminal_g = d.get("terminal_growth", 0)
        if upside is not None:
            if upside > 0:
                sig = ("pos", "potentially undervalued")
            else:
                sig = ("neg", "potentially overvalued")
        else:
            sig = None

        # Margin of Safety = (intrinsic - current) / intrinsic * 100
        mos_pct = None
        if iv is not None and cp is not None and iv != 0:
            try:
                mos_pct = (float(iv) - float(cp)) / float(iv) * 100
            except (ValueError, TypeError):
                pass

        _render_card(
            "DCF \u00b7 3-STAGE MODEL \u00b7 LECTURE 5B",
            [
                ("WACC", f"{d.get('wacc', 0)*100:.2f}%"),
                ("Stage 1 Growth (Yr 1-5)", f"{d.get('near_term_growth', 0)*100:.1f}%"),
                ("Terminal Growth", f"{terminal_g*100:.1f}%"),
                ("Trailing FCF", _fmt(d.get("base_fcf"), "currency")),
                ("Intrinsic Value / Share", f"<strong>{_fmt(iv, 'price')}</strong>"),
                ("Current Price", _fmt(cp, "price")),
                ("Upside / Downside", _tag(upside, 10, -10, True, lambda v: f"{v:+.1f}%") if upside is not None else "N/A"),
                ("Margin of Safety", f"{mos_pct:+.1f}%" if mos_pct is not None else "N/A"),
                ("Market-Implied Growth", f"{terminal_g*100:.1f}%"),
            ],
            signal=sig,
            note="3-stage DCF: high growth \u2192 fade \u2192 terminal perpetuity. Sensitivity analysis below.",
        )
        # Sensitivity table (always visible)
        sens = d.get("sensitivity", {})
        if sens:
            st.markdown(f'<div style="font-size:0.7rem; color:{GREY}; text-transform:uppercase; letter-spacing:2px; margin:0.3rem 0;">Sensitivity — Intrinsic Value / Share</div>', unsafe_allow_html=True)
            rows_data = []
            for k, v in sens.items():
                parts = k.split(",")
                wacc_str = parts[0].replace("WACC=", "")
                g_str = parts[1].replace("g=", "") if len(parts) > 1 else ""
                rows_data.append({"WACC": wacc_str, "Terminal g": g_str, "Value/Share": f"${v:,.2f}"})
            st.table(pd.DataFrame(rows_data))


# ---------------------------------------------------------------------------
# FS column render
# ---------------------------------------------------------------------------

def _render_fs_column(fs, info=None):
    """Render all Financial Strategy cards inside a column."""
    info = info or {}

    # 1. Capital Structure Ratios
    d = fs.get("capital_structure", {})
    if d:
        nd_ebitda = d.get("net_debt_to_ebitda")
        nd_cap = d.get("net_debt_to_capital")
        nd = d.get("net_debt")
        mc = d.get("market_cap")
        nd_mkt = None
        if nd is not None and mc and mc > 0:
            nd_mkt = nd / mc

        # Signal based on net_debt_to_capital
        if nd_cap is not None:
            try:
                nd_cap_f = float(nd_cap)
                if nd_cap_f < 0.3:
                    sig = ("pos", "very low leverage")
                elif nd_cap_f > 0.6:
                    sig = ("neg", "High leverage \u2014 distress risk")
                else:
                    sig = ("amber", "Moderate leverage")
            except (ValueError, TypeError):
                sig = None
        elif nd_ebitda is not None:
            try:
                nd_ebitda_f = float(nd_ebitda)
                sig = ("pos", "very low leverage") if nd_ebitda_f < 2 else (("neg", "High leverage \u2014 distress risk") if nd_ebitda_f > 4 else ("amber", "Moderate leverage"))
            except (ValueError, TypeError):
                sig = None
        else:
            sig = None

        _render_card(
            "CAPITAL STRUCTURE RATIOS \u00b7 D1",
            [
                ("Total Debt", _fmt(d.get("total_debt"), "currency")),
                ("Cash & Liquid Assets", _fmt(d.get("total_cash"), "currency")),
                ("Net Debt", _fmt(nd, "currency")),
                ("Net Debt / Book Capital", f"{nd_cap*100:.1f}%" if nd_cap else "N/A"),
                ("Net Debt / Market Capital", f"{nd_mkt*100:.1f}%" if nd_mkt else "N/A"),
                ("Net Debt / EBITDA", f"{nd_ebitda}x" if nd_ebitda is not None else "N/A"),
                ("FCF / Total Debt", f"{d.get('fcf_to_debt', 0)*100:.1f}%" if d.get("fcf_to_debt") else "N/A"),
            ],
            signal=sig,
            note="Net Debt = Total Debt \u2212 Cash. Negative net debt = net cash position.",
        )

    # 2. Implied S&P Credit Rating
    d = fs.get("credit_rating", {})
    if d:
        rating = d.get("implied_rating", "N/A")
        score = d.get("composite_score")
        spread = d.get("credit_spread_bps")
        default_prob = d.get("default_probability")
        if score is not None:
            grade = "Investment Grade" if score >= 4 else "Speculative Grade"
            grade_color = "#16a34a" if score >= 4 else "#d97706"
        else:
            grade = ""
            grade_color = "#53565A"

        rating_html = (
            f'<div style="text-align:center;margin:0.5rem 0;">'
            f'<span style="font-size:2.2rem;font-weight:800;color:{MAROON}">{rating}</span>'
            f'<br><span style="display:inline-block;background:{grade_color};color:white;'
            f'padding:0.15rem 0.7rem;border-radius:999px;font-size:0.7rem;font-weight:600;'
            f'margin-top:0.3rem;">{grade}</span></div>'
        )

        _render_card(
            "IMPLIED S&P CREDIT RATING \u00b7 D1",
            [
                ("Rating", rating_html),
                ("Composite Score", f"{score}/8" if score is not None else "N/A"),
                ("Default Prob. (ann.)", f"{default_prob:.2f}%" if default_prob is not None else "N/A"),
                ("Credit Spread", f"{spread} bps" if spread is not None else "N/A"),
                ("EBIT / Interest", f"{d.get('ebit_to_interest', 'N/A')}x"),
                ("EBITDA / Interest", f"{d.get('ebitda_to_interest', 'N/A')}x"),
            ],
            note="Based on coverage ratios, leverage, and profitability metrics mapped to S&P rating scale.",
        )

    # 3. Static Trade-Off — scoring format
    d = fs.get("static_tradeoff", {})
    if d:
        pvts = d.get("pv_tax_shield")
        pvdb = d.get("pv_discipline_benefit")
        pvdc = d.get("pv_distress_cost")

        # Get market cap from info if available, else from capital_structure
        mkt = 0
        cs_d = fs.get("capital_structure", {})
        if cs_d:
            mkt = cs_d.get("market_cap", 0) or 0

        # Calculate scores
        ts_score = 2 if pvts and mkt and pvts > mkt * 0.05 else (1 if pvts and pvts > 0 else 0)
        disc_score = 2 if pvdb and pvdb > 0 else 0
        dist_score = -4 if pvdc and mkt and pvdc > mkt * 0.1 else (-2 if pvdc and mkt and pvdc > mkt * 0.03 else 0)
        net = ts_score + disc_score + dist_score

        if net > 0:
            sig = ("pos", "lean toward debt")
        elif net < 0:
            sig = ("neg", "lean toward equity \u2014 distress costs are real")
        else:
            sig = ("amber", "Balanced \u2014 debt benefits roughly offset distress costs")

        _render_card(
            "STATIC TRADE-OFF \u00b7 D2/D3/D4",
            [
                ("PV(Tax Shield)", f"+{ts_score} / 2"),
                ("PV(Discipline)", f"+{disc_score} / 2"),
                ("PV(Distress Cost)", f"{dist_score} / -4"),
                ("Net Score", f"<strong>{net:+d}</strong>"),
            ],
            signal=sig,
            note="V\u1d38 = V\u1d41 + PV(tax shield) + PV(discipline) \u2212 PV(distress). Modigliani-Miller with frictions.",
        )

    # 4. Payout & Cash Policy
    d = fs.get("payout_policy", {})
    if d:
        assessment = d.get("assessment", "")
        excess = d.get("excess_cash")
        total_cash = d.get("total_cash")
        revenue = d.get("revenue")
        mkt_cap_pp = d.get("market_cap")
        tax_drag = d.get("tax_drag_annual")
        div_yield = d.get("dividend_yield", 0)

        # Computed fields
        cash_rev_pct = None
        if total_cash and revenue and revenue > 0:
            cash_rev_pct = total_cash / revenue * 100
        cash_mkt_pct = None
        if total_cash and mkt_cap_pp and mkt_cap_pp > 0:
            cash_mkt_pct = total_cash / mkt_cap_pp * 100
        net_cash = False
        try:
            net_cash = True if excess and float(excess) > 0 else False
        except (ValueError, TypeError):
            pass
        tax_drag_mkt_pct = None
        if tax_drag and mkt_cap_pp and mkt_cap_pp > 0:
            try:
                tax_drag_mkt_pct = float(tax_drag) / float(mkt_cap_pp) * 100
            except (ValueError, TypeError):
                pass

        # Signal: amber "excess cash with minimal payout" when excess > 0 and dividend yield < 2%
        try:
            excess_f = float(excess) if excess is not None else 0
        except (ValueError, TypeError):
            excess_f = 0
        if excess_f > 0 and div_yield < 2:
            sig = ("amber", "excess cash with minimal payout")
        elif excess_f > 0:
            sig = ("pos", "Net cash position \u2014 financial flexibility")
        else:
            sig = ("amber", assessment) if assessment else None

        _render_card(
            "PAYOUT & CASH POLICY \u00b7 D4 (FANUC)",
            [
                ("Cash & Liquid Assets", _fmt(total_cash, "currency")),
                ("Cash / Revenue", f"{cash_rev_pct:.1f}%" if cash_rev_pct is not None else "N/A"),
                ("Cash / Mkt Cap", f"{cash_mkt_pct:.1f}%" if cash_mkt_pct is not None else "N/A"),
                ("Net Cash?", '<span class="tag-good">Yes</span>' if net_cash else '<span class="tag-bad">No</span>'),
                ("Estimated Excess Cash", _fmt(excess, "currency")),
                ("Annual Tax Drag", _fmt(tax_drag, "currency")),
                ("Tax Drag / Mkt Cap", f"{tax_drag_mkt_pct:.3f}%" if tax_drag_mkt_pct is not None else "N/A"),
                ("Dividend Yield", f"{div_yield:.2f}%"),
            ],
            signal=sig,
            note="D4 FANUC: Excess cash = Cash \u2212 Operating needs. Tax drag on excess cash = marginal corporate rate \u00d7 excess. Firms with excess cash and low payout destroy value via tax drag.",
        )

    # 5. Altman Z-Score
    d = fs.get("altman_z", {})
    if d and "error" not in d:
        z = d.get("z_score", 0)
        zone = d.get("zone", "")
        if z >= 2.99:
            z_color = "#16a34a"
            sig = ("pos", f"Z = {z:.2f} — Safe zone, low bankruptcy risk")
            badge_bg = "#16a34a"
        elif z >= 1.81:
            z_color = "#53565A"
            sig = ("warn", f"Z = {z:.2f} — Grey zone, moderate risk")
            badge_bg = "#d97706"
        else:
            z_color = "#dc2626"
            sig = ("neg", f"Z = {z:.2f} — Distress zone, high bankruptcy risk")
            badge_bg = "#dc2626"

        z_big = (
            f'<div style="text-align:center;margin:0.5rem 0;">'
            f'<span style="font-size:2.2rem;font-weight:800;color:{z_color}">{z:.2f}</span>'
            f'<br><span style="display:inline-block;background:{badge_bg};color:white;'
            f'padding:0.15rem 0.7rem;border-radius:999px;font-size:0.7rem;font-weight:600;'
            f'margin-top:0.3rem;">{zone}</span></div>'
        )

        # Count available components
        comp_labels = ['wc_ta', 're_ta', 'ebit_ta', 'mktcap_liab', 'rev_ta']
        comp_avail = sum(1 for c in comp_labels if d.get(c) is not None)

        _render_card(
            "ALTMAN Z-SCORE \u00b7 DISTRESS PREDICTOR",
            [
                ("Z-Score", z_big),
                ("X1: WC / Total Assets (\u00d71.2)", f"{d.get('wc_ta', 0):.4f}"),
                ("X2: RE / Total Assets (\u00d71.4)", f"{d.get('re_ta', 0):.4f}"),
                ("X3: EBIT / Total Assets (\u00d73.3)", f"{d.get('ebit_ta', 0):.4f}"),
                ("X4: MktCap / Liabilities (\u00d70.6)", f"{d.get('mktcap_liab', 0):.4f}"),
                ("X5: Revenue / Total Assets (\u00d71.0)", f"{d.get('rev_ta', 0):.4f}"),
                ("Components", f"{comp_avail}/5"),
            ],
            signal=sig,
            note="Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5. Safe >2.99, Grey 1.81\u20132.99, Distress <1.81.",
        )

    # 6. Pecking Order — score as X/4
    d = fs.get("pecking_order", {})
    if d:
        internal = d.get("internal_funding_sufficient")
        payout = d.get("payout_ratio")
        debt_level = d.get("debt_level", "")
        fcf_po = d.get("free_cash_flow")
        capex_po = d.get("capex")
        nd_ebitda_po = d.get("net_debt_to_ebitda")

        # Score: 4 criteria
        checks = 0
        if fcf_po is not None and capex_po is not None:
            try:
                if abs(float(fcf_po)) > abs(float(capex_po)):
                    checks += 1
            except (ValueError, TypeError):
                pass
        if payout is not None:
            try:
                if float(payout) < 50:
                    checks += 1
            except (ValueError, TypeError):
                pass
        if str(debt_level).lower() in ("low", "moderate"):
            checks += 1
        if internal:
            checks += 1

        sig = ("pos", f"Score {checks}/4 \u2014 internal funding sufficient") if internal else ("amber", f"Score {checks}/4 \u2014 relies on external financing")

        # Debt level as Xx EBITDA
        debt_level_display = debt_level or "N/A"
        if nd_ebitda_po is not None:
            try:
                debt_level_display = f"{float(nd_ebitda_po):.1f}x EBITDA"
            except (ValueError, TypeError):
                pass

        # Price / Book from info dict passed via closure
        pb_val = info.get("priceToBook") if info else None

        _render_card(
            "PECKING ORDER \u00b7 MYERS-MAJLUF 1984",
            [
                ("Score", f"<strong>{checks}/4</strong>"),
                ("FCF vs CapEx", f"FCF {_fmt(fcf_po, 'currency')} vs CapEx {_fmt(capex_po, 'currency')}"),
                ("Internal Funding OK?", '<span class="tag-good">Yes</span>' if internal else '<span class="tag-bad">No</span>'),
                ("Payout Ratio", f"{payout:.1f}%" if payout is not None else "N/A"),
                ("Debt Level", debt_level_display),
                ("Price / Book", f"{pb_val:.2f}x" if pb_val is not None else "N/A"),
            ],
            signal=sig,
            note="Myers-Majluf (1984): firms prefer internal \u2192 debt \u2192 equity. +1 FCF>CapEx, +1 payout<50%, +1 low/mod debt, +1 internal funding.",
        )


# ---------------------------------------------------------------------------
# OM render
# ---------------------------------------------------------------------------

def _render_om_section(om):
    """Render Operations Management section in two columns."""
    _section_bar("CB OPERATIONS MANAGEMENT")

    left, right = st.columns([1, 1])

    with left:
        # Supply Chain Efficiency
        d = om.get("supply_chain", {})
        if d:
            ccc = d.get("cash_conversion_cycle")
            if ccc is not None:
                try:
                    ccc_f = float(ccc)
                    sig = ("pos", f"CCC = {ccc_f:.0f} days — efficient cash cycle") if ccc_f < 40 else (("neg", f"CCC = {ccc_f:.0f} days — slow cash conversion") if ccc_f > 80 else ("warn", f"CCC = {ccc_f:.0f} days"))
                except (ValueError, TypeError):
                    sig = None
            else:
                sig = None
            _render_card(
                "SUPPLY CHAIN EFFICIENCY \u00b7 S1/S6/S7",
                [
                    ("Cash Conversion Cycle", f"{ccc} days" if ccc is not None else "N/A"),
                    ("DIO (Days Inventory)", f"{d.get('dio_days', 'N/A')} days"),
                    ("DSO (Days Sales)", f"{d.get('dso_days', 'N/A')} days"),
                    ("DPO (Days Payables)", f"{d.get('dpo_days', 'N/A')} days"),
                    ("Inventory Turnover", f"{d.get('inventory_turnover', 'N/A')}x"),
                ],
                signal=sig,
                note="S1 Process Analysis / S6 Inventory / S7 Supply Chain: CCC = DIO + DSO \u2212 DPO. Lower CCC = faster cash recovery from operations.",
            )

        # Process Quality & Lean
        d = om.get("process_quality", {})
        if d:
            gm = d.get("gross_margin")
            om_val = d.get("operating_margin")
            gap = d.get("overhead_gap_pct")
            if gap is not None:
                try:
                    gap_f = float(gap)
                    sig = ("pos", f"Overhead gap {gap_f:.1f}% — lean operations") if gap_f < 20 else (("neg", f"Overhead gap {gap_f:.1f}% — high overhead drag") if gap_f > 40 else ("warn", f"Overhead gap {gap_f:.1f}%"))
                except (ValueError, TypeError):
                    sig = None
            else:
                sig = None
            _render_card(
                "PROCESS QUALITY & LEAN \u00b7 S5 (TQM/TPS)",
                [
                    ("Gross Margin", f"{gm:.2f}%" if gm is not None else "N/A"),
                    ("Operating Margin", f"{om_val:.2f}%" if om_val is not None else "N/A"),
                    ("Overhead Gap (GM \u2212 OM)", f"{gap:.2f}%" if gap is not None else "N/A"),
                    ("ROA", f"{d.get('roa', 'N/A')}%"),
                    ("Gross Margin Trend", d.get("gross_margin_trend", "N/A")),
                    ("WC / Revenue", f"{d.get('wc_to_revenue', 'N/A')}%"),
                ],
                signal=sig,
                note="S5 TQM/TPS framework: overhead gap = gross margin \u2212 operating margin. Lower gap = leaner operations. Track gross margin trend for quality trajectory.",
            )

    with right:
        # Operational Throughput
        d = om.get("operational_throughput", {})
        if d:
            fat = d.get("fixed_asset_turnover")
            rg = d.get("revenue_growth")
            if rg is not None:
                try:
                    rg_f = float(rg) * 100
                    sig = ("pos", f"Revenue growth {rg_f:.1f}% — strong throughput") if rg_f > 10 else (("neg", f"Revenue growth {rg_f:.1f}% — declining throughput") if rg_f < 0 else ("warn", f"Revenue growth {rg_f:.1f}%"))
                except (ValueError, TypeError):
                    sig = None
            else:
                sig = None
            _render_card(
                "OPERATIONAL THROUGHPUT \u00b7 S2/S4",
                [
                    ("Revenue", _fmt(d.get("revenue"), "currency")),
                    ("Revenue Growth", f"{rg*100:.1f}%" if rg is not None else "N/A"),
                    ("Fixed Asset Turnover", f"{fat}x" if fat is not None else "N/A"),
                    ("CapEx (Current)", _fmt(d.get("capex_current"), "currency")),
                    ("CapEx Growth", f"{d.get('capex_growth', 0)*100:.1f}%" if d.get("capex_growth") is not None else "N/A"),
                ],
                signal=sig,
                note="S2 Theory of Constraints / S4 Capacity: throughput = revenue velocity through bottleneck assets. Fixed asset turnover measures capital efficiency.",
            )

        # Demand Variability & Bullwhip
        d = om.get("demand_variability", {})
        if d:
            bw = d.get("bullwhip_ratio")
            if bw is not None:
                try:
                    bw_f = float(bw)
                    sig = ("pos", f"Bullwhip ratio {bw_f:.2f} — stable supply chain") if bw_f < 1.0 else (("neg", f"Bullwhip ratio {bw_f:.2f} — significant demand amplification") if bw_f > 1.5 else ("warn", f"Bullwhip ratio {bw_f:.2f}"))
                except (ValueError, TypeError):
                    sig = None
            else:
                sig = None
            _render_card(
                "DEMAND VARIABILITY & BULLWHIP \u00b7 S7/S8",
                [
                    ("Revenue CV", f"{d.get('revenue_cv', 'N/A')}"),
                    ("Revenue Growth", f"{d.get('revenue_growth', 0)*100:.1f}%" if d.get("revenue_growth") is not None else "N/A"),
                    ("Bullwhip Ratio", _tag(bw, 1.0, 1.5, False, lambda v: f"{v:.3f}") if bw else "N/A"),
                ],
                signal=sig,
                note="S7/S8 Supply Chain Dynamics: Bullwhip = upstream variability / downstream variability. Ratio >1 = demand amplification up the chain. Key driver of excess inventory.",
            )


# ---------------------------------------------------------------------------
# CS render
# ---------------------------------------------------------------------------

def _render_cs_section(cs, om=None):
    """Render Competitive Strategy section in three columns."""
    _section_bar("CB COMPETITIVE STRATEGY")

    left, mid, right = st.columns([1, 1, 1])

    with left:
        d = cs.get("competitive_moat", {})
        if d:
            total = d.get("total_score", 0)
            avg = d.get("average_score", 0)
            width = d.get("moat_width", "N/A")
            scores = d.get("scores", {})

            if avg >= 6:
                sig = ("pos", f"Wide moat ({width}) — durable competitive advantage")
            elif avg >= 4:
                sig = ("warn", f"Narrow moat ({width}) — some competitive protection")
            else:
                sig = ("neg", f"No moat ({width}) — vulnerable to competition")

            # Convert scores to /2 format (if max is /10 with 5 dimensions,
            # divide by 5 to get /2 equivalent, cap at 2)
            score_rows = []
            for k, v in scores.items():
                try:
                    v_num = float(v)
                    # If scores are already on /2 scale, use as-is; if on /10, convert
                    if v_num > 2:
                        v_scaled = min(round(v_num / 5, 1), 2)
                    else:
                        v_scaled = v_num
                    score_rows.append((k.replace("_", " ").title(), f"{v_scaled} / 2"))
                except (ValueError, TypeError):
                    score_rows.append((k.replace("_", " ").title(), f"{v} / 2"))

            _render_card(
                "COMPETITIVE MOAT \u00b7 SESSION 2/6",
                [
                    ("Moat Score", f"<strong>{total} / 10</strong>"),
                    ("Moat Width", f"<strong>{width}</strong>"),
                    *score_rows,
                    ("Gross Margin", f"{d.get('gross_margin', 0):.1f}%"),
                    ("Operating Margin", f"{d.get('operating_margin', 0):.1f}%"),
                    ("R&D Intensity", f"{d.get('rd_intensity_pct', 0):.1f}%"),
                    ("ROE", f"{d.get('roe', 'N/A')}%"),
                ],
                signal=sig,
                note="Porter's Five Forces: switching costs, network effects, cost advantage, intangible assets, efficient scale.",
            )

    with mid:
        d = cs.get("disruption_risk", {})
        if d:
            risk_score = d.get("disruption_risk_score", 0)
            risk_level = d.get("risk_level", "N/A")

            if risk_score <= 3:
                r_color = "#16a34a"
                sig = ("pos", f"Low disruption risk ({risk_score}/10)")
            elif risk_score <= 6:
                r_color = "#d97706"
                sig = ("warn", f"Moderate disruption risk ({risk_score}/10)")
            else:
                r_color = "#dc2626"
                sig = ("neg", f"High disruption risk ({risk_score}/10)")

            risk_big = (
                f'<div style="text-align:center;margin:0.5rem 0;">'
                f'<span style="font-size:1.8rem;font-weight:800;color:{r_color}">{risk_level}</span>'
                f'<br><span style="font-size:0.8rem;color:#53565A">{risk_score}/10</span></div>'
            )

            _render_card(
                "DISRUPTION RISK \u00b7 SESSION 7",
                [
                    ("Risk Level", risk_big),
                    ("Innovation Type", d.get("innovation_type", "N/A")),
                    ("R&D Intensity", f"{d.get('rd_intensity_pct', 0):.1f}%"),
                    ("Revenue Growth", f"{d.get('revenue_growth', 'N/A')}%"),
                    ("Gross Margin Trend", d.get("gross_margin_trend", "N/A")),
                ],
                signal=sig,
                note="Henderson & Clark framework: architectural vs modular innovation. Higher R&D intensity may reduce disruption risk.",
            )

    with right:
        d = cs.get("market_position", {})
        if d:
            position = d.get("market_position", "N/A")
            detail = d.get("position_detail", "")
            cap_tier = d.get("cap_tier", "N/A")

            # Badge color by position
            pos_lower = str(position).lower()
            if "leader" in pos_lower or "dominant" in pos_lower:
                p_color = "#16a34a"
                sig = ("pos", f"{position} — strong market positioning")
            elif "challenger" in pos_lower or "contender" in pos_lower:
                p_color = "#d97706"
                sig = ("warn", f"{position} — competitive but not dominant")
            else:
                p_color = "#53565A"
                sig = ("warn", f"{position}")

            pos_badge = (
                f'<div style="text-align:center;margin:0.5rem 0;">'
                f'<span style="display:inline-block;background:{p_color};color:white;'
                f'padding:0.3rem 1rem;border-radius:999px;font-size:0.85rem;font-weight:700;">'
                f'{position}</span></div>'
            )

            # Key Barriers text based on financial metrics
            barriers = []
            gm_pct = d.get("gross_margin_pct", 0)
            roe_pct = d.get("roe_pct")
            if gm_pct and gm_pct > 40:
                barriers.append("high gross margin (pricing power)")
            if roe_pct is not None:
                try:
                    if float(roe_pct) > 15:
                        barriers.append("ROE above cost of equity")
                except (ValueError, TypeError):
                    pass
            if d.get("beta") is not None:
                try:
                    if float(d.get("beta")) < 0.8:
                        barriers.append("low beta (defensive moat)")
                except (ValueError, TypeError):
                    pass
            key_barriers = "; ".join(barriers) if barriers else "No clear barriers identified"

            # Prior Yr GM from process_quality if available
            prior_gm = None
            if om and om.get("process_quality", {}).get("gross_margin_history"):
                gm_hist = om["process_quality"]["gross_margin_history"]
                if isinstance(gm_hist, (list, tuple)) and len(gm_hist) > 1:
                    prior_gm = gm_hist[-2] if len(gm_hist) >= 2 else None

            mp_rows = [
                ("Position", pos_badge),
                ("Detail", detail),
                ("Cap Tier", cap_tier),
                ("Risk Profile", d.get("risk_profile", "N/A")),
                ("Gross Margin", f"{gm_pct:.1f}%"),
                ("Operating Margin", f"{d.get('operating_margin_pct', 0):.1f}%"),
                ("Revenue Growth", f"{d.get('revenue_growth_pct', 'N/A')}%"),
                ("ROE", f"{roe_pct}%" if roe_pct is not None else "N/A"),
                ("Beta", f"{d.get('beta', 'N/A')}"),
                ("Key Barriers", key_barriers),
            ]
            if prior_gm is not None:
                mp_rows.append(("Prior Yr GM", f"{prior_gm:.1f}%"))

            _render_card(
                "MARKET POSITION \u00b7 SESSION 2/3",
                mp_rows,
                signal=sig,
                note="Market position derived from cap tier, margins, growth, and risk profile.",
            )


# ===================================================================
# PAGE 2: CB ANALYSIS — Main page function
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
        if not info or (not info.get("currentPrice") and not info.get("regularMarketPrice") and not info.get("shortName")):
            st.error(f"Could not fetch data for {ticker}. yfinance may be rate-limited on Streamlit Cloud. Try again in a few seconds, or add FINNHUB_KEY to secrets for fallback data.")
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

        # Company header with pill tags
        st.markdown(f"""
        <div class="company-header">
            <h1>{name} ({ticker})</h1>
            <div class="sector" style="margin-top:0.4rem;">
                <span class="pill">{sector}</span>
                <span class="pill">{industry}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 8-metric stats row
        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
        with c1:
            st.markdown(f'<div class="metric-card"><h4>Price</h4><div class="value">{_fmt(price, "price")}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><h4>Market Cap</h4><div class="value">{_fmt(mkt_cap, "currency")}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><h4>P/E</h4><div class="value">{_fmt(pe)}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-card"><h4>Fwd P/E</h4><div class="value">{_fmt(fwd_pe)}</div></div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="metric-card"><h4>EPS</h4><div class="value">{_fmt(eps_val, "price")}</div></div>', unsafe_allow_html=True)
        with c6:
            div_display = f"{div_yield*100:.2f}%" if div_yield else "N/A"
            st.markdown(f'<div class="metric-card"><h4>Div Yield</h4><div class="value">{div_display}</div></div>', unsafe_allow_html=True)
        with c7:
            st.markdown(f'<div class="metric-card"><h4>52W High</h4><div class="value">{_fmt(high52, "price")}</div></div>', unsafe_allow_html=True)
        with c8:
            st.markdown(f'<div class="metric-card"><h4>52W Low</h4><div class="value">{_fmt(low52, "price")}</div></div>', unsafe_allow_html=True)

        if description:
            st.markdown(f"""<div style="border-left:3px solid {MAROON}; padding:0.8rem 1rem; margin:0.8rem 0;
                background:#fdf8f0; font-size:0.9rem; line-height:1.6; color:#475569; border-radius:0 3px 3px 0;">
                {description[:600] + '...' if len(description) > 600 else description}
            </div>""", unsafe_allow_html=True)

        # --- Run all 4 analyses ---
        booth = _cached_booth(ticker)
        fs = _cached_fs(ticker)
        om = _cached_om(ticker)
        cs = _cached_cs(ticker)

        # ====== EXECUTIVE SUMMARY ======
        _section_bar("EXECUTIVE SUMMARY")
        _render_executive_summary(booth, fs)

        # ====== INVESTMENT THESIS AI ======
        st.markdown(
            '<div class="ai-header">INVESTMENT THESIS \u00b7 AI ANALYSIS \u00b7 POWERED BY ADEPT-CB ANALYSIS</div>',
            unsafe_allow_html=True,
        )
        with st.spinner("Generating investment thesis..."):
            thesis = _get_ai_narrative(
                "You are an equity research analyst trained at Chicago Booth. "
                "Write a concise investment thesis (3-4 paragraphs) covering valuation, "
                "financial health, capital structure, and risk factors. Use bullet points for key metrics.",
                {"corporate_finance": booth, "financial_strategy": fs},
            )
        if thesis:
            st.markdown(f'<div class="ai-body">{_md(thesis)}</div>', unsafe_allow_html=True)

        # ====== TWO-COLUMN CF | FS LAYOUT ======
        cf_col, fs_col = st.columns([1, 1])

        with cf_col:
            st.markdown('<div class="section-bar">CB CORPORATE FINANCE</div>', unsafe_allow_html=True)
            _render_cf_column(booth)

        with fs_col:
            st.markdown('<div class="section-bar">CB FINANCIAL STRATEGY</div>', unsafe_allow_html=True)
            _render_fs_column(fs, info=info)

        # ====== CF+FS THESIS AI (full-width) ======
        _ai_block(
            "CF + FS THESIS \u00b7 AI ANALYSIS \u00b7 POWERED BY ADEPT-CB ANALYSIS",
            _md(thesis) if thesis else "<em>No thesis generated.</em>",
        )

        # ====== OPERATIONS MANAGEMENT ======
        _render_om_section(om)

        # OM Narrative AI
        st.markdown(
            '<div class="ai-header">OPERATIONS MANAGEMENT \u00b7 AI NARRATIVE \u00b7 POWERED BY ADEPT-CB ANALYSIS</div>',
            unsafe_allow_html=True,
        )
        with st.spinner("Generating operations narrative..."):
            om_narrative = _get_ai_narrative(
                "You are an operations management consultant trained at Chicago Booth. "
                "Analyze the supply chain efficiency, operational throughput, process quality, "
                "and demand variability. Provide actionable insights in 2-3 paragraphs.",
                om,
            )
        if om_narrative:
            st.markdown(f'<div class="ai-body">{_md(om_narrative)}</div>', unsafe_allow_html=True)

        # ====== COMPETITIVE STRATEGY ======
        _render_cs_section(cs, om=om)

        # CS Narrative AI
        st.markdown(
            '<div class="ai-header">COMPETITIVE STRATEGY \u00b7 AI NARRATIVE \u00b7 POWERED BY ADEPT-CB ANALYSIS</div>',
            unsafe_allow_html=True,
        )
        with st.spinner("Generating strategy narrative..."):
            cs_narrative = _get_ai_narrative(
                "You are a competitive strategy analyst trained at Chicago Booth. "
                "Assess the company's competitive moat, disruption risk, and market position. "
                "Reference Porter's Five Forces and Henderson & Clark where relevant. 2-3 paragraphs.",
                cs,
            )
        if cs_narrative:
            st.markdown(f'<div class="ai-body">{_md(cs_narrative)}</div>', unsafe_allow_html=True)

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


# ===================================================================
# SIDEBAR NAV + MAIN
# ===================================================================

with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:1rem 0;">
        <div style="font-size:1.3rem; font-weight:700; color:{MAROON};">Adept Academy</div>
        <div style="font-size:0.75rem; color:{GREY}; letter-spacing:2px; text-transform:uppercase;">CB Research Framework</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("Navigation", ["Dashboard", "CB Analysis"], label_visibility="collapsed")

if page == "Dashboard":
    page_dashboard()
else:
    page_cb_analysis()
