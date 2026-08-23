# Overnight vs. Intraday Returns: Is There a General Edge?

## Why this exists

This started from a [viral tweet](https://x.com/wheelieinvestor/status/2090827673136472542?s=48) ([@wheelieinvestor](https://x.com/wheelieinvestor), reproduced in [`assets/inspiration_tweet.png`](assets/inspiration_tweet.png) for commentary/attribution) claiming Micron (MU) is up **+138,330,342%** if you only held it overnight (buy at close, sell at next open) since 1990, and **-99.92%** if you only held it during the trading day (buy at open, sell at close). That specific claim [checked out](#appendix-the-original-mu-claim) against real MU price data. The question this project answers is different: **is that a Micron-specific fluke, or a real, tradable, market-wide edge?**

> **Methodology v2.** This report was rebuilt after an independent institutional-style review flagged two material issues in the first pass: (1) unadjusted price data was letting ex-dividend gaps leak into the overnight leg, artificially inflating the apparent effect in high-yield sectors, and (2) the "real edge" framing hadn't been tested against known risk factors, so it could have just been repackaged momentum exposure. Both are fixed below; see the [methodology](#1-method) and [§4](#4-is-this-just-repackaged-momentum). The core numbers changed modestly; the qualitative conclusions did not.

## 1. Method

- **Universe:** 33 liquid large-caps spanning all 11 GICS sectors (3-4 names each) plus SPY, QQQ, and MU as benchmarks/focus names. Full ticker list in [`scripts/fetch_data.py`](scripts/fetch_data.py). This is a deliberate departure from testing MU alone: a single winning stock's history is exactly the kind of sample survivorship bias warns against.
- **Data:** Full available daily OHLC history per ticker from Yahoo Finance, **adjusted for both splits and dividends** (`auto_adjust=True`: Open, High, Low, and Close all use the same adjustment factor). An earlier version of this script used raw, dividend-*unadjusted* prices, which put every ex-dividend price drop mechanically into the overnight leg (`open[t]/close[t-1]`) since Yahoo's raw Close is conventionally dividend-adjusted but raw Open is not, inflating the apparent overnight edge for high-yield sectors by roughly their dividend yield. Fixed by re-pulling with consistent adjustment. History ranges from 1962 for the oldest names to 2010+ for newer listings; MU itself: 1984-06-04 to 2026-08-21, 10,637 trading days. Cached in `data/*.csv`.
- **Decomposition:** every trading day's return is split into two legs:
  - **Overnight**: `open[t] / close[t-1] - 1`, the return earned while the market is *closed*.
  - **Intraday**: `close[t] / open[t] - 1`, the return earned while the market is *open*.

  These compound multiplicatively back to the stock's actual return (`overnight × intraday = buy-and-hold`), so this is a decomposition, not an approximation.
- **Significance testing:** all t-statistics use **Newey-West HAC-robust standard errors** ([`scripts/stats_utils.py`](scripts/stats_utils.py)), not naive `std/sqrt(n)`. Daily equity returns are autocorrelated and volatility-clustered, so with n in the thousands a naive t-test overstates significance.
- **Tests run per ticker:**
  1. Mean daily return, annualized return, annualized volatility, Sharpe, HAC t-statistic and p-value for each leg.
  2. **Breakeven transaction cost**: the flat round-trip cost (in bps) that, subtracted from every day's return, drives the leg's compounded return to exactly zero. Binary-searched per ticker.
  3. **Sub-period split**: first half vs. second half of each ticker's available history, to check the effect isn't an artifact of one regime or an accident of the exact date range used.
  4. **Factor regression**: each leg's daily return regressed (HAC-robust) on the Fama-French Mkt-RF/SMB/HML factors plus momentum, to test whether any "edge" survives controlling for known risk exposures. See [§4](#4-is-this-just-repackaged-momentum).
- **Cross-sectional tests:** one-sample and paired t-tests across ticker-level mean returns, run on a **30-ticker population that excludes SPY, QQQ, and MU**. SPY/QQQ are baskets that overlap with the other 30 constituents (double-counting), and MU was the hand-picked motivating case for this whole project (selection bias). All three are still analyzed and charted individually.
- **Multiple comparisons:** individual-ticker significance counts are reported both raw and after Benjamini-Hochberg false-discovery-rate control, since testing 30 tickers at 95% confidence should produce ~1.5 false positives by chance alone.

Full numeric output: [`reports/summary.json`](reports/summary.json) (cross-sectional) and [`reports/per_ticker_results.json`](reports/per_ticker_results.json) (per-ticker, incl. factor regressions). Reproduce fully offline with `python3 scripts/analyze.py && python3 scripts/make_charts.py` (uses committed `data/*.csv` and `data/factors/`); re-fetch with `python3 scripts/fetch_data.py` / `python3 scripts/fetch_factors.py`.

## 2. Headline result: the pattern is real, but it is not the MU pattern

![Per-ticker overnight vs intraday annualized return](charts/per_ticker_overnight_vs_intraday.png)

The dashed gold line marks SPY's own realized buy-and-hold CAGR over this project's full sample window (1993-2026: 10.9%/yr), the standard "long-term S&P 500 average return" benchmark. Any bar that clears it is beating the market on that leg alone: most of the overnight bars do, most of the intraday bars don't, which is the clearest single visual of where the "alpha" in this whole topic actually comes from.

### Summary: Is This Idea Tradeable?

| Question | Headline Finding | Details & Quantitative Reality |
|---|---|---|
| **Is the statistical edge real?** | **Yes.** | 26 of 30 sector-diversified large-caps remain statistically significant after Benjamini-Hochberg FDR correction ($p < 0.0001$). It is not repackaged momentum ($\text{Mom } t = 0.13$). |
| **Does the extreme MU pattern generalise?** | **No.** | Only MU, BAC, and FCX have a negative intraday leg. For most stocks, both legs are positive; overnight captures the majority of gains. |
| **Where does the edge exist?** | **Selective (Growth/Tech).** | Concentrates in high-attention growth sectors (Tech, Discretionary, Comm Services); **reverses** in defensive sectors (Staples, Utilities, Energy). |
| **Is it tradeable net of execution costs?** | **Yes, but only past a capital threshold ($\ge \$50\text{k}$).** | • **Accounts $<\$30\text{k}\text{--}\$40\text{k}$:** **Ruinous** at every spread level tested (total loss by 2004) due to broker ticket minimums ($\$0.35/\text{order}$) eating $15\text{--}25+\text{ bps}$ per trade against a $4.71\text{ bps}$ breakeven.<br/>• **Accounts $\ge \$50\text{k}$, crediting real T-bill cash yield on idle capital:** **beats SPY's Sharpe at every spread tested** ($0.89$-$1.10$ vs SPY's $0.65$); beating SPY's $10.87\%$ CAGR outright ($9.2$-$11.7\%$) additionally requires real spreads $\le 0.75\text{bps}$, per a sensitivity sweep. See [`background/idle_cash_yield_modeling.md`](background/idle_cash_yield_modeling.md) and [`background/portfolio_backtest.md`](background/portfolio_backtest.md#stress-testing-the-spread-assumption). |
| **What are the structural risks?** | **Tail risk & low diversification.** | 30 names behave like only $\sim 5$ independent bets (mean pairwise correlation $0.38$), with downside $1\%$ CVaR $1.71\times$ fatter than normal. |

