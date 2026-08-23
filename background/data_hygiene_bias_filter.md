# Data Hygiene: Quantifying the Open==Close Bias

[`background/independent_review.md`](independent_review.md) finding #2 flagged an undisclosed data issue: some pre-2000 rows in this project's price data record `Open == Close`, a Yahoo Finance vendor artifact (missing recorded opens, or split-adjustment rounding collapsing adjusted open/close to the same value at high split ratios). Since the overnight leg is `open[t]/close[t-1] - 1` and the intraday leg is `close[t]/open[t] - 1`, any such day forces that day's intraday leg to exactly 0% and dumps the entire day's move into the overnight leg, the review hypothesized this **inflates exactly the effect this project measures**. This note quantifies it and re-runs the headline test both ways, per the review's own recommendation.

## Step 1: how much of the data is affected

[`scripts/data_cleanse_filter.py`](../scripts/data_cleanse_filter.py) scans all 33 universe tickers for rows where `abs(open - close) < 1e-6 * close`. Full output: [`reports/data_hygiene_report.json`](../reports/data_hygiene_report.json).

| Decade | Flat-day rate (all 33 tickers pooled) |
|---|---:|
| 1962-1979 | 16.13% |
| 1980-1989 | 15.90% |
| 1990-1999 | 7.32% |
| 2000-2026 | **0.75%** |
| **Full history** | **5.32%** |

Confirms the review's premise: contamination is heavily concentrated pre-2000 and the modern era is clean. Worst-affected individual tickers (full-history rate): BAC 14.10%, NEE 10.63%, WMT 9.47%, DUK 8.44%, HD 8.32%, HON 6.97%, JNJ 6.59%, CVX 6.51%, XOM 6.33%, AAPL 6.32%, roughly matching the review's earlier spot-check (AAPL ~6.1%).

## Step 2: two ways of removing it, both re-run against the headline number

[`scripts/analyze.py --mode B`](../scripts/analyze.py) and `--mode C` implement the two filtering approaches the review suggested, both applied in `load_ticker()` by dropping affected rows entirely (the same way genuinely missing rows are already skipped), not by touching the leg-computation logic. Full output: [`reports/summary_mode_b.json`](../reports/summary_mode_b.json), [`reports/summary_mode_c.json`](../reports/summary_mode_c.json); Mode A (raw/baseline) is unchanged and untouched by this work.

- **Mode B (modern-era only):** truncate every ticker's history to `>= 2000-01-01`, where contamination is 0.75%.
- **Mode C (filtered):** drop only the specific flat-day rows across full history, keeping everything else, including pre-2000 data.

| | Mode A (raw, baseline) | Mode B (modern-era only) | Mode C (flat days excluded) |
|---|---:|---:|---:|
| Cross-sectional overnight mean | **5.74 bps/day** | 5.15 bps/day | **5.99 bps/day** |
| Cross-sectional t-stat | 6.61 | 6.10 | 6.74 |
| Tickers significant after BH-FDR | 26/30 | 22/30 | 26/30 |
| Paired overnight > intraday | t=2.07, p=0.0475 | t=1.97, **p=0.0587** | t=2.07, p=0.0475 |
| Median breakeven cost | 4.25 bps | 3.81 bps | 4.35 bps |

## The honest finding: the review's hypothesized direction was wrong

**Mode C, the direct test of the review's own mechanism, moves the headline number the *opposite* way from what was hypothesized.** Excluding flat-open days doesn't shrink the overnight leg, it grows it slightly (5.74 -> 5.99 bps/day, +4.3%), and every individually-checked contaminated ticker (BAC, KO, NEE, WMT, AAPL) shows the same direction: removing its flat days *raises*, not lowers, its overnight mean. The mechanical argument in the review ("dumps the whole day's return into the overnight leg, inflating exactly the effect being measured") is correct as a description of what happens to any single flat day, but it doesn't follow that those days are, on average, *larger* than a typical genuine overnight leg for the same ticker; empirically, for this dataset, they're smaller. Whatever the flat-open artifact is doing to this project's numbers, it isn't the inflation the review predicted, and shouldn't be cited as a reason to discount the headline 5.74bps figure.

**Mode B, a blunter but unrelated cut (just use less pre-2000 data), does move one specific number that matters.** The cross-sectional mean drifts modestly (5.74 -> 5.15 bps, within the kind of range a different-but-reasonable ticker draw would produce, consistent with [`report.md` §2](../report.md#2-headline-result-the-pattern-is-real-but-it-is-not-the-mu-pattern)'s own framing), and BH-FDR significance count drops from 26/30 to 22/30, still comfortably above the ~1.5 expected by chance. The more consequential change: **the paired overnight-vs-intraday significance test flips from barely-significant (p=0.0475) to not significant at 5% (p=0.0587)** when restricted to 2000+ data. [`report.md` §2](../report.md#2-headline-result-the-pattern-is-real-but-it-is-not-the-mu-pattern) already flagged this exact number as fragile ("read that 'barely' literally... a different but equally reasonable 30-ticker draw could easily land on either side of 0.05"); this confirms it empirically rather than just caveating it. This is not the same mechanism the review was worried about (Mode B removes clean and contaminated pre-2000 rows alike, it isn't isolating the bias), so it shouldn't be read as "the open==close artifact was responsible" -- it's a separate, real finding that the paired test's significance is sensitive to how much pre-2000 history is included at all.

## Bottom line

The specific mechanism the independent review flagged (`open==close` days inflating the overnight leg) is real as a data artifact and heavily concentrated pre-2000, but **removing it moves the headline overnight number up, not down**, and leaves the core FDR-significance conclusion (26/30 tickers) unchanged. The one number that is genuinely fragile is the paired overnight-vs-intraday significance test, which was already flagged as "barely significant" in the main report and now measurably flips to non-significant under a modern-era-only cut, for reasons unrelated to the flat-day artifact specifically. Everything else in [`report.md`](../report.md) that was stated as a >99% or >99.9% confidence result is unaffected by either filtering mode.
