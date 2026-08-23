"""
Correlation structure and tail-risk profile of the overnight leg.

The portfolio backtest's headline selling point (background/portfolio_backtest.md)
is that the equal-weight overnight book has roughly half SPY's volatility and a
better Sharpe ratio. That claim is only as good as the assumption that the 30
overnight legs are weakly correlated with each other -- if they mostly move
together (e.g. everything gaps down on the same macro nights), the book has far
fewer independent bets than its 30 names suggest, and Sharpe-style risk-adjusted
comparisons understate its true tail risk.

This script answers two distinct questions with the data already on disk:

  1. Correlation / effective bets: build the cross-sectional correlation
     matrix of the 30 tickers' daily overnight (and, for comparison,
     intraday) returns, then use the eigenvalue spectrum to compute the
     "effective number of independent bets" (Meucci's principal-component
     participation-ratio measure: PR = n^2 / sum(eigenvalues^2), bounded
     between 1 -- a single common factor -- and n = 30 -- fully
     uncorrelated). A portfolio's realized volatility only diversifies down
     by roughly sqrt(effective bets), not sqrt(30).

  2. Tail risk: the Sharpe ratio is a second-moment (mean/std) statistic and
     is blind to skew and kurtosis. execution_mechanics.md already flags,
     in prose, that an overnight position cannot be exited if a macro shock
     hits while the market is closed -- this script quantifies that: per-
     ticker and portfolio-level skewness, excess kurtosis, historical CVaR
     (expected shortfall) at the 1% and 5% tails, and a worst-10-days table,
     each compared against the intraday leg and against what a Gaussian
     distribution with the same mean/vol would predict.

Reuses portfolio_backtest.run_backtest (cost_bps=0) for the equal-weight,
staggered-entry portfolio return series, so the "portfolio" tail-risk numbers
here are for the same book already analyzed in the backtest, not a new
construction.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from scipy import stats

from portfolio_backtest import load_ohlc, run_backtest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

TRADING_DAYS_PER_YEAR = 252
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


def leg_series(ticker: str):
    """Returns (dict date->overnight_return, dict date->intraday_return)."""
    dates, opens, closes = load_ticker(ticker)
    overnight = opens[1:] / closes[:-1] - 1.0
    intraday = closes / opens - 1.0
    on_dict = dict(zip(dates[1:], overnight))
    id_dict = dict(zip(dates, intraday))
    return on_dict, id_dict


def correlation_block(leg_dicts: dict, tickers: list):
    """Common-date correlation matrix + eigenvalue-based effective-bets
    measure for a dict of {ticker: {date: return}}."""
    common_dates = None
    for t in tickers:
        d = set(leg_dicts[t].keys())
        common_dates = d if common_dates is None else common_dates & d
    common_dates = sorted(common_dates)

    matrix = np.array([[leg_dicts[t][d] for d in common_dates] for t in tickers])
    corr = np.corrcoef(matrix)
    n = len(tickers)
    off_diag_sum = corr.sum() - np.trace(corr)
    mean_pairwise_corr = off_diag_sum / (n * (n - 1))

    eigenvalues = np.linalg.eigvalsh(corr)[::-1]  # descending
    eigenvalues = np.clip(eigenvalues, 0, None)  # guard tiny negative numerical noise
    participation_ratio = (eigenvalues.sum() ** 2) / (eigenvalues ** 2).sum()
    pc1_variance_share_pct = eigenvalues[0] / n * 100

    return {
        "window_start": common_dates[0],
        "window_end": common_dates[-1],
        "n_common_days": len(common_dates),
        "n_tickers": n,
        "mean_pairwise_correlation": float(mean_pairwise_corr),
        "pc1_variance_share_pct": float(pc1_variance_share_pct),
        "effective_number_of_bets": float(participation_ratio),
        "top_5_eigenvalues": [float(e) for e in eigenvalues[:5]],
    }


def tail_stats(returns: np.ndarray):
    n = len(returns)
    mean, std = returns.mean(), returns.std(ddof=1)
    var_1pct = np.percentile(returns, 1)
    var_5pct = np.percentile(returns, 5)
    cvar_1pct = returns[returns <= var_1pct].mean()
    cvar_5pct = returns[returns <= var_5pct].mean()
    gaussian_cvar_1pct = mean - std * stats.norm.pdf(stats.norm.ppf(0.01)) / 0.01
    fat_tail_multiple = cvar_1pct / gaussian_cvar_1pct if gaussian_cvar_1pct != 0 else float("nan")
    return {
        "n": n,
        "skewness": float(stats.skew(returns)),
        "excess_kurtosis": float(stats.kurtosis(returns)),
        "cvar_1pct_bps": float(cvar_1pct * 10_000),
        "cvar_5pct_bps": float(cvar_5pct * 10_000),
        "gaussian_cvar_1pct_bps": float(gaussian_cvar_1pct * 10_000),
        "fat_tail_multiple_vs_gaussian": float(fat_tail_multiple),
        "worst_single_day_pct": float(returns.min() * 100),
        "best_single_day_pct": float(returns.max() * 100),
    }


def worst_n_days(dates: list, returns: np.ndarray, n: int = 10):
    idx = np.argsort(returns)[:n]
    return [{"date": dates[i], "return_pct": float(returns[i] * 100)} for i in idx]


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    cross_tickers = [t for group in universe.values() for t in group if t not in BENCHMARK_TICKERS]

    print(f"Loading overnight/intraday leg series for {len(cross_tickers)} tickers...")
    on_dicts, id_dicts = {}, {}
    for t in cross_tickers:
        on_dicts[t], id_dicts[t] = leg_series(t)

    print("\nBuilding correlation matrices on the common-date window across all 30 names...")
    on_corr = correlation_block(on_dicts, cross_tickers)
    id_corr = correlation_block(id_dicts, cross_tickers)
    print(f"  Common window: {on_corr['window_start']} to {on_corr['window_end']} ({on_corr['n_common_days']} days)")
    print(f"  Overnight: mean pairwise corr {on_corr['mean_pairwise_correlation']:.3f}, "
          f"PC1 variance share {on_corr['pc1_variance_share_pct']:.1f}%, "
          f"effective independent bets {on_corr['effective_number_of_bets']:.1f} of {len(cross_tickers)}")
    print(f"  Intraday:  mean pairwise corr {id_corr['mean_pairwise_correlation']:.3f}, "
          f"PC1 variance share {id_corr['pc1_variance_share_pct']:.1f}%, "
          f"effective independent bets {id_corr['effective_number_of_bets']:.1f} of {len(cross_tickers)}")

    print("\nPer-ticker tail-risk stats (full available history per ticker)...")
    per_ticker_tail = {}
    for t in cross_tickers:
        dates, opens, closes = load_ticker(t)
        overnight = opens[1:] / closes[:-1] - 1.0
        intraday = closes / opens - 1.0
        per_ticker_tail[t] = {
            "overnight": tail_stats(overnight),
            "intraday": tail_stats(intraday),
        }
        ov, iv = per_ticker_tail[t]["overnight"], per_ticker_tail[t]["intraday"]
        print(f"  {t:6s} overnight skew={ov['skewness']:6.2f} kurt={ov['excess_kurtosis']:7.2f} "
              f"CVaR1%={ov['cvar_1pct_bps']:8.1f}bps  |  intraday skew={iv['skewness']:6.2f} kurt={iv['excess_kurtosis']:7.2f}")

    print("\nPortfolio-level tail risk (equal-weight, staggered entry, same book as portfolio_backtest.py, 0bps cost)...")
    tickers_ohlc = {t: load_ohlc(t) for t in cross_tickers}
    spy_ohlc = load_ohlc("SPY")
    dates = sorted(spy_ohlc.keys())
    on_ret, on_equity, id_ret, id_equity, n_members = run_backtest(tickers_ohlc, dates, cost_bps=0.0)

    on_ret_valid = on_ret[n_members > 0]
    id_ret_valid = id_ret[n_members > 0]
    dates_valid = [d for d, n in zip(dates, n_members) if n > 0]

    portfolio_on_tail = tail_stats(on_ret_valid)
    portfolio_id_tail = tail_stats(id_ret_valid)
    portfolio_on_worst = worst_n_days(dates_valid, on_ret_valid, 10)
    portfolio_id_worst = worst_n_days(dates_valid, id_ret_valid, 10)

    print(f"  Overnight portfolio: skew={portfolio_on_tail['skewness']:.2f} "
          f"kurt={portfolio_on_tail['excess_kurtosis']:.2f} "
          f"CVaR1%={portfolio_on_tail['cvar_1pct_bps']:.1f}bps "
          f"(Gaussian-implied {portfolio_on_tail['gaussian_cvar_1pct_bps']:.1f}bps, "
          f"{portfolio_on_tail['fat_tail_multiple_vs_gaussian']:.2f}x)")
    print(f"  Intraday portfolio:  skew={portfolio_id_tail['skewness']:.2f} "
          f"kurt={portfolio_id_tail['excess_kurtosis']:.2f} "
          f"CVaR1%={portfolio_id_tail['cvar_1pct_bps']:.1f}bps "
          f"(Gaussian-implied {portfolio_id_tail['gaussian_cvar_1pct_bps']:.1f}bps, "
          f"{portfolio_id_tail['fat_tail_multiple_vs_gaussian']:.2f}x)")
    print("  Worst 10 overnight-portfolio days:")
    for row in portfolio_on_worst:
        print(f"    {row['date']}  {row['return_pct']:7.2f}%")

    results = {
        "correlation": {
            "overnight": on_corr,
            "intraday": id_corr,
        },
        "per_ticker_tail_risk": per_ticker_tail,
        "portfolio_tail_risk": {
            "overnight": {**portfolio_on_tail, "worst_10_days": portfolio_on_worst},
            "intraday": {**portfolio_id_tail, "worst_10_days": portfolio_id_worst},
        },
    }
    with open(REPORTS_DIR / "correlation_tail_risk_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved -> {REPORTS_DIR / 'correlation_tail_risk_results.json'}")


if __name__ == "__main__":
    main()
