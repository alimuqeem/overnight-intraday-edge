"""
Overnight vs. intraday return decomposition and edge test.

For each ticker, splits every trading day's return into two legs:
  - overnight: prev_close -> today_open  (held while market is closed)
  - intraday:  today_open  -> today_close (held while market is open)

Then tests whether either leg carries a statistically and economically
significant edge, both per-ticker and pooled across the universe, and
checks whether the effect survives (a) realistic transaction costs,
(b) a split into two non-overlapping sub-periods, and (c) controlling for
known equity risk factors (market, size, value, momentum) via a HAC-robust
factor regression -- so the effect isn't just repackaged momentum exposure.

Methodology notes (v2, after an institutional-review pass):
  - Price data is dividend+split adjusted (see fetch_data.py) -- an
    earlier version used raw Close/unadjusted Open, which put the ex-
    dividend price drop mechanically into the overnight leg and inflated
    the apparent overnight edge for high-yield sectors.
  - All significance tests use Newey-West HAC standard errors (see
    stats_utils.py), not naive std/sqrt(n) -- daily returns are
    autocorrelated and volatility-clustered, so naive t-tests overstate
    significance given n in the thousands.
  - Cross-sectional pooling excludes SPY, QQQ, and MU: SPY/QQQ are
    baskets of (overlapping with) the other constituents, and MU was the
    hand-picked motivating case for this whole project -- pooling either
    into "how many of N tickers show this" double-counts or cherry-picks.
    They're still analyzed and reported individually.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

from stats_utils import hac_mean_test, hac_ols

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
REPORTS_DIR.mkdir(exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)

TRADING_DAYS_PER_YEAR = 252

# SPY/QQQ are baskets that overlap with the other 30 constituents, and MU
# was the hand-picked motivating case -- excluded from cross-sectional
# pooling to avoid double-counting/selection bias, but still analyzed and
# reported individually.
BENCHMARK_TICKERS = {"SPY", "QQQ", "MU"}


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


def load_factors():
    path = DATA_DIR / "factors" / "ff_factors_daily.csv"
    factors = {}
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            factors[row["date"]] = {
                "mkt_rf": float(row["mkt_rf"]),
                "smb": float(row["smb"]),
                "hml": float(row["hml"]),
                "mom": float(row["mom"]),
                "rf": float(row["rf"]),
            }
    return factors


def compute_legs(dates, opens, closes):
    """Return (dates_for_overnight, overnight_returns, intraday_returns)."""
    overnight = opens[1:] / closes[:-1] - 1.0
    intraday = closes / opens - 1.0
    return dates[1:], overnight, intraday


def leg_stats(returns: np.ndarray, cost_bps: float = 0.0):
    """Summary stats for one leg's daily return series, net of a flat
    per-trade round-trip cost expressed in basis points. Significance is
    Newey-West HAC-robust (see module docstring)."""
    net = returns - cost_bps / 10_000.0
    n = len(net)
    std = net.std(ddof=1)
    hac = hac_mean_test(net)
    mean = hac["mean"]
    ann_return = (1 + mean) ** TRADING_DAYS_PER_YEAR - 1
    ann_vol = std * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (mean * TRADING_DAYS_PER_YEAR) / ann_vol if ann_vol > 0 else float("nan")
    win_rate = (net > 0).mean()
    compound = np.prod(1 + net) - 1
    return {
        "n": n,
        "mean_daily_bps": mean * 10_000,
        "ann_return_pct": ann_return * 100,
        "ann_vol_pct": ann_vol * 100,
        "sharpe": sharpe,
        "t_stat": hac["t_stat"],
        "p_value": hac["p_value"],
        "hac_lags": hac["lags_used"],
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


def factor_regression(leg_dates, leg_returns, factors):
    """Regress a leg's daily returns on [Mkt-RF, SMB, HML, Mom] with a
    HAC-robust intercept (alpha). Tests whether the leg's return is
    distinct from known risk-factor exposure, not just repackaged
    momentum/market beta. Returns None if too few overlapping dates."""
    rows = []
    for d, r in zip(leg_dates, leg_returns):
        f = factors.get(d)
        if f is None:
            continue
        rows.append((r - f["rf"], f["mkt_rf"], f["smb"], f["hml"], f["mom"]))

    if len(rows) < 250:
        return None

    arr = np.array(rows)
    y = arr[:, 0]
    X = np.column_stack([np.ones(len(arr)), arr[:, 1:]])
    out = hac_ols(y, X)

    labels = ["alpha", "mkt_rf", "smb", "hml", "mom"]
    result = {"n": out["n"], "lags_used": out["lags_used"], "r_squared": out["r_squared"]}
    for i, label in enumerate(labels):
        result[label] = out["coefs"][i]
        result[f"{label}_t"] = out["t_stat"][i]
        result[f"{label}_p"] = out["p_value"][i]
    result["alpha_ann_pct"] = ((1 + out["coefs"][0]) ** TRADING_DAYS_PER_YEAR - 1) * 100
    return result


def spy_buyhold_benchmark():
    """Realized buy-and-hold CAGR for SPY over this project's full sample
    window (first open to last close), used as the long-term S&P 500
    reference line on the annualized-return charts. This is realized
    CAGR (total_return ** (1/years) - 1), not the mean-daily-return
    annualization used for the overnight/intraday legs elsewhere in this
    module, so it lines up with the commonly quoted "~10%/year" long-run
    S&P 500 figure rather than running hot the way mean-of-daily-returns
    annualization does under volatility drag."""
    dates, opens, closes = load_ticker("SPY")
    years = len(dates) / TRADING_DAYS_PER_YEAR
    total_return = closes[-1] / opens[0]
    cagr = total_return ** (1 / years) - 1
    return {
        "cagr_pct": cagr * 100,
        "start": dates[0],
        "end": dates[-1],
        "years": years,
    }


def analyze_ticker(ticker: str, factors: dict):
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
        "overnight_factor_regression": factor_regression(d, overnight, factors),
        "intraday_factor_regression": factor_regression(d, intraday, factors),
    }

    # Sub-period split: first half vs second half of available history,
    # to check the effect isn't an artifact of one regime.
    mid = len(d) // 2
    result["overnight_first_half"] = leg_stats(overnight[:mid])
    result["overnight_second_half"] = leg_stats(overnight[mid:])
    result["intraday_first_half"] = leg_stats(intraday[:mid])
    result["intraday_second_half"] = leg_stats(intraday[mid:])

    return result, overnight, intraday, d


def benjamini_hochberg(p_values: list, alpha: float = 0.05):
    """Returns the set of indices (into p_values) that remain significant
    after Benjamini-Hochberg false-discovery-rate control, and the
    expected number of false positives at alpha under pure chance."""
    m = len(p_values)
    order = np.argsort(p_values)
    sorted_p = np.array(p_values)[order]
    thresholds = alpha * (np.arange(1, m + 1) / m)
    below = sorted_p <= thresholds
    if not below.any():
        significant_idx = set()
    else:
        max_k = np.max(np.where(below)[0])
        significant_idx = set(order[: max_k + 1].tolist())
    expected_false_positives = alpha * m
    return significant_idx, expected_false_positives


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)

    factors = load_factors()
    print(f"Loaded {len(factors)} days of Fama-French factor data")

    per_ticker = {}
    cross_section_tickers = []  # excludes BENCHMARK_TICKERS

    for sector, tickers in universe.items():
        for ticker in tickers:
            path = DATA_DIR / f"{ticker}.csv"
            if not path.exists():
                print(f"SKIP {ticker}: no data")
                continue
            out = analyze_ticker(ticker, factors)
            if out is None:
                print(f"SKIP {ticker}: insufficient data")
                continue
            result, overnight, intraday, d = out
            result["sector"] = sector
            per_ticker[ticker] = result
            if ticker not in BENCHMARK_TICKERS:
                cross_section_tickers.append(ticker)

            fr_on = result["overnight_factor_regression"]
            alpha_str = f"alpha_ann={fr_on['alpha_ann_pct']:6.1f}% (t={fr_on['alpha_t']:5.2f})" if fr_on else "alpha_ann=   n/a"
            print(
                f"{ticker:6s} ({sector[:20]:20s}) "
                f"overnight ann={result['overnight']['ann_return_pct']:9.1f}%  "
                f"t={result['overnight']['t_stat']:6.2f}   "
                f"intraday ann={result['intraday']['ann_return_pct']:9.1f}%  "
                f"t={result['intraday']['t_stat']:6.2f}   "
                f"[factor-adj overnight {alpha_str}]"
            )

    # Cross-sectional tests on the 30-ticker diversified population only
    # (excludes SPY/QQQ/MU -- see BENCHMARK_TICKERS note above).
    overnight_arr = np.array([per_ticker[t]["overnight"]["mean_daily_bps"] for t in cross_section_tickers])
    intraday_arr = np.array([per_ticker[t]["intraday"]["mean_daily_bps"] for t in cross_section_tickers])
    cross_overnight_t, cross_overnight_p = stats.ttest_1samp(overnight_arr, 0)
    cross_intraday_t, cross_intraday_p = stats.ttest_1samp(intraday_arr, 0)
    paired_t, paired_p = stats.ttest_rel(overnight_arr, intraday_arr)

    overnight_p_values = [per_ticker[t]["overnight"]["p_value"] for t in cross_section_tickers]
    intraday_p_values = [per_ticker[t]["intraday"]["p_value"] for t in cross_section_tickers]
    on_sig_idx, on_expected_fp = benjamini_hochberg(overnight_p_values)
    id_sig_idx, id_expected_fp = benjamini_hochberg(intraday_p_values)

    # Factor-regression alpha significance across the cross-section
    on_alphas = [per_ticker[t]["overnight_factor_regression"] for t in cross_section_tickers
                 if per_ticker[t]["overnight_factor_regression"] is not None]
    id_alphas = [per_ticker[t]["intraday_factor_regression"] for t in cross_section_tickers
                 if per_ticker[t]["intraday_factor_regression"] is not None]

    summary = {
        "n_tickers_total": len(per_ticker),
        "n_tickers_cross_section": len(cross_section_tickers),
        "benchmark_tickers_excluded_from_cross_section": sorted(BENCHMARK_TICKERS),
        "spy_buyhold_benchmark": spy_buyhold_benchmark(),
        "cross_sectional_overnight_mean_bps": float(overnight_arr.mean()),
        "cross_sectional_overnight_t": float(cross_overnight_t),
        "cross_sectional_overnight_p": float(cross_overnight_p),
        "cross_sectional_intraday_mean_bps": float(intraday_arr.mean()),
        "cross_sectional_intraday_t": float(cross_intraday_t),
        "cross_sectional_intraday_p": float(cross_intraday_p),
        "paired_overnight_vs_intraday_t": float(paired_t),
        "paired_overnight_vs_intraday_p": float(paired_p),
        "pct_tickers_overnight_positive_significant_uncorrected": float(
            np.mean([per_ticker[t]["overnight"]["t_stat"] > 1.96 for t in cross_section_tickers]) * 100
        ),
        "pct_tickers_intraday_negative_significant_uncorrected": float(
            np.mean([per_ticker[t]["intraday"]["t_stat"] < -1.96 for t in cross_section_tickers]) * 100
        ),
        "n_tickers_overnight_significant_after_bh_fdr": len(on_sig_idx),
        "n_tickers_intraday_significant_after_bh_fdr": len(id_sig_idx),
        "expected_false_positives_at_5pct_by_chance": float(on_expected_fp),
        "median_overnight_breakeven_bps": float(np.median([
            per_ticker[t]["overnight_breakeven_bps"]
            for t in cross_section_tickers if per_ticker[t]["overnight_breakeven_bps"] is not None
        ])),
        "n_overnight_alpha_significant_after_factors": int(np.sum([
            abs(a["alpha_t"]) > 1.96 for a in on_alphas
        ])),
        "n_overnight_alpha_regressions": len(on_alphas),
        "mean_overnight_alpha_ann_pct": float(np.mean([a["alpha_ann_pct"] for a in on_alphas])),
        "n_intraday_alpha_significant_after_factors": int(np.sum([
            abs(a["alpha_t"]) > 1.96 for a in id_alphas
        ])),
        "n_intraday_alpha_regressions": len(id_alphas),
        "mean_intraday_alpha_ann_pct": float(np.mean([a["alpha_ann_pct"] for a in id_alphas])),
        "mean_overnight_mom_loading": float(np.mean([a["mom"] for a in on_alphas])),
        "mean_overnight_mom_loading_t": float(np.mean([a["mom_t"] for a in on_alphas])),
    }

    with open(REPORTS_DIR / "per_ticker_results.json", "w") as f:
        json.dump(per_ticker, f, indent=2, default=str)
    with open(REPORTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n=== CROSS-SECTIONAL SUMMARY (30-ticker diversified population, excl. SPY/QQQ/MU) ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
