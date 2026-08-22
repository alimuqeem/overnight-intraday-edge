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

| | Overnight leg | Intraday leg |
|---|---:|---:|
| Cross-sectional mean daily return (30 tickers, excl. SPY/QQQ/MU) | **+5.74 bps/day** | +3.37 bps/day |
| Cross-sectional t-stat (vs. zero) | 6.61 (p < 0.0001) | 6.58 (p < 0.0001) |
| % individually significant, raw (95%) | 86.7% positive | 3.3% negative |
| Individually significant after Benjamini-Hochberg FDR control | **26 / 30** (vs. ~1.5 expected by chance) | 16 / 30 |
| Paired t-test, overnight mean > intraday mean across tickers | t = 2.07, **p = 0.047** | n/a |

Two things are true at once:

1. **The overnight leg is a genuine, statistically significant, broad-based phenomenon, and it survives multiple-comparisons correction.** 26 of 30 tickers remain significant after Benjamini-Hochberg FDR control, against an expected ~1.5 false positives by chance. This replicates the published literature (see [§5](#5-is-there-academic-basis-for-this)); it is not noise, and not a multiple-testing artifact.
2. **The MU-style pattern (massive overnight gains *and* a losing intraday leg) is still not the general case.** Only BAC (and FCX marginally) join MU with a significantly *negative* intraday leg. For most stocks, both legs are positive; overnight is usually the bigger slice, but intraday isn't burning money, it's just growing slower.

![Significance scatter](charts/significance_scatter.png)

In the scatter above, MU, BAC, and FCX are alone in the bottom-right quadrant (overnight strongly positive AND intraday negative). Everyone else with a strong overnight effect (AAPL, NVDA, TSLA, AVGO, HD) still has a *positive*, just statistically weaker, intraday leg.

One change from the dividend-adjustment fix: the cross-sectional paired test (overnight mean > intraday mean) now lands at **p = 0.047**, barely significant, versus p = 0.067 (not significant) before the fix and before excluding SPY/QQQ/MU from the pool. Read that "barely" literally: this is not a strong result, and a different but equally reasonable 30-ticker draw could easily land on either side of 0.05.

## 3. Where the effect concentrates: growth/attention sectors, not the whole market

![Sector gap](charts/sector_gap.png)

Grouping by GICS sector still makes the pattern explicit even after the dividend fix. The overnight-dominant effect concentrates in **Information Technology, Consumer Discretionary, Communication Services, and Financials**, sectors full of high-volatility, high-retail-attention, "story" stocks. It **reverses** in **Consumer Staples, Energy, Utilities, and (mildly) Health Care**, the boring, low-attention, dividend-paying end of the market, where the *intraday* session now captures more of the return even with the dividend-leakage artifact removed.

This lines up with the leading academic explanation for the overnight effect (retail investors chasing high-attention stocks at the open, see §5): staples and utilities don't attract that kind of speculative morning order flow, so they don't show the pattern.

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

## 6. Is there academic basis for this?

Yes, this is a well-documented phenomenon, not a chart trick. Key references (full literature review with links: [`background/literature_review.md`](background/literature_review.md)):

- **French & Roll (1986)**: first documented that volatility (and by extension return patterns) differs sharply between trading and non-trading hours for the aggregate market.
- **Berkman, Koch, Tuttle & Zhang (2012, *Journal of Financial and Quantitative Analysis*), "Paying Attention: Overnight Returns and the Hidden Cost of Buying at the Open"**: the leading mechanism. Retail investors queue orders overnight and buy attention-grabbing stocks right at the open, pushing the open price up; institutions fade that flow intraday, pulling the price back down by the close. This is consistent with what §3 finds: the effect concentrates in the stocks retail investors actually chase (growth/tech/consumer names), not staples and utilities.
- **Lou, Polk & Skouras (2019, *Journal of Financial Economics*), "A Tug of War: Overnight Versus Intraday Expected Returns"**: shows overnight and intraday returns behave like two separate return series with opposite momentum/reversal signatures, driven by different investor clienteles. §4's factor regression is a direct empirical check on this paper's own momentum framing, and finds the momentum loading itself isn't what's driving it here.
- Follow-on market-microstructure work confirms retail and institutional order-flow imbalances are negatively correlated: wholesalers internalize retail flow specifically to offset institutional demand, mechanically producing the open-high/close-low pattern in attention-grabbing names.

## 7. Bottom line

| Question | Answer |
|---|---|
| Is the original MU chart's math right? | Yes, independently reproduced (see appendix). |
| Does the *extreme* MU pattern (huge overnight gain, losing intraday) generalize across the market? | **No.** Only MU, BAC, and FCX show it out of 33 names; it's the exception, not the rule. |
| Is there a *real, general* overnight-return effect at all? | **Yes.** 26 of 30 sector-diversified tickers remain significant after FDR correction (vs. ~1.5 expected by chance), matching published academic findings. |
| Does it concentrate anywhere? | **Yes**, in growth/high-attention sectors (Tech, Discretionary, Comm Services, Financials). It *reverses* in Staples, Energy, Utilities. |
| Is it repackaged momentum? | **No.** Momentum-factor loading on the overnight leg is statistically zero (t=0.13); 16/30 tickers retain significant alpha after controlling for market/size/value/momentum. |
| Is it persistent over time? | Reasonably: 0.65 cross-sectional correlation between first-half and second-half overnight returns. |
| Is it a free lunch net of costs? | **No.** Median breakeven cost is ~4.2bps round-trip; even the best cases (TSLA, MU, NVDA) only tolerate ~13-15bps. This is a real, documented, factor-distinct statistical regularity in *where* returns show up, not a low-cost trading strategy. |

## Limitations

- Universe is 33 large/mega-cap US names, and doesn't cover small-caps, non-US markets, or delisted/failed companies. The 30-ticker cross-section is still conditioned on "large-cap today," so survivorship bias is reduced (dividend fix, factor-neutrality) but not eliminated: a stock's multi-decade winner status can still concentrate in the overnight leg if the overnight effect is itself momentum-like at the individual-stock level, even though the *aggregate* momentum-factor loading is flat.
- Fama-French factor data currently runs through 2026-06-30, so §4's factor regressions use a slightly shorter window than the full price history (which runs to 2026-08-21); this is a ~7-week truncation against decades of history and immaterial to the conclusions.
- Breakeven cost analysis assumes a flat per-trade cost; real costs vary by name, liquidity, and order type (MOO/MOC auctions specifically, which is what this strategy would require in practice, carry their own execution risk beyond simple spread cost), and an actual overnight holder collects any dividend paid, which isn't separately modeled as a benefit here even though the price-adjustment fix removes it as a distortion.
- Sub-period "first half vs. second half" uses each ticker's own full history, so the split date differs by ticker (not a shared out-of-sample date): this tests persistence of each stock's *own* pattern, not a shared regime shift.
- Sector labels are assigned once, present-day, and applied to each ticker's entire history: a company's sector character can drift over decades (e.g. AMZN's business mix looked very different in 1998 than today).
- Only 2-3 tickers per sector for several sectors (Energy, Materials, Real Estate, Utilities): thin enough that a different random draw of the same sectors could shift the sector-level conclusions in §3-4, even though the overall growth-vs-defensive pattern is unlikely to fully reverse.

## Appendix: the original MU claim

Independently reproduced from full MU daily OHLC history, dividend+split adjusted (1990-01-02 to 2026-08-21, 9,227 trading days):

| Leg | This analysis | Original claim |
|---|---:|---:|
| Overnight (buy close, sell next open), compounded | **+182,299,386%** | +138,330,342% |
| Intraday (buy open, sell close), compounded | **-99.94%** | -99.92% |

Close enough to confirm the claim is genuine (not fabricated), with the small gap likely explained by data vendor/adjustment differences or the exact snapshot date. `overnight × intraday ≈ buy-and-hold` checks out internally (both before and after the dividend-adjustment fix), confirming the decomposition wasn't gamed. MU pays no meaningful dividend over most of this window, so the dividend-adjustment fix barely moved its own numbers; the fix mattered for the *sector* conclusions in §3, not for MU itself.

## Disclaimer

Research only, not investment advice. Historical statistical patterns, however well-documented and factor-adjusted, are not guarantees of future returns, and this analysis does not model taxes, real execution mechanics (market-on-open/market-on-close order types), or the risk of adverse overnight gaps on any specific position.
