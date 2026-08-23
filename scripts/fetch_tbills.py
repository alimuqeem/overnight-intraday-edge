"""
Download and cache the daily 3-month Treasury Bill secondary-market rate
(FRED series DTB3), used by portfolio_backtest.py to credit idle cash with
a real money-market-like yield during the roughly half of each trading
cycle the overnight-only/intraday-only strategies aren't holding stock.

Goes straight at FRED's public fredgraph.csv endpoint (no API key
required) rather than the FRED API. An earlier version of
portfolio_backtest.py logged plain urllib/T-bill fetches as unreachable
from this environment; that turned out to be the same TLS-fingerprint
block documented in fetch_data.py/fetch_vix.py for Yahoo's endpoints, not
FRED being genuinely unreachable -- plain urllib.request times out here,
but a curl_cffi session impersonating Chrome's TLS fingerprint gets a
clean 200, so this uses that instead of urllib.
"""
from __future__ import annotations

import csv
from pathlib import Path

from curl_cffi import requests as cffi_requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FACTORS_DIR = DATA_DIR / "factors"
FACTORS_DIR.mkdir(parents=True, exist_ok=True)

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3&cosd=1993-01-01"
SESSION = cffi_requests.Session(impersonate="chrome")


def main():
    out_path = FACTORS_DIR / "tbills_daily.csv"
    if out_path.exists():
        print("SKIP tbills_daily.csv (already downloaded)")
        return

    print("Fetching 3-month T-bill secondary market rate (FRED DTB3)...")
    resp = SESSION.get(URL, timeout=30)
    resp.raise_for_status()
    text = resp.text

    rows = []
    for line in text.splitlines()[1:]:  # skip "observation_date,DTB3" header
        parts = line.split(",")
        if len(parts) != 2:
            continue
        date, value = parts
        if value in (".", ""):
            continue  # FRED's marker for a non-trading/no-print day
        rows.append((date, float(value) / 100.0))

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "tbill_yield"])
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows -> {out_path} ({rows[0][0]} to {rows[-1][0]})")


if __name__ == "__main__":
    main()
