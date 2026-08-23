"""
Does a stock's own trailing overnight performance predict its future
overnight performance?

background/literature_review.md already cites Lou, Polk & Skouras (2019)
for this specific claim, but report.md's factor regression (section 4)
only tested loading on the Fama-French *cross-sectional* momentum factor
(ordinary price momentum) and found it near zero -- a different and
narrower question. This script runs the actual LPS-style test: sort
tickers each day by their own trailing overnight-return average (a
signal fully known before that day's close is bought, so this is a
legitimate no-look-ahead predictive test, not a repackaging of the
descriptive averages already reported elsewhere), form equal-weight top-
and bottom-tercile portfolios from the forward overnight return, and test
whether top beats bottom by more than noise.

Three lookback windows are tested (1 week, 1 month, 1 quarter of trading
days) since the literature doesn't pin down a single horizon. The 21-day
(1-month) window is treated as the headline case and gets a full equity-
curve comparison against the equal-weight-all-names portfolio already
built in portfolio_backtest.py, at the same flat 5bps round-trip cost for
apples-to-apples comparability.
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
COST_BPS = 5.0  # matches portfolio_backtest.py's flat-cost convention
BENCHMARK_TICKERS = {"SPY", "QQQ", "MU"}
WINDOWS = [5, 21, 63]
HEADLINE_WINDOW = 21
MIN_NAMES_FOR_SORT = 9  # need at least 3 per tercile


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


def build_overnight_series(tickers: list):
    """Per ticker: (dates_on, overnight_returns), where overnight_returns[i]
    is realized on the open of dates_on[i], having been bought at the prior
    trading day's close."""
    series = {}
    for t in tickers:
        dates, opens, closes = load_ticker(t)
        overnight = opens[1:] / closes[:-1] - 1.0
        series[t] = (dates[1:], overnight)
    return series


def cross_sectional_tercile_test(series: dict, window: int):
    """For a given trailing-window length, pool all (date, ticker) cells
    where a no-look-ahead trailing-mean signal is available, sort into
    terciles each date, and return the top/bottom tercile forward-return
    time series (as dicts date -> list of returns) plus HAC stats."""
    # Build per-ticker signal (trailing mean of the last `window` overnight
    # returns, known as of the close being bought -- see module docstring)
    # aligned to the same index as the forward return it predicts.
    per_ticker_signal = {}
    for t, (dates_on, ov) in series.items():
        if len(ov) <= window:
            continue
        signal = np.full(len(ov), np.nan)
        for i in range(window, len(ov)):
            signal[i] = ov[i - window:i].mean()
        per_ticker_signal[t] = (dates_on, ov, signal)

    by_date = {}
    for t, (dates_on, ov, signal) in per_ticker_signal.items():
        for i, d in enumerate(dates_on):
            if np.isnan(signal[i]):
                continue
            by_date.setdefault(d, []).append((t, signal[i], ov[i]))

    top_by_date, bottom_by_date, all_by_date = {}, {}, {}
    for d, rows in sorted(by_date.items()):
        if len(rows) < MIN_NAMES_FOR_SORT:
            continue
        rows_sorted = sorted(rows, key=lambda r: r[1])
        third = len(rows_sorted) // 3
        bottom = rows_sorted[:third]
        top = rows_sorted[-third:]
        top_by_date[d] = [r[2] for r in top]
        bottom_by_date[d] = [r[2] for r in bottom]
        all_by_date[d] = [r[2] for r in rows_sorted]

    top_daily = np.array([np.mean(v) for d, v in sorted(top_by_date.items())])
    bottom_daily = np.array([np.mean(v) for d, v in sorted(bottom_by_date.items())])
    dates_sorted = [d for d, v in sorted(top_by_date.items())]
    spread_daily = top_daily - bottom_daily

    top_hac = hac_mean_test(top_daily)
    bottom_hac = hac_mean_test(bottom_daily)
    spread_hac = hac_mean_test(spread_daily)

    def ann(mean):
        return ((1 + mean) ** TRADING_DAYS_PER_YEAR - 1) * 100

    return {
        "window_days": window,
        "n_days_with_valid_sort": len(dates_sorted),
        "first_date": dates_sorted[0] if dates_sorted else None,
        "last_date": dates_sorted[-1] if dates_sorted else None,
        "top_tercile_ann_return_pct": ann(top_hac["mean"]),
        "top_tercile_t_stat": top_hac["t_stat"],
        "top_tercile_p_value": top_hac["p_value"],
        "bottom_tercile_ann_return_pct": ann(bottom_hac["mean"]),
        "bottom_tercile_t_stat": bottom_hac["t_stat"],
        "bottom_tercile_p_value": bottom_hac["p_value"],
        "spread_ann_return_pct": ann(spread_hac["mean"]),
        "spread_t_stat": spread_hac["t_stat"],
        "spread_p_value": spread_hac["p_value"],
    }, dates_sorted, top_daily, bottom_daily, all_by_date


