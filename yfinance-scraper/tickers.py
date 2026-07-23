"""Fetch ticker lists for supported indices."""

import io
import re
import requests
import pandas as pd
from config import SP500_URL, SGX_URL

HEADERS = {"User-Agent": "Mozilla/5.0 (yfinance-scraper)"}


def get_sp500_tickers() -> pd.DataFrame:
    """Return S&P 500 constituents with symbol, company, sector columns."""
    resp = requests.get(SP500_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]
    df = df.rename(columns={
        "Symbol": "symbol",
        "Security": "company",
        "GICS Sector": "sector",
        "GICS Sub-Industry": "sub_industry",
        "Headquarters Location": "headquarters",
        "Date added": "date_added",
        "CIK": "cik",
        "Founded": "founded",
    })
    # Yahoo uses dashes where Wikipedia uses dots
    df["symbol"] = df["symbol"].str.replace(".", "-", regex=False)
    return df


def get_sgx_tickers() -> pd.DataFrame:
    """Return all SGX mainboard companies with symbol (Yahoo .SI suffix), company name."""
    resp = requests.get(SGX_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    # stockanalysis.com embeds data in a JS variable — parse the table from HTML
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]

    # Normalize column names (the site uses "Symbol" and "Company Name" or similar)
    cols = df.columns.tolist()
    rename_map = {}
    for c in cols:
        cl = c.lower()
        if "symbol" in cl or "ticker" in cl:
            rename_map[c] = "symbol"
        elif "company" in cl or "name" in cl:
            rename_map[c] = "company"
        elif "market" in cl and "cap" in cl:
            rename_map[c] = "market_cap"
        elif "sector" in cl:
            rename_map[c] = "sector"

    df = df.rename(columns=rename_map)

    if "symbol" not in df.columns:
        # Fallback: first column is likely the symbol
        df = df.rename(columns={cols[0]: "symbol", cols[1]: "company"})

    # Clean symbols — remove any exchange prefix and add .SI suffix for Yahoo
    df["symbol"] = df["symbol"].apply(_to_yahoo_sgx)

    # Filter out warrants, structured warrants, and ETFs with W suffix
    df = df[~df["symbol"].str.contains("W.SI$", regex=True, na=False)]

    return df


def _to_yahoo_sgx(raw: str) -> str:
    """Convert a raw SGX ticker to Yahoo Finance format (append .SI)."""
    raw = str(raw).strip().upper()
    # Remove any existing .SI suffix
    raw = re.sub(r"\.SI$", "", raw)
    # Remove exchange prefixes like "SGX:" if present
    if ":" in raw:
        raw = raw.split(":")[-1]
    return f"{raw}.SI"


def get_tickers(index: str) -> pd.DataFrame:
    """Dispatcher — fetch tickers for a given index name."""
    if index == "sp500":
        return get_sp500_tickers()
    elif index == "sgx":
        return get_sgx_tickers()
    else:
        raise ValueError(f"Unknown index: {index}. Use one of: sp500, sgx")


if __name__ == "__main__":
    for idx in ["sp500", "sgx"]:
        df = get_tickers(idx)
        print(f"\n{idx.upper()}: {len(df)} companies")
        print(df[["symbol", "company"]].head(5))
