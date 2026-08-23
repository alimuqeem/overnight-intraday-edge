"""
Out-of-sample validation for the trailing overnight-momentum overlay
(overnight_momentum_analysis.py), which reports a headline Sharpe of 1.16
for the 21-day lookback, discovered in-sample across the whole 1993-2026
(or 1972-2026, full-history) window. background/independent_review.md
flags this directly: "there is no out-of-sample or walk-forward test
anywhere in this project... 'Sharpe 1.16' shouldn't be treated as an
achievable number until it's tested on a genuine holdout period."

This reuses overnight_momentum_analysis.py's signal construction and
tercile-sort logic rather than duplicating it: the tercile sort at each
date only depends on that date's own cross-section (no lookback into
other dates' sort decisions), so it's computed once per candidate window
over the full history, and every test below is a date-range slice of
those already-causal daily return series -- not a re-fit.

Three tests, per the spec:
  1. Standard holdout: pick the best lookback (5/21/63 days) using only
     1993-2010 data, then report that pick's performance on the
     genuinely-unseen 2011-2026 period.
  2. Purged 5-fold walk-forward selection: same idea repeated 5 times
     over rolling calendar folds, each with a 5-trading-day purge buffer
     (translated from the headline 21-day window's trading calendar and
     applied uniformly to all three candidate windows) trimmed from the
     training folds around the held-out fold's boundary, to prevent a
     signal window from straddling the train/test split.
  3. Deflated Sharpe Ratio (Bailey & Lopez de Prado): the observed 1.16
     Sharpe is checked against the Sharpe expected under the null of
     "best-of-3 independent trials with zero true skill", accounting for
     the return series' actual skew/kurtosis, not just multiple-testing
     alpha inflation the way Benjamini-Hochberg (used elsewhere in this
     project) does for the ticker-level cross-section.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import kurtosis, norm, skew

from overnight_momentum_analysis import (
    BENCHMARK_TICKERS,
    COST_BPS,
    HEADLINE_WINDOW,
    TRADING_DAYS_PER_YEAR,
    WINDOWS,
    build_overnight_series,
    cross_sectional_tercile_test,
    perf_metrics,
)
from stats_utils import hac_mean_test

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

IN_SAMPLE_START = "1993-01-01"
IN_SAMPLE_END = "2010-12-31"
OUT_OF_SAMPLE_START = "2011-01-01"

N_FOLDS = 5
PURGE_TRADING_DAYS = 5
EULER_MASCHERONI = 0.5772156649015329


def date_mask(dates: list, lo: str | None = None, hi: str | None = None) -> np.ndarray:
    return np.array([(lo is None or d >= lo) and (hi is None or d <= hi) for d in dates])


def sub_period_stats(dates: list, top: np.ndarray, bottom: np.ndarray, mask: np.ndarray):
    """Net-of-cost top-tercile performance plus the HAC-robust top-minus-
    bottom spread test, restricted to `mask`."""
    top_sub, bottom_sub = top[mask], bottom[mask]
    if len(top_sub) < 30:
        return None
    cost = COST_BPS / 10_000.0
    net = top_sub - cost
    equity = np.cumprod(1 + net)
    m = perf_metrics(net, equity)
    spread_hac = hac_mean_test(top_sub - bottom_sub)
    return {
        "n_days": int(mask.sum()),
        "start": dates[np.argmax(mask)] if mask.any() else None,
        "end": dates[len(mask) - 1 - np.argmax(mask[::-1])] if mask.any() else None,
        "cagr_pct": m["cagr_pct"],
        "sharpe": m["sharpe"],
        "max_drawdown_pct": m["max_drawdown_pct"],
        "spread_ann_pct": ((1 + spread_hac["mean"]) ** TRADING_DAYS_PER_YEAR - 1) * 100,
        "spread_t_stat": spread_hac["t_stat"],
        "spread_p_value": spread_hac["p_value"],
    }


def standard_holdout(window_data: dict):
    by_window = {}
    for w in WINDOWS:
        dates, top, bottom = window_data[w]
        is_mask = date_mask(dates, lo=IN_SAMPLE_START, hi=IN_SAMPLE_END)
        oos_mask = date_mask(dates, lo=OUT_OF_SAMPLE_START)
        by_window[str(w)] = {
            "in_sample": sub_period_stats(dates, top, bottom, is_mask),
            "out_of_sample": sub_period_stats(dates, top, bottom, oos_mask),
        }

    selected = max(WINDOWS, key=lambda w: by_window[str(w)]["in_sample"]["sharpe"])
    return {
        "in_sample_window": [IN_SAMPLE_START, IN_SAMPLE_END],
        "out_of_sample_window_start": OUT_OF_SAMPLE_START,
        "by_window": by_window,
        "selected_window_days": selected,
        "selected_matches_headline": selected == HEADLINE_WINDOW,
        "selected_out_of_sample": by_window[str(selected)]["out_of_sample"],
        "headline_out_of_sample": by_window[str(HEADLINE_WINDOW)]["out_of_sample"],
    }


def fold_boundaries(reference_dates: list, n_folds: int = N_FOLDS):
    n = len(reference_dates)
    edges = [round(i * n / n_folds) for i in range(n_folds + 1)]
    return [(reference_dates[edges[k]], reference_dates[edges[k + 1] - 1]) for k in range(n_folds)]


def purge_cutoff(reference_dates: list, boundary_date: str, direction: str, purge_days: int = PURGE_TRADING_DAYS) -> str:
    idx = reference_dates.index(boundary_date)
    if direction == "before":
        return reference_dates[max(0, idx - purge_days)]
    return reference_dates[min(len(reference_dates) - 1, idx + purge_days)]


def purged_kfold(window_data: dict):
    reference_dates = window_data[HEADLINE_WINDOW][0]
    bounds = fold_boundaries(reference_dates)

    by_fold = []
    for k, (lo, hi) in enumerate(bounds):
        purge_lo = purge_cutoff(reference_dates, lo, "before")
        purge_hi = purge_cutoff(reference_dates, hi, "after")

        fold_by_window = {}
        for w in WINDOWS:
            dates, top, bottom = window_data[w]
            test_mask = date_mask(dates, lo=lo, hi=hi)
            train_mask = ~date_mask(dates, lo=purge_lo, hi=purge_hi)
            train_stats = sub_period_stats(dates, top, bottom, train_mask)
            test_stats = sub_period_stats(dates, top, bottom, test_mask)
            fold_by_window[str(w)] = {"train": train_stats, "test": test_stats}

        valid_windows = [w for w in WINDOWS if fold_by_window[str(w)]["train"] is not None]
        selected = max(valid_windows, key=lambda w: fold_by_window[str(w)]["train"]["sharpe"])
        by_fold.append({
            "fold": k,
            "test_start": lo,
            "test_end": hi,
            "purge_train_excluded_range": [purge_lo, purge_hi],
            "by_window": fold_by_window,
            "selected_window_days": selected,
            "selected_train_sharpe": fold_by_window[str(selected)]["train"]["sharpe"],
            "selected_test_sharpe": fold_by_window[str(selected)]["test"]["sharpe"] if fold_by_window[str(selected)]["test"] else None,
        })

    selected_test_sharpes = [f["selected_test_sharpe"] for f in by_fold if f["selected_test_sharpe"] is not None]
    return {
        "n_folds": N_FOLDS,
        "purge_trading_days": PURGE_TRADING_DAYS,
        "reference_window_days": HEADLINE_WINDOW,
        "by_fold": by_fold,
        "mean_selected_test_sharpe": float(np.mean(selected_test_sharpes)) if selected_test_sharpes else None,
        "pct_folds_selecting_headline_window": float(
            np.mean([f["selected_window_days"] == HEADLINE_WINDOW for f in by_fold]) * 100
        ),
    }


def deflated_sharpe_ratio(window_data: dict):
    """Bailey & Lopez de Prado (2014) DSR: deflates the headline window's
    Sharpe ratio for (a) having been the best-looking of N=3 tested
    lookbacks (multiple-trials selection bias) and (b) the return
    series' actual skew/kurtosis, not the normal-distribution assumption
    a plain Sharpe ratio implicitly makes."""
    daily_sharpe = {}
    trial_stats = {}
    for w in WINDOWS:
        dates, top, bottom = window_data[w]
        cost = COST_BPS / 10_000.0
        net = top - cost
        sr = net.mean() / net.std(ddof=1)
        daily_sharpe[w] = sr
        trial_stats[w] = {
            "n_days": len(net),
            "daily_sharpe": sr,
            "annualized_sharpe": sr * np.sqrt(TRADING_DAYS_PER_YEAR),
            "skew": float(skew(net)),
            "kurtosis": float(kurtosis(net, fisher=False)),
        }

    n_trials = len(WINDOWS)
    sr_values = np.array(list(daily_sharpe.values()))
    var_sr = sr_values.var(ddof=1)
    # Expected max Sharpe under the null of n_trials independent, zero-skill
    # trials (Bailey & Lopez de Prado eq. 8).
    sr_benchmark = np.sqrt(var_sr) * (
        (1 - EULER_MASCHERONI) * norm.ppf(1 - 1 / n_trials)
        + EULER_MASCHERONI * norm.ppf(1 - 1 / (n_trials * np.e))
    )

    by_window = {}
    for w in WINDOWS:
        s = trial_stats[w]
        sr_hat = s["daily_sharpe"]
        t = s["n_days"]
        gamma3, gamma4 = s["skew"], s["kurtosis"]
        denom = np.sqrt(max(1 - gamma3 * sr_hat + (gamma4 - 1) / 4 * sr_hat ** 2, 1e-12))
        z = (sr_hat - sr_benchmark) * np.sqrt(t - 1) / denom
        by_window[str(w)] = {**s, "dsr": float(norm.cdf(z))}

    return {
        "n_trials": n_trials,
        "sr_benchmark_expected_max_under_null": float(sr_benchmark),
        "by_window": by_window,
        "headline_window_days": HEADLINE_WINDOW,
        "headline_dsr": by_window[str(HEADLINE_WINDOW)]["dsr"],
    }


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    cross_tickers = [t for group in universe.values() for t in group if t not in BENCHMARK_TICKERS]

    print(f"Building overnight-return series for {len(cross_tickers)} tickers...")
    series = build_overnight_series(cross_tickers)

    window_data = {}
    for w in WINDOWS:
        print(f"Computing {w}-day tercile sort (full history, reused for all sub-period slices)...")
        _, dates_sorted, top_daily, bottom_daily, _ = cross_sectional_tercile_test(series, w)
        window_data[w] = (dates_sorted, top_daily, bottom_daily)

    print("\n=== Standard holdout: 1993-2010 in-sample, 2011-2026 out-of-sample ===")
    holdout = standard_holdout(window_data)
    for w in WINDOWS:
        is_, oos = holdout["by_window"][str(w)]["in_sample"], holdout["by_window"][str(w)]["out_of_sample"]
        print(f"  {w:2d}-day: IS Sharpe {is_['sharpe']:5.2f} (n={is_['n_days']})   "
              f"OOS Sharpe {oos['sharpe']:5.2f} (n={oos['n_days']})")
    print(f"  Selected by in-sample Sharpe: {holdout['selected_window_days']}-day "
          f"(matches headline: {holdout['selected_matches_headline']})")
    print(f"  Selected window's OOS Sharpe: {holdout['selected_out_of_sample']['sharpe']:.2f}")

    print("\n=== Purged 5-fold walk-forward selection ===")
    kfold = purged_kfold(window_data)
    for f in kfold["by_fold"]:
        print(f"  Fold {f['fold']} ({f['test_start']} to {f['test_end']}): "
              f"selected {f['selected_window_days']}-day (train Sharpe {f['selected_train_sharpe']:.2f}) "
              f"-> test Sharpe {f['selected_test_sharpe']:.2f}" if f['selected_test_sharpe'] is not None
              else f"  Fold {f['fold']}: insufficient test-fold data")
    print(f"  Mean selected-window test Sharpe across folds: {kfold['mean_selected_test_sharpe']:.2f}")
    print(f"  % of folds selecting the headline {HEADLINE_WINDOW}-day window: {kfold['pct_folds_selecting_headline_window']:.0f}%")

    print("\n=== Deflated Sharpe Ratio (N=3 trials: 5/21/63-day lookbacks) ===")
    dsr = deflated_sharpe_ratio(window_data)
    print(f"  Benchmark (expected max Sharpe under null, N=3): {dsr['sr_benchmark_expected_max_under_null']:.4f} (daily)")
    for w in WINDOWS:
        d = dsr["by_window"][str(w)]
        print(f"  {w:2d}-day: annualized Sharpe {d['annualized_sharpe']:5.2f}  skew {d['skew']:6.2f}  "
              f"kurtosis {d['kurtosis']:6.2f}  DSR {d['dsr']:.4f}")

    results = {
        "windows_tested_days": WINDOWS,
        "headline_window_days": HEADLINE_WINDOW,
        "cost_bps": COST_BPS,
        "standard_holdout": holdout,
        "purged_kfold": kfold,
        "deflated_sharpe_ratio": dsr,
    }
    with open(REPORTS_DIR / "walk_forward_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved -> {REPORTS_DIR / 'walk_forward_results.json'}")


if __name__ == "__main__":
    main()
