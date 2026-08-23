"""
Does the overnight effect depend on the volatility regime?

Motivated by the same literature already cited in background/literature_review.md:
Berkman et al. (2012) tie the overnight effect to retail-driven attention/
sentiment, and Bondarenko & Muravyev's uncertainty-resolution story predicts
the effect should be strongest when there is the most overnight uncertainty
to resolve by the next open. recency_regime_analysis.md already showed the
effect rotates across calendar time; this asks whether it also rotates with
the market's volatility state, using VIX at the close being bought as the
regime indicator for that overnight leg.

Buckets every overnight-leg observation, pooled across the 30-ticker
cross-section (excl. SPY/QQQ/MU, consistent with analyze.py), by the VIX
close on the buy day (the close date the position is entered), split into
quartiles of the full VIX history's distribution. Runs a HAC-robust mean
test per bucket, plus a HAC-robust regression of the pooled overnight
return on the same day's VIX level and day-over-day VIX change, to see
whether the level or the change in fear is what matters.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from stats_utils import hac_mean_test, hac_ols

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


def load_vix():
    path = DATA_DIR / "VIX.csv"
    vix = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            if not row["close"]:
                continue
            vix[row["date"]] = float(row["close"])
    return vix


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    cross_tickers = [t for group in universe.values() for t in group if t not in BENCHMARK_TICKERS]

    vix = load_vix()
    vix_dates_sorted = sorted(vix.keys())
    vix_levels_all = np.array([vix[d] for d in vix_dates_sorted])
    quartile_edges = np.percentile(vix_levels_all, [25, 50, 75])
    print(f"VIX quartile edges (full 1990-2026 history): {quartile_edges}")

    # Pool (vix_level_on_buy_day, vix_change_on_buy_day, overnight_return)
    # across all 30 tickers, keyed by the buy-day date.
    pooled_vix_level = []
    pooled_vix_change = []
    pooled_overnight = []

    vix_date_to_idx = {d: i for i, d in enumerate(vix_dates_sorted)}
    for ticker in cross_tickers:
        dates, opens, closes = load_ticker(ticker)
        overnight = opens[1:] / closes[:-1] - 1.0
        buy_dates = dates[:-1]
        for d, r in zip(buy_dates, overnight):
            if d not in vix_date_to_idx:
                continue
            idx = vix_date_to_idx[d]
            level = vix_levels_all[idx]
            change = (vix_levels_all[idx] / vix_levels_all[idx - 1] - 1.0) if idx > 0 else 0.0
            pooled_vix_level.append(level)
            pooled_vix_change.append(change)
            pooled_overnight.append(r)

    pooled_vix_level = np.array(pooled_vix_level)
    pooled_vix_change = np.array(pooled_vix_change)
    pooled_overnight = np.array(pooled_overnight)
    print(f"Pooled {len(pooled_overnight)} ticker-day overnight observations with matched VIX data")

    # Quartile buckets by VIX *level* on the buy day.
    quartile_labels = ["Q1 (lowest VIX)", "Q2", "Q3", "Q4 (highest VIX)"]
    edges_full = np.concatenate([[-np.inf], quartile_edges, [np.inf]])
    by_quartile = {}
    for i, label in enumerate(quartile_labels):
        mask = (pooled_vix_level > edges_full[i]) & (pooled_vix_level <= edges_full[i + 1])
        rets = pooled_overnight[mask]
        hac = hac_mean_test(rets)
        ann_return = (1 + hac["mean"]) ** TRADING_DAYS_PER_YEAR - 1
        by_quartile[label] = {
            "n": len(rets),
            "vix_range": [float(edges_full[i]), float(edges_full[i + 1])],
            "mean_vix_in_bucket": float(pooled_vix_level[mask].mean()),
            "mean_daily_bps": hac["mean"] * 10_000,
            "ann_return_pct": ann_return * 100,
            "t_stat": hac["t_stat"],
            "p_value": hac["p_value"],
        }
        print(f"  {label:20s} n={len(rets):6d}  mean VIX={pooled_vix_level[mask].mean():5.1f}  "
              f"ann_return={ann_return*100:7.2f}%  t={hac['t_stat']:6.2f}  p={hac['p_value']:.4f}")

    # HAC-robust regression: pooled overnight return on VIX level (scaled)
    # and VIX day-over-day % change.
    X = np.column_stack([
        np.ones(len(pooled_overnight)),
        (pooled_vix_level - pooled_vix_level.mean()) / 10.0,  # per-10-point VIX move
        pooled_vix_change,
    ])
    reg = hac_ols(pooled_overnight, X)
    regression_result = {
        "intercept": float(reg["coefs"][0]),
        "intercept_t": float(reg["t_stat"][0]),
        "vix_level_per_10pt_coef_bps": float(reg["coefs"][1] * 10_000),
        "vix_level_t": float(reg["t_stat"][1]),
        "vix_level_p": float(reg["p_value"][1]),
        "vix_change_coef_bps": float(reg["coefs"][2] * 10_000),
        "vix_change_t": float(reg["t_stat"][2]),
        "vix_change_p": float(reg["p_value"][2]),
        "r_squared": float(reg["r_squared"]),
        "n": int(reg["n"]),
    }
    print("\nHAC-robust regression of pooled overnight return on VIX level (per +10pt) and VIX %change:")
    print(f"  VIX level coef: {regression_result['vix_level_per_10pt_coef_bps']:.2f}bps/10pt "
          f"(t={regression_result['vix_level_t']:.2f}, p={regression_result['vix_level_p']:.4f})")
    print(f"  VIX change coef: {regression_result['vix_change_coef_bps']:.2f}bps per 100% VIX move "
          f"(t={regression_result['vix_change_t']:.2f}, p={regression_result['vix_change_p']:.4f})")

    # High-vs-low split specifically around the VIX 20 "elevated fear"
    # threshold commonly used in practice, distinct from the sample
    # quartiles above (which are relative to this dataset's own history).
    above_20 = pooled_overnight[pooled_vix_level >= 20]
    below_20 = pooled_overnight[pooled_vix_level < 20]
    hac_above = hac_mean_test(above_20)
    hac_below = hac_mean_test(below_20)
    threshold_20_split = {
        "vix_above_20": {
            "n": len(above_20),
            "ann_return_pct": ((1 + hac_above["mean"]) ** TRADING_DAYS_PER_YEAR - 1) * 100,
            "t_stat": hac_above["t_stat"],
            "p_value": hac_above["p_value"],
        },
        "vix_below_20": {
            "n": len(below_20),
            "ann_return_pct": ((1 + hac_below["mean"]) ** TRADING_DAYS_PER_YEAR - 1) * 100,
            "t_stat": hac_below["t_stat"],
            "p_value": hac_below["p_value"],
        },
    }
    print(f"\nVIX >= 20 (elevated fear): n={len(above_20)} ann_return={threshold_20_split['vix_above_20']['ann_return_pct']:.2f}% t={hac_above['t_stat']:.2f}")
    print(f"VIX <  20 (calm):          n={len(below_20)} ann_return={threshold_20_split['vix_below_20']['ann_return_pct']:.2f}% t={hac_below['t_stat']:.2f}")

    results = {
        "vix_data_range": [vix_dates_sorted[0], vix_dates_sorted[-1]],
        "n_pooled_observations": len(pooled_overnight),
        "by_vix_quartile": by_quartile,
        "vix_level_and_change_regression": regression_result,
        "vix_20_threshold_split": threshold_20_split,
    }
    with open(REPORTS_DIR / "vix_regime_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved -> {REPORTS_DIR / 'vix_regime_results.json'}")


if __name__ == "__main__":
    main()
