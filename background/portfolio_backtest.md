# Portfolio Backtest: Is This Actually Tradeable?

Every other analysis in this project is descriptive: does the overnight pattern exist, is it statistically significant, does it survive factor controls, has it decayed. None of that answers the practical question a trader actually cares about: **if you had run this as a real, diversified, cost-aware portfolio for the last 33 years, would you have made money?** This is that test.

## Method

- **Universe:** the same 30 cross-section tickers used throughout this project (excludes SPY/QQQ/MU, see [`../report.md` §1](../report.md#1-method)). Each ticker enters the equal-weight portfolio on its first available trading day, no survivorship-adjusted backfill, no look-ahead. The number of names held grows from a handful in 1993 to all 30 by the mid-2010s as later IPOs (TSLA, META, AVGO, V, and others) become available.
- **Window:** 1993-01-29 to 2026-08-21 (8,448 trading days), SPY's full available history, used as the common benchmark window.
- **Three simulated equity curves:**
  1. **Overnight-only**: equal-weight the tickers available each day, buy at close (MOC), sell at next open (MOO), net of a flat round-trip cost.
  2. **Intraday-only**: same universe/weighting, buy at open (MOO), sell at close (MOC), same cost, for direct contrast.
  3. **SPY buy & hold**: this project's standing benchmark throughout.
- **Cost, two models:** (1) a flat 5bps round-trip matching the convention in [`../vix-regime-switch-backtest`](https://github.com/alimuqeem/vix-regime-switch-backtest) for direct comparability across the two projects, used for the headline result below; (2) a realistic, position-size-dependent model built from actual IBKR Pro fee schedules, run across a grid of starting account sizes, see [Sharpening the cost model](#sharpening-the-cost-model-real-ibkr-pro-fees-by-account-size) below.
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

Below the 4.71bps breakeven, the picture is genuinely attractive: at 0bps cost, the portfolio's 12.60% CAGR actually beats SPY's 10.87%, with less than half the volatility (10.59% vs. 18.55%). The entire practical question comes down to whether an implementation can execute below ~4.7bps round-trip, which is a real possibility for the most liquid names via MOC/MOO at a broker like Interactive Brokers (see [`execution_mechanics.md`](execution_mechanics.md)), but is not guaranteed, and this project has no independent way to verify actual achievable spread costs at that precision. The section below tests exactly this.

## Sharpening the cost model: real IBKR Pro fees by account size

The 5bps figure above is a flat modeling assumption, imported from the sibling repo for comparability, not derived from an actual fee schedule. [`execution_mechanics.md`](execution_mechanics.md) researched real costs at IBKR Pro (the broker that supports MOC/MOO) and found the picture is dominated by **position size**, not a single flat number: IBKR Pro's tiered commission is $0.0035/share with a **$0.35 per-order minimum**, which is a large fraction of a small trade's notional and a negligible fraction of a large one. This section rebuilds the backtest with that real fee schedule (plus a flat 0.75bps round-trip spread assumption for this project's mega-cap universe) instead of the flat 5bps, run across a grid of starting account sizes so the position-size dependency is explicit rather than assumed away.

**A methodology note on how this was built, including a bug caught and fixed along the way:** computing a per-trade commission requires knowing how many shares a given dollar amount buys, which requires the stock's actual historical nominal price. This project's price data is dividend+split adjusted (correct for computing returns, see [`../report.md` §1](../report.md#1-method)), but adjusted prices are scaled *down* to reflect every split that has happened between the historical date and today, so a stock that traded at a real $50 in 1993 and has since split several times shows up as a few adjusted dollars in this data. An earlier version of this backtest used those adjusted prices directly to compute share counts, which overstated 1990s-era share counts by the cumulative split factor and produced obviously-wrong "realistic" costs of 25-30bps, 5-6x too high, purely from that artifact, plus every single starting-capital level from $10k to $2M wiping out to exactly $0, which was the tell that something was systematically broken rather than a genuine finding. The fix: use a fixed assumed nominal share price ($150, a reasonable large-cap figure) for the share-count/commission calculation only, not for returns. This avoids needing a second, unadjusted price dataset, and the choice of exact price within a normal large-cap range ($50-300 spans only a 0.23-1.4bps difference in the at-scale commission) doesn't change the qualitative result, which is driven by the $0.35 minimum, not the per-share rate.

![Realistic cost by capital](../charts/portfolio_realistic_cost_by_capital.png)

| Starting capital | CAGR | Sharpe | Max drawdown | Avg. cost (round-trip) | Outcome |
|---|---:|---:|---:|---:|---|
| $10,000 | **-100%** | -0.36 | -100% | 156bps | Wiped out (~2004) |
| $25,000 | **-100%** | -0.33 | -100% | 63bps | Wiped out (~2004) |
| $50,000 | 3.99% | 0.42 | -38.5% | 3.16bps | Marginal, survives |
| $100,000 | 8.43% | 0.82 | -31.6% | 1.50bps | Solid |
| $250,000 | 9.19% | 0.88 | -30.1% | 1.22bps | Converged |
| $500,000 - $2,000,000 | 9.20% | 0.88 | -30.1% | 1.22bps | Converged, identical |

![Realistic cost equity paths](../charts/portfolio_realistic_cost_equity_paths.png)

Three regimes, not one number:

1. **Below roughly $30-40k starting capital, the strategy is genuinely ruinous**, not just unprofitable. At $10-30k spread across ~18-30 names, per-name notional is small enough (a few hundred dollars) that the $0.35 minimum alone costs 15-20+bps round-trip, well above what the underlying edge can support. Losses compound, shrinking positions further, raising the effective bps cost further, in a reflexive spiral that runs to complete capital destruction well within the 33-year window (visible in the $25,000 line above, essentially gone by 2004). This is a materially worse outcome than the flat-5bps case ever shows, because a flat cost cannot represent a cost that gets *worse* as the account loses money.
2. **At $50,000, the strategy survives but only marginally** (CAGR 3.99%, well below SPY, with a rougher drawdown profile than larger accounts because cost is still meaningfully elevated during losing stretches).
3. **At $100,000 and above, the picture flips positive and attractive.** CAGR converges to 9.20%, just under SPY's 10.87%, but at roughly half SPY's volatility (Sharpe 0.88 vs. SPY's 0.65), a genuinely competitive risk-adjusted result. Cost converges to 1.22bps round-trip (the 0.75bps spread assumption plus ~0.47bps of at-scale commission) once the account is comfortably past the point where the $0.35 minimum binds, and adding more capital beyond ~$250k changes nothing further in bps terms, only in dollar scale.

**This meaningfully revises the flat-5bps headline finding above.** The flat 5bps assumption turns out to be *too pessimistic* for a realistically-sized account trading through IBKR Pro (real cost converges to ~1.2bps, comfortably under the 4.71bps breakeven) and simultaneously *far too optimistic* for a small account (real cost can exceed 20bps and cause total ruin, something a flat-bps model cannot show at all). Whether "is this tradeable" is a yes or a no depends almost entirely on how much capital is behind it, not on whether the underlying statistical pattern is real.

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

- **Idle cash yield not modeled** (see Method above), which understates all simulated portfolios (flat-cost and realistic-cost alike) relative to SPY buy & hold.
- **The realistic-cost model insists on equal-weighting all 30 names even when capital is too small to do so sensibly.** A real trader with $10-25k would concentrate in fewer, higher-conviction names rather than mechanically subdividing into unsustainably small positions across all 30; the small-account "ruin" result above is partly an artifact of that rigid rule, not solely an unavoidable fact about small accounts trading this strategy at all. A sensibly-run small account (fewer names, larger per-name notional) would likely land somewhere between the $25k and $100k results shown, not literally at $0.
- **The $150 assumed nominal share price is a simplification**, not a per-ticker historical reconstruction (see the methodology note above); it affects only the at-scale commission component, which is small next to the minimum-driven cost at low notional, so this is unlikely to change the *qualitative* conclusion, but the precise crossover point between "ruin" and "marginal" could shift with a different assumption.
- **Static equal weighting, no periodic reconstitution or quality filters.** A real implementation might do better (or worse) by weighting toward the highest-Sharpe or highest-alpha names identified elsewhere in this project (e.g. MU, AVGO from [`../report.md`](../report.md)) rather than naive equal-weight across all 30; that's a different, untested strategy design.
- **No slippage beyond the modeled spread assumption**, and no modeling of auction-specific execution mechanics detailed in [`execution_mechanics.md`](execution_mechanics.md) (auction depth, name-specific spread variation).
- **Survivorship bias remains**: this is the same fixed 30-name "still large-cap today" universe used throughout the project, not a point-in-time historical index membership.
- **Crisis-window and beta/alpha figures above use the flat-5bps overnight portfolio**, not the realistic-cost-by-capital variant; they haven't been recomputed per capital level.

## Bottom line

The statistical finding throughout this project, that the overnight effect is real, significant, factor-distinct, and not fully explained by a handful of tail-event nights, survives this test either way. What the flat-5bps result and the realistic-cost-by-capital result disagree on is whether that survives contact with real trading costs, and the honest answer is: **it depends entirely on account size.** Below roughly $30-40k, this strategy, run mechanically and without a stop-loss, is not just unprofitable but genuinely ruinous, a reflexive spiral where losses shrink positions, which raises the effective cost, which deepens losses. At $100k and above through a broker with real MOC/MOO access and IBKR Pro's actual tiered commission, the picture flips to a CAGR of ~9.2%, just under SPY's, but at roughly half the volatility and a better Sharpe ratio (0.88 vs. 0.65), a genuinely competitive result. "Is this tradeable" was never a single yes-or-no answer; it's a threshold, and this project's best estimate of where it sits is somewhere between $50,000 and $100,000 of dedicated capital.
