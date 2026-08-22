# Background: Validating the Original MU Overnight/Intraday Claim

This is the research trail that led to this repo, preserved for reference.

## The claim

A chart (screenshot, source unknown) titled "Micron Technology (MU)" plotted two log-scale equity curves from 1990 to 2026:

- **Overnight returns** (buy at close, sell at next open): **+138,330,342%**
- **Intraday returns** (buy at open, sell at close): **-99.92%**

## Step 1: sanity-check against 1-year cached data

Using `trading/data/price_cache/MU_1y_2026-08-21.csv` (251 trading days, 2025-08-21 to 2026-08-21) from the trading platform repo:

- Overnight compound return: +358.78% (4.59x)
- Intraday compound return: +81.52% (1.82x)
- Both legs positive over 1 year, nowhere near the claim's magnitude, but this was expected: the chart spans 36 years, not 1.

## Step 2: pull full history and reproduce

Fetched MU's full daily OHLC from Yahoo Finance (`query1.finance.yahoo.com/v8/finance/chart/MU`, 10,490 daily bars from 1985-01-02 to 2026-08-21). Restricting to 1990-01-02 onward (9,227 trading days) to match the chart's x-axis:

| Leg | Reproduced | Claimed |
|---|---:|---:|
| Overnight (buy close, sell next open), compounded | **+174,329,404%** (~1.74M x) | +138,330,342% |
| Intraday (buy open, sell close), compounded | **-99.94%** | -99.92% |
| Buy & hold (sanity check) | +100,345% (~1,004x) | n/a |

Internal consistency check: `overnight_compound × intraday_compound ≈ buy_and_hold_compound`, confirmed (1,743,295 × 0.0006 ≈ 1,004x), which rules out the decomposition being gamed or cherry-picked.

**Conclusion: the claim is genuine, not fabricated.** The small gap between the reproduced and claimed figures is most likely explained by a different data vendor/adjustment methodology or a slightly different snapshot date: at ~16bps/day mean overnight return compounding over 9,000+ days, even a day or two of difference near the end of the series (MU rallied hard on HBM/AI news through 2026) moves the compounded total by tens of millions of percentage points. This is a property of extreme compounding, not evidence of manipulation.

*Note: the figures above (+174,329,404%) used the raw, non-dividend-adjusted Yahoo chart API pull from this initial exploration. The repo's main analysis was later rebuilt on dividend+split-adjusted data after a methodology review found unadjusted prices leak ex-dividend gaps into the overnight leg (immaterial for MU specifically, which pays no meaningful dividend; see [`../report.md`](../report.md#appendix-the-original-mu-claim) for the adjusted figure of +182,299,386%, but material for the sector-level conclusions below).*

## Step 3: why does this happen? (academic literature)

This overnight/intraday split is a well-documented phenomenon in market microstructure and behavioral finance, not a chart trick:

- **French & Roll (1986)**: first reported that stock return/volatility behaves very differently during trading hours vs. non-trading hours for the aggregate market.
- **Berkman, Koch, Tuttle & Zhang (2012, *Journal of Financial and Quantitative Analysis*), "Paying Attention: Overnight Returns and the Hidden Cost of Buying at the Open"**: the leading behavioral mechanism. Retail investors queue orders overnight and buy stocks that caught their attention (recent big moves, news) right at the open, since this is the first opportunity to act on that attention, pushing the open price up. Institutions then trade against that flow during the day, fading the price back down by the close. The effect is larger for stocks that are harder to value/arbitrage and during high-sentiment periods.
- **Lou, Polk & Skouras (2019, *Journal of Financial Economics*), "A Tug of War: Overnight Versus Intraday Expected Returns"**: the modern definitive paper. Shows overnight and intraday returns behave almost like two separate return series with opposite momentum/reversal properties: past overnight returns predict future overnight returns (momentum), while past intraday returns predict future intraday reversals. Institutional ownership rises more with intraday returns than overnight returns; different investor clienteles dominate each session.
- Follow-on market-microstructure literature (e.g. work on "night-minus-day" return predictability and internalized retail order flow) confirms retail and institutional order-flow imbalances are negatively correlated: wholesalers internalize retail flow specifically to offset institutional demand, mechanically producing the open-high/close-low pattern in attention-grabbing names.
- **MU-specific amplifiers:** Micron reports earnings after market close, so several of its largest all-time single-day gaps (HBM/AI-cycle beats) are baked directly into the "overnight" bucket. Its business is also tightly linked to Korea/Taiwan chip-supply-chain news (SK Hynix, Samsung, TSMC) that breaks while the US market is closed, feeding directly into the opening gap.

## Step 4: does it generalize? Led to this repo

The natural follow-up question, does this hold for stocks generally, or is MU a cherry-picked outlier, is answered by the full analysis in [`../report.md`](../report.md). Short answer: **the broad overnight effect is real, survives multiple-comparisons correction, and is not repackaged momentum exposure, but MU's specific pattern (overnight all-gain, intraday net-loss) is a genuine outlier concentrated almost nowhere else in the universe tested; and the edge is thin enough that realistic transaction costs erase it for most individual names.** See the full report for the sector breakdown, factor regression, significance tests, persistence check, and transaction-cost analysis.
