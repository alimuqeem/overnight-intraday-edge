"""
Download full daily OHLC history for the test universe.

Plain yfinance / raw Yahoo chart-API requests get rate-limited (429) after a
handful of calls. Routing yfinance through a curl_cffi session that
impersonates Chrome's TLS fingerprint avoids that -- same fix used in
../vix-regime-switch-backtest.

Uses auto_adjust=True so Open/High/Low/Close are all consistently adjusted
for splits AND dividends. Without this, raw Close is dividend-adjusted by
convention but raw Open is not (they come from different vendor fields),
so every ex-dividend morning shows a mechanical price drop that lands
entirely in the close->open ("overnight") leg of the decomposition this
project runs -- a real bug found in an earlier version of this script that
was silently inflating the apparent overnight/intraday gap for high-yield
sectors (utilities, staples, energy) by roughly their dividend yield.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import yfinance as yf
from curl_cffi import requests as cffi_requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ~30-40 liquid large-caps spanning all 11 GICS sectors, plus SPY/QQQ as
# broad-market benchmarks and MU as the stock that prompted this project.
UNIVERSE = {
    "Information Technology": ["AAPL", "MSFT", "NVDA", "AVGO"],
    "Communication Services": ["GOOGL", "META", "NFLX"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD"],
    "Consumer Staples": ["PG", "KO", "WMT"],
    "Financials": ["JPM", "BAC", "V"],
    "Health Care": ["UNH", "JNJ", "LLY"],
    "Industrials": ["CAT", "HON", "UPS"],
    "Energy": ["XOM", "CVX"],
    "Materials": ["LIN", "FCX"],
    "Real Estate": ["PLD", "AMT"],
    "Utilities": ["NEE", "DUK"],
    "Benchmarks / Focus": ["SPY", "QQQ", "MU"],
}

TICKERS = [t for group in UNIVERSE.values() for t in group]

SESSION = cffi_requests.Session(impersonate="chrome")


def main():
    for ticker in TICKERS:
        out_path = DATA_DIR / f"{ticker}.csv"
        if out_path.exists():
            print(f"SKIP {ticker} (already downloaded)")
            continue

        print(f"Fetching {ticker}...")
        df = None
        for attempt in range(4):
            try:
                df = yf.download(
                    ticker, period="max", progress=False,
                    session=SESSION, auto_adjust=True,
                )
                break
            except Exception as e:
                print(f"  attempt {attempt + 1} failed: {e}")
                time.sleep(5 * (attempt + 1))

        if df is None or df.empty:
            print(f"  FAILED {ticker}: no data")
            continue

        df.columns = df.columns.get_level_values(0)  # drop ticker sub-level
        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
        df[["date", "open", "high", "low", "close", "volume"]].to_csv(out_path, index=False)
        print(f"  Saved {len(df)} rows -> {out_path.name} ({df['date'].iloc[0]} to {df['date'].iloc[-1]})")
        time.sleep(1)

    with open(DATA_DIR / "universe.json", "w") as f:
        json.dump(UNIVERSE, f, indent=2)


if __name__ == "__main__":
    main()
