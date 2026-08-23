"""
Download full daily history for the VIX index, used by
vix_regime_analysis.py to condition the overnight effect on the market's
volatility regime.

Goes straight at Yahoo's chart API via a curl_cffi Chrome-impersonated
session rather than the yfinance wrapper: yfinance's crumb/cookie handling
broke (AttributeError: 'str' object has no attribute 'name') for this
endpoint in this environment, a variant of the same crumb bug worked
around elsewhere in this project (see fetch_data.py's docstring). The
chart API's range=max parameter also silently truncated to ~440 rows
here; passing explicit period1/period2 unix timestamps spanning 1990 to
today returns the full 9500+ row history, which is what this script does.

VIX is an index, not a security, so there is no dividend/split adjustment
question here.
"""
from __future__ import annotations

import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from curl_cffi import requests as cffi_requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

SESSION = cffi_requests.Session(impersonate="chrome")
PERIOD1 = int(datetime(1990, 1, 1, tzinfo=timezone.utc).timestamp())
PERIOD2 = int(datetime.now(timezone.utc).timestamp())


def main():
    out_path = DATA_DIR / "VIX.csv"
    if out_path.exists():
        print("SKIP VIX (already downloaded)")
        return

    print("Fetching ^VIX via direct chart API...")
    result = None
    for attempt in range(4):
        try:
            r = SESSION.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
                params={"period1": PERIOD1, "period2": PERIOD2, "interval": "1d"},
            )
            data = r.json()
            result = data["chart"]["result"][0]
            break
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {e}")
            time.sleep(5 * (attempt + 1))

    if result is None:
        print("  FAILED: no data")
        return

    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    rows = []
    for i, ts in enumerate(timestamps):
        o, h, l, c, v = (quote[k][i] for k in ("open", "high", "low", "close", "volume"))
        if o is None or c is None:
            continue
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        rows.append([date, o, h, l, c, v])

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        writer.writerows(rows)
    print(f"  Saved {len(rows)} rows -> {out_path.name} ({rows[0][0]} to {rows[-1][0]})")


if __name__ == "__main__":
    main()
