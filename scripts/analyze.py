"""
Overnight vs. intraday return decomposition and edge test.

For each ticker, splits every trading day's return into two legs:
  - overnight: prev_close -> today_open  (held while market is closed)
  - intraday:  today_open  -> today_close (held while market is open)

Then tests whether either leg carries a statistically and economically
significant edge, both per-ticker and pooled across the universe, and
checks whether the effect survives (a) realistic transaction costs and
(b) a split into two non-overlapping sub-periods (out-of-sample check
against regime-specific noise).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
REPORTS_DIR.mkdir(exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)

TRADING_DAYS_PER_YEAR = 252


def load_ticker(ticker: str):
    path = DATA_DIR / f"{ticker}.csv"
    dates, opens, closes = [], [], []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["open"] or not row["close"]:
                continue
            dates.append(row["date"])
            opens.append(float(row["open"]))
            closes.append(float(row["close"]))
    return dates, np.array(opens), np.array(closes)


def compute_legs(dates, opens, closes):
    """Return (dates_for_overnight, overnight_returns, intraday_returns)."""
    overnight = opens[1:] / closes[:-1] - 1.0
    intraday = closes / opens - 1.0
    return dates[1:], overnight, intraday


def leg_stats(returns: np.ndarray, cost_bps: float = 0.0):
    """Summary stats for one leg's daily return series, net of a flat
    per-trade round-trip cost expressed in basis points."""
    net = returns - cost_bps / 10_000.0
    n = len(net)
    mean = net.mean()
    std = net.std(ddof=1)
    se = std / math.sqrt(n)
    t_stat = mean / se if se > 0 else float("nan")
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df=n - 1)) if not math.isnan(t_stat) else float("nan")
    ann_return = (1 + mean) ** TRADING_DAYS_PER_YEAR - 1
    ann_vol = std * math.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (mean * TRADING_DAYS_PER_YEAR) / ann_vol if ann_vol > 0 else float("nan")
    win_rate = (net > 0).mean()
    compound = np.prod(1 + net) - 1
    return {
        "n": n,
        "mean_daily_bps": mean * 10_000,
        "ann_return_pct": ann_return * 100,
        "ann_vol_pct": ann_vol * 100,
        "sharpe": sharpe,
        "t_stat": t_stat,
        "p_value": p_value,
        "win_rate_pct": win_rate * 100,
        "compound_return_pct": compound * 100,
    }


def breakeven_cost_bps(returns: np.ndarray, lo=0.0, hi=200.0, tol=1e-6):
    """Binary-search the flat round-trip cost (bps) that drives the
    compounded return of this leg to zero. Returns None if the leg is
    unprofitable even at zero cost."""
    def compound_at(cost_bps):
        net = returns - cost_bps / 10_000.0
        return np.prod(1 + net) - 1

    if compound_at(0.0) <= 0:
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if compound_at(mid) > 0:
            lo = mid
        else:
            hi = mid
    return lo


def analyze_ticker(ticker: str):
    dates, opens, closes = load_ticker(ticker)
    if len(dates) < 500:
        return None
    d, overnight, intraday = compute_legs(dates, opens, closes)

    result = {
        "ticker": ticker,
        "start": d[0],
        "end": d[-1],
        "n_days": len(d),
        "overnight": leg_stats(overnight),
        "intraday": leg_stats(intraday),
        "overnight_breakeven_bps": breakeven_cost_bps(overnight),
        "intraday_breakeven_bps": breakeven_cost_bps(intraday),
    }

    # Sub-period split: first half vs second half of available history,
    # to check the effect isn't an artifact of one regime.
    mid = len(d) // 2
    result["overnight_first_half"] = leg_stats(overnight[:mid])
    result["overnight_second_half"] = leg_stats(overnight[mid:])
    result["intraday_first_half"] = leg_stats(intraday[:mid])
    result["intraday_second_half"] = leg_stats(intraday[mid:])

    return result, overnight, intraday, d


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    ticker_to_sector = {t: sector for sector, ts in universe.items() for t in ts}

    per_ticker = {}
    all_overnight_means = []
    all_intraday_means = []

    for sector, tickers in universe.items():
        for ticker in tickers:
            path = DATA_DIR / f"{ticker}.csv"
            if not path.exists():
                print(f"SKIP {ticker}: no data")
                continue
            out = analyze_ticker(ticker)
            if out is None:
                print(f"SKIP {ticker}: insufficient data")
                continue
            result, overnight, intraday, d = out
            result["sector"] = sector
            per_ticker[ticker] = result
            all_overnight_means.append(result["overnight"]["mean_daily_bps"])
            all_intraday_means.append(result["intraday"]["mean_daily_bps"])
            print(
                f"{ticker:6s} ({sector[:20]:20s}) "
                f"overnight ann={result['overnight']['ann_return_pct']:9.1f}%  "
                f"t={result['overnight']['t_stat']:6.2f}   "
                f"intraday ann={result['intraday']['ann_return_pct']:9.1f}%  "
                f"t={result['intraday']['t_stat']:6.2f}"
            )

    # Cross-sectional test: is the mean overnight edge across tickers
    # significantly different from zero / from the mean intraday edge?
    overnight_arr = np.array(all_overnight_means)
    intraday_arr = np.array(all_intraday_means)
    cross_overnight_t, cross_overnight_p = stats.ttest_1samp(overnight_arr, 0)
    cross_intraday_t, cross_intraday_p = stats.ttest_1samp(intraday_arr, 0)
    paired_t, paired_p = stats.ttest_rel(overnight_arr, intraday_arr)

    summary = {
        "n_tickers": len(per_ticker),
        "cross_sectional_overnight_mean_bps": float(overnight_arr.mean()),
        "cross_sectional_overnight_t": float(cross_overnight_t),
        "cross_sectional_overnight_p": float(cross_overnight_p),
        "cross_sectional_intraday_mean_bps": float(intraday_arr.mean()),
        "cross_sectional_intraday_t": float(cross_intraday_t),
        "cross_sectional_intraday_p": float(cross_intraday_p),
        "paired_overnight_vs_intraday_t": float(paired_t),
        "paired_overnight_vs_intraday_p": float(paired_p),
        "pct_tickers_overnight_positive_significant": float(
            np.mean([
                per_ticker[t]["overnight"]["t_stat"] > 1.96
                for t in per_ticker
            ]) * 100
        ),
        "pct_tickers_intraday_negative_significant": float(
            np.mean([
                per_ticker[t]["intraday"]["t_stat"] < -1.96
                for t in per_ticker
            ]) * 100
        ),
        "median_overnight_breakeven_bps": float(np.median([
            per_ticker[t]["overnight_breakeven_bps"]
            for t in per_ticker if per_ticker[t]["overnight_breakeven_bps"] is not None
        ])),
    }

    with open(REPORTS_DIR / "per_ticker_results.json", "w") as f:
        json.dump(per_ticker, f, indent=2, default=str)
    with open(REPORTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== CROSS-SECTIONAL SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
