"""Generate the charts referenced in report.md from reports/*.json."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"
BENCHMARK_TICKERS = {"SPY", "QQQ", "MU"}

with open(REPORTS_DIR / "per_ticker_results.json") as f:
    per_ticker = json.load(f)
with open(REPORTS_DIR / "summary.json") as f:
    summary = json.load(f)

spy_bench = summary["spy_buyhold_benchmark"]
spy_cagr = spy_bench["cagr_pct"]
spy_label = f"S&P 500 (SPY) buy & hold, {spy_bench['start'][:4]}–{spy_bench['end'][:4]}: {spy_cagr:.1f}%/yr CAGR"

tickers = sorted(per_ticker.keys(), key=lambda t: per_ticker[t]["overnight"]["ann_return_pct"])
overnight_ann = [per_ticker[t]["overnight"]["ann_return_pct"] for t in tickers]
intraday_ann = [per_ticker[t]["intraday"]["ann_return_pct"] for t in tickers]

# --- Chart 1: per-ticker annualized overnight vs intraday return ---
fig, ax = plt.subplots(figsize=(11, 9))
y = np.arange(len(tickers))
ax.barh(y - 0.2, overnight_ann, height=0.4, label="Overnight (close→open)", color="#2b6cb0")
ax.barh(y + 0.2, intraday_ann, height=0.4, label="Intraday (open→close)", color="#38a169")
ax.set_yticks(y)
ax.set_yticklabels(tickers, fontsize=8)
ax.axvline(0, color="black", linewidth=0.8)
ax.axvline(spy_cagr, color="#d69e2e", linewidth=1.3, linestyle="--", zorder=4, label=spy_label)
ax.set_xlabel("Annualized return (%), log-scale-equivalent daily compounding")
ax.set_title("Overnight vs. Intraday Annualized Return by Ticker")
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout()
fig.savefig(CHARTS_DIR / "per_ticker_overnight_vs_intraday.png", dpi=150)
plt.close(fig)

# --- Chart 2: scatter, overnight t-stat vs intraday t-stat ---
overnight_t = [per_ticker[t]["overnight"]["t_stat"] for t in per_ticker]
intraday_t = [per_ticker[t]["intraday"]["t_stat"] for t in per_ticker]
labels = list(per_ticker.keys())

fig, ax = plt.subplots(figsize=(9, 8))
ax.scatter(overnight_t, intraday_t, color="#805ad5", s=40, zorder=3)
for i, lbl in enumerate(labels):
    ax.annotate(lbl, (overnight_t[i], intraday_t[i]), fontsize=7, xytext=(4, 2), textcoords="offset points")
ax.axhline(0, color="grey", linewidth=0.8)
ax.axvline(0, color="grey", linewidth=0.8)
ax.axhline(-1.96, color="red", linewidth=0.6, linestyle="--", alpha=0.5)
ax.axvline(1.96, color="red", linewidth=0.6, linestyle="--", alpha=0.5)
ax.set_xlabel("Overnight leg t-statistic")
ax.set_ylabel("Intraday leg t-statistic")
ax.set_title("Significance of Overnight vs. Intraday Mean Return, per Ticker\n(dashed lines = 95% significance threshold)")
fig.tight_layout()
fig.savefig(CHARTS_DIR / "significance_scatter.png", dpi=150)
plt.close(fig)

# --- Chart 3: sub-period consistency (first half vs second half overnight ann return) ---
first_half = [per_ticker[t]["overnight_first_half"]["ann_return_pct"] for t in tickers]
second_half = [per_ticker[t]["overnight_second_half"]["ann_return_pct"] for t in tickers]

fig, ax = plt.subplots(figsize=(11, 9))
ax.barh(y - 0.2, first_half, height=0.4, label="First half of history", color="#dd6b20")
ax.barh(y + 0.2, second_half, height=0.4, label="Second half of history", color="#3182ce")
ax.set_yticks(y)
ax.set_yticklabels(tickers, fontsize=8)
ax.axvline(0, color="black", linewidth=0.8)
ax.axvline(spy_cagr, color="#d69e2e", linewidth=1.3, linestyle="--", zorder=4, label=spy_label)
ax.set_xlabel("Annualized overnight return (%)")
ax.set_title("Overnight Edge: First Half vs. Second Half of Each Ticker's History")
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout()
fig.savefig(CHARTS_DIR / "subperiod_consistency.png", dpi=150)
plt.close(fig)

# --- Chart 4: breakeven cost distribution ---
breakevens = [
    per_ticker[t]["overnight_breakeven_bps"]
    for t in per_ticker
    if per_ticker[t]["overnight_breakeven_bps"] is not None
]
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(breakevens, bins=15, color="#2b6cb0", edgecolor="white")
ax.axvline(np.median(breakevens), color="red", linestyle="--", label=f"Median = {np.median(breakevens):.1f} bps")
ax.set_xlabel("Round-trip cost (bps) that erases the overnight edge")
ax.set_ylabel("Number of tickers")
ax.set_title("Overnight-Edge Breakeven Transaction Cost, by Ticker")
ax.legend()
fig.tight_layout()
fig.savefig(CHARTS_DIR / "breakeven_cost_distribution.png", dpi=150)
plt.close(fig)

# --- Chart 5: sector-mean overnight-minus-intraday gap (raw, descriptive) ---
sectors = {}
for t, r in per_ticker.items():
    sectors.setdefault(r["sector"], []).append(r)

sector_names, gaps = [], []
for sector, rows in sectors.items():
    on = np.mean([r["overnight"]["ann_return_pct"] for r in rows])
    idy = np.mean([r["intraday"]["ann_return_pct"] for r in rows])
    sector_names.append(f"{sector} (n={len(rows)})")
    gaps.append(on - idy)

order = np.argsort(gaps)
sector_names = [sector_names[i] for i in order]
gaps = [gaps[i] for i in order]

fig, ax = plt.subplots(figsize=(10, 6))
colors = ["#c53030" if g < 0 else "#2b6cb0" for g in gaps]
ax.barh(sector_names, gaps, color=colors)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("Overnight-minus-Intraday annualized return gap (pp), sector mean")
ax.set_title(
    "The 'MU Pattern' Is a Growth/Attention-Sector Effect, Not a Market-Wide Law\n"
    "(raw returns, dividend/split-adjusted; blue = overnight-dominant, red = intraday-dominant)"
)
fig.tight_layout()
fig.savefig(CHARTS_DIR / "sector_gap.png", dpi=150)
plt.close(fig)

# --- Chart 6: sector-mean factor-neutral overnight alpha (controls for
# market/size/value/momentum -- the harder test of whether the sector
# split in Chart 5 is a distinct effect or just factor exposure) ---
sector_alpha_names, sector_alphas, sector_alpha_ts = [], [], []
for sector, rows in sectors.items():
    alphas = [r["overnight_factor_regression"]["alpha_ann_pct"] for r in rows if r.get("overnight_factor_regression")]
    ts = [r["overnight_factor_regression"]["alpha_t"] for r in rows if r.get("overnight_factor_regression")]
    if not alphas:
        continue
    sector_alpha_names.append(f"{sector} (n={len(alphas)})")
    sector_alphas.append(np.mean(alphas))
    sector_alpha_ts.append(np.mean(ts))

order = np.argsort(sector_alphas)
sector_alpha_names = [sector_alpha_names[i] for i in order]
sector_alphas = [sector_alphas[i] for i in order]
sector_alpha_ts = [sector_alpha_ts[i] for i in order]

fig, ax = plt.subplots(figsize=(10, 6))
colors = ["#c53030" if a < 0 else "#2b6cb0" for a in sector_alphas]
alpha_shade = [1.0 if abs(t) > 1.96 else 0.4 for t in sector_alpha_ts]
bars = ax.barh(sector_alpha_names, sector_alphas, color=colors)
for bar, shade in zip(bars, alpha_shade):
    bar.set_alpha(shade)
ax.axvline(0, color="black", linewidth=0.8)
ax.set_xlabel("Mean overnight alpha (%/yr), after controlling for Mkt-RF, SMB, HML, Momentum")
ax.set_title(
    "Sector Split Survives Controlling for Known Risk Factors\n"
    "(solid = avg |t|>1.96 across sector's tickers, faded = not significant)"
)
fig.tight_layout()
fig.savefig(CHARTS_DIR / "sector_factor_alpha.png", dpi=150)
plt.close(fig)

# --- Chart 7: per-ticker overnight factor-neutral alpha t-stat vs momentum
# loading t-stat -- tests whether the effect is repackaged momentum ---
cross_tickers = [t for t in per_ticker if t not in BENCHMARK_TICKERS and per_ticker[t].get("overnight_factor_regression")]
alpha_t = [per_ticker[t]["overnight_factor_regression"]["alpha_t"] for t in cross_tickers]
mom_t = [per_ticker[t]["overnight_factor_regression"]["mom_t"] for t in cross_tickers]

fig, ax = plt.subplots(figsize=(9, 8))
ax.scatter(mom_t, alpha_t, color="#2b6cb0", s=40, zorder=3)
for i, lbl in enumerate(cross_tickers):
    ax.annotate(lbl, (mom_t[i], alpha_t[i]), fontsize=7, xytext=(4, 2), textcoords="offset points")
ax.axhline(0, color="grey", linewidth=0.8)
ax.axvline(0, color="grey", linewidth=0.8)
ax.axhline(1.96, color="red", linewidth=0.6, linestyle="--", alpha=0.5)
ax.axhline(-1.96, color="red", linewidth=0.6, linestyle="--", alpha=0.5)
ax.set_xlabel("Momentum-factor loading t-statistic (overnight leg)")
ax.set_ylabel("Factor-neutral alpha t-statistic (overnight leg)")
ax.set_title(
    "The Overnight Effect Is Not Repackaged Momentum\n"
    "(alpha t-stats spread widely at ~zero momentum loading; dashed = 95% significance)"
)
fig.tight_layout()
fig.savefig(CHARTS_DIR / "alpha_vs_momentum_loading.png", dpi=150)
plt.close(fig)

# --- Chart 8: day-of-week overnight return (which weekday's close to buy) ---
dow_path = REPORTS_DIR / "day_of_week_results.json"
if dow_path.exists():
    with open(dow_path) as f:
        dow = json.load(f)
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    weekday_means = [dow["summary"]["mean_ann_return_by_weekday_pct"][d] for d in weekday_names]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = ["#2b6cb0"] * 4 + ["#c53030"]  # Friday (weekend gap) highlighted
    ax.bar(weekday_names, weekday_means, color=colors)
    ax.axhline(spy_cagr, color="#d69e2e", linewidth=1.3, linestyle="--", zorder=4, label=spy_label)
    ax.set_ylabel("Mean overnight annualized return across 30 tickers (%)")
    ax.set_title(
        "Which Weekday's Close Is Best to Buy?\n"
        "(red = Friday close -> Monday open, the 3-day weekend gap)"
    )
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "day_of_week_overnight_return.png", dpi=150)
    plt.close(fig)

# --- Chart 9: extreme-gap decomposition (all days vs. ordinary days only) ---
eg_path = REPORTS_DIR / "extreme_gap_results.json"
if eg_path.exists():
    with open(eg_path) as f:
        eg = json.load(f)
    eg_per_ticker = eg["per_ticker"]
    eg_cross = [t for t in eg_per_ticker if t not in BENCHMARK_TICKERS]
    eg_cross_sorted = sorted(eg_cross, key=lambda t: eg_per_ticker[t]["all_days_ann_return_pct"])

    all_ann = [eg_per_ticker[t]["all_days_ann_return_pct"] for t in eg_cross_sorted]
    ordinary_ann = [eg_per_ticker[t]["ordinary_days_ann_return_pct"] for t in eg_cross_sorted]

    fig, ax = plt.subplots(figsize=(11, 9))
    y2 = np.arange(len(eg_cross_sorted))
    ax.barh(y2 - 0.2, all_ann, height=0.4, label="All days", color="#2b6cb0")
    ax.barh(y2 + 0.2, ordinary_ann, height=0.4, label=f"Excluding top ~{eg['summary']['mean_pct_days_extreme']:.1f}% extreme-gap days", color="#38a169")
    ax.set_yticks(y2)
    ax.set_yticklabels(eg_cross_sorted, fontsize=8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.axvline(spy_cagr, color="#d69e2e", linewidth=1.3, linestyle="--", zorder=4, label=spy_label)
    ax.set_xlabel("Annualized overnight return (%)")
    ax.set_title(
        "Overnight Edge: All Days vs. Excluding Extreme Gap Days (>3 std dev)\n"
        "(proxy for earnings/news-driven gaps, not a precise earnings-date match)"
    )
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "extreme_gap_decomposition.png", dpi=150)
    plt.close(fig)

# --- Chart 10: rolling 2-year overnight return over time (has the edge decayed?) ---
recency_path = REPORTS_DIR / "recency_results.json"
if recency_path.exists():
    with open(recency_path) as f:
        recency = json.load(f)
    rolling = recency["rolling"]

    fig, ax = plt.subplots(figsize=(12, 6))
    line_specs = [
        ("cross_sectional_mean", "Cross-sectional mean (30 tickers)", "#000000", 2.2),
        ("SPY", "SPY", "#2b6cb0", 1.2),
        ("QQQ", "QQQ", "#38a169", 1.2),
        ("MU", "MU", "#c53030", 1.2),
        ("NVDA", "NVDA", "#805ad5", 1.0),
        ("AVGO", "AVGO", "#dd6b20", 1.0),
        ("TSLA", "TSLA", "#d53f8c", 1.0),
    ]
    for key, label, color, lw in line_specs:
        if key not in rolling or not rolling[key]:
            continue
        series = rolling[key]
        dates = [datetime.strptime(p["date"], "%Y-%m-%d") for p in series]
        vals = [p["ann_return_pct"] for p in series]
        ax.plot(dates, vals, label=label, color=color, linewidth=lw, alpha=0.9 if key == "cross_sectional_mean" else 0.75)

    ax.axhline(0, color="grey", linewidth=0.6)
    ax.axvline(datetime.strptime(recency["summary"]["regime_break_date"], "%Y-%m-%d"),
               color="red", linewidth=1.0, linestyle="--", alpha=0.6,
               label="2021-01-01 (NY Fed 'disappearing drift' break date)")
    ax.set_ylabel("Trailing 2-year annualized overnight return (%)")
    ax.set_title("Has the Overnight Edge Decayed? Trailing 2-Year Rolling Return")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.autofmt_xdate(rotation=45)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "recency_rolling_return.png", dpi=150)
    plt.close(fig)

# --- Chart 11: portfolio backtest equity curve + drawdown ---
pb_path = REPORTS_DIR / "portfolio_backtest_results.json"
pb_ledger_path = REPORTS_DIR / "portfolio_backtest_ledger.csv"
if pb_path.exists() and pb_ledger_path.exists():
    import csv as _csv
    with open(pb_ledger_path) as f:
        ledger_rows = list(_csv.DictReader(f))
    pb_dates = [datetime.strptime(r["date"], "%Y-%m-%d") for r in ledger_rows]
    on_equity = np.array([float(r["overnight_equity"]) for r in ledger_rows])
    id_equity = np.array([float(r["intraday_equity"]) for r in ledger_rows])
    spy_equity = np.array([float(r["spy_equity"]) for r in ledger_rows])

    fig, axes = plt.subplots(2, 1, figsize=(11, 9), sharex=True, gridspec_kw={"height_ratios": [2.2, 1.2]})

    ax = axes[0]
    ax.plot(pb_dates, on_equity, label="Overnight-only portfolio (5bps cost)", color="#2b6cb0", linewidth=1.3)
    ax.plot(pb_dates, id_equity, label="Intraday-only portfolio (5bps cost)", color="#38a169", linewidth=1.1)
    ax.plot(pb_dates, spy_equity, label="SPY buy & hold", color="#57606a", linewidth=1.1)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $1 (log scale)")
    ax.set_title("Portfolio Backtest: Equal-Weight 30-Ticker Overnight vs. Intraday vs. SPY Buy & Hold")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", alpha=0.25)

    ax = axes[1]
    cum_max_on = np.maximum.accumulate(on_equity)
    dd_on = on_equity / cum_max_on - 1
    cum_max_spy = np.maximum.accumulate(spy_equity)
    dd_spy = spy_equity / cum_max_spy - 1
    ax.fill_between(pb_dates, dd_on * 100, 0, color="#2b6cb0", alpha=0.5, label="Overnight-only drawdown")
    ax.plot(pb_dates, dd_spy * 100, color="#57606a", linewidth=0.9, label="SPY buy & hold drawdown")
    ax.set_ylabel("Drawdown (%)")
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_locator(mdates.YearLocator(3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.autofmt_xdate(rotation=45)

    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "portfolio_backtest_equity.png", dpi=150)
    plt.close(fig)

    # Cost sensitivity chart
    with open(pb_path) as f:
        pb = json.load(f)
    cs = pb["cost_sensitivity"]
    bps_vals = [r["cost_bps"] for r in cs]
    cagr_vals = [r["cagr_pct"] for r in cs]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = ["#38a169" if c >= 0 else "#c53030" for c in cagr_vals]
    ax.bar([str(b) for b in bps_vals], cagr_vals, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    breakeven = pb.get("portfolio_breakeven_cost_bps")
    if breakeven is not None:
        ax.set_title(f"Portfolio Overnight Strategy: CAGR vs. Round-Trip Cost\n(breakeven = {breakeven:.2f}bps; sibling-repo convention is 5bps)")
    ax.set_xlabel("Round-trip cost assumption (bps)")
    ax.set_ylabel("CAGR (%)")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "portfolio_cost_sensitivity.png", dpi=150)
    plt.close(fig)

    # Realistic (IBKR Pro fee schedule) cost-by-capital results
    rc_ledger_path = REPORTS_DIR / "portfolio_realistic_cost_ledger.csv"
    if rc_ledger_path.exists() and "realistic_cost_model" in pb:
        rc = pb["realistic_cost_model"]["by_starting_capital"]
        capitals = [r["starting_capital"] for r in rc]
        cagrs = [r["cagr_pct"] for r in rc]
        sharpes = [r["sharpe"] for r in rc]

        fig, ax1 = plt.subplots(figsize=(9, 6))
        colors = ["#c53030" if c < 0 else "#38a169" for c in cagrs]
        x = np.arange(len(capitals))
        ax1.bar(x, cagrs, color=colors, alpha=0.85, label="CAGR (%)")
        ax1.axhline(0, color="black", linewidth=0.8)
        ax1.set_xticks(x)
        ax1.set_xticklabels([f"${c:,.0f}" for c in capitals], rotation=45, ha="right")
        ax1.set_ylabel("CAGR (%)")
        ax1.set_xlabel("Starting capital (equal-weight across all 30 names)")
        ax1.set_title(
            "Realistic Cost Model (IBKR Pro fee schedule): CAGR by Starting Account Size\n"
            "Small accounts get wiped out by the 35c/order minimum; cost converges above ~250k"
        )

        ax2 = ax1.twinx()
        ax2.plot(x, sharpes, color="#2b6cb0", marker="o", linewidth=1.5, label="Sharpe ratio")
        ax2.set_ylabel("Sharpe ratio", color="#2b6cb0")
        ax2.tick_params(axis="y", labelcolor="#2b6cb0")

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower right", fontsize=8)
        fig.tight_layout()
        fig.savefig(CHARTS_DIR / "portfolio_realistic_cost_by_capital.png", dpi=150)
        plt.close(fig)

        # Equity curves for a few representative capital levels
        with open(rc_ledger_path) as f:
            rc_rows = list(_csv.DictReader(f))
        rc_dates = [datetime.strptime(r["date"], "%Y-%m-%d") for r in rc_rows]
        representative = [25_000, 50_000, 100_000, 250_000]
        fig, ax = plt.subplots(figsize=(11, 6.5))
        colors_map = {25_000: "#c53030", 50_000: "#dd6b20", 100_000: "#2b6cb0", 250_000: "#38a169"}
        for cap in representative:
            col = f"equity_{cap}"
            if col not in rc_rows[0]:
                continue
            vals = np.array([float(r[col]) for r in rc_rows])
            vals_plot = np.clip(vals, 1e-4, None)  # avoid log(0) for wiped-out paths
            ax.plot(rc_dates, vals_plot, label=f"${cap:,.0f} start", color=colors_map.get(cap, "#805ad5"), linewidth=1.2)
        ax.set_yscale("log")
        ax.axhline(1.0, color="grey", linewidth=0.6)
        ax.set_ylabel("Equity multiple of starting capital (log scale)")
        ax.set_title("Realistic-Cost Overnight Portfolio: Equity Path by Starting Capital\n(IBKR Pro fee schedule, path-dependent cost)")
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, which="both", alpha=0.25)
        ax.xaxis.set_major_locator(mdates.YearLocator(3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        fig.autofmt_xdate(rotation=45)
        fig.tight_layout()
        fig.savefig(CHARTS_DIR / "portfolio_realistic_cost_equity_paths.png", dpi=150)
        plt.close(fig)

# --- Chart 12: correlation structure -- effective independent bets ---
corr_path = REPORTS_DIR / "correlation_tail_risk_results.json"
if corr_path.exists():
    with open(corr_path) as f:
        corr_tail = json.load(f)
    corr = corr_tail["correlation"]

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    ax = axes[0]
    legs = ["Overnight", "Intraday"]
    eff_bets = [corr["overnight"]["effective_number_of_bets"], corr["intraday"]["effective_number_of_bets"]]
    n_names = corr["overnight"]["n_tickers"]
    ax.bar(legs, eff_bets, color=["#2b6cb0", "#38a169"])
    ax.axhline(n_names, color="grey", linewidth=1.0, linestyle="--", label=f"{n_names} names (fully independent)")
    for i, v in enumerate(eff_bets):
        ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=10)
    ax.set_ylabel("Effective number of independent bets (PCA participation ratio)")
    ax.set_title("How Much Diversification Is Really There?")
    ax.legend(fontsize=8)

    ax = axes[1]
    corrs = [corr["overnight"]["mean_pairwise_correlation"], corr["intraday"]["mean_pairwise_correlation"]]
    ax.bar(legs, corrs, color=["#2b6cb0", "#38a169"])
    for i, v in enumerate(corrs):
        ax.text(i, v + 0.01, f"{v:.2f}", ha="center", fontsize=10)
    ax.set_ylabel("Mean pairwise correlation")
    ax.set_title("Cross-Sectional Correlation, 30 Names")
    fig.suptitle(f"The 30-Name Book Has ~{eff_bets[0]:.0f} Independent Overnight Bets, Not 30", fontsize=12)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "correlation_effective_bets.png", dpi=150)
    plt.close(fig)

    # --- Chart 13: fat-tail risk, actual vs Gaussian-implied CVaR ---
    pt = corr_tail["portfolio_tail_risk"]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    cats = ["Overnight\n(actual)", "Overnight\n(Gaussian-implied)", "Intraday\n(actual)", "Intraday\n(Gaussian-implied)"]
    vals = [pt["overnight"]["cvar_1pct_bps"], pt["overnight"]["gaussian_cvar_1pct_bps"],
            pt["intraday"]["cvar_1pct_bps"], pt["intraday"]["gaussian_cvar_1pct_bps"]]
    colors = ["#c53030", "#e2a5a5", "#c53030", "#e2a5a5"]
    ax.bar(cats, vals, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("1% CVaR / expected shortfall (bps, single day)")
    ax.set_title(
        f"The Overnight Leg's Worst-Day Tail Is {pt['overnight']['fat_tail_multiple_vs_gaussian']:.1f}x Fatter Than Gaussian Predicts\n"
        f"(portfolio-level, equal-weight, staggered entry; intraday leg is {pt['intraday']['fat_tail_multiple_vs_gaussian']:.1f}x)"
    )
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "tail_risk_cvar.png", dpi=150)
    plt.close(fig)

# --- Chart 14: VIX-regime conditioning ---
vix_path = REPORTS_DIR / "vix_regime_results.json"
if vix_path.exists():
    with open(vix_path) as f:
        vix_regime = json.load(f)
    quartiles = list(vix_regime["by_vix_quartile"].keys())
    q_ann = [vix_regime["by_vix_quartile"][q]["ann_return_pct"] for q in quartiles]
    q_vix = [vix_regime["by_vix_quartile"][q]["mean_vix_in_bucket"] for q in quartiles]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.bar(quartiles, q_ann, color="#2b6cb0")
    ax.axhline(spy_cagr, color="#d69e2e", linewidth=1.3, linestyle="--", zorder=4, label=spy_label)
    for i, (a, v) in enumerate(zip(q_ann, q_vix)):
        ax.text(i, a + 0.3, f"mean VIX={v:.1f}", ha="center", fontsize=8)
    ax.set_ylabel("Pooled overnight annualized return (%), 30 tickers")
    ax.set_title("Overnight Edge by VIX Quartile on the Buy Day\n(mildly stronger in high-fear regimes, but not a statistically significant slope)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "vix_regime_overnight_return.png", dpi=150)
    plt.close(fig)

# --- Chart 15: overnight-momentum sort -- equity curves and cross-window spread ---
mom_path = REPORTS_DIR / "overnight_momentum_results.json"
mom_ledger_path = REPORTS_DIR / "overnight_momentum_ledger.csv"
if mom_path.exists() and mom_ledger_path.exists():
    import csv as _csv
    with open(mom_path) as f:
        mom = json.load(f)
    with open(mom_ledger_path) as f:
        mom_rows = list(_csv.DictReader(f))
    mom_dates = [datetime.strptime(r["date"], "%Y-%m-%d") for r in mom_rows]
    top_eq = np.array([float(r["top_tercile_equity"]) for r in mom_rows])
    all_eq = np.array([float(r["equal_weight_all_equity"]) for r in mom_rows])
    bottom_eq = np.array([float(r["bottom_tercile_equity"]) for r in mom_rows])

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(mom_dates, top_eq, label="Top tercile (strongest trailing overnight momentum)", color="#2b6cb0", linewidth=1.3)
    ax.plot(mom_dates, all_eq, label="Equal-weight, all names", color="#57606a", linewidth=1.1)
    ax.plot(mom_dates, np.clip(bottom_eq, 1e-4, None), label="Bottom tercile (weakest trailing momentum)", color="#c53030", linewidth=1.1)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $1 (log scale)")
    ax.set_title(
        f"Sorting on Trailing {mom['headline_window_days']}-Day Overnight Momentum Separates Winners From Losers\n"
        f"({mom['headline_equity_curve']['start']} to {mom['headline_equity_curve']['end']}, {mom['cost_bps']:.0f}bps cost)"
    )
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", alpha=0.25)
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "overnight_momentum_equity.png", dpi=150)
    plt.close(fig)

    windows = mom["windows_tested_days"]
    spreads = [mom["by_window"][str(w)]["spread_ann_return_pct"] for w in windows]
    spread_ts = [mom["by_window"][str(w)]["spread_t_stat"] for w in windows]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.bar([f"{w}-day" for w in windows], spreads, color="#2b6cb0")
    for i, (s, t) in enumerate(zip(spreads, spread_ts)):
        ax.text(i, s + 0.5, f"t={t:.1f}", ha="center", fontsize=9)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Top-minus-bottom tercile spread, annualized (%)")
    ax.set_xlabel("Trailing lookback window used for the momentum signal")
    ax.set_title("Overnight-Momentum Spread Is Robust Across Lookback Horizons")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "overnight_momentum_spread_by_window.png", dpi=150)
    plt.close(fig)

# --- Chart 16: walk-forward validation -- in-sample vs out-of-sample equity split ---
wf_path = REPORTS_DIR / "walk_forward_results.json"
wf_ledger_path = REPORTS_DIR / "overnight_momentum_ledger.csv"
if wf_path.exists() and wf_ledger_path.exists():
    import csv as _csv
    with open(wf_path) as f:
        wf = json.load(f)
    with open(wf_ledger_path) as f:
        wf_rows = list(_csv.DictReader(f))
    wf_dates = [datetime.strptime(r["date"], "%Y-%m-%d") for r in wf_rows]
    wf_top_eq = np.array([float(r["top_tercile_equity"]) for r in wf_rows])

    oos_start = datetime.strptime(wf["standard_holdout"]["out_of_sample_window_start"], "%Y-%m-%d")
    headline_key = str(wf["headline_window_days"])
    is_stats = wf["standard_holdout"]["by_window"][headline_key]["in_sample"]
    oos_stats = wf["standard_holdout"]["by_window"][headline_key]["out_of_sample"]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(wf_dates, wf_top_eq, color="#2b6cb0", linewidth=1.3,
             label=f"{wf['headline_window_days']}-day momentum overlay (top tercile)")
    ax.axvline(oos_start, color="#c53030", linewidth=1.2, linestyle="--", label="2011: in-sample / out-of-sample split")
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $1 (log scale)")
    ax.set_title(
        f"Walk-Forward Validation: the {wf['headline_window_days']}-Day Overlay's Sharpe Roughly Halves Out-of-Sample\n"
        f"(in-sample 1993-2010 Sharpe {is_stats['sharpe']:.2f} -> out-of-sample 2011-2026 Sharpe {oos_stats['sharpe']:.2f}, {wf['cost_bps']:.0f}bps cost)"
    )
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, which="both", alpha=0.25)
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.autofmt_xdate(rotation=45)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "walk_forward_is_oos_split.png", dpi=150)
    plt.close(fig)

    # --- Chart 17: purged 5-fold walk-forward selection -- test-fold Sharpe stability ---
    folds = wf["purged_kfold"]["by_fold"]
    labels = [f"{f['test_start'][:4]}-{f['test_end'][:4]}\n({f['selected_window_days']}d)" for f in folds]
    test_sharpes = [f["selected_test_sharpe"] for f in folds]
    colors = ["#2b6cb0" if f["selected_window_days"] == wf["headline_window_days"] else "#805ad5" for f in folds]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.bar(labels, test_sharpes, color=colors)
    ax.axhline(0.65, color="#d69e2e", linewidth=1.2, linestyle="--", label="SPY buy & hold Sharpe (0.65)")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Out-of-sample (test fold) Sharpe ratio")
    ax.set_xlabel("Test fold period (selected lookback shown in parentheses)")
    ax.set_title("Purged Walk-Forward Selection: Positive in Every Fold, but Weaker Recently")
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "walk_forward_fold_stability.png", dpi=150)
    plt.close(fig)

print("Charts written to", CHARTS_DIR)
