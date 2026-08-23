"""
Recency/regime test: has the overnight edge decayed recently?

Motivated by Liberty Street Economics (NY Fed), "The Disappearing
Overnight Drift" (2026): using S&P 500 E-mini futures, they find the
2:00-3:00am ET window (European market open) averaged +3.7%/yr from
1998-2020 but has averaged close to zero since 2021, attributed to a
compression in end-of-day order-imbalance dispersion (algorithmic
liquidity providers slicing flow more finely, reducing the inventory
pressure that used to create the overnight opportunity).

This project only has daily OHLC (no intraday/tick data), so it cannot
isolate that specific 2-3am window. Instead this tests the broader
question with what's available: has the *full* overnight leg (close to
next open) decayed since the same 2021 regime break, and separately,
does the most recent 2 years still show a live edge right now?
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats as scipy_stats

from stats_utils import hac_mean_test
from analyze import benjamini_hochberg

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

TRADING_DAYS_PER_YEAR = 252
REGIME_BREAK_DATE = "2021-01-01"  # matches the NY Fed paper's break
RECENT_WINDOW_DAYS = 2 * TRADING_DAYS_PER_YEAR  # trailing 2 years
BENCHMARK_TICKERS = {"SPY", "QQQ", "MU"}
ROLLING_WINDOW_DAYS = TRADING_DAYS_PER_YEAR * 2  # 2-year rolling window
ROLLING_STEP_DAYS = 21  # ~monthly


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


def leg_stats(returns: np.ndarray):
    n = len(returns)
    if n < 30:
        return None
    hac = hac_mean_test(returns)
    ann_return = (1 + hac["mean"]) ** TRADING_DAYS_PER_YEAR - 1
    return {
        "n": n,
        "ann_return_pct": ann_return * 100,
        "t_stat": hac["t_stat"],
        "p_value": hac["p_value"],
    }


def analyze_ticker(ticker: str):
    dates, opens, closes = load_ticker(ticker)
    overnight = opens[1:] / closes[:-1] - 1.0
    d = dates[1:]

    pre_mask = np.array([dt < REGIME_BREAK_DATE for dt in d])
    post_mask = ~pre_mask

    recent_cutoff_idx = max(0, len(d) - RECENT_WINDOW_DAYS)
    recent = overnight[recent_cutoff_idx:]
    prior = overnight[:recent_cutoff_idx]

    return {
        "ticker": ticker,
        "start": d[0],
        "end": d[-1],
        "full_sample": leg_stats(overnight),
        "pre_2021": leg_stats(overnight[pre_mask]),
        "post_2021": leg_stats(overnight[post_mask]),
        "last_2yr": leg_stats(recent),
        "prior_to_last_2yr": leg_stats(prior),
    }


def rolling_series(ticker: str):
    """Trailing 2-year annualized overnight return, stepped ~monthly."""
    dates, opens, closes = load_ticker(ticker)
    overnight = opens[1:] / closes[:-1] - 1.0
    d = dates[1:]

    points = []
    for end_idx in range(ROLLING_WINDOW_DAYS, len(overnight), ROLLING_STEP_DAYS):
        window = overnight[end_idx - ROLLING_WINDOW_DAYS: end_idx]
        mean = window.mean()
        ann = (1 + mean) ** TRADING_DAYS_PER_YEAR - 1
        points.append({"date": d[end_idx - 1], "ann_return_pct": ann * 100})
    return points


def rolling_value_at_dates(ticker: str, target_dates: list) -> dict:
    """Trailing ROLLING_WINDOW_DAYS-day annualized overnight return for
    `ticker`, evaluated at each of `target_dates` (a shared date grid,
    e.g. SPY's own rolling check-in dates) rather than this ticker's own
    independently-stepped grid. An earlier version averaged tickers'
    rolling_series() output by positional index against SPY's date axis;
    since each ticker's own series starts at a different calendar date,
    that lined up different real dates under the same index and
    misrepresented the cross-sectional mean line. Returns
    {date: ann_return_pct} only for dates this ticker both reaches (has
    >= ROLLING_WINDOW_DAYS of prior history) and was already trading on."""
    dates, opens, closes = load_ticker(ticker)
    overnight = opens[1:] / closes[:-1] - 1.0
    d = dates[1:]
    date_to_idx = {date: i for i, date in enumerate(d)}

    out = {}
    for date in target_dates:
        idx = date_to_idx.get(date)
        if idx is None or idx + 1 < ROLLING_WINDOW_DAYS:
            continue
        window = overnight[idx + 1 - ROLLING_WINDOW_DAYS: idx + 1]
        ann = (1 + window.mean()) ** TRADING_DAYS_PER_YEAR - 1
        out[date] = ann * 100
    return out


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    tickers = [t for group in universe.values() for t in group]

    per_ticker = {}
    for ticker in tickers:
        if not (DATA_DIR / f"{ticker}.csv").exists():
            continue
        per_ticker[ticker] = analyze_ticker(ticker)
        r = per_ticker[ticker]
        pre = r["pre_2021"]
        post = r["post_2021"]
        pre_str = f"{pre['ann_return_pct']:6.1f}%(t={pre['t_stat']:5.2f},n={pre['n']:5d})" if pre else "   n/a"
        post_str = f"{post['ann_return_pct']:6.1f}%(t={post['t_stat']:5.2f},n={post['n']:5d})" if post else "   n/a"
        print(f"{ticker:6s} pre-2021={pre_str}   post-2021={post_str}")

    cross_tickers = [t for t in per_ticker if t not in BENCHMARK_TICKERS]

    pre_ann = np.array([per_ticker[t]["pre_2021"]["ann_return_pct"] for t in cross_tickers if per_ticker[t]["pre_2021"]])
    post_ann = np.array([per_ticker[t]["post_2021"]["ann_return_pct"] for t in cross_tickers if per_ticker[t]["post_2021"]])
    # paired only over tickers that have both
    paired_tickers = [t for t in cross_tickers if per_ticker[t]["pre_2021"] and per_ticker[t]["post_2021"]]
    pre_paired = np.array([per_ticker[t]["pre_2021"]["ann_return_pct"] for t in paired_tickers])
    post_paired = np.array([per_ticker[t]["post_2021"]["ann_return_pct"] for t in paired_tickers])
    decay_t, decay_p = scipy_stats.ttest_rel(pre_paired, post_paired)

    post_p_values = [per_ticker[t]["post_2021"]["p_value"] for t in paired_tickers]
    n_post_significant = int(np.sum([
        per_ticker[t]["post_2021"]["p_value"] < 0.05 and per_ticker[t]["post_2021"]["ann_return_pct"] > 0
        for t in paired_tickers
    ]))
    post_sig_idx, post_expected_fp = benjamini_hochberg(post_p_values)
    n_post_significant_bh = len(post_sig_idx)

    last2yr_tickers = [t for t in cross_tickers if per_ticker[t]["last_2yr"]]
    last2yr_ann = np.array([per_ticker[t]["last_2yr"]["ann_return_pct"] for t in last2yr_tickers])
    n_last2yr_significant = int(np.sum([
        per_ticker[t]["last_2yr"]["p_value"] < 0.05 and per_ticker[t]["last_2yr"]["ann_return_pct"] > 0
        for t in last2yr_tickers
    ]))

    summary = {
        "regime_break_date": REGIME_BREAK_DATE,
        "n_tickers_paired": len(paired_tickers),
        "mean_ann_return_pre_2021_pct": float(pre_paired.mean()),
        "mean_ann_return_post_2021_pct": float(post_paired.mean()),
        "pre_vs_post_2021_paired_t": float(decay_t),
        "pre_vs_post_2021_paired_p": float(decay_p),
        "n_tickers_still_significant_post_2021": n_post_significant,
        "n_tickers_still_significant_post_2021_after_bh_fdr": n_post_significant_bh,
        "post_2021_expected_false_positives_at_5pct_by_chance": float(post_expected_fp),
        "n_tickers_paired_post_2021": len(paired_tickers),
        "mean_ann_return_last_2yr_pct": float(last2yr_ann.mean()),
        "n_tickers_still_significant_last_2yr": n_last2yr_significant,
        "n_tickers_last_2yr": len(last2yr_tickers),
    }

    print("\n=== RECENCY SUMMARY ===")
    print(json.dumps(summary, indent=2))

    # Rolling time series for the market benchmarks + cross-sectional mean
    rolling = {}
    for ticker in ["SPY", "QQQ", "MU", "TSLA", "NVDA", "AVGO"]:
        if ticker in per_ticker:
            rolling[ticker] = rolling_series(ticker)

    # Cross-sectional mean rolling series, evaluated at SPY's own rolling
    # check-in dates: each ticker's trailing-window value is looked up by
    # actual calendar date (rolling_value_at_dates), not by position in its
    # own independently-stepped series, so tickers with different start
    # dates are compared date-for-date rather than offset-for-offset.
    ref_dates = [p["date"] for p in rolling.get("SPY", [])]
    per_ticker_asof = {t: rolling_value_at_dates(t, ref_dates) for t in cross_tickers}
    cross_mean_series = []
    for date in ref_dates:
        vals = [per_ticker_asof[t][date] for t in cross_tickers if date in per_ticker_asof[t]]
        if vals:
            cross_mean_series.append({"date": date, "ann_return_pct": float(np.mean(vals))})
    rolling["cross_sectional_mean"] = cross_mean_series

    with open(REPORTS_DIR / "recency_results.json", "w") as f:
        json.dump({"per_ticker": per_ticker, "summary": summary, "rolling": rolling}, f, indent=2, default=str)

    print(f"\nSaved -> {REPORTS_DIR / 'recency_results.json'}")


if __name__ == "__main__":
    main()
