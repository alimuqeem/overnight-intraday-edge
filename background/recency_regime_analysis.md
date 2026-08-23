# Has the Overnight Edge Decayed Recently?

Motivated by Liberty Street Economics (Federal Reserve Bank of New York), ["The Disappearing Overnight Drift"](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/) (2026), which finds that using S&P 500 E-mini futures, a specific narrow window (2:00-3:00am ET, when European markets open) averaged +3.7%/yr from 1998-2020 but has averaged close to zero since 2021. Their explanation isn't a change in volatility or liquidity broadly, it's a compression in end-of-day order-imbalance dispersion (the standard deviation fell from 6.5% to 2.9%), consistent with algorithmic liquidity providers slicing flow more finely and reducing the inventory pressure that used to create that specific overnight opportunity.

This project only has daily OHLC data, not intraday ticks, so it cannot isolate that specific 2-3am window. This tests the broader, available question instead: has the *full* overnight leg (close to next open), across this project's 30-ticker cross-section, decayed since the same 2021 regime break, or more generally in the last 2 years? Full method: [`../scripts/recency_analysis.py`](../scripts/recency_analysis.py); raw output: [`../reports/recency_results.json`](../reports/recency_results.json).

## Headline answer: no, not at the aggregate level

![Rolling overnight return](../charts/recency_rolling_return.png)

> **Chart fixed:** [`background/independent_review.md`](independent_review.md) finding #3 caught a bug in the black line above -- it was built by averaging each ticker's own rolling series at the same *positional* index against SPY's date axis, but each ticker's series starts at a different calendar date, so the same index lined up different real dates per ticker. Fixed in `scripts/recency_analysis.py`'s `rolling_value_at_dates()`, which now looks up each ticker's trailing value by actual calendar date. The pre/post-2021 statistics below were never affected (they were always computed via explicit date masks, not this chart), but the visual has changed, most noticeably pre-2000 (previously an inflated, steeply-declining line from a spurious ~96% start; now a smoother rise from ~10%) and right at the 2021 break (previously a dip to ~5.5%; now a local *peak* near 40%). The corrected chart supports "no decay at 2021" at least as clearly as the original claim, just for a different reason (a peak rather than a dip at the break date).

The trailing 2-year rolling annualized overnight return for the 30-ticker cross-sectional mean (black line above) has stayed in roughly the same 0-40% range since 2000, including through and after the 2021-01-01 break date the NY Fed paper identifies. There is no visible structural break, and the pre-2021 vs. post-2021 cross-sectional mean change (17.97% to 13.24% annualized) is **not statistically significant** (paired t = 1.38, p = 0.179).

**8 of 30 tickers remain individually significant post-2021 after Benjamini-Hochberg FDR correction**, against an expected ~1.5 false positives by chance alone, down from 26/30 over the full sample, but the post-2021 window is only ~5.6 years (~1,415 trading days per ticker) against decades for the full-sample test, so materially lower statistical power is the more parsimonious explanation for most of that drop, not necessarily a shrinking true effect. The magnitude test above (which doesn't depend on per-ticker significance) is the more informative number, and it shows no significant decay.

**The most recent 2 years alone (last_2yr) actually show a slightly higher cross-sectional mean (19.3% annualized) than either the pre- or post-2021 windows**, though only 7/30 tickers are individually significant at that sample size (~504 trading days each), again a power story more than a magnitude story.

## But the aggregate stability hides real heterogeneity

| Biggest decays (pre-2021 to post-2021) | Biggest increases |
|---|---|
| TSLA: 74.3% → 23.6% | LLY: 3.2% → 31.0% |
| AAPL: 36.7% → -7.3% | AVGO: 32.4% → 59.1% |
| HD: 31.6% → -0.3% | CAT: 8.7% → 24.9% |
| GOOGL: 32.9% → 8.3% | CVX: 6.1% → 22.2% |
| NFLX: 31.0% → 7.6% | XOM: 1.5% → 14.6% |
| META: 31.7% → 10.2% | NEE: 2.2% → 13.5% |

This isn't random noise around a stable mean, it looks like **sector rotation, not decay**. The names that faded hardest (TSLA, AAPL, HD, GOOGL, NFLX, META) are exactly the growth/attention names that drove the pre-2021 effect in [`../report.md` §3](../report.md#3-where-the-effect-concentrates-growth-attention-sectors-not-the-whole-market). The names that strengthened (LLY, AVGO, CAT, CVX, XOM, NEE) span the AI/semiconductor supercycle (AVGO) and a rotation into value/industrials/energy/healthcare names that had shown little or no overnight effect before 2021. MU and NVDA, the other AI-cycle chip name, also *strengthened* post-2021 (MU: 47.8%→58.0%, NVDA: 46.9%→52.5%), consistent with the AVGO pattern.

## What this means practically

- **The broad phenomenon this project tests is not disappearing.** Unlike the NY Fed's narrow futures-based finding, the full overnight leg across a diversified large-cap universe shows no significant aggregate decay through 2026.
- **Which specific names carry the edge changes over time.** A stock-picking approach based on this project's historical rankings (e.g. "buy AAPL or HD at the close because they had the strongest historical overnight effect") would have been increasingly wrong for exactly those two names since 2021, while a name like AVGO, LLY, or CAT would have been increasingly right. This project's per-ticker rankings elsewhere in the repo are full-sample averages and don't reflect this rotation; treat any single-ticker recommendation as regime-dependent, not fixed.
- **This doesn't resolve which underlying mechanism (§7 of the main report) is driving the effect**, but the sector-rotation pattern is more consistent with the retail-attention story (Berkman et al.) tracking wherever retail attention currently concentrates (AI/chips since 2023, away from some of the 2010s mega-cap-tech names) than with a single structural liquidity mechanism fading market-wide the way the NY Fed paper describes for its specific futures window.

## Caveats

- **Single break date, not independently validated for this universe.** 2021-01-01 is imported directly from the NY Fed paper's own finding for a different instrument (E-mini futures) and a different specific window (2-3am ET); this project did not independently search for its own optimal break date in this data, which would risk data-mining a break to fit a story.
- **Smaller post-break samples reduce statistical power**, as noted above; the drop in individually-significant tickers should not be read as proof of decay on its own, only the magnitude test (not significant) and the rolling chart (now date-aligned; still no visible trend break) support that conclusion.
- **This is not a test of the NY Fed's specific 2-3am mechanism.** This project's overnight leg spans the entire close-to-open window (roughly 17.5 hours for a standard trading day), not the specific hour they isolate. A finding of "no decay" here and "decay" in their narrow window are not in conflict; they could both be true simultaneously if the 2-3am effect shrank while other parts of the overnight window (e.g. the US pre-market hours, or reaction to after-hours earnings) compensated.
