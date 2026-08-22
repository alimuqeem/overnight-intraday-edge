"""Generate the charts referenced in report.md from reports/*.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
CHARTS_DIR = Path(__file__).resolve().parent.parent / "charts"

with open(REPORTS_DIR / "per_ticker_results.json") as f:
    per_ticker = json.load(f)

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
ax.set_xlabel("Annualized return (%), log-scale-equivalent daily compounding")
ax.set_title("Overnight vs. Intraday Annualized Return by Ticker")
ax.legend(loc="lower right")
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
ax.set_xlabel("Annualized overnight return (%)")
ax.set_title("Overnight Edge: First Half vs. Second Half of Each Ticker's History")
ax.legend(loc="lower right")
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

# --- Chart 5: sector-mean overnight-minus-intraday gap ---
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
    "(blue = overnight-dominant, red = intraday-dominant)"
)
fig.tight_layout()
fig.savefig(CHARTS_DIR / "sector_gap.png", dpi=150)
plt.close(fig)

print("Charts written to", CHARTS_DIR)