---

### Core Decomposition Statistics

| | Overnight leg | Intraday leg |
|---|---:|---:|
| Cross-sectional mean daily return (30 tickers, excl. SPY/QQQ/MU) | **+5.74 bps/day** | +3.37 bps/day |
| Cross-sectional t-stat (vs. zero) | 6.61 (p < 0.0001) | 6.58 (p < 0.0001) |
| % individually significant, raw (95%) | 86.7% positive | 3.3% negative |
| Individually significant after Benjamini-Hochberg FDR control | **26 / 30** (vs. ~1.5 expected by chance) | 16 / 30 |
| Paired t-test, overnight mean > intraday mean across tickers | t = 2.07, **p = 0.047** | n/a |

Two things are true at once:

1. **The overnight leg is a genuine, statistically significant, broad-based phenomenon, and it survives multiple-comparisons correction.** 26 of 30 tickers remain significant after Benjamini-Hochberg FDR control, against an expected ~1.5 false positives by chance. This replicates the published literature (see [§8](#8-is-there-academic-basis-for-this)); it is not noise, and not a multiple-testing artifact.
2. **The MU-style pattern (massive overnight gains *and* a losing intraday leg) is still not the general case.** Only BAC (and FCX marginally) join MU with a significantly *negative* intraday leg. For most stocks, both legs are positive; overnight is usually the bigger slice, but intraday isn't burning money, it's just growing slower.

![Significance scatter](charts/significance_scatter.png)

In the scatter above, MU, BAC, and FCX are alone in the bottom-right quadrant (overnight strongly positive AND intraday negative). Everyone else with a strong overnight effect (AAPL, NVDA, TSLA, AVGO, HD) still has a *positive*, just statistically weaker, intraday leg.

One change from the dividend-adjustment fix: the cross-sectional paired test (overnight mean > intraday mean) now lands at **p = 0.047**, barely significant, versus p = 0.067 (not significant) before the fix and before excluding SPY/QQQ/MU from the pool. Read that "barely" literally: this is not a strong result, and a different but equally reasonable 30-ticker draw could easily land on either side of 0.05. That fragility is now measured, not just caveated: restricting to 2000+ data only (removing the pre-2000 decades where per-ticker coverage is thinner) flips this specific test to **p = 0.059**, not significant at 5%, while every other headline number in this section (26/30 FDR-significant, cross-sectional mean itself) moves only modestly. See [`background/data_hygiene_bias_filter.md`](background/data_hygiene_bias_filter.md).


## 3. Where the effect concentrates: growth/attention sectors, not the whole market

![Sector gap](charts/sector_gap.png)

Grouping by GICS sector still makes the pattern explicit even after the dividend fix. The overnight-dominant effect concentrates in **Information Technology, Consumer Discretionary, Communication Services, and Financials**, sectors full of high-volatility, high-retail-attention, "story" stocks. It **reverses** in **Consumer Staples, Energy, Utilities, and (mildly) Health Care**, the boring, low-attention, dividend-paying end of the market, where the *intraday* session now captures more of the return even with the dividend-leakage artifact removed.

This lines up with the leading academic explanation for the overnight effect (retail investors chasing high-attention stocks at the open, see §8): staples and utilities don't attract that kind of speculative morning order flow, so they don't show the pattern.

**Practical read:** "buy the close, sell the open" is closer to a **growth/momentum-stock characteristic** than a market-wide law. Applying it uniformly across a diversified portfolio would be fighting the data in roughly a third of your sectors.

## 4. Is this just repackaged momentum?

The literature this project draws on (Lou-Polk-Skouras) explicitly frames overnight returns as a momentum-clientele effect, which raises the obvious question: is "the overnight edge" just exposure to the standard momentum factor wearing a costume? Each ticker's overnight leg was regressed (HAC-robust) on Mkt-RF, SMB, HML, and Momentum; the intercept (**alpha**) is the return left over after controlling for all four.

![Sector factor alpha](charts/sector_factor_alpha.png)

The sector split survives almost unchanged after stripping out factor exposure. Consumer Discretionary and Information Technology still show the largest positive alpha, Consumer Staples the most negative, and the ordering is nearly identical to the raw chart in §3. **16 of 30 tickers retain a statistically significant overnight alpha** after controlling for all four factors (mean +8.6%/yr across the cross-section); 3 (PG, XOM, LIN) have a *significantly negative* alpha.

![Alpha vs momentum loading](charts/alpha_vs_momentum_loading.png)

More directly: the mean momentum-factor loading on the overnight leg across the cross-section is **0.0015 (t = 0.13)**, statistically indistinguishable from zero. The scatter above shows alpha t-statistics spread widely from -5 to +6 while momentum-loading t-statistics cluster tightly around zero for almost every ticker; there's no relationship between "how exposed is this stock's overnight leg to momentum" and "how big is its overnight alpha." **This is not repackaged momentum.** Whatever is producing the sector split in §3, it isn't showing up as standard momentum-factor exposure.

## 5. Does it survive costs and time? Partially.

**Persistence:** splitting each ticker's own history into a first half and second half, the cross-sectional correlation of overnight annualized return is **0.65** (tickers with a strong overnight effect early tend to keep it later) vs. much weaker for the intraday leg. That's evidence the overnight effect is closer to a real, persistent stock characteristic than the intraday leg is.

![Sub-period consistency](charts/subperiod_consistency.png)

**Transaction costs are still the real problem.** For each ticker, we solved for the flat round-trip cost that would erase the entire compounded overnight edge:

![Breakeven cost distribution](charts/breakeven_cost_distribution.png)

- **27 of 30** cross-section tickers have a gross-profitable overnight leg at all.
- Median breakeven cost: **4.2 bps round-trip** (down slightly from the pre-fix estimate: some of the apparent margin in defensive names was the dividend artifact). Half of the profitable names (14/27) lose their entire edge to a cost below 5bps.
- Even the most extreme cases in the whole universe, **TSLA (15.0bps), MU (14.3bps), NVDA (13.3bps)**, only survive costs up to ~13-15bps round-trip. This is a *daily* number compounding over 4,000-10,600 trading days: even a cost that looks negligible on any single day fully erases decades of the headline result.

This is the actual answer to "is there a tradable edge": **gross of costs, yes, a real, factor-distinct, FDR-robust effect for roughly half the names tested, concentrated in growth sectors. Net of realistic execution costs, the margin of safety is razor-thin to nonexistent for the median stock**, and only comfortably survives costs for a handful of high-volatility names that also carry the highest overnight *gap risk* (the same mechanism that produces big up-gaps produces big down-gaps on bad news).

## 6. Does timing within the week matter, and is it just a few big nights?

Two follow-up questions, each with its own dedicated background note since the methodology needs more caveats than fit cleanly here.

**Which weekday should you buy the close on?** It matters, a lot.

![Day of week overnight return](charts/day_of_week_overnight_return.png)

Splitting the overnight leg by the weekday of the close being bought, Monday is the strongest day of the week (27.4% mean annualized return across the cross-section) and Friday, the 3-day weekend gap into Monday's open, is the weakest (7.8%), both statistically significant (p < 0.001). This is a new finding for this project, not confirmed anywhere in the literature reviewed in §8, so treat it as an empirical pattern in this dataset rather than an established result. Full writeup: [`background/day_of_week_analysis.md`](background/day_of_week_analysis.md).

**Is the edge just a handful of earnings-like gap nights?** Mostly no.

![Extreme gap decomposition](charts/extreme_gap_decomposition.png)

Flagging the ~1.7% of days with the most extreme overnight moves (>3 standard deviations, a proxy for earnings/news gaps since precise historical earnings-date data isn't available for free at this depth) and removing them, 27 of 30 tickers keep a statistically significant positive overnight return, and the cross-sectional mean only falls from 16.4% to 14.5% annualized. The effect is broad-based for most names, though a handful of the biggest headline numbers (TSLA, HD, BAC, GOOGL, NVDA, AVGO) lean more heavily on tail events than the average name does. Full writeup: [`background/extreme_gap_analysis.md`](background/extreme_gap_analysis.md).

## 7. Has the edge decayed recently?

Motivated by a Federal Reserve Bank of New York paper, ["The Disappearing Overnight Drift"](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/), which finds a narrow 2:00-3:00am ET window in S&P 500 futures (the European market open) averaged +3.7%/yr from 1998-2020 but has averaged close to zero since 2021, attributed to a compression in end-of-day order-imbalance dispersion, not a change in volatility.

![Recency rolling return](charts/recency_rolling_return.png)

**No, not at the aggregate level, though the composition underneath has shifted a lot.** This project can't isolate that specific 2-3am window (daily OHLC only, no intraday ticks), but testing the full overnight leg across the 30-ticker cross-section: the pre-2021 vs. post-2021 mean annualized return (17.97% vs. 13.24%) is not a statistically significant change (paired t = 1.38, p = 0.18), and the rolling 2-year chart above (date-alignment bug fixed, see [`background/recency_regime_analysis.md`](background/recency_regime_analysis.md)) shows no visible break at 2021, if anything a local peak right at the break date. 8 of 30 tickers remain individually significant post-2021 after Benjamini-Hochberg FDR correction, well above the ~1.5 expected by chance, despite a much smaller post-break sample.

But aggregate stability hides real rotation: TSLA, AAPL, HD, GOOGL, NFLX, and META, the growth/attention names that drove much of the pre-2021 effect in §3, all faded sharply post-2021 (AAPL actually flips to a small, insignificant negative), while AVGO, LLY, CAT, CVX, XOM, and NEE all strengthened. This looks more like retail/market attention rotating to new names (the AI/semiconductor cycle since 2023) than a single structural mechanism fading market-wide the way the NY Fed's narrow futures-window finding describes. Full writeup, including the caveat that this project didn't independently validate 2021 as *its own* optimal break date: [`background/recency_regime_analysis.md`](background/recency_regime_analysis.md).

## 8. Is there academic basis for this?

Yes, this is a well-documented phenomenon, not a chart trick. Key references (full literature review with links: [`background/literature_review.md`](background/literature_review.md)):

- **French & Roll (1986)**: first documented that volatility (and by extension return patterns) differs sharply between trading and non-trading hours for the aggregate market.
- **Berkman, Koch, Tuttle & Zhang (2012, *Journal of Financial and Quantitative Analysis*), "Paying Attention: Overnight Returns and the Hidden Cost of Buying at the Open"**: the leading mechanism. Retail investors queue orders overnight and buy attention-grabbing stocks right at the open, pushing the open price up; institutions fade that flow intraday, pulling the price back down by the close. This is consistent with what §3 finds: the effect concentrates in the stocks retail investors actually chase (growth/tech/consumer names), not staples and utilities.
- **Lou, Polk & Skouras (2019, *Journal of Financial Economics*), "A Tug of War: Overnight Versus Intraday Expected Returns"**: shows overnight and intraday returns behave like two separate return series with opposite momentum/reversal signatures, driven by different investor clienteles. §4's factor regression is a direct empirical check on this paper's own momentum framing, and finds the momentum loading itself isn't what's driving it here.
- Follow-on market-microstructure work confirms retail and institutional order-flow imbalances are negatively correlated: wholesalers internalize retail flow specifically to offset institutional demand, mechanically producing the open-high/close-low pattern in attention-grabbing names.

## 9. Is this actually tradeable? A full portfolio backtest

Everything above is descriptive: does the pattern exist, is it significant, does it survive controls. This section is different: a simulated, day-by-day equal-weight portfolio of all 30 cross-section tickers, bought at close and sold at next open (and, for contrast, the intraday-only version), net of a 5bps round-trip cost, run against real SPY buy & hold over the full 1993-2026 window.

![Portfolio backtest equity curve](charts/portfolio_backtest_equity.png)

**No, not at a realistic cost.** At 5bps round-trip, matching the convention used in this project's sibling VIX-regime-switch backtest, the diversified overnight-only portfolio loses money: CAGR -0.73%, Sharpe -0.02, a max drawdown of -52.83% that it stays underwater from for roughly 26 of the 33 years tested. It is still clearly the better of the two legs (intraday-only loses far more: CAGR -5.19%, growth of $1 to just $0.17), consistent with everything else in this report, but "less bad" is not "profitable."

**Why this is worse than the per-ticker breakeven analysis in §5 suggested:** that analysis found a median single-ticker breakeven of ~4.2bps and a cross-sectional mean overnight return of 5.74bps/day, numbers unweighted across each ticker's own full history. A real portfolio's daily return is instead weighted by whichever tickers actually existed that day, and the early decades of this backtest (1993-2010) held far fewer names and specifically lacked the growth/semiconductor names (NVDA, META, TSLA, AVGO) that carry the strongest individual overnight edge. The portfolio's own solved breakeven cost is **4.71bps**, close to but still below the 5bps this project treats as realistic.

![Portfolio cost sensitivity](charts/portfolio_cost_sensitivity.png)

Below that breakeven the picture is genuinely attractive (0bps cost: 12.60% CAGR, beating SPY's 10.87%, at little more than half SPY's volatility), so the entire practical question comes down to whether an implementation can execute below ~4.7bps round-trip, plausible for the most liquid names via MOC/MOO at a broker like Interactive Brokers (see [`background/execution_mechanics.md`](background/execution_mechanics.md)).

**Rebuilding the cost model with IBKR Pro's actual fee schedule instead of the flat 5bps assumption answers that question directly, and it depends entirely on account size.** IBKR Pro charges $0.0035/share with a $0.35 per-order minimum; that minimum is a large fraction of a small trade and negligible on a large one, so cost isn't one number, it's a function of capital.

![Realistic cost by capital](charts/portfolio_realistic_cost_by_capital.png)

| Starting capital | CAGR | Sharpe | Outcome |
|---|---:|---:|---|
| $10,000-$25,000 | **-100%** | -0.3 to -0.4 | Wiped out by ~2004 |
| $50,000 | 3.99% | 0.42 | Marginal, survives |
| $100,000 | 8.43% | 0.82 | Solid |
| $250,000+ | **9.20%** | **0.88** | Converged, beats SPY's Sharpe |

Below roughly $30-40k, the strategy is not just unprofitable but **ruinous**: small positions mean the $0.35 minimum alone costs 15-20+bps round-trip, and losses compound into smaller positions, which raises the effective cost further, a reflexive spiral to total capital destruction that a flat-bps model cannot represent (the $25,000 equity path below is essentially gone by 2004). At $100k and above, cost converges to ~1.2bps round-trip, comfortably under the 4.71bps breakeven, and CAGR converges to 9.20%, just under SPY's, but at roughly half the volatility and a better Sharpe ratio (0.88 vs. SPY's 0.65).

![Realistic cost equity paths](charts/portfolio_realistic_cost_equity_paths.png)

**This revises the flat-5bps result above rather than replacing it.** The flat 5bps assumption is too pessimistic for a realistically-capitalized account (real cost converges far below it) and far too optimistic for a small one (real cost can exceed 20bps and cause total ruin, which no flat number can show). Full methodology, including a bug in an earlier version of this calculation that was caught and fixed (using split-adjusted historical prices to estimate historical share counts, which overstated 1990s-era commissions by 5-6x), is in [`background/portfolio_backtest.md`](background/portfolio_backtest.md).

**Crediting real T-bill cash yield on idle capital revises it again, and this is the single biggest lever tested in this project.** The models above leave idle cash at 0% yield; [`background/idle_cash_yield_modeling.md`](background/idle_cash_yield_modeling.md) credits it with a real, tiered T-bill-based sweep yield (FRED `DTB3`, 1993-2026) on the roughly half of each cycle the overnight-only book holds cash instead of stock. **The $50k tier flips from marginal (3.99% CAGR, Sharpe 0.42) to solidly beating SPY's Sharpe (9.25% CAGR, Sharpe 0.89), and the $100k+ tier flips from "beats SPY on a risk-adjusted basis only" to beating SPY outright on both CAGR and Sharpe (11.28-11.67% CAGR vs. SPY's 10.87%, Sharpe 1.06-1.10 vs. 0.65).** The sub-$30-40k ruin case doesn't flip: transaction costs there are an order of magnitude larger than any plausible cash yield, so cash income can delay the wipe-out but not prevent it.

**The 0.75bps spread this uses is a modeling assumption, not a measurement, and a sensitivity sweep (0.5/0.75/1.0/1.5bps) finds the CAGR-outperformance claim is more fragile than the Sharpe-outperformance claim.** The ruin verdict below $30-40k is robust across the whole range tested. The Sharpe advantage over SPY holds at every capital level and spread tested (though only barely: $50k at 1.5bps drops to Sharpe 0.59, just under SPY's 0.65). But **beating SPY's CAGR outright only holds at spreads of 0.75bps or tighter**; at 1.0-1.5bps, every capital level from $50k to $250k+ still beats SPY on Sharpe but falls back below SPY on CAGR. Full sweep: [`background/portfolio_backtest.md`](background/portfolio_backtest.md#stress-testing-the-spread-assumption).

**Crisis behavior (flat-5bps version) is not uniformly protective.** The overnight portfolio meaningfully outperformed SPY during the 2008-09 GFC (-17.6% vs. -36.6%), the 2010 Flash Crash, and the 2018 Q4 selloff, but meaningfully underperformed during the 2020 COVID crash (-20.1% vs. -13.6%) and the 2022 rate-hike bear market (-24.4% vs. -18.2%), the two most recent major drawdowns. Overall beta vs. SPY is 0.32 (expected, given it's invested only half of each day), but annualized alpha is **-3.97%/yr** at the 5bps cost this section uses, negative even after adjusting for that lower beta exposure.

Limitation carried into the crisis-window and beta/alpha figures specifically: they use the flat-5bps version, which still leaves idle cash at 0% yield, understating this portfolio's real-world return relative to SPY buy & hold, since SPY captures 100% of every trading day while this strategy is only ever invested for half of each day-night cycle. Full method, all caveats, and the exact numbers behind every claim above: [`background/portfolio_backtest.md`](background/portfolio_backtest.md).

## 10. Three further stress tests: correlation risk, volatility regime, and a momentum overlay

Everything above establishes that the effect is real, where it concentrates, and whether a diversified implementation is tradeable. Three further questions, prompted by an independent review of what else this dataset could answer, each get a dedicated background note since the methodology needs more room than fits here.

**How much real diversification does the 30-name portfolio actually have?** Less than it looks. The correlation matrix of the 30 tickers' overnight returns shows a mean pairwise correlation of 0.38, with a single common factor explaining 41% of the cross-sectional variance; the eigenvalue spectrum implies the book behaves like roughly **5 independent bets**, not 30. The overnight leg's downside tail is also fatter than its own volatility would predict under a normal distribution (1% CVaR is 1.71x the Gaussian-implied figure, versus 1.4x for the intraday leg), and 8 of the 10 worst single days for the equal-weight portfolio cluster into just three systemic-crisis windows (COVID March 2020, the 2008 GFC, and the August 2015 China-deval selloff). This doesn't change any realized number in [§9](#9-is-this-actually-tradeable-a-full-portfolio-backtest), which is measured directly from the equity curve, but it explains *why* the portfolio's volatility isn't lower than it is despite holding 30 names, and confirms its risk is concentrated in correlated macro-shock nights, not spread evenly across idiosyncratic single-stock risk. Full writeup: [`background/correlation_tail_risk_analysis.md`](background/correlation_tail_risk_analysis.md).

**Is the edge timeable by volatility regime?** No reliable signal found. Pooling all 30 tickers' overnight returns and conditioning on the VIX level at the buy-day close, the top VIX quartile does show the highest raw annualized return (15.0% vs. 11.4-12.7% in the other three quartiles), consistent with an uncertainty-resolution mechanism. But a HAC-robust regression of the pooled return directly on VIX level finds no statistically reliable relationship (t = 0.53, p = 0.59, R-squared effectively zero across 236,905 pooled observations), and neither does a regression on the day-over-day change in VIX. The honest read: the effect does not appear to break down in high-stress regimes (useful, and consistent with §9's crisis-window survival), but there's no evidence of a tradeable VIX-based timing overlay either. Full writeup: [`background/vix_regime_analysis.md`](background/vix_regime_analysis.md).

**Does a stock's own trailing overnight performance predict its future overnight performance?** Yes, strongly, and it's the most promising lever in this whole project, though not as strong going forward as the full-sample number suggests. Sorting the cross-section into terciles by trailing overnight momentum (tested at 5, 21, and 63-day lookback windows, all local, no new data) and holding only the top tercile produces an annualized top-minus-bottom spread of 22.7-28.8%, highly significant at every horizon (t = 13.4-16.6) and robust to restricting the sample to the same 1993-2026 window used in §9 (top tercile: 11.2% CAGR, Sharpe 0.89 vs. equal-weight-all's -0.84% CAGR, Sharpe -0.03 over that window). At the headline 21-day window and the same flat 5bps cost used in §9, top-tercile-only produces Sharpe 1.16, better than either the naive equal-weight portfolio or SPY's 0.65. One caveat worth stating plainly: over multi-decade horizons, part of what a persistent-loser sort like this can capture is structural company quality or distress rather than a short-horizon overnight-specific signal, a distinction this dataset can't fully separate. Full writeup: [`background/overnight_momentum_analysis.md`](background/overnight_momentum_analysis.md).

**Out-of-sample validation, since Sharpe 1.16 was discovered in-sample: real, but roughly half the headline number.** [`background/walk_forward_validation.md`](background/walk_forward_validation.md) selects the best lookback using only 1993-2010 data (the 21-day headline window wins in-sample too, so it wasn't cherry-picked with hindsight), then tests it strictly on 2011-2026: **Sharpe 0.53, not 1.16**, still ahead of the naive equal-weight book but well below the full-sample figure. A purged 5-fold walk-forward selection test (5-trading-day purge buffer around each fold boundary) shows every single fold's selected lookback stays positive out-of-sample, but with a clear temporal pattern: the three earliest folds (1972-2005) show Sharpes of 1.11-2.17, while the two most recent folds (2005-2026) are weaker (0.84, then 0.43 in 2015-2026, the single weakest result in the strategy's 54-year history). A Deflated Sharpe Ratio check (Bailey & Lopez de Prado) rules out the full-sample Sharpe being a multiple-testing artifact of trying 3 lookbacks (DSR > 0.9999 for all three), but that's a narrower claim than "will repeat going forward," which the holdout test already answers: underwrite this overlay around a Sharpe of 0.4-0.7 in the current regime, not 1.16.

## 11. Bottom line

| Question | Answer |
|---|---|
| Is the original MU chart's math right? | Yes, independently reproduced (see appendix). |
| Does the *extreme* MU pattern (huge overnight gain, losing intraday) generalize across the market? | **No.** Only MU, BAC, and FCX show it out of 33 names; it's the exception, not the rule. |
| Is there a *real, general* overnight-return effect at all? | **Yes.** 26 of 30 sector-diversified tickers remain significant after FDR correction (vs. ~1.5 expected by chance), matching published academic findings. |
| Does it concentrate anywhere? | **Yes**, in growth/high-attention sectors (Tech, Discretionary, Comm Services, Financials). It *reverses* in Staples, Energy, Utilities. |
| Is it repackaged momentum? | **No.** Momentum-factor loading on the overnight leg is statistically zero (t=0.13); 16/30 tickers retain significant alpha after controlling for market/size/value/momentum. |
| Does the weekday you buy matter? | **Yes.** Monday's close is the strongest (27.4% mean annualized), Friday's close (the weekend gap) the weakest (7.8%), both p<0.001. New to this project, not independently confirmed in the literature. |
| Is it just a few earnings-like pops? | **Mostly no.** Only ~1.7% of days are extreme gaps; 27/30 tickers stay significant with those days excluded, and the mean annualized return only falls 16.4%→14.5%. |
| Has the edge decayed recently (post-2021)? | **Not at the aggregate level** (17.97%→13.24% annualized, p=0.18, not significant; 8/30 tickers still significant after FDR). But real rotation underneath: TSLA/AAPL/HD/GOOGL/NFLX/META faded, AVGO/LLY/CAT/CVX/XOM/NEE strengthened. |
| Is it persistent over time? | Reasonably: 0.65 cross-sectional correlation between first-half and second-half overnight returns. |
| Is it a free lunch net of costs, per-ticker? | **No.** Median breakeven cost is ~4.2bps round-trip; even the best cases (TSLA, MU, NVDA) only tolerate ~13-15bps. |
| **Would a real, diversified, cost-aware portfolio actually have made money?** | **It depends entirely on account size, and somewhat on the spread assumption.** At a flat 5bps assumption, no (CAGR -0.73% vs. SPY's 10.87%). Rebuilt with IBKR Pro's real fee schedule: **ruinous below ~$30-40k** (total capital loss by ~2004, robust to spread assumption), **marginal at $50k** (3.99% CAGR), **solidly profitable at $100k+** (CAGR converges to 9.20%, Sharpe 0.88). Crediting real T-bill cash yield on idle capital, the single biggest lever tested in this project, moves this further: **$50k-$250k+ beat SPY's Sharpe at every spread level tested (0.5-1.5bps)**, and **beat SPY's CAGR outright too, but only at spreads of 0.75bps or tighter** (at 1.0-1.5bps, every level still wins on Sharpe but falls back below SPY on CAGR). See [`background/idle_cash_yield_modeling.md`](background/idle_cash_yield_modeling.md) and [`background/portfolio_backtest.md`](background/portfolio_backtest.md#stress-testing-the-spread-assumption). This is the single most important nuance in the whole report: the effect is statistically real everywhere, but whether it's tradeable is a threshold in dollars conditioned on real execution quality, not a yes/no answer. |
| How diversified is the 30-name portfolio really? | **Less than it looks.** The overnight legs behave like roughly **5 independent bets**, not 30 (mean pairwise correlation 0.38, one common factor explains 41% of cross-sectional variance), and the overnight leg's downside tail is 1.71x fatter than a Gaussian with the same mean/vol would predict. 8 of the 10 worst single days cluster into three systemic-crisis windows. |
| Is the edge stronger in high-volatility regimes, i.e. is it timeable? | **No reliable signal.** Raw VIX-quartile averages show a mild upward tilt (11.4-15.0% annualized), but a HAC-robust regression on VIX level finds no statistically significant relationship (t=0.53, R-squared~0). The edge doesn't break down under stress, but there's no tradeable VIX-timing overlay here. |
| Does a stock's own trailing overnight performance predict its future overnight performance? | **Yes, strongly, but the Sharpe 1.16 headline is in-sample.** Top-vs-bottom tercile spread of 22.7-28.8%/yr annualized, significant at every lookback tested (5/21/63-day, t=13.4-16.6), robust to the 1993-2026 window. Walk-forward tested (select on 1993-2010, evaluate on 2011-2026): **Sharpe 0.53, not 1.16**, and the most recent purged fold (2015-2026) is the weakest in the strategy's 54-year history (Sharpe 0.43). Still positive in every out-of-sample cut tested and ahead of naive equal-weighting; long-run persistence sorts like this can also partly reflect company quality/distress rather than a pure overnight-specific signal. See [`background/walk_forward_validation.md`](background/walk_forward_validation.md). |

## Limitations

- Universe is 33 large/mega-cap US names, and doesn't cover small-caps, non-US markets, or delisted/failed companies. The 30-ticker cross-section is still conditioned on "large-cap today," so survivorship bias is reduced (dividend fix, factor-neutrality) but not eliminated: a stock's multi-decade winner status can still concentrate in the overnight leg if the overnight effect is itself momentum-like at the individual-stock level, even though the *aggregate* momentum-factor loading is flat.
- Fama-French factor data currently runs through 2026-06-30, so §4's factor regressions use a slightly shorter window than the full price history (which runs to 2026-08-21); this is a ~7-week truncation against decades of history and immaterial to the conclusions.
- Breakeven cost analysis assumes a flat per-trade cost; real costs vary by name, liquidity, and order type (MOO/MOC auctions specifically, which is what this strategy would require in practice, carry their own execution risk beyond simple spread cost), and an actual overnight holder collects any dividend paid, which isn't separately modeled as a benefit here even though the price-adjustment fix removes it as a distortion.
- Sub-period "first half vs. second half" uses each ticker's own full history, so the split date differs by ticker (not a shared out-of-sample date): this tests persistence of each stock's *own* pattern, not a shared regime shift.
- Sector labels are assigned once, present-day, and applied to each ticker's entire history: a company's sector character can drift over decades (e.g. AMZN's business mix looked very different in 1998 than today).
- Only 2-3 tickers per sector for several sectors (Energy, Materials, Real Estate, Utilities): thin enough that a different random draw of the same sectors could shift the sector-level conclusions in §3-4, even though the overall growth-vs-defensive pattern is unlikely to fully reverse.
- None of the above models taxes, or the real mechanics of actually placing MOC/MOO orders (exchange cutoff times, broker support, execution slippage vs. the official auction print). See [`background/execution_mechanics.md`](background/execution_mechanics.md) for what it would actually take to trade this.
- §9's flat-5bps and IBKR-realistic-cost portfolio backtests do not model idle cash earning a yield during the half of each cycle they aren't invested; a third model does (see §9), and moves the $50k and $100k+ verdicts materially, but the specific tier-spread assumptions in that model are this project's own estimate, not a published broker rate card (see [`background/idle_cash_yield_modeling.md`](background/idle_cash_yield_modeling.md)). None of the three models test any weighting beyond naive equal-weight, and all inherit the same static-universe survivorship noted above. See [`background/portfolio_backtest.md`](background/portfolio_backtest.md) for the full caveat list.
- §10's momentum-overlay full-sample Sharpe (1.16) was discovered in-sample; walk-forward tested (see §10), the genuinely out-of-sample Sharpe is 0.53, and long-horizon trailing-return sorts can also partly capture structural company quality/distress rather than a pure overnight-specific effect. See [`background/overnight_momentum_analysis.md`](background/overnight_momentum_analysis.md) and [`background/walk_forward_validation.md`](background/walk_forward_validation.md).
- An outside audit found an undisclosed data issue: days where the recorded open equals the recorded close (a Yahoo Finance artifact, concentrated in the pre-2000 portion of each ticker's history, 16% of rows in the 1962-1999 decades pooled, 0.75% in 2000-2026) mechanically route the whole day's return into the overnight leg. This has since been quantified and re-run two ways: excluding those specific days actually *raises* the headline cross-sectional overnight mean slightly (5.74 -> 5.99bps), the opposite of the review's hypothesized direction, while restricting to modern-era-only data (a blunter, unrelated cut) flips the already-fragile paired overnight-vs-intraday significance test from p=0.047 to p=0.059. Full findings: [`background/data_hygiene_bias_filter.md`](background/data_hygiene_bias_filter.md). The review's other flags, the (now-resolved) idle-cash-yield gap and the still-open OOS-validation gap for the momentum overlay, are in [`background/independent_review.md`](background/independent_review.md).

## 12. Glossary of Terms (Layperson's Guide)

A quick-reference guide explaining the financial, quantitative, and statistical concepts used throughout this project in plain English.

### Trading Sessions & Order Mechanics

*   **Overnight Leg (Overnight Drift):** The percentage price change from the official market close of one day ($16:00\text{ ET}$) to the official market open of the following trading day ($09:30\text{ ET}$). Computed as $\frac{\text{Open}_t}{\text{Close}_{t-1}} - 1$. This captures gains or losses that happen while regular US stock exchanges are closed.
*   **Intraday Leg:** The percentage price change during the regular trading session from the opening bell to the closing bell. Computed as $\frac{\text{Close}_t}{\text{Open}_t} - 1$.
*   **Buy-and-Hold:** The traditional investment approach of buying a share and simply holding it continuously across both day and night sessions without trading. Mathematically, $(1 + \text{Overnight}) \times (1 + \text{Intraday}) = 1 + \text{Buy-and-Hold Return}$.
*   **Market-on-Close (MOC) Order:** An order sent to the exchange execution auction requesting to purchase or sell shares exactly at the official closing print of the regular trading day.
*   **Market-on-Open (MOO) Order:** An order requesting execution at the official opening price determined by the exchange's morning opening auction.
*   **Weekend Gap:** The overnight return earned between Friday's close and Monday's open, spanning three calendar days of global news and events rather than a single 17.5-hour overnight gap.
*   **Bid-Ask Spread & Slippage:** The bid is the highest price buyers offer; the ask is the lowest price sellers accept. The spread is the difference between them (a direct cost of trading). Slippage is the difference between the expected price when placing an order and the actual price at which the order fills in the market auction.

### Statistical & Econometric Concepts

*   **Autocorrelation (Serial Correlation):** When today's return is correlated with yesterday's return rather than being completely independent. In daily stock returns, treating days as independent when they are autocorrelated creates artificially inflated statistical confidence.
*   **Volatility Clustering:** The tendency for calm trading days to follow calm days, and turbulent, volatile days to follow turbulent days (risk arrives in clusters rather than being evenly spread).
*   **Newey-West HAC Standard Errors:** An econometric correction technique (Heteroskedasticity and Autocorrelation Consistent) developed by Whitney Newey and Kenneth West. It adjusts standard statistical tests (like the $t$-test) to remain accurate even when returns suffer from autocorrelation and volatility clustering, preventing false claims of "statistical significance."
*   **$t$-Statistic & $p$-Value:** A $t$-statistic measures how many standard errors an estimated return is away from zero (a value above $+1.96$ or below $-1.96$ indicates a $<5\%$ chance of occurring randomly under normal assumptions). The $p$-value is the probability that the observed result occurred by pure random chance. A $p$-value $<0.05$ is conventionally called "statistically significant."
*   **Benjamini-Hochberg False Discovery Rate (FDR):** When you test 30 different stocks at a $95\%$ confidence level, you expect $\sim 1.5$ false positives purely by chance (the *multiple comparisons problem*). The Benjamini-Hochberg procedure dynamically tightens the $p$-value threshold across all 30 tests so that the overall proportion of accidental false discoveries is controlled below $5\%$.
*   **Selection Bias & Survivorship Bias:** *Selection bias* occurs when picking a winning stock (like Micron / $MU$) because of its known historical success, creating a distorted impression of average market behaviour. *Survivorship bias* occurs when only studying companies that survived and are large caps today, ignoring failed or delisted companies.
*   **Z-Score & 3-Sigma ($3\sigma$) Extreme Gaps:** A Z-score measures how many standard deviations a single day's move is away from that stock's average move. A $3\sigma$ move represents an extreme statistical outlier (the top/bottom $\sim 0.3\%$ of a normal distribution), typically caused by earnings surprises, takeover bids, or major macro shocks.

### Asset Pricing & Risk Factors

*   **Fama-French 4-Factor Model:** A standard financial model explaining stock returns through four systematic market drivers:
    1.  **Mkt-RF (Market Risk):** Broad stock market return minus the risk-free cash rate.
    2.  **SMB (Small Minus Big):** The historical premium earned by small-cap companies over large-caps.
    3.  **HML (High Minus Low / Value):** The historical premium earned by value stocks (high book-to-market) over growth stocks.
    4.  **MOM / UMD (Momentum):** The premium earned by stocks that went up over the past 12 months over stocks that went down.
*   **Alpha ($\alpha$):** The portion of an investment's return that cannot be explained by exposure to broad market movements or known risk factors (Fama-French factors). True "excess return" or genuine managerial/strategy edge.
*   **Beta ($\beta$):** A measure of sensitivity to the broad market. A beta of $1.0$ moves in lockstep with the market; a beta of $0.5$ experiences half the market's swings.
*   **Risk-Free Rate ($R_f$):** The theoretical rate of return on an investment with zero credit risk, usually represented by short-term US Treasury bill yields.
*   **CBOE Volatility Index (VIX):** Often called Wall Street's "fear gauge", the VIX measures the stock market's 30-day forward implied volatility priced into S&P 500 index options.
*   **Uncertainty Resolution Hypothesis:** A financial theory suggesting that holding risk overnight carries uncertainty (macro announcements, international market moves, geopolitical news). Investors require an overnight premium (higher return) as compensation for bearing this closed-market risk, which resolves when the market opens.

### Portfolio Performance & Risk Metrics

*   **Basis Point (bps):** A unit of measure equal to one-hundredth of a percentage point ($0.01\%$). $100\text{ bps} = 1.0\%$; $5\text{ bps} = 0.05\%$.
*   **Compound Annual Growth Rate (CAGR):** The geometric annualised rate of return that would grow an investment from its initial value to its ending balance, accounting for compounding.
*   **Annualised Volatility:** The standard deviation of daily returns scaled to an annual basis (multiplying by $\sqrt{252}$ trading days). A measure of how wildly an asset's price fluctuates.
*   **Sharpe Ratio:** A measure of risk-adjusted return calculated as $\frac{\text{Mean Return} - R_f}{\text{Annualised Volatility}}$. Higher values indicate more return per unit of total risk (values above $1.0$ are generally considered strong).
*   **Sortino Ratio:** Similar to the Sharpe ratio, but only penalises *downside volatility* (losses), ignoring upside volatility.
*   **Maximum Drawdown (Max DD):** The largest peak-to-trough percentage loss experienced by an investment portfolio before a new high is reached.
*   **Calmar Ratio:** The ratio of a portfolio's CAGR to its Maximum Drawdown ($\frac{\text{CAGR}}{|\text{Max DD}|}$), measuring return relative to severe downside pain.
*   **Breakeven Transaction Cost:** The exact round-trip trading cost (in bps) that completely eliminates a strategy's compounded profit, reducing total return to $0\%$.
*   **Ticket Fee Minimum & Reflexive Death Spiral:** Brokers often charge a minimum fixed ticket fee per order (e.g. IBKR's $\$0.35/\text{trade}$). On small accounts, a $\$0.35$ fee on a tiny position represents a massive percentage cost ($15\text{--}25+\text{ bps}$). When losses shrink the account further, position sizes get smaller, making the fixed fee an even larger percentage drag, triggering a reflexive downward spiral to total ruin.

### Portfolio Construction & Tail Risk

*   **Meucci Participation Ratio (Effective Bets):** A linear-algebra metric based on principal component eigenvalues ($PR = \frac{n^2}{\sum \lambda_i^2}$). It measures how many truly independent bets a portfolio holds. If 30 stocks all move together during macro shocks, their effective bets may only equal $\sim 5$ rather than $30$.
*   **Skewness & Excess Kurtosis (Fat Tails):** *Skewness* measures asymmetry in return distribution (negative skew means rare, large crashes). *Kurtosis* measures the thickness of distribution tails relative to a bell curve (high kurtosis means extreme outlier events happen much more frequently than normal Gaussian probability predicts).
*   **Conditional Value at Risk (CVaR / Expected Shortfall):** The average expected loss occurring in the worst $1\%$ or $5\%$ tail of trading days. Unlike standard Value at Risk (which only gives a cutoff threshold), CVaR answers: *"When severe disaster strikes, how much do we actually lose on average?"*
*   **Cross-Sectional Tercile Sort (Overnight Momentum):** Dividing all stocks in the universe into three equal tiers (top $33\%$, middle $33\%$, bottom $33\%$) based on their past overnight performance, and systematically investing in the top tier while avoiding or shorting the bottom tier.

---

## Appendix: the original MU claim

Independently reproduced from full MU daily OHLC history, dividend+split adjusted (1990-01-02 to 2026-08-21, 9,227 trading days):

| Leg | This analysis | Original claim |
|---|---:|---:|
| Overnight (buy close, sell next open), compounded | **+182,299,386%** | +138,330,342% |
| Intraday (buy open, sell close), compounded | **-99.94%** | -99.92% |

Close enough to confirm the claim is genuine (not fabricated), with the small gap likely explained by data vendor/adjustment differences or the exact snapshot date. `overnight × intraday ≈ buy-and-hold` checks out internally (both before and after the dividend-adjustment fix), confirming the decomposition wasn't gamed. MU pays no meaningful dividend over most of this window, so the dividend-adjustment fix barely moved its own numbers; the fix mattered for the *sector* conclusions in §3, not for MU itself.

## Disclaimer

Research only, not investment advice. Historical statistical patterns, however well-documented and factor-adjusted, are not guarantees of future returns, and this analysis does not model taxes, real execution mechanics (market-on-open/market-on-close order types), or the risk of adverse overnight gaps on any specific position.

