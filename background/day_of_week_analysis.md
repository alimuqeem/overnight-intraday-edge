# Does It Matter Which Weekday You Buy the Close On?

This project's main analysis pools every trading day together. This note splits the overnight leg by the weekday of the close you'd be buying, to answer a specific practical question: is buying Monday's close different from any other weekday, and is the Friday-close-to-Monday-open "weekend gap" (a 3-calendar-day span, not a normal 1-day gap) different from the rest?

## Method

For each of the 30 cross-section tickers (excludes SPY, QQQ, MU, same convention as [`../report.md`](../report.md)), every overnight return is tagged by the weekday of the close date being bought, then grouped into five buckets (Monday through Friday) and tested with the same Newey-West HAC-robust methodology used throughout this project. Full detail: [`../scripts/day_of_week_analysis.py`](../scripts/day_of_week_analysis.py); raw output: [`../reports/day_of_week_results.json`](../reports/day_of_week_results.json).

## Result

![Day of week overnight return](../charts/day_of_week_overnight_return.png)

| Weekday bought | Mean annualized overnight return (30-ticker cross-section) |
|---|---:|
| **Monday** | **27.4%** |
| Tuesday | 18.5% |
| Wednesday | 16.1% |
| Thursday | 15.6% |
| **Friday** (the weekend gap) | **7.8%** |

Two clean, statistically significant results:

1. **Monday's close is the strongest day of the week to buy, by a wide margin.** Monday's mean overnight return is significantly higher than the pooled Tuesday-Thursday average (paired t = 5.26, p = 0.000012 across the 30-ticker cross-section).
2. **Friday's close, the weekend gap, is the weakest**, and significantly so (paired t = -4.00, p = 0.0004 vs. the pooled Monday-Thursday average). Buying Friday's close to capture Monday's open gives up roughly two-thirds of the average weekday edge.

This pattern held for the large majority of individual tickers too (see the per-ticker breakdown in the raw JSON), not just in the pooled average, though not every single name shows it with equal strength.

## Caveats

- **This finding is new to this project, not drawn from the literature review.** None of the seven papers in [`literature_review.md`](literature_review.md) test a day-of-week split of the overnight leg specifically, so there's no independent academic confirmation to point to here. Treat it as an empirical pattern in this dataset, not an established result.
- **This is a new dimension of multiple comparisons** (5 weekday buckets x 30 tickers) beyond what the rest of this project's Benjamini-Hochberg correction covers. The pooled cross-sectional tests above are strong (p < 0.001), but the per-ticker weekday breakdowns in the raw JSON haven't individually been FDR-corrected and should be read as descriptive, not each independently conclusive.
- **Smaller subsample per bucket.** Splitting the overnight series five ways cuts the per-ticker sample roughly to a fifth, so individual-ticker significance is noisier here than in the pooled full-sample tests elsewhere in this project.
- **This is not the classic "weekend effect" from the finance literature** (French, 1980), which is about the *Monday trading session's* return, not the Friday-close-to-Monday-open gap specifically. The result here (Friday-close is weak, Monday-close is strong) is a related but distinct claim about the overnight leg only.

## Practical read

If executing this as a real strategy: Monday's close historically has been the single best entry point of the week for the overnight leg, and Friday's close (holding through the weekend) has been the weakest. That's a genuinely useful, if unverified-elsewhere, empirical result for the exact question "should I buy at the last minute of the market on Monday."