def perf_metrics(daily_ret: np.ndarray, equity: np.ndarray):
    n = len(daily_ret)
    years = n / TRADING_DAYS_PER_YEAR
    cagr = equity[-1] ** (1 / years) - 1
    vol = np.std(daily_ret) * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = np.mean(daily_ret) / np.std(daily_ret) * np.sqrt(TRADING_DAYS_PER_YEAR) if np.std(daily_ret) > 0 else float("nan")
    cum_max = np.maximum.accumulate(equity)
    max_dd = (equity / cum_max - 1).min()
    return {"cagr_pct": cagr * 100, "ann_vol_pct": vol * 100, "sharpe": sharpe,
            "max_drawdown_pct": max_dd * 100, "final_equity": float(equity[-1]), "years": years}


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    cross_tickers = [t for group in universe.values() for t in group if t not in BENCHMARK_TICKERS]

    print(f"Building overnight-return series for {len(cross_tickers)} tickers...")
    series = build_overnight_series(cross_tickers)

    window_results = {}
    headline_data = None
    for w in WINDOWS:
        print(f"\nTesting {w}-day trailing overnight-momentum signal...")
        stats_out, dates_sorted, top_daily, bottom_daily, all_by_date = cross_sectional_tercile_test(series, w)
        window_results[str(w)] = stats_out
        print(f"  n_days={stats_out['n_days_with_valid_sort']}  "
              f"top={stats_out['top_tercile_ann_return_pct']:7.2f}% (t={stats_out['top_tercile_t_stat']:5.2f})  "
              f"bottom={stats_out['bottom_tercile_ann_return_pct']:7.2f}% (t={stats_out['bottom_tercile_t_stat']:5.2f})  "
              f"spread={stats_out['spread_ann_return_pct']:7.2f}% (t={stats_out['spread_t_stat']:5.2f}, p={stats_out['spread_p_value']:.4f})")
        if w == HEADLINE_WINDOW:
            headline_data = (dates_sorted, top_daily, bottom_daily, all_by_date)

    # Headline window: full equity-curve comparison at flat 5bps cost,
    # top-tercile-only vs equal-weight-all (using the SAME date-restricted
    # window as the momentum sort, i.e. dates where a valid signal existed
    # for enough names -- an early-history apples-to-apples comparison,
    # not the full 1993-2026 window used elsewhere in this project).
    dates_sorted, top_daily, bottom_daily, all_by_date = headline_data
    cost = COST_BPS / 10_000.0
    all_daily = np.array([np.mean(v) for d, v in sorted(all_by_date.items())])

    top_net = top_daily - cost
    all_net = all_daily - cost
    bottom_net = bottom_daily - cost

    top_equity = np.cumprod(1 + top_net)
    all_equity = np.cumprod(1 + all_net)
    bottom_equity = np.cumprod(1 + bottom_net)

    top_metrics = perf_metrics(top_net, top_equity)
    all_metrics = perf_metrics(all_net, all_equity)
    bottom_metrics = perf_metrics(bottom_net, bottom_equity)

    print(f"\nHeadline {HEADLINE_WINDOW}-day equity curve comparison ({dates_sorted[0]} to {dates_sorted[-1]}, {COST_BPS}bps cost):")
    for label, m in [("Top tercile (momentum)", top_metrics), ("Equal-weight all", all_metrics), ("Bottom tercile", bottom_metrics)]:
        print(f"  {label:26s} CAGR {m['cagr_pct']:7.2f}%  Vol {m['ann_vol_pct']:6.2f}%  Sharpe {m['sharpe']:5.2f}  MaxDD {m['max_drawdown_pct']:7.2f}%")

    results = {
        "windows_tested_days": WINDOWS,
        "headline_window_days": HEADLINE_WINDOW,
        "min_names_for_sort": MIN_NAMES_FOR_SORT,
        "cost_bps": COST_BPS,
        "by_window": window_results,
        "headline_equity_curve": {
            "start": dates_sorted[0],
            "end": dates_sorted[-1],
            "top_tercile": top_metrics,
            "equal_weight_all": all_metrics,
            "bottom_tercile": bottom_metrics,
        },
    }
    with open(REPORTS_DIR / "overnight_momentum_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    with open(REPORTS_DIR / "overnight_momentum_ledger.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "top_tercile_equity", "equal_weight_all_equity", "bottom_tercile_equity"])
        for i, d in enumerate(dates_sorted):
            writer.writerow([d, top_equity[i], all_equity[i], bottom_equity[i]])

    print(f"\nSaved -> {REPORTS_DIR / 'overnight_momentum_results.json'}")
    print(f"Saved -> {REPORTS_DIR / 'overnight_momentum_ledger.csv'}")


if __name__ == "__main__":
    main()
