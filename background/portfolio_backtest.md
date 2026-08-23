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
- **Idle cash yield, modeled separately.** The flat-5bps and IBKR-realistic-cost sections below both leave idle cash at 0% yield, unchanged from earlier versions of this project (both portfolios are only ever holding stock for roughly half of each trading day, so this understates their real-world return relative to SPY buy & hold, which captures 100% of every day). A third model, `run_backtest_with_cash_yield()`, credits idle cash with a real, tiered T-bill-based yield: see [Crediting real cash yield](#crediting-real-cash-yield-the-single-biggest-lever-on-the-marginal-account-verdict) below and the full writeup, [`idle_cash_yield_modeling.md`](idle_cash_yield_modeling.md). An earlier version of this project logged live T-bill data as unreachable here; that turned out to be the same TLS-fingerprint block already documented for Yahoo's endpoints, not FRED being genuinely unreachable (see [`fetch_tbills.py`](../scripts/fetch_tbills.py)).

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

## Crediting real cash yield: the single biggest lever on the marginal-account verdict

The section above still leaves idle cash at 0% yield. [`idle_cash_yield_modeling.md`](idle_cash_yield_modeling.md) credits it with a real, tiered T-bill-based sweep yield (FRED `DTB3`, 1993-2026) on top of the same IBKR Pro fee schedule, run across the same starting-capital grid.

| Starting capital | CAGR (no cash yield) | CAGR (with cash yield) | Sharpe (no cash yield) | Sharpe (with cash yield) |
|---|---:|---:|---:|---:|
| $10,000 - $25,000 | -100% | -100% (delayed, still ruinous) | -0.3 to -0.4 | -0.2 to -0.3 |
| **$50,000** | **3.99%** | **9.25%** | **0.42** | **0.89** |
| **$100,000** | **8.43%** | **11.28%** | **0.82** | **1.06** |
| $250,000+ | 9.20% | 11.67% | 0.88 | 1.10 |

Two of the three tiers move meaningfully: **$50k flips from "marginal, worse than SPY on every metric" to "solidly beats SPY on Sharpe (0.89 vs. 0.65)"**, and **$100k+ moves from "beats SPY on a risk-adjusted basis only" to "beats SPY outright on both CAGR and Sharpe"** (11.28-11.67% CAGR vs. SPY's 10.87%). The sub-$30-40k ruin case does not flip: the $0.35 per-order minimum drives round-trip costs an order of magnitude larger than any plausible cash yield, so cash income cannot outrun that cost structure, though it does delay the wipe-out (the $25k account survives to 2005-10 instead of 2003-06). Full method, tier assumptions, and caveats: [`idle_cash_yield_modeling.md`](idle_cash_yield_modeling.md).

## Stress-testing the spread assumption

[`background/independent_review.md`](independent_review.md) finding #5: the 0.75bps round-trip spread used throughout is a modeling assumption for this project's mega-cap universe (see [`execution_mechanics.md`](execution_mechanics.md)), not a per-trade measurement, and the whole tradeability verdict rests on it without ever having been stress-tested. This sweeps it across 0.5/0.75/1.0/1.5bps, on the cash-yield model, at the capital levels where the verdict actually turns.

| Spread | $25,000 | $50,000 | $100,000 | $250,000 |
|---|---:|---:|---:|---:|
| 0.5bps | Ruined | 10.21% CAGR, Sharpe 0.97 | 12.01% CAGR, Sharpe 1.12 | 12.37% CAGR, Sharpe 1.15 |
| 0.75bps (base case) | Ruined | 9.25% CAGR, Sharpe 0.89 | 11.28% CAGR, Sharpe 1.06 | 11.67% CAGR, Sharpe 1.10 |
| 1.0bps | Ruined | 8.23% CAGR, Sharpe 0.80 | 10.54% CAGR, Sharpe 1.00 | 10.97% CAGR, Sharpe 1.04 |
| 1.5bps | Ruined | 5.79% CAGR, **Sharpe 0.59** | 9.05% CAGR, Sharpe 0.87 | 9.58% CAGR, Sharpe 0.92 |

SPY buy & hold over the same window: 10.87% CAGR, 0.65 Sharpe.

**Two findings, in opposite directions.** The sub-$30-40k ruin verdict is completely robust: $25k is wiped out at every spread level tested, 0.5bps to 1.5bps, because the $0.35 per-order minimum dominates regardless of the spread assumption; nothing about that conclusion depends on the 0.75bps figure being right. But **"beats SPY outright on both CAGR and Sharpe" is not fully robust.** The Sharpe advantage over SPY holds at every capital level and spread tested, down to the pessimistic end of the range, but only barely at $50k/1.5bps (0.59, just below SPY's own 0.65). The CAGR advantage is more fragile: **$50k-$250k+ only beat SPY's 10.87% CAGR at spreads of 0.75bps or tighter; at 1.0bps and 1.5bps, every capital level tested still beats SPY on Sharpe but falls back below SPY on CAGR.** Whether "$50k/$100k+ beats SPY outright" or "beats SPY on a risk-adjusted basis only" is the right characterization depends on where real achievable spreads for this universe actually land, and this project has no independent way to pin that down more precisely than the 0.5-1bps range [`execution_mechanics.md`](execution_mechanics.md) already estimated.

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

- **Idle cash yield is not modeled in the flat-cost and realistic-cost sections above** (see Method above), which understates those two portfolios relative to SPY buy & hold; the cash-yield-augmented model above addresses this but has its own caveats, see [`idle_cash_yield_modeling.md`](idle_cash_yield_modeling.md).
- **The 0.75bps spread assumption is a modeling estimate, not a measurement**, and the "beats SPY on CAGR" claim specifically (not the Sharpe claim, and not the ruin verdict, both of which are robust) depends on real achievable spreads landing at 0.75bps or tighter; see the spread-sensitivity sweep above.
- **The realistic-cost model insists on equal-weighting all 30 names even when capital is too small to do so sensibly.** A real trader with $10-25k would concentrate in fewer, higher-conviction names rather than mechanically subdividing into unsustainably small positions across all 30; the small-account "ruin" result above is partly an artifact of that rigid rule, not solely an unavoidable fact about small accounts trading this strategy at all. A sensibly-run small account (fewer names, larger per-name notional) would likely land somewhere between the $25k and $100k results shown, not literally at $0.
- **The $150 assumed nominal share price is a simplification**, not a per-ticker historical reconstruction (see the methodology note above); it affects only the at-scale commission component, which is small next to the minimum-driven cost at low notional, so this is unlikely to change the *qualitative* conclusion, but the precise crossover point between "ruin" and "marginal" could shift with a different assumption.
- **Static equal weighting, no periodic reconstitution or quality filters.** A real implementation might do better (or worse) by weighting toward the highest-Sharpe or highest-alpha names identified elsewhere in this project (e.g. MU, AVGO from [`../report.md`](../report.md)) rather than naive equal-weight across all 30; that's a different, untested strategy design.
- **No slippage beyond the modeled spread assumption**, and no modeling of auction-specific execution mechanics detailed in [`execution_mechanics.md`](execution_mechanics.md) (auction depth, name-specific spread variation).
- **Survivorship bias remains**: this is the same fixed 30-name "still large-cap today" universe used throughout the project, not a point-in-time historical index membership.
- **Crisis-window and beta/alpha figures above use the flat-5bps overnight portfolio**, not the realistic-cost-by-capital variant; they haven't been recomputed per capital level.

## Bottom line

The statistical finding throughout this project, that the overnight effect is real, significant, factor-distinct, and not fully explained by a handful of tail-event nights, survives this test either way. What the flat-5bps result and the realistic-cost-by-capital result disagree on is whether that survives contact with real trading costs, and the honest answer is: **it depends entirely on account size.** Below roughly $30-40k, this strategy, run mechanically and without a stop-loss, is not just unprofitable but genuinely ruinous, a reflexive spiral where losses shrink positions, which raises the effective cost, which deepens losses, and crediting real cash yield doesn't rescue this tier; this verdict is robust across the whole 0.5-1.5bps spread range tested. At $50k and above, crediting real T-bill cash yield on the idle half of each trading cycle (see above) moves the picture from "competitive" to attractive: $50k now beats SPY's Sharpe (0.89 vs. 0.65 at the 0.75bps base case, still ahead down to 0.59 at 1.5bps), and $100k+ beats SPY's Sharpe comfortably at every spread level tested. The CAGR advantage is less robust: **$50k-$250k+ only beat SPY's 10.87% CAGR outright at spreads of 0.75bps or tighter**; at real costs of 1.0-1.5bps, every capital level tested still wins on risk-adjusted terms (Sharpe) but not on raw CAGR. "Is this tradeable" was never a single yes-or-no answer; it's a threshold, and this project's best estimate of where it sits is $50,000 of dedicated capital for a risk-adjusted edge, with outright CAGR outperformance conditional on execution quality this project can't independently verify.
