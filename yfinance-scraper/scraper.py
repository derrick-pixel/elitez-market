"""Core scraper: pulls all available yfinance data for a single ticker."""

import warnings
import time
import yfinance as yf
import pandas as pd
from pathlib import Path
from config import MAX_RETRIES, PRICE_HISTORY_PERIOD

# Suppress deprecated .earnings warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="yfinance")


def scrape_ticker(symbol: str, out_dir: Path) -> dict:
    """
    Scrape all available data for a single ticker and save to CSVs.
    Returns a status dict: {"symbol": ..., "status": "ok"|"error", "error": ...}
    """
    ticker_dir = out_dir / symbol
    ticker_dir.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            tk = yf.Ticker(symbol)

            # --- Company info (dict → single-row CSV) ---
            info = tk.info or {}
            if info:
                pd.DataFrame([info]).to_csv(ticker_dir / "info.csv", index=False)

            # --- Price history ---
            hist = tk.history(period=PRICE_HISTORY_PERIOD)
            if not hist.empty:
                hist.to_csv(ticker_dir / "price_history.csv")

            # --- Financial statements (use newer API names) ---
            _save(tk.income_stmt, ticker_dir / "income_statement.csv")
            _save(tk.quarterly_income_stmt, ticker_dir / "income_statement_quarterly.csv")
            _save(tk.balance_sheet, ticker_dir / "balance_sheet.csv")
            _save(tk.quarterly_balance_sheet, ticker_dir / "balance_sheet_quarterly.csv")
            _save(tk.cashflow, ticker_dir / "cashflow.csv")
            _save(tk.quarterly_cashflow, ticker_dir / "cashflow_quarterly.csv")

            # --- Dividends & splits ---
            _save(tk.dividends, ticker_dir / "dividends.csv")
            _save(tk.splits, ticker_dir / "splits.csv")

            # --- Holders ---
            _save(tk.major_holders, ticker_dir / "major_holders.csv")
            _save(tk.institutional_holders, ticker_dir / "institutional_holders.csv")
            _save(tk.mutualfund_holders, ticker_dir / "mutualfund_holders.csv")

            # --- Analyst data ---
            _save(tk.recommendations, ticker_dir / "recommendations.csv")
            _save(tk.analyst_price_targets, ticker_dir / "analyst_price_targets.csv")
            _save(tk.earnings_estimate, ticker_dir / "earnings_estimate.csv")
            _save(tk.revenue_estimate, ticker_dir / "revenue_estimate.csv")

            # --- Options chain (nearest expiry) ---
            try:
                expirations = tk.options
                if expirations:
                    chain = tk.option_chain(expirations[0])
                    chain.calls.to_csv(ticker_dir / "options_calls.csv", index=False)
                    chain.puts.to_csv(ticker_dir / "options_puts.csv", index=False)
            except Exception:
                pass

            # --- Actions, calendar, sustainability ---
            _save(tk.actions, ticker_dir / "actions.csv")
            _save(tk.calendar, ticker_dir / "calendar.csv")
            _save(tk.sustainability, ticker_dir / "sustainability.csv")

            return {"symbol": symbol, "status": "ok", "error": None}

        except Exception as e:
            if attempt == MAX_RETRIES:
                return {"symbol": symbol, "status": "error", "error": str(e)}
            time.sleep(2 * attempt)

    return {"symbol": symbol, "status": "error", "error": "max retries exceeded"}


def _save(data, path: Path):
    """Save data to CSV — handles DataFrame, Series, dict, or None."""
    if data is None:
        return
    if isinstance(data, dict):
        if data:
            pd.DataFrame([data]).to_csv(path, index=False)
    elif isinstance(data, pd.Series):
        if not data.empty:
            data.to_frame().to_csv(path)
    elif isinstance(data, pd.DataFrame):
        if not data.empty:
            data.to_csv(path)
