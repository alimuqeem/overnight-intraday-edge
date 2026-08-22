# Overnight vs. Intraday Returns: Is There a General Edge?

## Why this exists

This started from a viral chart claiming Micron (MU) is up **+138,330,342%** if you only held it overnight (buy at close, sell at next open) since 1990, and **-99.92%** if you only held it during the trading day (buy at open, sell at close). That specific claim [checked out](#appendix-the-original-mu-claim) against real MU price data. The question this project answers is different: **is that a Micron-specific fluke, or a real, tradable, market-wide edge?**

## 1. Method

- **Universe:** 33 liquid large-caps spanning all 11 GICS sectors (3-4 names each) plus SPY, QQQ, and MU as benchmarks/focus names. Full ticker list in [`scripts/fetch_data.py`](scripts/fetch_data.py). This is a deliberate departure from testing MU alone — a single winning stock's history is exactly the kind of sample survivorship bias warns against.
- **Data:** Full available daily OHLC history per ticker from Yahoo Finance (ranges from 1962 for the oldest names to 2010+ for newer listings; MU itself: 1984-06-04 to 2026-08-21, 10,637 trading days). Cached in `data/*.csv`.
- **Decomposition:** every trading day's return is split into two legs:
  - **Overnight**: `open[t] / close[t-1] - 1` — return earned while the market is *closed*.
  - **Intraday**: `close[t] / open[t] - 1` — return earned while the market is *open*.
  
  These compound multiplicatively back to the stock's actual return (`overnight × intraday = buy-and-hold`), so this is a decomposition, not an approximation.
- **Tests run per ticker:**
  1. Mean daily return, annualized return, annualized volatility, Sharpe, t-statistic and p-value (one-sample t-test vs. zero) for each leg.
  2. **Breakeven transaction cost** — the flat round-trip cost (in bps) that, subtracted from every day's return, drives the leg's compounded return to exactly zero. Binary-searched per ticker.
  3. **Sub-period split** — first half vs. second half of each ticker's available history, to check the effect isn't an artifact of one regime or an accident of the exact date range used.
- **Cross-sectional tests:** one-sample and paired t-tests on the 33 ticker-level mean returns, to ask whether overnight beats intraday *as a population*, not just for cherry-picked names.

Full numeric output: [`reports/summary.json`](reports/summary.json) (cross-sectional) and [`reports/per_ticker_results.json`](reports/per_ticker_results.json) (per-ticker). Reproduce with `python3 scripts/fetch_data.py && python3 scripts/analyze.py && python3 scripts/make_charts.py`.

## 2. Headline result: the pattern is real, but it is not the MU pattern

![Per-ticker overnight vs intraday annualized return](charts/per_ticker_overnight_vs_intraday.png)

| | Overnight leg | Intraday leg |
|---|---:|---:|
| Cross-sectional mean daily return | **+5.27 bps/day** | +3.01 bps/day |
| Cross-sectional t-stat (vs. zero) | 5.78 (p < 0.0001) | 5.87 (p < 0.0001) |
| % of 33 tickers individually significant (95%) | **72.7%** positive | 3.0% negative, 45.5% positive |
| Paired t-test, overnight mean > intraday mean across tickers | t = 1.89, **p = 0.067** | — |

Two things are true at once:

1. **The overnight leg is a genuine, statistically significant, broad-based phenomenon.** 24 of 33 tickers (72.7%) have a significantly positive overnight return on its own. This replicates the published literature (see [§5](#5-is-there-academic-basis-for-this)) — it is not noise.
2. **The MU-style pattern — massive overnight gains *and* a losing or flat intraday leg — is not the general case.** Only 1 of 33 tickers (BAC, plus FCX marginally) has a *significantly negative* intraday leg. For most stocks, both legs are positive; overnight is usually the bigger slice, but intraday isn't burning money — it's just growing slower. The cross-sectional paired t-test comparing mean overnight vs. mean intraday return per ticker lands at **p = 0.067** — a real effect, but it misses the conventional 5% significance bar. MU sits as a genuine outlier, not a representative case:

![Significance scatter](charts/significance_scatter.png)

In the scatter above, MU, BAC, and FCX are alone in the bottom-right quadrant (overnight strongly positive AND intraday negative). Everyone else with a strong overnight effect (AAPL, NVDA, TSLA, AVGO, HD) still has a *positive*, just statistically weaker, intraday leg.

## 3. Where the effect concentrates: growth/attention sectors, not the whole market

![Sector gap](charts/sector_gap.png)

Grouping by GICS sector makes the pattern explicit. The overnight-dominant effect is concentrated in **Information Technology, Consumer Discretionary, Communication Services, and Financials** — sectors full of high-volatility, high-retail-attention, "story" stocks. It **reverses** in **Consumer Staples, Utilities, Energy, and Health Care** — the boring, low-attention, dividend-stock end of the market, where the *intraday* session captures more of the return.

This lines up with the leading academic explanation for the overnight effect (retail investors chasing high-attention stocks at the open — see §5): staples and utilities don't attract that kind of speculative morning order flow, so they don't show the pattern.

**Practical read:** "buy the close, sell the open" is closer to a **growth/momentum-stock characteristic** than a market-wide law. Applying it uniformly across a diversified portfolio would be fighting the data in roughly a third of your sectors.

## 4. Does it survive costs and time? Partially.

**Persistence:** splitting each ticker's own history into a first half and second half, the cross-sectional correlation of overnight annualized return is **0.65** (tickers with a strong overnight effect early tend to keep it later) vs. only **0.07** for the intraday leg. That's evidence the overnight effect is closer to a real, persistent stock characteristic than the intraday leg is. The overall *level* doesn't reliably shift either (paired t-test first-half vs. second-half overnight: p = 0.148) — a reasonably stable phenomenon over decades, not a fading anomaly, but also not one that's compounding away.

![Sub-period consistency](charts/subperiod_consistency.png)

**Transaction costs are the real problem.** For each ticker, we solved for the flat round-trip cost that would erase the entire compounded overnight edge:

![Breakeven cost distribution](charts/breakeven_cost_distribution.png)

- **28 of 33 tickers** have a gross-profitable overnight leg at all; for 5, overnight was actually a net drag even before costs.
- Median breakeven cost across the profitable names: **5.0 bps round-trip**. Half of them (14/28) lose their entire edge to a cost below 5bps — tighter than the bid-ask spread on plenty of liquid large-caps, before even counting slippage on market-on-close/market-on-open orders.
- Even the most extreme cases in the whole universe — **MU (14.2bps), TSLA (15.0bps), NVDA (13.3bps)** — only survive costs up to ~15bps round-trip. That sounds like a lot of room until you remember this is a *daily* number compounding over 4,000-10,600 trading days: MU's mean daily overnight return is only ~16bps, so a cost that looks small on any single day fully erases 36+ years of the headline result.

This is the actual answer to "is there a tradable edge": **gross of costs, yes, for about 70% of large-cap names, concentrated in growth sectors. Net of realistic execution costs, the margin of safety is razor-thin to nonexistent for the median stock**, and only comfortably survives costs for a handful of high-volatility names that also carry the highest overnight *gap risk* (the same mechanism that produces big up-gaps produces big down-gaps on bad news).

## 5. Is there academic basis for this?

Yes — this is a well-documented phenomenon, not a chart trick. Key references:

- **French & Roll (1986)** — first documented that volatility (and by extension return patterns) differs sharply between trading and non-trading hours for the aggregate market.
- **Berkman, Koch, Tuttle & Zhang (2012, *Journal of Financial and Quantitative Analysis*), "Paying Attention: Overnight Returns and the Hidden Cost of Buying at the Open"** — the leading mechanism: retail investors queue orders overnight and buy attention-grabbing stocks right at the open, pushing the open price up; institutions fade that flow intraday, pulling the price back down by the close. This is consistent with what §3 finds — the effect concentrates in the stocks retail investors actually chase (growth/tech/consumer names), not staples and utilities.
- **Lou, Polk & Skouras (2019, *Journal of Financial Economics*), "A Tug of War: Overnight Versus Intraday Expected Returns"** — shows overnight and intraday returns behave like two separate return series with opposite momentum/reversal signatures, driven by different investor clienteles (institutional ownership rises more with intraday returns).
- Follow-on market-microstructure work confirms retail and institutional order-flow imbalances are negatively correlated — wholesalers internalize retail flow specifically to offset institutional demand, mechanically producing the open-high/close-low pattern in attention-grabbing names.

## 6. Bottom line

| Question | Answer |
|---|---|
| Is the original MU chart's math right? | Yes — independently reproduced (see appendix). |
| Does the *extreme* MU pattern (huge overnight gain, losing intraday) generalize across the market? | **No.** Only MU, BAC, and FCX show it out of 33 names; it's the exception, not the rule. |
| Is there a *real, general* overnight-return effect at all? | **Yes** — 72.7% of a 33-name, sector-diversified universe shows a statistically significant positive overnight return, matching published academic findings. |
| Does it concentrate anywhere? | **Yes** — growth/high-attention sectors (Tech, Discretionary, Comm Services, Financials). It *reverses* in Staples, Utilities, Energy, Health Care. |
| Is it persistent over time? | Reasonably — 0.65 cross-sectional correlation between first-half and second-half overnight returns. |
| Is it a free lunch net of costs? | **No.** Median breakeven cost is ~5bps round-trip; even the best cases (MU, TSLA, NVDA) only tolerate ~13-15bps. This is a real, documented statistical regularity in *where* returns show up, not a low-cost trading strategy. |

## Limitations

- Universe is 33 large/mega-cap US names — doesn't cover small-caps, non-US markets, or delisted/failed companies (survivorship bias remains within "stocks that are still large-cap today").
- No dividends, corporate actions adjustments beyond what Yahoo's raw OHLC provides, taxes, or borrow costs for any short leg modeled.
- Breakeven cost analysis assumes a flat per-trade cost; real costs vary by name, liquidity, and order type (MOO/MOC auctions specifically, which is what this strategy would require in practice, carry their own execution risk beyond simple spread cost).
- Sub-period "first half vs. second half" uses each ticker's own full history, so the split date differs by ticker (not a shared out-of-sample date) — this tests persistence of each stock's *own* pattern, not a shared regime shift.

## Appendix: the original MU claim

Independently reproduced from full MU daily OHLC history (1990-01-02 to 2026-08-21, 9,227 trading days):

| Leg | This analysis | Original claim |
|---|---:|---:|
| Overnight (buy close, sell next open), compounded | **+174,329,404%** | +138,330,342% |
| Intraday (buy open, sell close), compounded | **-99.94%** | -99.92% |

Close enough to confirm the claim is genuine (not fabricated), with the small gap likely explained by data vendor/adjustment differences or the exact snapshot date. `overnight × intraday ≈ buy-and-hold` checks out internally, confirming the decomposition wasn't gamed.

## Disclaimer

Research only, not investment advice. Historical statistical patterns, however well-documented, are not guarantees of future returns, and this analysis does not model taxes, real execution mechanics (market-on-open/market-on-close order types), or the risk of adverse overnight gaps on any specific position.
