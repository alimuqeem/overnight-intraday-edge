"""
Portfolio-level backtest: is this actually tradeable, not just real?

Everything else in this project is descriptive (per-ticker decomposition,
significance tests, factor regressions). This simulates three real
day-by-day equity curves over 1993-2026 (SPY's history, the benchmark
window):

  1. Overnight-only: equal-weight the 30 cross-section tickers available
     each day, buy at close (MOC), sell at next open (MOO), net of a flat
     round-trip cost.
  2. Intraday-only: same universe/weighting, buy at open (MOO), sell at
     close (MOC), same cost.
  3. SPY buy & hold (already the project's standing benchmark).

Tickers enter the equal-weight portfolio on their first available
trading day (no survivorship-adjusted backfill, no look-ahead), so the
number of names held grows from a handful in 1993 to all 30 by the
2010s as later IPOs (TSLA, META, AVGO, V, ...) become available.

Cost convention (5bps round-trip) matches ../vix-regime-switch-backtest
for comparability. Unlike that sibling repo, idle cash is NOT modeled as
earning a T-bill yield: live T-bill data proved unreliable to fetch in
this environment (Yahoo's ^IRX endpoint stayed rate-limited across
repeated attempts with backoff; FRED was unreachable from this sandbox).
This is a conservative simplification, not a hidden one: both the
overnight-only and intraday-only portfolios are only ever "invested"
for roughly half of each trading day by construction, and crediting zero
yield on the other half understates their real-world total return
relative to SPY buy & hold (which captures 100% of every day). See
report.md / background/portfolio_backtest.md for the full caveat.

This script deliberately uses numpy/csv instead of pandas (unlike the
sibling repo) to keep this project's offline-reproduction dependency
footprint at numpy/scipy/matplotlib only, consistent with every other
script here.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
REPORTS_DIR.mkdir(exist_ok=True)

TRADING_DAYS_PER_YEAR = 252
COST_BPS = 5.0

CRISIS_WINDOWS = {
    "2008-09 Global Financial Crisis": ("2008-09-01", "2009-03-31"),
    "2010 Flash Crash": ("2010-05-01", "2010-06-30"),
    "2011 US debt ceiling / EU crisis": ("2011-07-01", "2011-10-31"),
    "2015-16 China deval / oil crash": ("2015-08-01", "2016-02-29"),
    "2018 Volmageddon": ("2018-01-25", "2018-02-15"),
    "2018 Q4 selloff": ("2018-10-01", "2018-12-31"),
    "2020 COVID crash": ("2020-02-19", "2020-04-30"),
    "2022 Bear market (rate hikes)": ("2022-01-01", "2022-10-31"),
    "2023 Regional banking crisis": ("2023-03-01", "2023-03-31"),
}


def load_ohlc(ticker: str):
    path = DATA_DIR / f"{ticker}.csv"
    data = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            if not row["open"] or not row["close"]:
                continue
            data[row["date"]] = (float(row["open"]), float(row["close"]))
    return data


def perf_metrics(daily_ret: np.ndarray, equity: np.ndarray):
    n = len(daily_ret)
    years = n / TRADING_DAYS_PER_YEAR
    cagr = equity[-1] ** (1 / years) - 1
    vol = np.std(daily_ret) * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = np.mean(daily_ret) / np.std(daily_ret) * np.sqrt(TRADING_DAYS_PER_YEAR) if np.std(daily_ret) > 0 else float("nan")
    downside = daily_ret[daily_ret < 0]
    sortino = (np.mean(daily_ret) / np.std(downside) * np.sqrt(TRADING_DAYS_PER_YEAR)
               if len(downside) > 0 and np.std(downside) > 0 else float("nan"))
    cum_max = np.maximum.accumulate(equity)
    dd = equity / cum_max - 1
    max_dd = dd.min()
    calmar = cagr / abs(max_dd) if max_dd != 0 else float("nan")

    in_dd = dd < 0
    max_len, cur_len = 0, 0
    for v in in_dd:
        cur_len = cur_len + 1 if v else 0
        max_len = max(max_len, cur_len)

    return {
        "cagr_pct": cagr * 100,
        "ann_vol_pct": vol * 100,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown_pct": max_dd * 100,
        "calmar": calmar,
        "max_dd_duration_days": int(max_len),
        "final_equity": float(equity[-1]),
        "n_days": n,
        "years": years,
    }


def run_backtest(tickers_ohlc: dict, dates: list, cost_bps: float = COST_BPS):
    """Returns (overnight_ret, overnight_equity, intraday_ret, intraday_equity,
    n_members_per_day)."""
    n = len(dates)
    cost = cost_bps / 10000.0

    overnight_ret = np.zeros(n)
    intraday_ret = np.zeros(n)
    n_members = np.zeros(n, dtype=int)

    for i in range(1, n):
        d, d_prev = dates[i], dates[i - 1]
        on_legs, id_legs = [], []
        for ticker, ohlc in tickers_ohlc.items():
            if d in ohlc and d_prev in ohlc:
                open_t, close_t = ohlc[d]
                _, close_prev = ohlc[d_prev]
                on_legs.append(open_t / close_prev - 1.0)
                id_legs.append(close_t / open_t - 1.0)
        n_members[i] = len(on_legs)
        if on_legs:
            overnight_ret[i] = np.mean(on_legs) - cost
            intraday_ret[i] = np.mean(id_legs) - cost
        # else: no names available yet (before any IPO in the universe) -> 0% that day

    overnight_equity = np.cumprod(1 + overnight_ret)
    intraday_equity = np.cumprod(1 + intraday_ret)
    return overnight_ret, overnight_equity, intraday_ret, intraday_equity, n_members


def find_breakeven_bps(tickers_ohlc: dict, dates: list, lo=0.0, hi=20.0, tol=1e-4):
    """Binary-search the round-trip cost (bps) that drives the overnight
    portfolio's final equity to exactly 1.0 (breakeven)."""
    def final_equity_at(bps):
        _, equity, _, _, _ = run_backtest(tickers_ohlc, dates, cost_bps=bps)
        return equity[-1]

    if final_equity_at(0.0) <= 1.0:
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if final_equity_at(mid) > 1.0:
            lo = mid
        else:
            hi = mid
    return lo


