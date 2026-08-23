"""
Diagnostic scan for the open==close data-hygiene bias documented in
background/independent_review.md finding #2: in legacy Yahoo Finance data,
some pre-2000 rows record Open == Close (a vendor rounding/missing-print
artifact), which mechanically forces that day's intraday leg
(close[t]/open[t] - 1) to exactly 0% and dumps the entire day's move into
the overnight leg (open[t]/close[t-1] - 1), inflating exactly the effect
this project measures.

This script only reports where the bias lives -- it doesn't filter
anything itself. See analyze.py's --mode flag (Mode B/C) for the two
ways of actually removing it from the analysis.

Scans the 33-ticker universe (data/universe.json), not every file under
data/ -- VIX.csv is an index, not one of the analyzed stocks, so it's out
of scope for this check.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

FLAT_DAY_REL_TOL = 1e-6

DECADE_BUCKETS = [
    ("1962-1979", 1962, 1979),
    ("1980-1989", 1980, 1989),
    ("1990-1999", 1990, 1999),
    ("2000-2026", 2000, 2026),
]


def decade_bucket(date: str) -> str | None:
    year = int(date[:4])
    for label, lo, hi in DECADE_BUCKETS:
        if lo <= year <= hi:
            return label
    return None


def scan_ticker(ticker: str):
    path = DATA_DIR / f"{ticker}.csv"
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            if not row["open"] or not row["close"]:
                continue
            rows.append((row["date"], float(row["open"]), float(row["close"])))

    per_decade = {label: {"n_rows": 0, "n_flat": 0} for label, _, _ in DECADE_BUCKETS}
    n_flat_total = 0
    for date, open_, close in rows:
        bucket = decade_bucket(date)
        is_flat = abs(open_ - close) < FLAT_DAY_REL_TOL * close
        if is_flat:
            n_flat_total += 1
        if bucket is not None:
            per_decade[bucket]["n_rows"] += 1
            if is_flat:
                per_decade[bucket]["n_flat"] += 1

    for label in per_decade:
        n_rows = per_decade[label]["n_rows"]
        per_decade[label]["pct_flat"] = (
            per_decade[label]["n_flat"] / n_rows * 100 if n_rows > 0 else None
        )

    return {
        "start": rows[0][0] if rows else None,
        "end": rows[-1][0] if rows else None,
        "n_rows_total": len(rows),
        "n_flat_total": n_flat_total,
        "pct_flat_total": n_flat_total / len(rows) * 100 if rows else None,
        "by_decade": per_decade,
    }


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    tickers = sorted({t for group in universe.values() for t in group})

    per_ticker = {}
    for ticker in tickers:
        path = DATA_DIR / f"{ticker}.csv"
        if not path.exists():
            continue
        per_ticker[ticker] = scan_ticker(ticker)

    # Aggregate across all tickers, per decade bucket
    aggregate_by_decade = {}
    for label, _, _ in DECADE_BUCKETS:
        n_rows = sum(per_ticker[t]["by_decade"][label]["n_rows"] for t in per_ticker)
        n_flat = sum(per_ticker[t]["by_decade"][label]["n_flat"] for t in per_ticker)
        aggregate_by_decade[label] = {
            "n_rows": n_rows,
            "n_flat": n_flat,
            "pct_flat": n_flat / n_rows * 100 if n_rows > 0 else None,
        }

    n_rows_total = sum(v["n_rows_total"] for v in per_ticker.values())
    n_flat_total = sum(v["n_flat_total"] for v in per_ticker.values())

    report = {
        "flat_day_definition": "abs(open - close) < 1e-6 * close",
        "n_tickers_scanned": len(per_ticker),
        "n_rows_total": n_rows_total,
        "n_flat_total": n_flat_total,
        "pct_flat_total": n_flat_total / n_rows_total * 100 if n_rows_total > 0 else None,
        "aggregate_by_decade": aggregate_by_decade,
        "per_ticker": per_ticker,
    }

    with open(REPORTS_DIR / "data_hygiene_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Scanned {len(per_ticker)} tickers, {n_rows_total} total rows")
    print(f"Overall flat-day (open==close) rate: {report['pct_flat_total']:.2f}%\n")

    print("By decade (all tickers pooled):")
    for label, _, _ in DECADE_BUCKETS:
        v = aggregate_by_decade[label]
        pct = f"{v['pct_flat']:.2f}%" if v["pct_flat"] is not None else "n/a"
        print(f"  {label}: {pct} flat ({v['n_flat']}/{v['n_rows']} rows)")

    print("\nWorst-affected tickers (by full-history flat-day rate):")
    ranked = sorted(
        ((t, v["pct_flat_total"]) for t, v in per_ticker.items() if v["pct_flat_total"] is not None),
        key=lambda x: -x[1],
    )
    for ticker, pct in ranked[:10]:
        print(f"  {ticker:6s} {pct:5.2f}%")

    print(f"\nSaved -> {REPORTS_DIR / 'data_hygiene_report.json'}")


if __name__ == "__main__":
    main()
