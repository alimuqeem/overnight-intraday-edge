"""
Extreme-gap decomposition of the overnight leg.

Answers: how much of the overnight edge comes from a handful of huge
gap nights (the kind an earnings surprise produces) versus a steady
grind across ordinary days?

This is NOT a precise earnings-calendar match -- free historical
earnings-date data going back 20-40 years per ticker isn't available
(Yahoo's own earnings-date endpoint only covers ~4 recent quarters, and
requires an auth crumb this project's fetch approach doesn't have). This
uses an explicit, clearly-labeled statistical proxy instead: for each
ticker, days where the overnight return exceeds a z-score threshold
(3 standard deviations of that ticker's own overnight return
distribution) are flagged as "extreme gap days" -- a mix of earnings
surprises, M&A news, guidance updates, and macro shocks, not earnings
specifically. Read the results as "edge excluding tail events," not
"edge excluding earnings."
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from stats_utils import hac_mean_test

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

TRADING_DAYS_PER_YEAR = 252
Z_THRESHOLD = 3.0
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


def decompose(ticker: str):
    dates, opens, closes = load_ticker(ticker)
    overnight = opens[1:] / closes[:-1] - 1.0

    mean, std = overnight.mean(), overnight.std(ddof=1)
    z = (overnight - mean) / std
    extreme_mask = np.abs(z) > Z_THRESHOLD
    n_extreme = int(extreme_mask.sum())

    all_compound = np.prod(1 + overnight) - 1
    extreme_only_compound = np.prod(1 + overnight[extreme_mask]) - 1 if n_extreme > 0 else 0.0
    ordinary = overnight[~extreme_mask]
    ordinary_compound = np.prod(1 + ordinary) - 1

    hac_ordinary = hac_mean_test(ordinary)
    ordinary_ann = (1 + hac_ordinary["mean"]) ** TRADING_DAYS_PER_YEAR - 1

    hac_all = hac_mean_test(overnight)
    all_ann = (1 + hac_all["mean"]) ** TRADING_DAYS_PER_YEAR - 1

    # Share of total compounded log-return contributed by extreme days
    log_total = np.sum(np.log(1 + overnight))
    log_extreme = np.sum(np.log(1 + overnight[extreme_mask])) if n_extreme > 0 else 0.0
    extreme_share_of_log_return = log_extreme / log_total if log_total != 0 else float("nan")

    return {
        "n_days": len(overnight),
        "n_extreme": n_extreme,
        "pct_days_extreme": n_extreme / len(overnight) * 100,
        "extreme_share_of_log_return_pct": extreme_share_of_log_return * 100,
        "all_days_ann_return_pct": all_ann * 100,
        "all_days_t_stat": hac_all["t_stat"],
        "ordinary_days_ann_return_pct": ordinary_ann * 100,
        "ordinary_days_t_stat": hac_ordinary["t_stat"],
        "ordinary_days_p_value": hac_ordinary["p_value"],
        "all_days_compound_pct": all_compound * 100,
        "ordinary_days_compound_pct": ordinary_compound * 100,
    }


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    tickers = [t for group in universe.values() for t in group]

    per_ticker = {}
    for ticker in tickers:
        if not (DATA_DIR / f"{ticker}.csv").exists():
            continue
        per_ticker[ticker] = decompose(ticker)
        r = per_ticker[ticker]
        print(
            f"{ticker:6s} all_ann={r['all_days_ann_return_pct']:7.1f}%  "
            f"ordinary_ann={r['ordinary_days_ann_return_pct']:7.1f}% (t={r['ordinary_days_t_stat']:5.2f})  "
            f"n_extreme={r['n_extreme']:3d}/{r['n_days']:5d} ({r['pct_days_extreme']:.2f}%)  "
            f"extreme_share_of_logret={r['extreme_share_of_log_return_pct']:6.1f}%"
        )

    cross_tickers = [t for t in per_ticker if t not in BENCHMARK_TICKERS]
    summary = {
        "z_threshold": Z_THRESHOLD,
        "n_tickers": len(cross_tickers),
        "mean_pct_days_extreme": float(np.mean([per_ticker[t]["pct_days_extreme"] for t in cross_tickers])),
        "mean_extreme_share_of_log_return_pct": float(np.mean([per_ticker[t]["extreme_share_of_log_return_pct"] for t in cross_tickers])),
        "mean_all_days_ann_return_pct": float(np.mean([per_ticker[t]["all_days_ann_return_pct"] for t in cross_tickers])),
        "mean_ordinary_days_ann_return_pct": float(np.mean([per_ticker[t]["ordinary_days_ann_return_pct"] for t in cross_tickers])),
        "n_tickers_ordinary_days_still_significant": int(np.sum([
            per_ticker[t]["ordinary_days_p_value"] < 0.05 and per_ticker[t]["ordinary_days_ann_return_pct"] > 0
            for t in cross_tickers
        ])),
    }

    with open(REPORTS_DIR / "extreme_gap_results.json", "w") as f:
        json.dump({"per_ticker": per_ticker, "summary": summary}, f, indent=2, default=str)

    print("\n=== EXTREME-GAP SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
