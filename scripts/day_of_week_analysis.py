"""
Day-of-week breakdown of the overnight leg.

Directly answers: does it matter which weekday you buy the close on?
In particular, buying Friday's close is structurally different from
buying Monday/Tuesday/Wednesday/Thursday's close -- Friday->Monday spans
a 3-calendar-day weekend gap (the classic "weekend effect" from French
1980), while the other four are ordinary one-business-day gaps. Grouping
by the weekday of the close (the "buy day") captures this automatically:
the Friday bucket *is* the weekend-gap bucket.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from stats_utils import hac_mean_test

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

TRADING_DAYS_PER_YEAR = 252
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
BENCHMARK_TICKERS = {"SPY", "QQQ", "MU"}


def load_ticker(ticker: str):
    path = DATA_DIR / f"{ticker}.csv"
    dates, opens, closes = [], [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            if not row["open"] or not row["close"]:
                continue
            dates.append(row["date"])
            opens.append(float(row["open"]))
            closes.append(float(row["close"]))
    return dates, np.array(opens), np.array(closes)


def overnight_by_buy_weekday(ticker: str):
    dates, opens, closes = load_ticker(ticker)
    overnight = opens[1:] / closes[:-1] - 1.0
    buy_dates = dates[:-1]  # the close date being bought
    buy_weekdays = [datetime.strptime(d, "%Y-%m-%d").weekday() for d in buy_dates]

    buckets = {i: [] for i in range(5)}
    for wd, ret in zip(buy_weekdays, overnight):
        if wd in buckets:  # 5=Sat, 6=Sun shouldn't occur for a close date, but guard anyway
            buckets[wd].append(ret)

    result = {}
    for wd, name in enumerate(WEEKDAY_NAMES):
        rets = np.array(buckets[wd])
        if len(rets) < 30:
            continue
        hac = hac_mean_test(rets)
        ann_return = (1 + hac["mean"]) ** TRADING_DAYS_PER_YEAR - 1
        result[name] = {
            "n": len(rets),
            "mean_daily_bps": hac["mean"] * 10_000,
            "ann_return_pct": ann_return * 100,
            "t_stat": hac["t_stat"],
            "p_value": hac["p_value"],
        }
    return result


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    tickers = [t for group in universe.values() for t in group]

    per_ticker = {}
    for ticker in tickers:
        if not (DATA_DIR / f"{ticker}.csv").exists():
            continue
        per_ticker[ticker] = overnight_by_buy_weekday(ticker)
        row = per_ticker[ticker]
        line = f"{ticker:6s} " + "  ".join(
            f"{name[:3]}={row[name]['ann_return_pct']:6.1f}%(t={row[name]['t_stat']:5.2f})"
            for name in WEEKDAY_NAMES if name in row
        )
        print(line)

    # Pooled cross-section test: is Friday's overnight leg (the weekend
    # gap) different from the pooled Monday-Thursday legs? And is Monday
    # specifically different from Tuesday-Thursday?
    cross_tickers = [t for t in per_ticker if t not in BENCHMARK_TICKERS]

    friday_ann = np.array([per_ticker[t]["Friday"]["ann_return_pct"] for t in cross_tickers if "Friday" in per_ticker[t]])
    monthu_ann = np.array([
        np.mean([per_ticker[t][d]["ann_return_pct"] for d in ["Monday", "Tuesday", "Wednesday", "Thursday"] if d in per_ticker[t]])
        for t in cross_tickers
    ])
    monday_ann = np.array([per_ticker[t]["Monday"]["ann_return_pct"] for t in cross_tickers if "Monday" in per_ticker[t]])
    tuethu_ann = np.array([
        np.mean([per_ticker[t][d]["ann_return_pct"] for d in ["Tuesday", "Wednesday", "Thursday"] if d in per_ticker[t]])
        for t in cross_tickers
    ])

    from scipy import stats as scipy_stats
    fri_vs_rest_t, fri_vs_rest_p = scipy_stats.ttest_rel(friday_ann, monthu_ann)
    mon_vs_tuethu_t, mon_vs_tuethu_p = scipy_stats.ttest_rel(monday_ann, tuethu_ann)

    summary = {
        "n_tickers": len(cross_tickers),
        "mean_ann_return_by_weekday_pct": {
            name: float(np.mean([per_ticker[t][name]["ann_return_pct"] for t in cross_tickers if name in per_ticker[t]]))
            for name in WEEKDAY_NAMES
        },
        "friday_close_vs_mon_thu_close_paired_t": float(fri_vs_rest_t),
        "friday_close_vs_mon_thu_close_paired_p": float(fri_vs_rest_p),
        "monday_close_vs_tue_thu_close_paired_t": float(mon_vs_tuethu_t),
        "monday_close_vs_tue_thu_close_paired_p": float(mon_vs_tuethu_p),
    }

    with open(REPORTS_DIR / "day_of_week_results.json", "w") as f:
        json.dump({"per_ticker": per_ticker, "summary": summary}, f, indent=2, default=str)

    print("\n=== DAY-OF-WEEK SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
