# Portfolio Backtest: Is This Actually Tradeable?

Every other analysis in this project is descriptive: does the overnight pattern exist, is it statistically significant, does it survive factor controls, has it decayed. None of that answers the practical question a trader actually cares about: **if you had run this as a real, diversified, cost-aware portfolio for the last 33 years, would you have made money?** This is that test.

## Method

- **Universe:** the same 30 cross-section tickers used throughout this project (excludes SPY/QQQ/MU, see [`../report.md` §1](../report.md#1-method)). Each ticker enters the equal-weight portfolio on its first available trading day, no survivorship-adjusted backfill, no look-ahead. The number of names held grows from a handful in 1993 to all 30 by the mid-2010s as later IPOs (TSLA, META, AVGO, V, and others) become available.
- **Window:** 1993-01-29 to 2026-08-21 (8,448 trading days), SPY's full available history, used as the common benchmark window.
- **Three simulated equity curves:**
  1. **Overnight-only**: equal-weight the tickers available each day, buy at close (MOC), sell at next open (MOO), net of a flat round-trip cost.
  2. **Intraday-only**: same universe/weighting, buy at open (MOO), sell at close (MOC), same cost, for direct contrast.
  3. **SPY buy & hold**: this project's standing benchmark throughout.
- **Cost:** 5bps round-trip, matching the convention in [`../vix-regime-switch-backtest`](https://github.com/alimuqeem/vix-regime-switch-backtest) for direct comparability across the two projects.
- **What's deliberately not modeled: idle cash yield.** Both the overnight-only and intraday-only portfolios are, by construction, only ever holding stock for roughly half of each trading day; the sibling repo credits idle cash with the 3-month T-bill yield during out-of-market periods, and this project intended to do the same. Live T-bill data (Yahoo's ^IRX) proved unreliable to fetch in this environment across repeated attempts with backoff (stayed rate-limited), and FRED was unreachable from this sandbox. Rather than hand-estimate a historical rate series from memory and risk stating a wrong number as fact, this was dropped. **This is a conservative simplification that understates both simulated portfolios' real-world total return relative to SPY buy & hold**, which captures 100% of every trading day. A real implementation would likely earn a modest money-market-like yield (roughly 0-5%/yr depending on era) on the idle half of each cycle, not credited here.

Full method: [`../scripts/portfolio_backtest.py`](../scripts/portfolio_backtest.py). Raw output: [`../reports/portfolio_backtest_results.json`](../reports/portfolio_backtest_results.json), full daily ledger: [`../reports/portfolio_backtest_ledger.csv`](../reports/portfolio_backtest_ledger.csv).

## Headline result: no, not at a realistic cost

![Portfolio backtest equity curve](../charts/portfolio_backtest_equity.png)

| | Overnight-only | Intraday-only | SPY buy & hold |
|---|---:|---:|---:|
| CAGR | **-0.73%** | -5.19% | **10.87%** |
| Annualized volatility | 10.59% | 15.39% | 18.55% |
| Sharpe ratio | -0.02 | -0.27 | 0.65 |
| Max drawdown | -52.83% | -84.01% | -55.19% |
| Max drawdown duration | 6,651 days (~26 years) | 6,947 days | 1,656 days |
| Growth of $1 | $0.78 | $0.17 | **$31.76** |

At the 5bps round-trip cost this project has used as its standard assumption throughout, **the diversified overnight-only portfolio loses money over 33 years**, and spends nearly the entire backtest underwater relative to its own peak (a max drawdown duration of ~26 years). It is unambiguously the better of the two legs, exactly consistent with everything else in this project, but "better than intraday-only, which loses far more" is not the same as "profitable."

## Why this is worse than the per-ticker breakeven analysis suggested

[`../report.md` §5](../report.md#5-does-it-survive-costs-and-time-partially) found a median single-ticker breakeven cost of ~4.2bps and a cross-sectional mean overnight return of 5.74bps/day, numbers that might suggest a diversified portfolio should comfortably clear a 5bps cost. It doesn't, because those numbers are **unweighted averages across tickers' full individual histories**, while a real portfolio's return each day is **weighted by whichever tickers actually existed that day**. The gross (pre-cost) portfolio return averages 4.93bps/day, not 5.74bps, because the early decades of the backtest (1993-2010) held far fewer names (avg. 23.2) and specifically lacked the growth/semiconductor names that carry the strongest individual overnight edge (NVDA, META, TSLA, AVGO all IPO'd well after 1993). Pre-2010, the portfolio's mean daily return was **negative** even before cost (-0.67bps net of the 5bps cost actually charged, i.e. ~4.33bps gross); post-2010, with more growth names in the mix, it's back to a healthier 5.55bps gross. **The portfolio's own solved breakeven cost is 4.71bps**, close to but still below the 5bps this project (and the sibling repo) treats as the realistic institutional-grade assumption.

![Portfolio cost sensitivity](../charts/portfolio_cost_sensitivity.png)

Below the 4.71bps breakeven, the picture is genuinely attractive: at 0bps cost, the portfolio's 12.60% CAGR actually beats SPY's 10.87%, with less than half the volatility (10.59% vs. 18.55%). The entire practical question comes down to whether an implementation can execute below ~4.7bps round-trip, which is a real possibility for the most liquid names via MOC/MOO at a broker like Interactive Brokers (see [`execution_mechanics.md`](execution_mechanics.md)), but is not guaranteed, and this project has no independent way to verify actual achievable spread costs at that precision.

## Crisis-window behavior: not uniformly protective

| Crisis | Overnight portfolio | SPY buy & hold |
|---|---:|---:|
| 2008-09 Global Financial Crisis | -17.6% | -36.6% |
| 2010 Flash Crash | -2.9% | -13.8% |
| 2011 US debt ceiling / EU crisis | -6.8% | -5.8% |
| 2015-16 China deval / oil crash | -9.0% | -6.7% |
| 2018 Volmageddon | -3.1% | -3.6% |
| 2018 Q4 selloff | -1.3% | -13.8% |
| **2020 COVID crash** | **-20.1%** | -13.6% |
| **2022 Bear market (rate hikes)** | **-24.4%** | -18.2% |
| 2023 Regional banking crisis | +0.8% | +4.1% |

The overnight portfolio meaningfully outperformed SPY during the GFC, the 2010 Flash Crash, and the 2018 Q4 selloff, but **meaningfully underperformed during COVID (2020) and the 2022 rate-hike bear market**, the two most recent major drawdowns. This isn't a uniform "safer in a crisis" story; it depends on the specific character of the selloff. Overall beta vs. SPY is 0.32 (much lower than 1, as expected for a strategy invested only half of each day), but annualized alpha is **-3.97%/yr**, negative even after adjusting for that lower beta exposure, at the 5bps cost this table uses.

## Caveats

- **Idle cash yield not modeled** (see Method above), which understates both simulated portfolios relative to SPY buy & hold.
- **Static equal weighting, no periodic reconstitution or quality filters.** A real implementation might do better (or worse) by weighting toward the highest-Sharpe or highest-alpha names identified elsewhere in this project (e.g. MU, AVGO from [`../report.md`](../report.md)) rather than naive equal-weight across all 30; that's a different, untested strategy design.
- **No slippage beyond the flat cost assumption**, and no modeling of the specific MOC/MOO execution mechanics detailed in [`execution_mechanics.md`](execution_mechanics.md) (auction depth, name-specific spread).
- **Survivorship bias remains**: this is the same fixed 30-name "still large-cap today" universe used throughout the project, not a point-in-time historical index membership.
- **The 5bps cost convention is a specific choice**, imported from the sibling `vix-regime-switch-backtest` repo for comparability, not independently re-derived for this specific overnight-trading use case; see [`execution_mechanics.md`](execution_mechanics.md) for the broker-level context behind whether 5bps or something tighter is realistically achievable.

## Bottom line

The statistical finding throughout this project, that the overnight effect is real, significant, factor-distinct, and not fully explained by a handful of tail-event nights, all survive this test. What doesn't survive is the leap from "real" to "tradeable at scale." A diversified, cost-aware implementation of the exact strategy this project has been describing would have lost money net of a realistic institutional cost assumption over the last 33 years, purely because the compounding of a genuinely thin (sub-5bps) daily edge across a portfolio, including decades before the strongest-edge names even existed, isn't large enough to survive costs at portfolio scale, even though the underlying statistical pattern is not in question.
