#!/usr/bin/env python3
"""
Multi-Index Monthly Scraper — Entry Point

Usage:
    python run.py                        # scrape all indices (sp500 + sgx)
    python run.py --index sp500          # S&P 500 only
    python run.py --index sgx            # SGX mainboard only
    python run.py --index sgx --test 5   # test with first 5 SGX tickers
    python run.py --tickers AAPL,MSFT    # specific tickers only
"""

import argparse
import time
import json
from datetime import datetime

from config import DATA_DIR, SNAPSHOT_MONTH, BATCH_SIZE, SLEEP_BETWEEN, AVAILABLE_INDICES
from tickers import get_tickers
from scraper import scrape_ticker


def run_index(index_name: str, test_limit: int = 0):
    """Scrape a single index and return results."""
    index_dir = DATA_DIR / index_name / SNAPSHOT_MONTH
    index_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nFetching {index_name.upper()} ticker list...")
    df = get_tickers(index_name)
    df.to_csv(index_dir / f"{index_name}_constituents.csv", index=False)
    symbols = df["symbol"].tolist()
    print(f"Found {len(symbols)} companies")

    if test_limit > 0:
        symbols = symbols[:test_limit]
        print(f"TEST MODE: limiting to {test_limit} tickers")

    results = []
    total = len(symbols)
    start_time = time.time()

    for i, symbol in enumerate(symbols, 1):
        elapsed = time.time() - start_time
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total - i) / rate if rate > 0 else 0

        print(f"[{i}/{total}] {symbol:<10}  ", end="", flush=True)

        result = scrape_ticker(symbol, index_dir)
        results.append(result)

        if result["status"] == "ok":
            print("OK")
        else:
            print(f"ERROR: {result['error']}")

        if i % BATCH_SIZE == 0 and i < total:
            mins = int(eta // 60)
            secs = int(eta % 60)
            print(f"    --- batch pause ({SLEEP_BETWEEN}s) | ETA ~{mins}m {secs}s ---")
            time.sleep(SLEEP_BETWEEN)

    elapsed = time.time() - start_time
    ok = sum(1 for r in results if r["status"] == "ok")
    errors = sum(1 for r in results if r["status"] == "error")

    print(f"\n  {index_name.upper()}: {ok}/{total} OK, {errors} errors in {elapsed / 60:.1f} min")

    return {
        "index": index_name,
        "total": total,
        "success": ok,
        "errors": errors,
        "elapsed_seconds": round(elapsed, 1),
        "failed_tickers": [r for r in results if r["status"] == "error"],
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-Index Yahoo Finance Scraper")
    parser.add_argument("--index", type=str, default="all",
                        help=f"Index to scrape: {', '.join(AVAILABLE_INDICES)}, or 'all' (default: all)")
    parser.add_argument("--test", type=int, default=0, help="Only scrape first N tickers per index")
    parser.add_argument("--tickers", type=str, default="", help="Comma-separated list of specific tickers")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  Monthly Financial Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output: {DATA_DIR}/<index>/{SNAPSHOT_MONTH}/")

    # Custom tickers mode
    if args.tickers:
        symbols = [t.strip().upper() for t in args.tickers.split(",")]
        custom_dir = DATA_DIR / "custom" / SNAPSHOT_MONTH
        custom_dir.mkdir(parents=True, exist_ok=True)
        print(f"\nCustom ticker list: {len(symbols)} tickers")
        results = []
        for i, sym in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] {sym:<10}  ", end="", flush=True)
            r = scrape_ticker(sym, custom_dir)
            results.append(r)
            print("OK" if r["status"] == "ok" else f"ERROR: {r['error']}")
        ok = sum(1 for r in results if r["status"] == "ok")
        print(f"\nDone: {ok}/{len(symbols)} OK")
        return

    # Index mode
    indices = AVAILABLE_INDICES if args.index == "all" else [args.index]
    all_logs = []

    for idx in indices:
        log = run_index(idx, test_limit=args.test)
        all_logs.append(log)

    # Save combined run log
    run_log = {
        "timestamp": datetime.now().isoformat(),
        "indices": all_logs,
    }
    log_path = DATA_DIR / f"run_log_{SNAPSHOT_MONTH}.json"
    with open(log_path, "w") as f:
        json.dump(run_log, f, indent=2)

    print("\n" + "=" * 60)
    for log in all_logs:
        print(f"  {log['index'].upper():>8}: {log['success']}/{log['total']} OK  ({log['elapsed_seconds']/60:.1f} min)")
    print("=" * 60)
    print(f"Run log: {log_path}")
    for idx in indices:
        print(f"  {DATA_DIR / idx / SNAPSHOT_MONTH}/")


if __name__ == "__main__":
    main()