def crisis_breakdown(dates: list, overnight_equity: np.ndarray, spy_equity: np.ndarray):
    out = {}
    for name, (start, end) in CRISIS_WINDOWS.items():
        idx_in_range = [i for i, d in enumerate(dates) if start <= d <= end]
        if len(idx_in_range) < 2:
            continue
        i0, i1 = idx_in_range[0], idx_in_range[-1]
        strat_ret = overnight_equity[i1] / overnight_equity[i0] - 1
        bh_ret = spy_equity[i1] / spy_equity[i0] - 1
        out[name] = {
            "overnight_portfolio_return_pct": float(strat_ret * 100),
            "spy_buyhold_return_pct": float(bh_ret * 100),
        }
    return out


def main():
    with open(DATA_DIR / "universe.json") as f:
        universe = json.load(f)
    cross_tickers = [t for group in universe.values() for t in group if t not in ("SPY", "QQQ", "MU")]

    print(f"Loading {len(cross_tickers)} tickers + SPY...")
    tickers_ohlc = {t: load_ohlc(t) for t in cross_tickers}
    spy_ohlc = load_ohlc("SPY")

    dates = sorted(spy_ohlc.keys())
    print(f"Backtest window: {dates[0]} to {dates[-1]} ({len(dates)} trading days)")

    print(f"Running backtest at {COST_BPS}bps round-trip cost...")
    on_ret, on_equity, id_ret, id_equity, n_members = run_backtest(tickers_ohlc, dates)

    spy_ret = np.zeros(len(dates))
    for i in range(1, len(dates)):
        spy_ret[i] = spy_ohlc[dates[i]][1] / spy_ohlc[dates[i - 1]][1] - 1.0
    spy_equity = np.cumprod(1 + spy_ret)

    on_metrics = perf_metrics(on_ret[1:], on_equity[1:])
    id_metrics = perf_metrics(id_ret[1:], id_equity[1:])
    spy_metrics = perf_metrics(spy_ret[1:], spy_equity[1:])

    # beta/alpha of the overnight portfolio vs SPY buy & hold
    beta, alpha_daily = np.polyfit(spy_ret[1:], on_ret[1:], 1)
    alpha_annual_pct = alpha_daily * TRADING_DAYS_PER_YEAR * 100

    print("\n=== HEADLINE METRICS ===")
    for label, m in [("Overnight-only portfolio", on_metrics), ("Intraday-only portfolio", id_metrics), ("SPY buy & hold", spy_metrics)]:
        print(f"{label:28s} CAGR {m['cagr_pct']:6.2f}%  Vol {m['ann_vol_pct']:6.2f}%  "
              f"Sharpe {m['sharpe']:5.2f}  MaxDD {m['max_drawdown_pct']:7.2f}%  Final $ {m['final_equity']:.2f}")
    print(f"Overnight portfolio beta vs SPY: {beta:.3f}, alpha: {alpha_annual_pct:.2f}%/yr")
    print(f"Avg number of names held per day: {n_members[1:].mean():.1f} (range {n_members[1:].min()}-{n_members[1:].max()})")

    print("\nCost sensitivity...")
    cost_sensitivity = []
    for bps in [0, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30]:
        r, e, _, _, _ = run_backtest(tickers_ohlc, dates, cost_bps=bps)
        m = perf_metrics(r[1:], e[1:])
        cost_sensitivity.append({"cost_bps": bps, "cagr_pct": m["cagr_pct"], "sharpe": m["sharpe"], "final_equity": m["final_equity"]})
        print(f"  {bps:3.0f}bps: CAGR {m['cagr_pct']:6.2f}%  Sharpe {m['sharpe']:5.2f}  Final $ {m['final_equity']:.2f}")

    print("\nCrisis-window breakdown...")
    crises = crisis_breakdown(dates, on_equity, spy_equity)
    for name, r in crises.items():
        print(f"  {name:38s} overnight {r['overnight_portfolio_return_pct']:7.2f}%   SPY {r['spy_buyhold_return_pct']:7.2f}%")

    print("\nSolving for the portfolio's exact breakeven cost...")
    breakeven_bps = find_breakeven_bps(tickers_ohlc, dates)
    print(f"  Portfolio breakeven round-trip cost: {breakeven_bps:.2f}bps" if breakeven_bps is not None else "  Not profitable even at 0bps cost")

    results = {
        "period_start": dates[0],
        "period_end": dates[-1],
        "n_trading_days": len(dates),
        "cost_bps": COST_BPS,
        "idle_cash_yield_modeled": False,
        "portfolio_breakeven_cost_bps": breakeven_bps,
        "avg_names_held": float(n_members[1:].mean()),
        "overnight_portfolio": on_metrics,
        "intraday_portfolio": id_metrics,
        "spy_buy_and_hold": spy_metrics,
        "overnight_beta_vs_spy": float(beta),
        "overnight_alpha_annualized_pct": float(alpha_annual_pct),
        "cost_sensitivity": cost_sensitivity,
        "crisis_windows": crises,
    }
    with open(REPORTS_DIR / "portfolio_backtest_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Save the daily ledger for transparency/reproducibility
    with open(REPORTS_DIR / "portfolio_backtest_ledger.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "overnight_ret", "overnight_equity", "intraday_ret", "intraday_equity",
                          "spy_ret", "spy_equity", "n_members"])
        for i in range(len(dates)):
            writer.writerow([dates[i], on_ret[i], on_equity[i], id_ret[i], id_equity[i],
                              spy_ret[i], spy_equity[i], n_members[i]])

    print(f"\nSaved -> {REPORTS_DIR / 'portfolio_backtest_results.json'}")
    print(f"Saved -> {REPORTS_DIR / 'portfolio_backtest_ledger.csv'}")


if __name__ == "__main__":
    main()
