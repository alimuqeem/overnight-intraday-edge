# Is the Overnight Edge Just a Few Earnings-Like Pops?

A natural objection to any overnight-return finding: maybe the whole effect is really just a handful of huge single-night gaps (the kind an earnings beat produces), and the rest of the trading days are noise. This note tests that directly.

## Why this isn't a precise earnings-date match

The honest way to answer this would be to exclude actual earnings-announcement dates per ticker and recompute. That data isn't available for free at the depth this project needs: Yahoo's own earnings-date endpoint only covers roughly the last 4 quarters and, in this project's environment, requires an authentication crumb the price-data fetch approach doesn't have (see [`../scripts/fetch_data.py`](../scripts/fetch_data.py) for why a plain-GET approach was needed for price data in the first place). Getting 20-40 years of earnings dates per ticker across 30 names isn't feasible without a paid data vendor.

Instead, this uses an explicit statistical proxy: for each ticker, days where the overnight return exceeds 3 standard deviations of that ticker's own overnight return distribution are flagged as "extreme gap days." This catches earnings surprises, but also M&A news, guidance updates, and macro shocks, so read every result below as "excluding tail-event nights," not "excluding earnings nights." Full method: [`../scripts/extreme_gap_analysis.py`](../scripts/extreme_gap_analysis.py); raw output: [`../reports/extreme_gap_results.json`](../reports/extreme_gap_results.json).

## Result

![Extreme gap decomposition](../charts/extreme_gap_decomposition.png)

Across the 30-ticker cross-section, only **1.7% of trading days** are flagged as extreme by this threshold. Removing them:

- Mean annualized overnight return falls from **16.4% to 14.5%**, a real but modest give-back.
- **27 of 30 tickers keep a positive, statistically significant overnight return** (HAC-robust p < 0.05) even with every extreme-gap day removed.
- The three that don't (PG, UPS, LIN) already had a flat or negative overnight leg with extreme days *included*, so removing outliers doesn't change their conclusion either way.

**The overnight edge is not primarily an artifact of a few explosive nights.** For most of the universe, it's a broad, steady effect present across ordinary trading days, consistent with this project's earlier finding ([`../report.md` §4](../report.md#4-is-this-just-repackaged-momentum)) that it isn't reducible to a single dominant mechanism.

That said, dependence on extreme days varies a lot by name. TSLA, HD, BAC, GOOGL, NVDA, and AVGO all give back a meaningfully larger share of their annualized return when extreme days are excluded than the cross-sectional average, so the very largest headline numbers in this project's per-ticker rankings lean more on tail events than the typical name does. META in particular loses more than half its overnight t-statistic (down to t=2.66) once extreme days are removed, worth knowing if picking a specific name to trade rather than relying on the pooled effect.

## Caveats

- **Proxy, not ground truth.** A 3-standard-deviation threshold is a reasonable, transparent rule, but it's a choice, not a fact; a different threshold would flag a different set of days. It was not tuned or cherry-picked to produce this result.
- **A per-ticker "share of total return contributed by extreme days" metric is included in the raw JSON but is numerically unstable for tickers whose total overnight return is already close to zero** (the ratio can exceed 100% or go sharply negative for names like UPS, XOM, PLD, where a small denominator amplifies noise). The annualized-return comparison above (all days vs. ordinary days only) is the reliable number; treat the log-return-share figures in the JSON as illustrative only.
- Excluding the top ~1.7% of days by definition also removes some of the ticker's best days along with its worst, since the z-score threshold is symmetric (both directions). This is a test of "does the edge depend on tail events," not a claim that avoiding big up-gaps specifically would leave the return unchanged.
