"""
PDF Report generation using WeasyPrint.

Color theme: ChicagoBooth Maroon (#9B1B30) and Grey (#94a3b8).
Branding: Elitez Asia's Analytics, Powered by CB Research Framework.

Important: WeasyPrint has limited CSS support — avoid flexbox flex:1/flex:2.
Use simple block/table layouts instead.
"""

import base64
import io
import re
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAROON = "#9B1B30"
GREY = "#94a3b8"

# ---------------------------------------------------------------------------
# Minimal Elitez logo (white "E" on transparent background, base64 SVG)
# ---------------------------------------------------------------------------
_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 40">
  <rect width="120" height="40" rx="6" fill="#9B1B30"/>
  <text x="10" y="30" font-family="Helvetica,Arial,sans-serif" font-size="26" font-weight="700" fill="white">ELITEZ</text>
</svg>"""
_LOGO_B64 = base64.b64encode(_LOGO_SVG.encode()).decode()


def _md_to_html(text: str) -> str:
    """Convert markdown to simple HTML (same logic as app.py _md)."""
    if not text:
        return ""
    text = re.sub(r'^### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = text.replace('\n', '<br>')
    return text


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


def _table(rows: list) -> str:
    """Generate an HTML table from [(label, value), ...] pairs."""
    html = '<table class="data-table">'
    for label, val in rows:
        if val is None:
            continue
        html += f'<tr><td class="label">{label}</td><td class="value">{val}</td></tr>'
    html += '</table>'
    return html


def _section(title: str, content: str) -> str:
    return f'<div class="section"><h2>{title}</h2>{content}</div>'


def _narrative_block(title: str, text: str) -> str:
    return f"""
    <div class="narrative">
        <h3>{title}</h3>
        <div class="narrative-body">{_md_to_html(text)}</div>
    </div>
    """


# ---------------------------------------------------------------------------
# Build full HTML document
# ---------------------------------------------------------------------------

def _build_html(
    ticker: str,
    info: dict,
    booth: dict,
    fs: dict,
    om: dict,
    cs: dict,
    thesis: str,
    om_narrative: str,
    cs_narrative: str,
) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    mkt_cap = info.get("marketCap")
    pe = info.get("trailingPE")
    fwd_pe = info.get("forwardPE")
    eps_val = info.get("trailingEps")
    div_yield = info.get("dividendYield")
    description = info.get("longBusinessSummary", "")

    css = f"""
    @page {{
        size: A4;
        margin: 2cm 1.8cm 2.5cm 1.8cm;
        @bottom-center {{
            content: "{today} | {ticker} | Page " counter(page);
            font-size: 8pt;
            color: {GREY};
        }}
    }}
    body {{
        font-family: Helvetica, Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.5;
        color: #1e293b;
    }}
    h1 {{ color: {MAROON}; font-size: 22pt; margin: 0 0 4pt 0; }}
    h2 {{ color: {MAROON}; font-size: 14pt; border-bottom: 2px solid {MAROON}; padding-bottom: 4pt; margin-top: 18pt; }}
    h3 {{ color: {MAROON}; font-size: 12pt; margin-top: 12pt; }}
    h4 {{ color: #475569; font-size: 10pt; margin-top: 8pt; }}
    .cover {{
        page-break-after: always;
        text-align: center;
        padding-top: 60pt;
    }}
    .cover .logo {{
        margin-bottom: 30pt;
    }}
    .cover .title {{
        font-size: 28pt;
        font-weight: 700;
        color: {MAROON};
        margin-bottom: 6pt;
    }}
    .cover .subtitle {{
        font-size: 13pt;
        color: {GREY};
        margin-bottom: 40pt;
    }}
    .cover .ticker-name {{
        font-size: 20pt;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 4pt;
    }}
    .cover .sector-line {{
        font-size: 11pt;
        color: {GREY};
        margin-bottom: 30pt;
    }}
    .stats-grid {{
        width: 100%;
        border-collapse: collapse;
        margin: 20pt auto;
    }}
    .stats-grid td {{
        width: 33%;
        padding: 8pt 12pt;
        border: 1px solid #e2e8f0;
        text-align: center;
    }}
    .stats-grid .stat-label {{
        font-size: 8pt;
        color: {GREY};
        text-transform: uppercase;
        letter-spacing: 0.5pt;
    }}
    .stats-grid .stat-value {{
        font-size: 14pt;
        font-weight: 700;
        color: #1e293b;
    }}
    .description {{
        font-size: 9pt;
        color: #475569;
        margin-top: 20pt;
        text-align: left;
        padding: 0 20pt;
        line-height: 1.6;
    }}
    .section {{
        page-break-inside: avoid;
    }}
    .data-table {{
        width: 100%;
        border-collapse: collapse;
        margin: 8pt 0 16pt 0;
    }}
    .data-table td {{
        padding: 4pt 8pt;
        border-bottom: 1px solid #f1f5f9;
        font-size: 9.5pt;
    }}
    .data-table td.label {{
        color: {GREY};
        width: 45%;
    }}
    .data-table td.value {{
        text-align: right;
        font-weight: 600;
    }}
    .narrative {{
        background: #fdf2f4;
        border-left: 3pt solid {MAROON};
        padding: 10pt 14pt;
        margin: 12pt 0;
        page-break-inside: avoid;
    }}
    .narrative h3 {{
        margin-top: 0;
        font-size: 11pt;
    }}
    .narrative-body {{
        font-size: 9.5pt;
        line-height: 1.6;
    }}
    .disclaimer {{
        page-break-before: always;
        font-size: 8pt;
        color: #64748b;
        line-height: 1.6;
    }}
    .disclaimer h2 {{
        color: {GREY};
        font-size: 12pt;
    }}
    .logo-band {{
        text-align: center;
        margin-top: 40pt;
        padding-top: 16pt;
        border-top: 2px solid {MAROON};
    }}
    """

    # --- Cover page ---
    div_display = f"{div_yield*100:.2f}%" if div_yield else "N/A"
    cover = f"""
    <div class="cover">
        <div class="logo">
            <img src="data:image/svg+xml;base64,{_LOGO_B64}" width="180" />
        </div>
        <div class="title">Elitez Asia's Analytics</div>
        <div class="subtitle">Powered by CB Research Framework</div>
        <div class="ticker-name">{name} ({ticker})</div>
        <div class="sector-line">{sector} | {industry}</div>
        <table class="stats-grid">
            <tr>
                <td><div class="stat-label">Price</div><div class="stat-value">{_fmt(price, "price")}</div></td>
                <td><div class="stat-label">Market Cap</div><div class="stat-value">{_fmt(mkt_cap, "currency")}</div></td>
                <td><div class="stat-label">PE Ratio</div><div class="stat-value">{_fmt(pe)}</div></td>
            </tr>
            <tr>
                <td><div class="stat-label">Forward PE</div><div class="stat-value">{_fmt(fwd_pe)}</div></td>
                <td><div class="stat-label">EPS</div><div class="stat-value">{_fmt(eps_val, "price")}</div></td>
                <td><div class="stat-label">Div Yield</div><div class="stat-value">{div_display}</div></td>
            </tr>
        </table>
        <div class="description">{description[:600] + "..." if len(description) > 600 else description}</div>
    </div>
    """

    # --- Executive Summary ---
    exec_summary = _section("Executive Summary", _build_exec_summary(booth, fs, cs))

    # --- CF + FS Details ---
    cf_detail = _section("Corporate Finance Analysis", _build_cf_section(booth))
    fs_detail = _section("Financial Strategy Analysis", _build_fs_section(fs))

    # --- AI Thesis ---
    thesis_html = _narrative_block("AI Investment Thesis (CF + FS)", thesis)

    # --- OM Details ---
    om_detail = _section("Operations Management Analysis", _build_om_section(om))
    om_narr_html = _narrative_block("AI Operations Narrative", om_narrative)

    # --- CS Details ---
    cs_detail = _section("Competitive Strategy Analysis", _build_cs_section(cs))
    cs_narr_html = _narrative_block("AI Strategy Narrative", cs_narrative)

    # --- Disclaimer ---
    disclaimer = f"""
    <div class="disclaimer">
        <h2>Disclaimers</h2>
        <p>This report is generated by Elitez Asia's Analytics platform for educational and informational
        purposes only. It does not constitute financial advice, investment recommendations, or an offer
        to buy or sell securities.</p>
        <p>The analytics framework is based on Chicago Booth research methodologies applied to publicly
        available financial data. All data is sourced from Yahoo Finance, Finnhub, Stooq, and FRED.
        Data accuracy depends on these third-party sources.</p>
        <p>AI-generated narratives are produced by Claude (Anthropic) and should be treated as analytical
        commentary, not professional financial advice. Always consult a qualified financial advisor before
        making investment decisions.</p>
        <p>Past performance does not guarantee future results. All investments carry risk, including
        potential loss of principal.</p>
        <p><strong>Report generated:</strong> {today}</p>
        <p><strong>Ticker:</strong> {ticker}</p>
        <div class="logo-band">
            <img src="data:image/svg+xml;base64,{_LOGO_B64}" width="140" />
            <div style="font-size:8pt; color:{GREY}; margin-top:6pt;">
                Elitez Asia's Analytics — Powered by CB Research Framework
            </div>
        </div>
    </div>
    """

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>{css}</style></head>
<body>
{cover}
{exec_summary}
{cf_detail}
{fs_detail}
{thesis_html}
{om_detail}
{om_narr_html}
{cs_detail}
{cs_narr_html}
{disclaimer}
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_exec_summary(booth: dict, fs: dict, cs: dict) -> str:
    parts = []

    # DCF verdict
    dcf = booth.get("dcf_model", {})
    if dcf and "error" not in dcf:
        upside = dcf.get("upside_pct")
        iv = dcf.get("intrinsic_value_per_share")
        cp = dcf.get("current_price")
        parts.append(f"<p><strong>DCF Valuation:</strong> Intrinsic value ${iv:,.2f} vs current ${cp:,.2f} ({upside:+.1f}% {'upside' if upside and upside > 0 else 'downside'})</p>")

    # Credit rating
    cr = fs.get("credit_rating", {})
    if cr:
        parts.append(f"<p><strong>Implied Credit Rating:</strong> {cr.get('implied_rating', 'N/A')} (spread: {cr.get('credit_spread_bps', 'N/A')} bps)</p>")

    # Altman Z
    az = fs.get("altman_z", {})
    if az and "error" not in az:
        parts.append(f"<p><strong>Altman Z-Score:</strong> {az.get('z_score', 'N/A')} — {az.get('zone', 'N/A')}</p>")

    # Moat
    moat = cs.get("competitive_moat", {})
    if moat:
        parts.append(f"<p><strong>Competitive Moat:</strong> {moat.get('moat_width', 'N/A')} ({moat.get('average_score', 0)}/10)</p>")

    # Market position
    mp = cs.get("market_position", {})
    if mp:
        parts.append(f"<p><strong>Market Position:</strong> {mp.get('market_position', 'N/A')} — {mp.get('position_detail', '')}</p>")

    return "".join(parts) if parts else "<p>Executive summary data not available.</p>"


def _build_cf_section(booth: dict) -> str:
    parts = []

    d = booth.get("capm_alpha", {})
    if d and "error" not in d:
        parts.append(f"<h3>CAPM & Jensen's Alpha (Lecture 2B)</h3>")
        parts.append(_table([
            ("Beta", d.get("beta")),
            ("Risk-Free Rate", f"{d.get('risk_free_rate', 0)*100:.2f}%"),
            ("Expected Return", f"{d.get('expected_return', 0)*100:.2f}%"),
            ("Actual Return", f"{d.get('actual_annualized_return', 0)*100:.2f}%"),
            ("Jensen's Alpha", f"{d.get('jensens_alpha', 0)*100:.2f}%"),
        ]))

    d = booth.get("valuation_multiples", {})
    if d:
        parts.append(f"<h3>Valuation Multiples (Lecture 5B)</h3>")
        parts.append(_table([
            ("PE Ratio", f"{d.get('pe_ratio', 'N/A')} (Median: {d.get('pe_sector_median')})"),
            ("EV/EBITDA", f"{d.get('ev_ebitda', 'N/A')} (Median: {d.get('ev_ebitda_sector_median')})"),
            ("P/B", f"{d.get('pb_ratio', 'N/A')} (Median: {d.get('pb_sector_median')})"),
            ("P/S", f"{d.get('ps_ratio', 'N/A')} (Median: {d.get('ps_sector_median')})"),
        ]))

    d = booth.get("wacc", {})
    if d and "error" not in d:
        parts.append(f"<h3>WACC (Lecture 4B)</h3>")
        parts.append(_table([
            ("WACC", f"{d.get('wacc', 0)*100:.2f}%"),
            ("Cost of Equity", f"{d.get('cost_of_equity', 0)*100:.2f}%"),
            ("Cost of Debt", f"{d.get('cost_of_debt', 0)*100:.2f}%"),
        ]))

    d = booth.get("free_cash_flow", {})
    if d:
        parts.append(f"<h3>Free Cash Flow (Lectures 4A/4B)</h3>")
        parts.append(_table([
            ("FCF", _fmt(d.get("free_cash_flow"), "currency")),
            ("FCF Yield", f"{d.get('fcf_yield_pct', 'N/A')}%"),
            ("FCF Margin", f"{d.get('fcf_margin_pct', 'N/A')}%"),
        ]))

    d = booth.get("dcf_model", {})
    if d and "error" not in d:
        parts.append(f"<h3>DCF 3-Stage Model (Lecture 5B)</h3>")
        parts.append(_table([
            ("Intrinsic Value/Share", _fmt(d.get("intrinsic_value_per_share"), "price")),
            ("Current Price", _fmt(d.get("current_price"), "price")),
            ("Upside/Downside", f"{d.get('upside_pct', 0):+.1f}%"),
            ("WACC", f"{d.get('wacc', 0)*100:.2f}%"),
            ("Near-term Growth", f"{d.get('near_term_growth', 0)*100:.1f}%"),
            ("Terminal Growth", f"{d.get('terminal_growth', 0)*100:.1f}%"),
        ]))

    return "".join(parts) if parts else "<p>Data not available.</p>"


def _build_fs_section(fs: dict) -> str:
    parts = []

    d = fs.get("capital_structure", {})
    if d:
        parts.append(f"<h3>Capital Structure (D1)</h3>")
        parts.append(_table([
            ("Net Debt", _fmt(d.get("net_debt"), "currency")),
            ("Net Debt/Capital", f"{d.get('net_debt_to_capital', 0)*100:.1f}%" if d.get("net_debt_to_capital") else "N/A"),
            ("Net Debt/EBITDA", f"{d.get('net_debt_to_ebitda', 'N/A')}x"),
        ]))

    d = fs.get("credit_rating", {})
    if d:
        parts.append(f"<h3>Implied Credit Rating (D1)</h3>")
        parts.append(_table([
            ("Rating", d.get("implied_rating")),
            ("Score", f"{d.get('composite_score')}/8"),
            ("Spread", f"{d.get('credit_spread_bps')} bps"),
        ]))

    d = fs.get("static_tradeoff", {})
    if d:
        parts.append(f"<h3>Static Trade-Off (D2/D3/D4)</h3>")
        parts.append(_table([
            ("PV Tax Shield", _fmt(d.get("pv_tax_shield"), "currency")),
            ("PV Distress Cost", _fmt(d.get("pv_distress_cost"), "currency")),
            ("Net Benefit", _fmt(d.get("net_benefit_of_debt"), "currency")),
            ("Assessment", d.get("assessment")),
        ]))

    d = fs.get("altman_z", {})
    if d and "error" not in d:
        parts.append(f"<h3>Altman Z-Score</h3>")
        parts.append(_table([
            ("Z-Score", f"{d.get('z_score', 0):.3f}"),
            ("Zone", d.get("zone")),
        ]))

    d = fs.get("payout_policy", {})
    if d:
        parts.append(f"<h3>Payout & Cash Policy (D4)</h3>")
        parts.append(_table([
            ("Excess Cash", _fmt(d.get("excess_cash"), "currency")),
            ("Dividend Yield", f"{d.get('dividend_yield', 0):.2f}%"),
            ("Payout Ratio", f"{d.get('payout_ratio', 0):.1f}%"),
        ]))

    d = fs.get("pecking_order", {})
    if d:
        parts.append(f"<h3>Pecking Order (Myers-Majluf)</h3>")
        parts.append(_table([
            ("Stage", d.get("pecking_order_stage")),
            ("Debt Level", d.get("debt_level")),
            ("Internal Funding", "Yes" if d.get("internal_funding_sufficient") else "No"),
        ]))

    return "".join(parts) if parts else "<p>Data not available.</p>"


def _build_om_section(om: dict) -> str:
    parts = []

    d = om.get("supply_chain", {})
    if d:
        parts.append(f"<h3>Supply Chain Efficiency (S1/S6/S7)</h3>")
        parts.append(_table([
            ("Cash Conversion Cycle", f"{d.get('cash_conversion_cycle', 'N/A')} days"),
            ("DIO", f"{d.get('dio_days', 'N/A')} days"),
            ("DSO", f"{d.get('dso_days', 'N/A')} days"),
            ("DPO", f"{d.get('dpo_days', 'N/A')} days"),
            ("Inventory Turnover", f"{d.get('inventory_turnover', 'N/A')}x"),
        ]))

    d = om.get("operational_throughput", {})
    if d:
        parts.append(f"<h3>Operational Throughput (S2/S4)</h3>")
        parts.append(_table([
            ("Fixed Asset Turnover", f"{d.get('fixed_asset_turnover', 'N/A')}x"),
            ("Revenue Growth", f"{d.get('revenue_growth', 0)*100:.1f}%" if d.get("revenue_growth") else "N/A"),
        ]))

    d = om.get("process_quality", {})
    if d:
        parts.append(f"<h3>Process Quality & Lean (S5)</h3>")
        parts.append(_table([
            ("Gross Margin", f"{d.get('gross_margin', 0):.2f}%"),
            ("Operating Margin", f"{d.get('operating_margin', 0):.2f}%"),
            ("Overhead Gap", f"{d.get('overhead_gap_pct', 0):.2f}%"),
        ]))

    d = om.get("demand_variability", {})
    if d:
        parts.append(f"<h3>Demand Variability & Bullwhip (S7/S8)</h3>")
        parts.append(_table([
            ("Revenue CV", d.get("revenue_cv", "N/A")),
            ("Bullwhip Ratio", d.get("bullwhip_ratio", "N/A")),
            ("Assessment", d.get("assessment", "N/A")),
        ]))

    return "".join(parts) if parts else "<p>Data not available.</p>"


def _build_cs_section(cs: dict) -> str:
    parts = []

    d = cs.get("competitive_moat", {})
    if d:
        parts.append(f"<h3>Competitive Moat (Session 2/6)</h3>")
        scores = d.get("scores", {})
        rows = [(k.replace("_", " ").title(), f"{v}/10") for k, v in scores.items()]
        rows.append(("Moat Width", d.get("moat_width")))
        parts.append(_table(rows))

    d = cs.get("disruption_risk", {})
    if d:
        parts.append(f"<h3>Disruption Risk (Session 7)</h3>")
        parts.append(_table([
            ("Risk Score", f"{d.get('disruption_risk_score', 0)}/10"),
            ("Risk Level", d.get("risk_level")),
            ("Innovation Type", d.get("innovation_type")),
        ]))

    d = cs.get("market_position", {})
    if d:
        parts.append(f"<h3>Market Position (Session 2/3)</h3>")
        parts.append(_table([
            ("Position", d.get("market_position")),
            ("Cap Tier", d.get("cap_tier")),
            ("Risk Profile", d.get("risk_profile")),
        ]))

    return "".join(parts) if parts else "<p>Data not available.</p>"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf(
    ticker: str,
    info: dict,
    booth: dict,
    fs: dict,
    om: dict,
    cs: dict,
    thesis: str = "",
    om_narrative: str = "",
    cs_narrative: str = "",
) -> bytes:
    """Generate PDF report and return bytes."""
    from weasyprint import HTML

    html_str = _build_html(ticker, info, booth, fs, om, cs, thesis, om_narrative, cs_narrative)
    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes
