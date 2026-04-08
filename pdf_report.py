"""
PDF Report generation using WeasyPrint.

Restructured layout:
  Page 1: Cover (includes compact executive summary)
  Pages 2+: CF|FS content (Investment Thesis, Company Info, two-column cards, narrative)
  OM content (cards + narrative together, no forced break)
  CS content (cards + narrative together, no forced break)
  Disclaimers

Color theme: ChicagoBooth Maroon (#9B1B30) and Grey (#53565A, Pantone Cool Gray 11C).
Branding: Elitez Asia's Analytics, Powered by CB Research Framework.

WeasyPrint constraints: NO flexbox flex:1/flex:2 — use <table> with percentage
widths for multi-column layouts.
"""

import base64
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

MAROON = "#9B1B30"
MAROON_LIGHT = "#fdf2f4"
GREY = "#53565A"
DARK_TEXT = "#1e293b"
BORDER_COLOR = "#e2e8f0"
GREEN = "#16a34a"
RED = "#dc2626"
AMBER = "#d97706"
GREEN_BG = "#f0fdf4"
RED_BG = "#fef2f2"
AMBER_BG = "#fffbeb"

# ---------------------------------------------------------------------------
# Logo — Elitez Group white PNG (886x886, RGBA, white on transparent)
# Loaded from file and embedded as base64 for PDF generation
# ---------------------------------------------------------------------------
import pathlib as _pathlib

def _load_logo_b64():
    """Load logo from multiple possible paths (handles Streamlit Cloud)."""
    candidates = [
        _pathlib.Path(__file__).resolve().parent / "assets" / "elitez_logo_white.png",
        _pathlib.Path("assets") / "elitez_logo_white.png",
        _pathlib.Path("/mount/src/elitez-market/assets/elitez_logo_white.png"),
    ]
    for p in candidates:
        try:
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except (FileNotFoundError, OSError):
            continue
    return ""

_LOGO_B64 = _load_logo_b64()
_LOGO_B64_SM = _LOGO_B64  # same PNG, sized differently via HTML height attr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _md_to_html(text: str) -> str:
    """Convert markdown to simple HTML."""
    if not text:
        return ""
    text = re.sub(r'^### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Convert bullet lines
    text = re.sub(r'^[-*] (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = text.replace('\n', '<br>')
    # Wrap consecutive <li> in <ul>
    text = re.sub(r'((?:<li>.*?</li><br>?)+)', r'<ul>\1</ul>', text)
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
    if fmt_type == "ratio":
        return f"{val:.2f}x"
    return f"{val:,.2f}"


def _safe(d: dict, key: str, default=None):
    """Safely get a value from a dict that might contain 'error'."""
    if not d or "error" in d:
        return default
    return d.get(key, default)


def _pct_safe(val, multiplier=100):
    """Format a decimal as percentage, handling None."""
    if val is None:
        return "N/A"
    try:
        return f"{float(val) * multiplier:.2f}%"
    except (ValueError, TypeError):
        return "N/A"


def _signal(positive: bool, text: str) -> str:
    """Return a signal indicator with colored left border accent."""
    color = GREEN if positive else RED
    arrow = "&#9650;" if positive else "&#9660;"
    return (f'<div style="border-left:3pt solid {color}; padding:3pt 8pt; margin-top:5pt;">'
            f'<span style="color:{color}; font-size:8pt; font-weight:600;">'
            f'{arrow} {text}</span></div>')


def _signal_amber(text: str) -> str:
    return (f'<div style="border-left:3pt solid {AMBER}; padding:3pt 8pt; margin-top:5pt;">'
            f'<span style="color:{AMBER}; font-size:8pt; font-weight:600;">'
            f'&#9651; {text}</span></div>')


def _data_rows(rows: list) -> str:
    """Generate data rows: [(label, value), ...] -> HTML table rows."""
    html = '<table style="width:100%; border-collapse:collapse; margin:4pt 0;">'
    for label, val in rows:
        if val is None:
            continue
        html += (f'<tr><td style="padding:2pt 0; border-bottom:1px solid #f1f5f9; '
                 f'font-size:8.5pt; color:{GREY};">{label}</td>'
                 f'<td style="padding:2pt 0; border-bottom:1px solid #f1f5f9; '
                 f'font-size:8.5pt; font-weight:600; text-align:right; '
                 f'font-family:\'Courier New\', Courier, monospace;">{val}</td></tr>')
    html += '</table>'
    return html


def _card(title: str, content: str, note: str = "") -> str:
    """Wrap content in a styled card with optional annotation note."""
    note_html = ""
    if note:
        note_html = (f'<div style="font-size:7pt; color:#6b7280; '
                     f'line-height:1.4; margin-top:6pt;">&middot; {note}</div>')
    return (f'<div style="border:1px solid {BORDER_COLOR}; border-radius:3px; '
            f'padding:10pt 14pt; margin-bottom:10pt; page-break-inside:avoid;">'
            f'<div style="text-transform:uppercase; letter-spacing:2pt; font-size:8pt; '
            f'color:{MAROON}; font-weight:700; margin-bottom:6pt; '
            f'border-bottom:0.5pt solid #d1d5db; padding-bottom:4pt;">{title}</div>'
            f'{content}{note_html}</div>')


def _section_bar(title: str) -> str:
    """Full-width maroon section bar."""
    return (f'<div style="background:{MAROON}; color:white; padding:6pt 12pt; '
            f'border-radius:4px; font-size:9pt; font-weight:700; letter-spacing:2pt; '
            f'text-transform:uppercase; margin:16pt 0 10pt 0;">{title}</div>')


def _narrative_card(title: str, text: str) -> str:
    """AI narrative block with disclaimer footer."""
    return (f'<div style="margin:14pt 0; page-break-inside:avoid;">'
            f'<div style="text-transform:uppercase; letter-spacing:1.5pt; font-size:9pt; '
            f'color:{MAROON}; font-weight:700; margin-bottom:6pt;">{title}</div>'
            f'<div style="border-top:2pt solid {MAROON}; '
            f'padding:12pt 16pt; background:#fafafa;">'
            f'<div style="font-size:9.5pt; line-height:1.6;">{_md_to_html(text)}</div>'
            f'</div>'
            f'<div style="font-size:7pt; color:{GREY}; margin-top:4pt;">'
            f'Based on public financial data and CB frameworks. Not investment advice.</div>'
            f'</div>')


def _metric_box(label: str, value: str, sublabel: str = "") -> str:
    """A single COMPACT metric box for the executive summary grid on cover page."""
    sub_html = ""
    if sublabel:
        sub_html = f'<div style="font-size:6.5pt; color:{GREY}; margin-top:1pt;">{sublabel}</div>'
    return (f'<td style="width:33%; padding:5pt; border:1px solid {BORDER_COLOR}; '
            f'border-radius:2px; text-align:center; vertical-align:top;">'
            f'<div style="font-size:6.5pt; color:{GREY}; text-transform:uppercase; '
            f'letter-spacing:0.5pt;">{label}</div>'
            f'<div style="font-size:12pt; font-weight:700; color:{DARK_TEXT}; '
            f'margin-top:1pt; font-family:\'Courier New\', Courier, monospace;">{value}</div>'
            f'{sub_html}</td>')


# ---------------------------------------------------------------------------
# Page header / footer
# ---------------------------------------------------------------------------

def _page_header(ticker: str) -> str:
    return (f'<div style="border-bottom:1px solid {BORDER_COLOR}; padding-bottom:6pt; '
            f'margin-bottom:12pt;">'
            f'<table width="100%"><tr>'
            f'<td style="font-size:8pt; color:{GREY};">Elitez Asia\'s Analytics</td>'
            f'<td style="font-size:8pt; color:{GREY}; text-align:right;">'
            f'{ticker} &middot; CB Analysis</td>'
            f'</tr></table></div>')


# ---------------------------------------------------------------------------
# PAGE 1: Cover (now includes compact executive summary)
# ---------------------------------------------------------------------------

def _build_cover(ticker: str, info: dict, today_str: str, booth: dict = None, fs: dict = None) -> str:
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
    div_display = f"{div_yield*100:.2f}%" if div_yield else "N/A"

    # Stats row: 8 stats in one row
    stats_html = f"""
    <table style="width:100%; border-collapse:collapse; margin:20pt 0;">
      <tr>
        <td style="width:12.5%; padding:8pt 4pt; text-align:center; border:1px solid {BORDER_COLOR};">
          <div style="font-size:7pt; color:{GREY}; text-transform:uppercase; letter-spacing:0.5pt;">PRICE</div>
          <div style="font-size:13pt; font-weight:700;">{_fmt(price, "price")}</div></td>
        <td style="width:12.5%; padding:8pt 4pt; text-align:center; border:1px solid {BORDER_COLOR};">
          <div style="font-size:7pt; color:{GREY}; text-transform:uppercase; letter-spacing:0.5pt;">MARKET CAP</div>
          <div style="font-size:13pt; font-weight:700;">{_fmt(mkt_cap, "currency")}</div></td>
        <td style="width:12.5%; padding:8pt 4pt; text-align:center; border:1px solid {BORDER_COLOR};">
          <div style="font-size:7pt; color:{GREY}; text-transform:uppercase; letter-spacing:0.5pt;">P/E (TTM)</div>
          <div style="font-size:13pt; font-weight:700;">{_fmt(pe)}</div></td>
        <td style="width:12.5%; padding:8pt 4pt; text-align:center; border:1px solid {BORDER_COLOR};">
          <div style="font-size:7pt; color:{GREY}; text-transform:uppercase; letter-spacing:0.5pt;">FWD P/E</div>
          <div style="font-size:13pt; font-weight:700;">{_fmt(fwd_pe)}</div></td>
        <td style="width:12.5%; padding:8pt 4pt; text-align:center; border:1px solid {BORDER_COLOR};">
          <div style="font-size:7pt; color:{GREY}; text-transform:uppercase; letter-spacing:0.5pt;">EPS</div>
          <div style="font-size:13pt; font-weight:700;">{_fmt(eps_val, "price")}</div></td>
        <td style="width:12.5%; padding:8pt 4pt; text-align:center; border:1px solid {BORDER_COLOR};">
          <div style="font-size:7pt; color:{GREY}; text-transform:uppercase; letter-spacing:0.5pt;">DIV YIELD</div>
          <div style="font-size:13pt; font-weight:700;">{div_display}</div></td>
        <td style="width:12.5%; padding:8pt 4pt; text-align:center; border:1px solid {BORDER_COLOR};">
          <div style="font-size:7pt; color:{GREY}; text-transform:uppercase; letter-spacing:0.5pt;">52W HIGH</div>
          <div style="font-size:13pt; font-weight:700;">{_fmt(high52, "price")}</div></td>
        <td style="width:12.5%; padding:8pt 4pt; text-align:center; border:1px solid {BORDER_COLOR};">
          <div style="font-size:7pt; color:{GREY}; text-transform:uppercase; letter-spacing:0.5pt;">52W LOW</div>
          <div style="font-size:13pt; font-weight:700;">{_fmt(low52, "price")}</div></td>
      </tr>
    </table>
    """

    # --- Executive Summary metrics (compact, on cover page) ---
    booth = booth or {}
    fs = fs or {}
    dcf = booth.get("dcf_model", {}) or {}
    capm = booth.get("capm_alpha", {}) or {}
    cr = fs.get("credit_rating", {}) or {}
    az = fs.get("altman_z", {}) or {}
    fcf_d = booth.get("free_cash_flow", {}) or {}
    po = fs.get("pecking_order", {}) or {}

    # DCF upside
    upside_val = _safe(dcf, "upside_pct")
    iv = _safe(dcf, "intrinsic_value_per_share")
    upside_str = f"{upside_val:+.1f}%" if upside_val is not None else "N/A"
    iv_str = f"IV: ${iv:,.2f}" if iv is not None else ""

    # Implied rating
    rating = cr.get("implied_rating", "N/A") if cr else "N/A"
    score = cr.get("composite_score", "N/A") if cr else "N/A"
    rating_sub = f"Score: {score}/8" if score != "N/A" else ""

    # Altman Z
    z_val = _safe(az, "z_score")
    z_str = f"{z_val:.2f}" if z_val is not None else "N/A"
    z_zone = _safe(az, "zone", "N/A")

    # FCF Yield
    fcf_yield = fcf_d.get("fcf_yield_pct") if fcf_d else None
    fcf_yield_str = f"{fcf_yield:.2f}%" if fcf_yield is not None else "N/A"

    # Jensen's Alpha
    alpha = _safe(capm, "jensens_alpha")
    alpha_str = f"{alpha*100:+.2f}%" if alpha is not None else "N/A"

    # Pecking Order
    po_stage = po.get("pecking_order_stage", "N/A") if po else "N/A"
    po_net = po.get("net_score", "") if po else ""
    po_sub = f"Net: {po_net}" if po_net else ""

    exec_summary_html = f"""
    <div style="margin:10pt 0 6pt 0;">
      <div style="text-transform:uppercase; letter-spacing:1.5pt; font-size:8pt;
                   color:{MAROON}; font-weight:700; margin-bottom:4pt;">Executive Summary</div>
      <table style="width:100%; border-collapse:separate; border-spacing:4pt;">
        <tr>
          {_metric_box("DCF Upside/Downside", upside_str, iv_str)}
          {_metric_box("Implied S&P Rating", rating, rating_sub)}
          {_metric_box("Altman Z-Score", z_str, z_zone)}
        </tr>
        <tr>
          {_metric_box("FCF Yield", fcf_yield_str)}
          {_metric_box("Jensen's Alpha", alpha_str)}
          {_metric_box("Pecking Order", po_stage, po_sub)}
        </tr>
      </table>
    </div>
    """

    # CB Framework Rating based on DCF upside
    _dcf = (booth or {}).get("dcf_model", {}) or {}
    _dcf_upside = _dcf.get("upside_pct") if _dcf and "error" not in _dcf else None
    if _dcf_upside is not None:
        if _dcf_upside > 15:
            _rating_verdict = "OVERWEIGHT"
        elif _dcf_upside < -15:
            _rating_verdict = "UNDERWEIGHT"
        else:
            _rating_verdict = "EQUAL-WEIGHT"
    else:
        _rating_verdict = "NOT RATED"

    rating_html = (
        f'<div style="margin:10pt 0; text-align:left;">'
        f'<span style="font-size:8pt; color:{GREY}; text-transform:uppercase; letter-spacing:1pt;">CB Framework Rating</span>'
        f'<div style="font-size:14pt; font-weight:700; color:{MAROON}; margin-top:2pt; letter-spacing:1pt;">'
        f'{_rating_verdict}</div>'
        f'<div style="font-size:7pt; color:{GREY};">Based on DCF intrinsic value vs. current market price</div>'
        f'</div>'
    )

    # Truncate description
    desc_text = description[:500] + "..." if len(description) > 500 else description

    # Pill tags for sector/industry
    pill_style = (f"display:inline-block; background:#f1f5f9; color:#475569; "
                  f"border-radius:12px; padding:3pt 10pt; font-size:8.5pt; margin:2pt 4pt;")

    return f"""
    <div style="page-break-after:always;">
      <!-- Header band — tall maroon, bleeds full-width -->
      <div style="background:{MAROON}; padding:36pt 28pt 28pt 28pt;
                   margin:0 -1.5cm 0 -1.5cm;">
        <!-- Logo + Company Name -->
        <table width="100%"><tr>
          <td style="vertical-align:middle;">
            <img src="data:image/png;base64,{_LOGO_B64}" height="50" />
          </td>
          <td style="vertical-align:middle; padding-left:16pt;">
            <div style="color:white; font-size:22pt; font-weight:700; letter-spacing:2pt;
                        font-family:Helvetica,Arial,sans-serif; line-height:1.2;">
              ELITEZ ASIA'S<br/>ANALYTICS</div>
            <div style="color:rgba(255,255,255,0.6); font-size:7.5pt; font-weight:400;
                        letter-spacing:2pt; text-transform:uppercase; margin-top:4pt;">
              Powered by CB Research Framework</div>
          </td>
          <td style="width:1%;"></td>
        </tr></table>
        <!-- Equity Research Report — bottom right -->
        <div style="text-align:right; margin-top:14pt;">
          <span style="color:rgba(255,255,255,0.7); font-size:9pt; font-weight:600; letter-spacing:2pt;
                       text-transform:uppercase;">Equity Research Report</span>
          <br/>
          <span style="color:rgba(255,255,255,0.45); font-size:7.5pt;
                       letter-spacing:1pt;">CB CF &middot; FS &middot; OM</span>
        </div>
      </div>

      <!-- Spacer -->
      <div style="height:30pt;"></div>

      <!-- Ticker (reduced from 42pt to 36pt) -->
      <div style="text-align:left;">
        <div style="font-size:36pt; font-weight:700; color:{DARK_TEXT}; letter-spacing:3pt;">{ticker}</div>
        <div style="font-size:14pt; color:#475569; margin-top:4pt;">{name}</div>
        <div style="margin-top:8pt;">
          <span style="{pill_style}">{sector}</span>
          <span style="{pill_style}">{industry}</span>
        </div>
      </div>

      <!-- Stats grid -->
      {stats_html}

      <!-- Executive Summary boxes (compact 2x3 grid) -->
      {exec_summary_html}

      <!-- CB Framework Rating -->
      {rating_html}

      <!-- Description -->
      <div style="border-left:3pt solid {BORDER_COLOR}; padding:10pt 14pt; margin:10pt 20pt;
                   font-size:9pt; color:#475569; line-height:1.6; background:#fafafa;">
        {desc_text}
      </div>

      <!-- Footer -->
      <div style="margin-top:20pt; border-top:1px solid {BORDER_COLOR}; padding-top:10pt;">
        <table width="100%"><tr>
          <td style="font-size:8pt; color:{GREY}; vertical-align:top;">
            <div>Report Date: {today_str}</div>
            <div style="margin-top:2pt;">Analysis powered by CB frameworks (CF &middot; FS &middot; OM)</div>
            <div style="margin-top:4pt; display:inline-block; border:1px solid #53565A; color:#53565A;
                        background:none; padding:2pt 10pt; border-radius:3px; font-size:7pt; font-weight:600;
                        letter-spacing:1pt; text-transform:uppercase;">CONFIDENTIAL</div>
          </td>
          <td style="text-align:right; font-size:8pt; color:{GREY}; vertical-align:top;">
            <div style="font-weight:600;">Elitez Asia's Analytics</div>
            <div>elitez-market.streamlit.app</div>
            <div>Powered by Elitez-CB Analysis</div>
          </td>
        </tr></table>
      </div>
    </div>
    """


# ---------------------------------------------------------------------------
# CF|FS content: continuous flow (no forced page breaks)
# Includes: Investment Thesis, Company Info, section bars, all cards, narrative
# ---------------------------------------------------------------------------

def _build_cf_fs_content(ticker: str, info: dict, booth: dict, fs: dict, thesis: str) -> str:
    """Build CF|FS as one continuous flow — no forced page breaks."""
    name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    mkt_cap = info.get("marketCap")
    description = info.get("longBusinessSummary", "")
    desc_short = description[:300] + "..." if len(description) > 300 else description

    pill_style = (f"display:inline-block; background:#f1f5f9; color:#475569; "
                  f"border-radius:12px; padding:2pt 8pt; font-size:7.5pt; margin:1pt 2pt;")

    # --- CF Cards ---

    # CAPM card
    capm_data = booth.get("capm_alpha", {}) or {}
    capm_content = ""
    if capm_data and "error" not in capm_data:
        beta = capm_data.get("beta")
        rf = capm_data.get("risk_free_rate")
        erp = capm_data.get("market_risk_premium")
        er = capm_data.get("expected_return")
        ar = capm_data.get("actual_annualized_return")
        ja = capm_data.get("jensens_alpha")
        r2 = capm_data.get("r_squared")

        positive_alpha = ja is not None and ja > 0
        sig_text = "Positive Alpha - Outperforming" if positive_alpha else "Negative Alpha - Underperforming"
        sig = _signal(positive_alpha, sig_text) if ja is not None else ""

        capm_content = _card("CAPM & Jensen's Alpha", _data_rows([
            ("Beta", f"{beta:.3f}" if beta is not None else "N/A"),
            ("Risk-Free Rate", _pct_safe(rf)),
            ("Market Risk Premium", _pct_safe(erp)),
            ("Expected Return (CAPM)", _pct_safe(er)),
            ("Actual Annualized Return", _pct_safe(ar)),
            ("Jensen's Alpha (\u03b1)", _pct_safe(ja)),
            ("R-Squared", f"{r2:.3f}" if r2 is not None else "N/A"),
        ]) + sig, "Lecture 2B: E(R) = Rf + \u03b2[E(Rm) - Rf]. Alpha measures risk-adjusted excess return.")
    else:
        capm_content = _card("CAPM & Jensen's Alpha", '<div style="font-size:9pt; color:#53565A;">Data not available.</div>', "")

    # Valuation Multiples
    vm = booth.get("valuation_multiples", {}) or {}
    vm_content = ""
    if vm:
        pe = vm.get("pe_ratio")
        pe_med = vm.get("pe_sector_median")
        pe_vs = vm.get("pe_vs_sector", "")
        ev = vm.get("ev_ebitda")
        ev_med = vm.get("ev_ebitda_sector_median")
        pb = vm.get("pb_ratio")
        pb_med = vm.get("pb_sector_median")
        ps = vm.get("ps_ratio")
        ps_med = vm.get("ps_sector_median")

        def _vs_sector(val, median, label):
            if val is not None and median is not None and median != 0:
                pct = (val - median) / median * 100
                word = "discount" if pct < 0 else "premium"
                return f"{abs(pct):.0f}% {word} vs sector median {label} of {median:.1f}x"
            return "N/A"

        vm_rows = []
        if pe is not None:
            vm_rows.append(("P/E (TTM)", f"{pe:.2f}x"))
            vm_rows.append(("vs Sector", _vs_sector(pe, pe_med, "P/E")))
        if ev is not None:
            vm_rows.append(("EV/EBITDA", f"{ev:.2f}x"))
            vm_rows.append(("vs Sector", _vs_sector(ev, ev_med, "EV/EBITDA")))
        if pb is not None:
            vm_rows.append(("P/B", f"{pb:.2f}x"))
            vm_rows.append(("vs Sector", _vs_sector(pb, pb_med, "P/B")))
        if ps is not None:
            vm_rows.append(("P/S", f"{ps:.2f}x"))
            vm_rows.append(("vs Sector", _vs_sector(ps, ps_med, "P/S")))

        discount_count = 0
        total_compared = 0
        for val, med in [(pe, pe_med), (ev, ev_med), (pb, pb_med), (ps, ps_med)]:
            if val is not None and med is not None and med != 0:
                total_compared += 1
                if val < med:
                    discount_count += 1
        if total_compared > 0:
            if discount_count > total_compared / 2:
                sig = _signal(True, "cheap vs peers")
            elif discount_count < total_compared / 2:
                sig = _signal(False, "expensive vs peers")
            else:
                sig = _signal_amber("fairly valued vs peers")
        else:
            sig = ""

        vm_content = _card("Valuation Multiples", _data_rows(vm_rows) + sig,
            "Lecture 5B: Relative valuation compares multiples to sector peers.")

    # WACC
    wacc_d = booth.get("wacc", {}) or {}
    wacc_content = ""
    if wacc_d and "error" not in wacc_d:
        w = wacc_d.get("wacc")
        ke = wacc_d.get("cost_of_equity")
        kd = wacc_d.get("cost_of_debt")
        ew = wacc_d.get("equity_weight")
        dw = wacc_d.get("debt_weight")
        beta = wacc_d.get("beta")
        tax = wacc_d.get("tax_rate")

        wacc_content = _card("WACC", _data_rows([
            ("Beta (\u03b2)", f"{beta:.3f}" if beta is not None else "N/A"),
            ("Cost of Equity (rE)", _pct_safe(ke)),
            ("Tax Rate", _pct_safe(tax)),
            ("E / (E+D)", _pct_safe(ew)),
            ("D / (E+D)", _pct_safe(dw)),
            ("WACC", _pct_safe(w)),
        ]), "Lecture 4B: WACC = (E/V)Ke + (D/V)Kd(1-T). Discount rate for firm valuation.")

    # Free Cash Flow
    fcf_d = booth.get("free_cash_flow", {}) or {}
    fcf_content = ""
    if fcf_d:
        fcf = fcf_d.get("free_cash_flow")
        ocf = fcf_d.get("operating_cash_flow")
        rev = fcf_d.get("revenue")
        fy = fcf_d.get("fcf_yield_pct")
        fm = fcf_d.get("fcf_margin_pct")
        mkt_cap_fcf = fcf_d.get("market_cap") or (booth.get("wacc", {}) or {}).get("market_cap")

        p_fcf = None
        if fcf and fcf > 0 and mkt_cap_fcf:
            try:
                p_fcf = float(mkt_cap_fcf) / float(fcf)
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        strong_cash = fy is not None and fy > 4
        sig_text = "strong cash generator" if strong_cash else "weak cash generation"
        sig = _signal(strong_cash, sig_text) if fy is not None else ""

        fcf_content = _card("Free Cash Flow", _data_rows([
            ("Operating CF", _fmt(ocf, "currency")),
            ("Free Cash Flow", _fmt(fcf, "currency")),
            ("FCF Yield", f"{fy:.2f}%" if fy is not None else "N/A"),
            ("FCF Margin", f"{fm:.2f}%" if fm is not None else "N/A"),
            ("P / FCF", f"{p_fcf:.2f}x" if p_fcf is not None else "N/A"),
        ]) + sig, "FCF = Operating CF \u2212 CapEx | FCF Yield > 4% = strong cash generator")

    # DCF 3-Stage
    dcf_d = booth.get("dcf_model", {}) or {}
    dcf_content = ""
    if dcf_d and "error" not in dcf_d:
        iv = dcf_d.get("intrinsic_value_per_share")
        cp = dcf_d.get("current_price")
        upside = dcf_d.get("upside_pct")
        w = dcf_d.get("wacc")
        ntg = dcf_d.get("near_term_growth")
        fg = dcf_d.get("fade_growth")
        tg = dcf_d.get("terminal_growth")
        base_fcf = dcf_d.get("base_fcf")

        positive_dcf = upside is not None and upside > 0
        sig = _signal(positive_dcf, "potentially undervalued" if positive_dcf else "potentially overvalued") if upside is not None else ""

        mos = None
        if iv is not None and cp is not None and iv != 0:
            try:
                mos = (float(iv) - float(cp)) / float(iv) * 100
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        mig = tg

        sens = dcf_d.get("sensitivity", {})
        sens_html = ""
        if sens:
            sens_html = '<div style="margin-top:8pt;"><div style="font-size:8pt; color:#53565A; margin-bottom:4pt; text-transform:uppercase; letter-spacing:0.5pt;">Sensitivity Grid (WACC vs Growth)</div>'
            sens_html += '<table style="width:100%; border-collapse:collapse; font-size:7.5pt;">'

            if isinstance(list(sens.values())[0], dict):
                g_keys = sorted(sens.keys())
                first_g = g_keys[0]
                w_keys = sorted(sens[first_g].keys()) if isinstance(sens[first_g], dict) else []

                sens_html += f'<tr><td style="padding:3pt; background:#f8fafc; border:1px solid {BORDER_COLOR}; font-weight:600;">g \\ WACC</td>'
                for wk in w_keys:
                    sens_html += f'<td style="padding:3pt; background:#f8fafc; border:1px solid {BORDER_COLOR}; text-align:center; font-weight:600;">WACC {wk}</td>'
                sens_html += '</tr>'
                for gk in g_keys:
                    sens_html += f'<tr><td style="padding:3pt; background:#f8fafc; border:1px solid {BORDER_COLOR}; font-weight:600;">g {gk}</td>'
                    for wk in w_keys:
                        v = sens[gk].get(wk, "N/A") if isinstance(sens[gk], dict) else "N/A"
                        cell_val = f"${v:,.0f}" if isinstance(v, (int, float)) else str(v)
                        sens_html += f'<td style="padding:3pt; border:1px solid {BORDER_COLOR}; text-align:center;">{cell_val}</td>'
                    sens_html += '</tr>'
            else:
                import re as _re
                grid = {}
                w_set = set()
                g_set = set()
                for k, v in sens.items():
                    m = _re.match(r'WACC=([\d.]+)%,g=([\d.]+)%', str(k))
                    if m:
                        wk, gk = m.group(1), m.group(2)
                        w_set.add(wk)
                        g_set.add(gk)
                        grid[(gk, wk)] = v
                if grid:
                    w_keys = sorted(w_set, key=lambda x: float(x))
                    g_keys = sorted(g_set, key=lambda x: float(x))
                    sens_html += f'<tr><td style="padding:3pt; background:#f8fafc; border:1px solid {BORDER_COLOR}; font-weight:600;">g \\ WACC</td>'
                    for wk in w_keys:
                        sens_html += f'<td style="padding:3pt; background:#f8fafc; border:1px solid {BORDER_COLOR}; text-align:center; font-weight:600;">WACC {wk}%</td>'
                    sens_html += '</tr>'
                    for gk in g_keys:
                        sens_html += f'<tr><td style="padding:3pt; background:#f8fafc; border:1px solid {BORDER_COLOR}; font-weight:600;">g {gk}%</td>'
                        for wk in w_keys:
                            v = grid.get((gk, wk), "N/A")
                            cell_val = f"${v:,.0f}" if isinstance(v, (int, float)) else str(v)
                            sens_html += f'<td style="padding:3pt; border:1px solid {BORDER_COLOR}; text-align:center;">{cell_val}</td>'
                        sens_html += '</tr>'
                else:
                    for k, v in sens.items():
                        cell_val = f"${v:,.0f}" if isinstance(v, (int, float)) else str(v)
                        sens_html += f'<tr><td style="padding:3pt; border:1px solid {BORDER_COLOR};">{k}</td><td style="padding:3pt; border:1px solid {BORDER_COLOR}; text-align:center;">{cell_val}</td></tr>'

            sens_html += '</table></div>'

        dcf_content = _card("DCF 3-Stage Model", _data_rows([
            ("Intrinsic Value / Share", _fmt(iv, "price")),
            ("Current Price", _fmt(cp, "price")),
            ("Upside / Downside", f"{upside:+.1f}%" if upside is not None else "N/A"),
            ("Trailing FCF", _fmt(base_fcf, "currency")),
            ("Margin of Safety", f"{mos:.1f}%" if mos is not None else "N/A"),
            ("Market-Implied Growth", _pct_safe(mig)),
            ("WACC", _pct_safe(w)),
            ("Near-Term Growth", _pct_safe(ntg)),
            ("Fade Growth", _pct_safe(fg)),
            ("Terminal Growth", _pct_safe(tg)),
        ]) + sig + sens_html, "Lecture 5B: 3-stage DCF with near-term, fade, and terminal growth assumptions.")

    # --- FS Cards ---

    # Capital Structure card
    cs_data = fs.get("capital_structure", {}) or {}
    cs_content = ""
    if cs_data:
        nd = cs_data.get("net_debt")
        nd_cap = cs_data.get("net_debt_to_capital")
        nd_ebitda = cs_data.get("net_debt_to_ebitda")
        fcf_debt = cs_data.get("fcf_to_debt")
        de = cs_data.get("debt_to_equity_pct")

        positive_cs = nd_cap is not None and nd_cap < 0.4
        sig_text = "Conservative Leverage" if positive_cs else "Elevated Leverage"
        sig = _signal(positive_cs, sig_text) if nd_cap is not None else ""

        cs_content = _card("Capital Structure", _data_rows([
            ("Total Debt", _fmt(cs_data.get("total_debt"), "currency")),
            ("Total Cash", _fmt(cs_data.get("total_cash"), "currency")),
            ("Net Debt", _fmt(nd, "currency")),
            ("Net Debt / Capital", f"{nd_cap*100:.1f}%" if nd_cap is not None else "N/A"),
            ("Net Debt / EBITDA", f"{nd_ebitda:.2f}x" if nd_ebitda is not None else "N/A"),
            ("FCF / Debt", f"{fcf_debt:.2f}x" if fcf_debt is not None else "N/A"),
            ("Debt / Equity", f"{de:.1f}%" if de is not None else "N/A"),
        ]) + sig, "D1: Optimal capital structure balances tax shield benefits against distress costs.")
    else:
        cs_content = _card("Capital Structure", '<div style="font-size:9pt; color:#53565A;">Data not available.</div>', "")

    # Credit Rating
    cr_d = fs.get("credit_rating", {}) or {}
    cr_content = ""
    if cr_d:
        rating = cr_d.get("implied_rating", "N/A")
        score = cr_d.get("composite_score", "N/A")
        spread = cr_d.get("credit_spread_bps")
        nf = cr_d.get("num_factors")
        ebit_int = cr_d.get("ebit_to_interest")
        ebitda_int = cr_d.get("ebitda_to_interest")

        ig_ratings = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"]
        is_ig = rating in ig_ratings
        grade_badge = (f'<div style="display:inline-block; background:{GREEN_BG}; color:{GREEN}; '
                       f'border:1px solid {GREEN}; border-radius:4px; padding:2pt 8pt; '
                       f'font-size:8pt; font-weight:600;">Investment Grade</div>'
                       if is_ig else
                       f'<div style="display:inline-block; background:{RED_BG}; color:{RED}; '
                       f'border:1px solid {RED}; border-radius:4px; padding:2pt 8pt; '
                       f'font-size:8pt; font-weight:600;">Speculative Grade</div>')

        def _default_prob(r):
            if r in ("AAA", "AA+", "AA", "AA-", "A+", "A", "A-"):
                return "0.0%"
            elif r in ("BBB+", "BBB", "BBB-"):
                return "0.1%"
            elif r in ("BB+", "BB", "BB-"):
                return "0.5%"
            elif r in ("B+", "B", "B-"):
                return "2.0%"
            elif r in ("CCC+", "CCC", "CCC-", "CC", "C"):
                return "10.0%"
            return "N/A"

        cr_content = _card("Implied Credit Rating",
            f'<div style="text-align:center; margin:8pt 0;">'
            f'<div style="font-size:28pt; font-weight:700; color:{DARK_TEXT};">{rating}</div>'
            f'{grade_badge}</div>' +
            _data_rows([
                ("Composite Score", f"{score} / 8" if score != "N/A" else "N/A"),
                ("Credit Spread", f"{spread} bps" if spread is not None else "N/A"),
                ("Factors Assessed", str(nf) if nf else "N/A"),
                ("EBIT / Interest", f"{ebit_int:.2f}x" if ebit_int is not None else "N/A"),
                ("EBITDA / Interest", f"{ebitda_int:.2f}x" if ebitda_int is not None else "N/A"),
                ("Default Prob. (ann.)", _default_prob(rating)),
            ]),
            "D1: Implied rating based on financial ratio scoring mapped to S&P rating scale.")

    # Static Trade-Off
    sto_d = fs.get("static_tradeoff", {}) or {}
    sto_content = ""
    if sto_d:
        pvts = sto_d.get("pv_tax_shield")
        pvdb = sto_d.get("pv_discipline_benefit")
        pvdc = sto_d.get("pv_distress_cost")
        nb = sto_d.get("net_benefit_of_debt")
        lr = sto_d.get("leverage_ratio")
        ic = sto_d.get("interest_coverage")
        assess = sto_d.get("assessment", "")

        cs_mkt = (fs.get("capital_structure", {}) or {}).get("market_cap") or (fs.get("payout_policy", {}) or {}).get("market_cap") or 1

        try:
            mkt_f = float(cs_mkt) if cs_mkt else 1
        except (ValueError, TypeError):
            mkt_f = 1

        ts_score = 2 if pvts and float(pvts) > mkt_f * 0.05 else (1 if pvts and float(pvts) > 0 else 0)
        disc_score = 2 if pvdb and float(pvdb) > 0 else 0
        dist_score = -4 if pvdc and float(pvdc) > mkt_f * 0.1 else (-2 if pvdc and float(pvdc) > mkt_f * 0.03 else 0)
        net_score = ts_score + disc_score + dist_score

        ts_explain = "insufficient data" if not pvts or float(pvts) == 0 else f"tax shield = {_fmt(pvts, 'currency')}"
        disc_explain = "insufficient data" if not pvdb or float(pvdb) == 0 else f"discipline benefit = {_fmt(pvdb, 'currency')}"
        dist_explain = "insufficient data" if not pvdc or float(pvdc) == 0 else f"distress cost = {_fmt(pvdc, 'currency')}"

        positive_net = net_score > 0
        sig_text = "lean toward debt" if positive_net else "lean toward equity \u2014 distress costs are real"
        sig = _signal(positive_net, sig_text)

        sto_content = _card("Static Trade-Off", _data_rows([
            ("PV(Tax Shield)", f"+{ts_score} / 2"),
            ("PV(Discipline)", f"+{disc_score} / 2"),
            ("PV(Distress Cost)", f"{dist_score} / -4"),
        ]) +
        f'<div style="font-size:7.5pt; color:{GREY}; margin:2pt 0;">{ts_explain}</div>'
        f'<div style="font-size:7.5pt; color:{GREY}; margin:2pt 0;">{disc_explain}</div>'
        f'<div style="font-size:7.5pt; color:{GREY}; margin:2pt 0;">{dist_explain}</div>'
        f'<div style="text-align:center; margin:8pt 0;">'
        f'<div style="font-size:28pt; font-weight:700; color:{DARK_TEXT};">{net_score:+d}</div>'
        f'<div style="font-size:8pt; color:{GREY};">Net Score</div></div>'
        + sig,
        "V_L = V_U + PV(TS) + PV(Discipline) \u2212 PV(Distress)")

    # Payout & Cash Policy
    pp_d = fs.get("payout_policy", {}) or {}
    pp_content = ""
    if pp_d:
        excess = pp_d.get("excess_cash")
        dy = pp_d.get("dividend_yield")
        pr = pp_d.get("payout_ratio")
        fcf_pp = pp_d.get("fcf")
        cash_pct = pp_d.get("cash_as_pct_of_mktcap")
        assess = pp_d.get("assessment", "")
        td = pp_d.get("tax_drag_annual")
        total_cash_pp = pp_d.get("total_cash")
        mkt_cap_pp = pp_d.get("market_cap")
        revenue_pp = pp_d.get("revenue")
        net_debt_pp = pp_d.get("net_debt")

        cash_rev = None
        if total_cash_pp and revenue_pp:
            try:
                cash_rev = float(total_cash_pp) / float(revenue_pp) * 100
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        net_cash_str = "N/A"
        if net_debt_pp is not None:
            net_cash_str = "yes (net cash)" if float(net_debt_pp) < 0 else "no (net debt)"

        td_mkt = None
        if td and mkt_cap_pp:
            try:
                td_mkt = float(td) / float(mkt_cap_pp) * 100
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        if excess is not None and float(excess) > 0 and (dy is None or dy < 0.02):
            sig = _signal_amber("excess cash with minimal payout")
        else:
            positive_pp = excess is not None and float(excess) > 0
            sig = _signal(positive_pp, assess if assess else ("Healthy Payout" if positive_pp else "Cash Constrained"))

        pp_content = _card("Payout & Cash Policy", _data_rows([
            ("Cash & Liquids", _fmt(total_cash_pp, "currency")),
            ("Cash / Revenue", f"{cash_rev:.1f}%" if cash_rev is not None else "N/A"),
            ("Cash / Mkt Cap", f"{cash_pct:.1f}%" if cash_pct is not None else "N/A"),
            ("Net Cash?", net_cash_str),
            ("Estimated Excess Cash", _fmt(excess, "currency")),
            ("Annual Tax Drag", _fmt(td, "currency")),
            ("Tax Drag / Mkt Cap", f"{td_mkt:.2f}%" if td_mkt is not None else "N/A"),
            ("Dividend Yield", f"{dy:.2f}%" if dy is not None else "N/A"),
        ]) + sig, "D4 FANUC insight: $1 held in corp earns after-tax (1-\u03c4) \u2014 excess cash is a negative tax shield. Optimal: hold only operating cash + buffer; return rest via buyback/dividend.")

    # Altman Z-Score
    az_d = fs.get("altman_z", {}) or {}
    az_content = ""
    if az_d and "error" not in az_d:
        z = az_d.get("z_score")
        zone = az_d.get("zone", "N/A")
        x1 = az_d.get("wc_ta")
        x2 = az_d.get("re_ta")
        x3 = az_d.get("ebit_ta")
        x4 = az_d.get("mktcap_liab")
        x5 = az_d.get("rev_ta")

        zone_color = GREEN if zone and "safe" in zone.lower() else (RED if zone and "distress" in zone.lower() else AMBER)
        zone_bg = GREEN_BG if zone and "safe" in zone.lower() else (RED_BG if zone and "distress" in zone.lower() else AMBER_BG)

        az_content = _card("Altman Z-Score",
            f'<div style="text-align:center; margin:8pt 0;">'
            f'<div style="font-size:28pt; font-weight:700; color:{DARK_TEXT};">{z:.2f}</div>'
            f'<div style="display:inline-block; background:{zone_bg}; color:{zone_color}; '
            f'border:1px solid {zone_color}; border-radius:4px; padding:2pt 8pt; '
            f'font-size:8pt; font-weight:600;">{zone}</div></div>' +
            _data_rows([
                ("X1: WC/TA", f"{x1:.4f}" if x1 is not None else "N/A"),
                ("X2: RE/TA", f"{x2:.4f}" if x2 is not None else "N/A"),
                ("X3: EBIT/TA", f"{x3:.4f}" if x3 is not None else "N/A"),
                ("X4: MktCap/Liab", f"{x4:.4f}" if x4 is not None else "N/A"),
                ("X5: Rev/TA", f"{x5:.4f}" if x5 is not None else "N/A"),
            ]),
            "Z = 1.2X1 + 1.4X2 + 3.3X3 + 0.6X4 + 1.0X5. Safe > 2.99, Grey 1.81-2.99, Distress < 1.81.")

    # Pecking Order
    po_d = fs.get("pecking_order", {}) or {}
    po_content = ""
    if po_d:
        fcf_po = po_d.get("free_cash_flow")
        capex = po_d.get("capex")
        fcf_cap = po_d.get("fcf_minus_capex")
        internal = po_d.get("internal_funding_sufficient")
        pr_po = po_d.get("payout_ratio")
        re = po_d.get("retained_earnings")
        re_eq = po_d.get("re_to_equity")
        dl = po_d.get("debt_level")
        dm = po_d.get("debt_to_mktcap")
        stage = po_d.get("pecking_order_stage", "N/A")

        cs_nd_ebitda = (fs.get("capital_structure", {}) or {}).get("net_debt_to_ebitda")
        debt_level_display = f"{cs_nd_ebitda:.1f}x EBITDA" if cs_nd_ebitda is not None else (dl if dl else "N/A")

        ptb_po = po_d.get("price_to_book")

        po_score = 0
        if fcf_po is not None and capex is not None and float(fcf_po) > abs(float(capex)):
            po_score += 1
        if pr_po is not None and pr_po < 50:
            po_score += 1
        if dl and dl.lower() in ("low", "moderate"):
            po_score += 1
        if internal:
            po_score += 1

        sig = _signal(internal, "Internal Funding Sufficient" if internal else "External Funding Needed") if internal is not None else ""

        po_content = _card("Pecking Order (Myers-Majluf)", _data_rows([
            ("Score", f"{po_score}/4"),
            ("FCF vs CapEx", f"FCF {_fmt(fcf_po, 'currency')} vs CapEx {_fmt(capex, 'currency')}"),
            ("Payout Ratio", f"{pr_po:.1f}%" if pr_po is not None else "N/A"),
            ("Retained Earnings / Equity", f"{re_eq:.2f}x" if re_eq is not None else "N/A"),
            ("Debt Level", debt_level_display),
            ("Price / Book", f"{ptb_po:.2f}x" if ptb_po is not None else "N/A"),
        ]) + sig, "Myers-Majluf: Firms prefer internal funds > debt > equity due to information asymmetry.")

    # Assemble CF and FS card columns
    cf_cards = capm_content + vm_content + wacc_content + fcf_content + dcf_content
    fs_cards = cs_content + cr_content + sto_content + pp_content + az_content + po_content

    return f"""
    <div>
      {_page_header(ticker)}

      <!-- Investment Thesis -->
      {_narrative_card("Investment Thesis &middot; Powered by Elitez-CB Analysis", thesis)}

      <!-- Company Info -->
      <div style="border:1px solid {BORDER_COLOR}; border-radius:3px; padding:10pt 14pt; margin:10pt 0; page-break-inside:avoid;">
        <div style="font-size:14pt; font-weight:700;">{ticker}</div>
        <div style="font-size:10pt; color:#475569;">{name}</div>
        <div style="margin:4pt 0;">
          <span style="{pill_style}">{sector}</span>
          <span style="{pill_style}">{industry}</span>
        </div>
        <div style="font-size:8pt; color:{GREY}; margin-top:2pt;">
          Price: {_fmt(price, "price")} &middot; Market Cap: {_fmt(mkt_cap, "currency")}
        </div>
        <div style="font-size:8pt; color:#475569; margin-top:4pt; line-height:1.4;">{desc_short}</div>
      </div>

      <!-- CF|FS: bars + cards in single table for perfect alignment -->
      <table width="100%" style="border-collapse:collapse;">
        <tr>
          <td width="50%" valign="top" style="padding:0 6pt 0 0;">
            {_section_bar("CB Corporate Finance")}
          </td>
          <td width="50%" valign="top" style="padding:0 0 0 6pt;">
            {_section_bar("CB Financial Strategy")}
          </td>
        </tr>
        <tr>
          <td width="50%" valign="top" style="padding:0 6pt 0 0;">
            {cf_cards}
          </td>
          <td width="50%" valign="top" style="padding:0 0 0 6pt;">
            {fs_cards}
          </td>
        </tr>
      </table>

      <!-- CF+FS Thesis narrative - full width -->
      {_narrative_card("CF + FS Investment Thesis &middot; Powered by Elitez-CB Analysis", thesis)}
    </div>
    """


# ---------------------------------------------------------------------------
# Operations Management content: cards + narrative together (no forced break)
# ---------------------------------------------------------------------------

def _build_om_content(ticker: str, om: dict, om_narrative: str) -> str:
    # Supply Chain
    sc = om.get("supply_chain", {}) or {}
    sc_content = ""
    if sc:
        ccc = sc.get("cash_conversion_cycle")
        dio = sc.get("dio_days")
        dso = sc.get("dso_days")
        dpo = sc.get("dpo_days")
        it = sc.get("inventory_turnover")
        assess = sc.get("assessment", "")

        positive = ccc is not None and ccc < 60
        sig = _signal(positive, assess if assess else ("Efficient Cycle" if positive else "Extended Cycle")) if ccc is not None else ""

        sc_content = _card("SUPPLY CHAIN EFFICIENCY &middot; S1/S6/S7", _data_rows([
            ("Cash Conversion Cycle", f"{ccc:.1f} days" if ccc is not None else "N/A"),
            ("DIO (Days Inventory)", f"{dio:.1f} days" if dio is not None else "N/A"),
            ("DSO (Days Sales)", f"{dso:.1f} days" if dso is not None else "N/A"),
            ("DPO (Days Payable)", f"{dpo:.1f} days" if dpo is not None else "N/A"),
            ("Inventory Turnover", f"{it:.2f}x" if it is not None else "N/A"),
        ]) + sig, "S1/S6/S7: CCC = DIO + DSO - DPO. Lower CCC indicates more efficient working capital management.")

    # Process Quality
    pq = om.get("process_quality", {}) or {}
    pq_content = ""
    if pq:
        gm = pq.get("gross_margin")
        opm = pq.get("operating_margin")
        ogap = pq.get("overhead_gap_pct")
        roa = pq.get("roa")
        gm_trend = pq.get("gross_margin_trend")
        wc = pq.get("working_capital")
        wc_rev = pq.get("wc_to_revenue")
        assess = pq.get("assessment", "")

        positive = gm is not None and gm > 30
        sig = _signal(positive, assess if assess else ("Strong Margins" if positive else "Thin Margins")) if gm is not None else ""

        pq_content = _card("PROCESS QUALITY &amp; LEAN &middot; S5 (TQM/TPS)", _data_rows([
            ("Gross Margin", f"{gm:.2f}%" if gm is not None else "N/A"),
            ("Operating Margin", f"{opm:.2f}%" if opm is not None else "N/A"),
            ("Overhead Gap", f"{ogap:.2f}%" if ogap is not None else "N/A"),
            ("ROA", f"{roa:.2f}%" if roa is not None else "N/A"),
            ("Gross Margin Trend", gm_trend if gm_trend else "N/A"),
            ("Working Capital", _fmt(wc, "currency")),
            ("WC / Revenue", f"{wc_rev:.2f}%" if wc_rev is not None else "N/A"),
        ]) + sig, "S5: Lean operations minimize waste. Overhead gap = Gross Margin - Operating Margin.")

    # Operational Throughput
    ot = om.get("operational_throughput", {}) or {}
    ot_content = ""
    if ot:
        rev = ot.get("revenue")
        rg = ot.get("revenue_growth")
        fa = ot.get("fixed_assets")
        fat = ot.get("fixed_asset_turnover")
        cx = ot.get("capex_current")
        cxg = ot.get("capex_growth")
        assess = ot.get("assessment", "")

        positive = fat is not None and fat > 2
        sig = _signal(positive, assess if assess else ("High Throughput" if positive else "Low Throughput")) if fat is not None else ""

        ot_content = _card("OPERATIONAL THROUGHPUT &middot; S2/S4", _data_rows([
            ("Revenue", _fmt(rev, "currency")),
            ("Revenue Growth", _pct_safe(rg)),
            ("Fixed Assets", _fmt(fa, "currency")),
            ("Fixed Asset Turnover", f"{fat:.2f}x" if fat is not None else "N/A"),
            ("CapEx", _fmt(cx, "currency")),
            ("CapEx Growth", _pct_safe(cxg)),
        ]) + sig, "S2/S4: Fixed asset turnover measures revenue generated per dollar of fixed assets (bottleneck theory).")

    # Demand Variability
    dv = om.get("demand_variability", {}) or {}
    dv_content = ""
    if dv:
        rcv = dv.get("revenue_cv")
        ig = dv.get("inventory_growth")
        rg = dv.get("revenue_growth")
        bw = dv.get("bullwhip_ratio")
        assess = dv.get("assessment", "")

        positive = bw is not None and bw < 1.5
        if bw is not None:
            sig = _signal(positive, assess if assess else ("Low Variability" if positive else "High Variability"))
        else:
            sig = ""

        dv_content = _card("DEMAND VARIABILITY &amp; BULLWHIP &middot; S7/S8", _data_rows([
            ("Revenue CV", f"{rcv:.4f}" if rcv is not None else "N/A"),
            ("Inventory Growth", _pct_safe(ig)),
            ("Revenue Growth", _pct_safe(rg)),
            ("Bullwhip Ratio", f"{bw:.2f}x" if bw is not None else "N/A"),
        ]) + sig, "S7/S8: Bullwhip effect amplifies demand signal variance up the supply chain. Ratio > 1 indicates amplification.")

    return f"""
    <div style="page-break-before:always;">
      {_page_header(ticker)}
      {_section_bar("CB Operations Management")}
      <table width="100%"><tr>
        <td width="50%" valign="top" style="padding-right:6pt;">
          {sc_content}
          {pq_content}
        </td>
        <td width="50%" valign="top" style="padding-left:6pt;">
          {ot_content}
          {dv_content}
        </td>
      </tr></table>

      <!-- OM Narrative flows right after cards -->
      {_narrative_card("OM Narrative &middot; Powered by Elitez-CB Analysis", om_narrative)}
    </div>
    """


# ---------------------------------------------------------------------------
# Competitive Strategy content: cards + narrative together (no forced break)
# ---------------------------------------------------------------------------

def _build_cs_content(ticker: str, cs: dict, cs_narrative: str) -> str:
    # Competitive Moat
    moat = cs.get("competitive_moat", {}) or {}
    moat_content = ""
    if moat:
        scores = moat.get("scores", {})
        total = moat.get("total_score", 0)
        avg = moat.get("average_score", 0)
        width = moat.get("moat_width", "N/A")
        gm = moat.get("gross_margin")
        om = moat.get("operating_margin")
        rd = moat.get("rd_intensity_pct")
        roe = moat.get("roe")
        roa = moat.get("roa")

        score_rows = []
        for dim, val in scores.items():
            dim_label = dim.replace("_", " ").title()
            score_rows.append((dim_label, f"{val} / 2"))

        moat_content = _card("COMPETITIVE MOAT &middot; SESSION 2/6",
            f'<div style="text-align:center; margin:6pt 0;">'
            f'<div style="font-size:24pt; font-weight:700; color:{DARK_TEXT};">{total} / 10</div>'
            f'<div style="font-size:9pt; color:{GREY};">Moat Width: {width}</div></div>' +
            _data_rows(score_rows + [
                ("Gross Margin", f"{gm:.2f}%" if gm is not None else "N/A"),
                ("Operating Margin", f"{om:.2f}%" if om is not None else "N/A"),
                ("R&D Intensity", f"{rd:.2f}%" if rd is not None else "N/A"),
                ("ROE", f"{roe:.2f}%" if roe is not None else "N/A"),
                ("ROA", f"{roa:.2f}%" if roa is not None else "N/A"),
            ]),
            "Session 2/6: Moat width from brand, switching costs, network effects, cost advantage, and intangibles.")

    # Disruption Risk
    dr = cs.get("disruption_risk", {}) or {}
    dr_content = ""
    if dr:
        score = dr.get("disruption_risk_score", 0)
        level = dr.get("risk_level", "N/A")
        inno = dr.get("innovation_type", "N/A")
        rd_pct = dr.get("rd_intensity_pct")
        rg = dr.get("revenue_growth")
        gm_trend = dr.get("gross_margin_trend")
        gm_hist = dr.get("gross_margin_history")

        level_color = GREEN if level and level.upper() == "LOW" else (RED if level and level.upper() == "HIGH" else AMBER)

        dr_content = _card("DISRUPTION RISK &middot; SESSION 7",
            f'<div style="text-align:center; margin:6pt 0;">'
            f'<div style="font-size:22pt; font-weight:700; color:{level_color};">{level.upper() if level else "N/A"}</div>'
            f'<div style="font-size:9pt; color:{GREY};">Score: {score}/10</div></div>' +
            _data_rows([
                ("Innovation Type", inno),
                ("R&D Intensity", f"{rd_pct:.2f}%" if rd_pct is not None else "N/A"),
                ("Revenue Growth", _pct_safe(rg)),
                ("GM Trend", gm_trend if gm_trend else "N/A"),
            ]),
            "Session 7: Henderson & Clark framework. Assesses vulnerability to architectural and radical innovation.")

    # Market Position
    mp = cs.get("market_position", {}) or {}
    mp_content = ""
    if mp:
        position = mp.get("market_position", "N/A")
        detail = mp.get("position_detail", "")
        tier = mp.get("cap_tier", "N/A")
        mc = mp.get("market_cap")
        gm_pct = mp.get("gross_margin_pct")
        om_pct = mp.get("operating_margin_pct")
        rg_pct = mp.get("revenue_growth_pct")
        ptb = mp.get("price_to_book")
        beta = mp.get("beta")
        roe_pct = mp.get("roe_pct")
        risk = mp.get("risk_profile", "N/A")

        mp_content = _card("MARKET POSITION &middot; SESSION 2/3",
            f'<div style="text-align:center; margin:6pt 0;">'
            f'<div style="display:inline-block; background:{MAROON_LIGHT}; color:{MAROON}; '
            f'border:1px solid {MAROON}; border-radius:4px; padding:3pt 12pt; '
            f'font-size:10pt; font-weight:700;">{position}</div></div>' +
            _data_rows([
                ("Position Detail", detail if detail else "N/A"),
                ("Cap Tier", tier),
                ("Market Cap", _fmt(mc, "currency")),
                ("Gross Margin", f"{gm_pct:.2f}%" if gm_pct is not None else "N/A"),
                ("Operating Margin", f"{om_pct:.2f}%" if om_pct is not None else "N/A"),
                ("Revenue Growth", f"{rg_pct:.2f}%" if rg_pct is not None else "N/A"),
                ("Price / Book", f"{ptb:.2f}x" if ptb is not None else "N/A"),
                ("Beta", f"{beta:.3f}" if beta is not None else "N/A"),
                ("ROE", f"{roe_pct:.2f}%" if roe_pct is not None else "N/A"),
                ("Risk Profile", risk),
            ]),
            "Session 2: Market positioning analysis based on Porter's generic strategies and competitive dynamics.")

    return f"""
    <div style="page-break-before:always;">
      {_page_header(ticker)}
      {_section_bar("CB Competitive Strategy")}
      <table width="100%"><tr>
        <td width="33%" valign="top" style="padding-right:4pt;">
          {moat_content}
        </td>
        <td width="33%" valign="top" style="padding:0 4pt;">
          {dr_content}
        </td>
        <td width="33%" valign="top" style="padding-left:4pt;">
          {mp_content}
        </td>
      </tr></table>

      <!-- CS Narrative flows right after cards -->
      {_narrative_card("Competitive Strategy Narrative &middot; Powered by Elitez-CB Analysis", cs_narrative)}
    </div>
    """


# ---------------------------------------------------------------------------
# Disclaimers
# ---------------------------------------------------------------------------

def _build_disclaimers(ticker: str, today_str: str) -> str:
    return f"""
    <div style="page-break-inside:avoid; page-break-after:avoid;">
      {_page_header(ticker)}
      {_section_bar("Important Disclosures & Disclaimer")}

      <div style="font-size:9pt; color:{GREY}; line-height:1.7;">
        <div style="margin-bottom:12pt;">
          <div style="font-weight:700; color:{DARK_TEXT}; margin-bottom:4pt;">Not Investment Advice</div>
          <div>This report has been prepared by Elitez Asia's Analytics solely for informational and educational purposes. Nothing contained in this report constitutes investment advice, a solicitation, an offer to buy or sell any security, or a recommendation of any investment strategy. The analysis and opinions expressed herein are based on publicly available financial data and do not represent the views of any regulated financial institution or licensed investment adviser.</div>
        </div>

        <div style="margin-bottom:12pt;">
          <div style="font-weight:700; color:{DARK_TEXT}; margin-bottom:4pt;">Data Sources &amp; Limitations</div>
          <div>Financial data is sourced from public filings (SEC/EDGAR), market data providers, and news sources via automated data feeds. While reasonable care has been taken to ensure accuracy, Elitez Asia's Analytics makes no warranty, express or implied, as to the completeness, timeliness, or accuracy of any data. Market data reflects conditions as at the report date ({today_str}) and may have changed materially since publication. Operations Management metrics (e.g. OEE, Cpk, actual queue lengths) are estimated from public financial statements and are not directly observed internal metrics.</div>
        </div>

        <div style="margin-bottom:12pt;">
          <div style="font-weight:700; color:{DARK_TEXT}; margin-bottom:4pt;">AI-Generated Content</div>
          <div>Portions of this report (Investment Thesis and OM Narrative sections) are generated using AI models based on structured financial data and publicly available news. AI-generated content is provided as a starting point for analysis and should be independently verified. It does not constitute professional financial advice.</div>
        </div>

        <div style="margin-bottom:12pt;">
          <div style="font-weight:700; color:{DARK_TEXT}; margin-bottom:4pt;">Analytical Frameworks</div>
          <div>Valuation and financial strategy frameworks referenced in this report are derived from publicly available academic and practitioner literature, including the University of Chicago Booth School of Business course materials. Altman Z-Score was developed for manufacturing firms; results for financial services, technology, and asset-light businesses should be interpreted with caution.</div>
        </div>

        <div style="margin-bottom:12pt;">
          <div style="font-weight:700; color:{DARK_TEXT}; margin-bottom:4pt;">No Liability</div>
          <div>Elitez Asia's Analytics, its affiliates, and contributors accept no liability for any loss or damage arising from the use of, or reliance on, information in this report. Past performance of any security referenced herein is not a reliable indicator of future results. All investments carry risk, including the possible loss of principal.</div>
        </div>
      </div>

      <!-- Footer band -->
      <div style="margin-top:30pt; border-top:2px solid {MAROON}; padding-top:12pt;">
        <table width="100%"><tr>
          <td style="vertical-align:top;">
            <div>
              <img src="data:image/png;base64,{_LOGO_B64_SM}" height="20" style="vertical-align:middle;" />
              <span style="font-size:9pt; font-weight:700; color:{MAROON}; margin-left:8pt;
                           vertical-align:middle;">ELITEZ ASIA'S ANALYTICS</span>
            </div>
            <div style="font-size:8pt; color:{GREY}; margin-top:4pt;">
              elitez-market.streamlit.app &middot; Powered by Elitez-CB Analysis
            </div>
          </td>
          <td style="text-align:right; vertical-align:top;">
            <div style="font-size:8pt; color:{GREY};">Report generated: {today_str}</div>
            <div style="font-size:8pt; color:{GREY};">Ticker: {ticker}</div>
            <div style="font-size:8pt; color:{GREY};">&copy; 2026 Elitez Asia's Analytics. All rights reserved.</div>
          </td>
        </tr></table>
      </div>

      <!-- Dark maroon band (reduced from 80pt to 8pt to avoid empty last page) -->
      <div style="background:{MAROON}; height:8pt; margin-top:12pt;"></div>
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
    today_str = datetime.now().strftime("%d %b %Y")

    css = f"""
    @page {{
        size: A4;
        margin: 1.5cm 1.5cm 2cm 1.5cm;
        @bottom-left {{
            content: "Elitez Asia's Analytics | {today_str}";
            font-size: 7.5pt;
            color: {GREY};
            font-family: Helvetica, Arial, sans-serif;
        }}
        @bottom-right {{
            content: counter(page) " / " counter(pages);
            font-size: 7.5pt;
            color: {GREY};
            font-family: Helvetica, Arial, sans-serif;
        }}
    }}
    @page :first {{
        margin-top: 0;
        @bottom-left {{ content: none; }}
        @bottom-right {{ content: none; }}
    }}
    * {{
        box-sizing: border-box;
    }}
    body {{
        font-family: Helvetica, Arial, sans-serif;
        font-size: 9.5pt;
        line-height: 1.5;
        color: {DARK_TEXT};
        margin: 0;
        padding: 0;
    }}
    h2, h3, h4 {{
        color: {MAROON};
        margin-top: 10pt;
        margin-bottom: 4pt;
    }}
    h2 {{ font-size: 13pt; }}
    h3 {{ font-size: 11pt; }}
    h4 {{ font-size: 9.5pt; color: #475569; }}
    ul {{
        margin: 4pt 0;
        padding-left: 16pt;
    }}
    li {{
        font-size: 9.5pt;
        margin-bottom: 2pt;
    }}
    table {{
        border-collapse: collapse;
    }}
    """

    page1 = _build_cover(ticker, info, today_str, booth, fs)
    cf_fs = _build_cf_fs_content(ticker, info, booth, fs, thesis)
    om_content = _build_om_content(ticker, om, om_narrative)
    cs_content = _build_cs_content(ticker, cs, cs_narrative)
    disclaimers = _build_disclaimers(ticker, today_str)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><style>{css}</style></head>
<body>
{page1}
{cf_fs}
{om_content}
{cs_content}
{disclaimers}
</body>
</html>"""
    return html


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
