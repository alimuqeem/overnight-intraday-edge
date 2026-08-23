# Out-of-Sample Validation of the Overnight-Momentum Overlay

[`background/independent_review.md`](independent_review.md) finding #4: the trailing overnight-momentum overlay in [`overnight_momentum_analysis.md`](overnight_momentum_analysis.md) reports a headline Sharpe of 1.16 for the 21-day lookback, but that number, and the choice of 21 days over the other two tested lookbacks (5, 63), was discovered in-sample, across the same data used to test it. "There is no out-of-sample or walk-forward test anywhere in this project... 'Sharpe 1.16' shouldn't be treated as an achievable number until it's tested on a genuine holdout period." This runs three such tests.

## Method

[`scripts/walk_forward_validator.py`](../scripts/walk_forward_validator.py) reuses `overnight_momentum_analysis.py`'s signal construction and tercile-sort logic rather than duplicating it: each day's tercile sort only depends on that day's own cross-section (no dependency on other dates), so the three candidate lookbacks (5/21/63 days) are each computed once over the full history, and every test below is a date-range slice of those already-causal daily return series, net of the same flat 5bps round-trip cost used throughout this project. Full output: [`reports/walk_forward_results.json`](../reports/walk_forward_results.json).

## Test 1: standard holdout (1993-2010 in-sample, 2011-2026 out-of-sample)

Select the best-looking lookback using only 1993-2010 data (what a strategy developer would have known at the time), then report that pick's performance on the years that follow, never touched during selection.

| Lookback | In-sample Sharpe (1993-2010) | Out-of-sample Sharpe (2011-2026) |
|---|---:|---:|
| 5-day | 1.05 | 0.61 |
| **21-day** | **1.20** | **0.53** |
| 63-day | 1.13 | 0.67 |

The in-sample winner is 21 days, matching this project's headline choice: the headline pick was not itself cherry-picked with the benefit of hindsight over the full sample. But its genuinely out-of-sample Sharpe is **0.53, less than half the full-sample 1.16 figure**, and modestly the *worst* of the three candidates out-of-sample despite winning in-sample (5-day and 63-day both hold up somewhat better, 0.61 and 0.67). This is exactly the decay pattern the review anticipated: real, but the strategy still clears SPY's own 0.65 Sharpe roughly at the boundary, and comfortably clears the naive equal-weight-all book's Sharpe (-0.03 to -0.10, per `overnight_momentum_analysis.md`), out of sample.

## Test 2: purged 5-fold walk-forward selection

Five contiguous chronological folds (boundaries set by the 21-day window's own trading-day sequence, split into five roughly equal chunks), with a 5-trading-day purge buffer trimmed from the training set around each held-out fold's boundary (translated from the 21-day reference window's calendar and applied uniformly to all three candidate windows) to prevent a trailing-signal window from straddling the train/test split. For each fold: select the best lookback using the other four folds, then measure its performance strictly on the held-out fold.

| Fold | Test period | Selected lookback | Train Sharpe | Test Sharpe |
|---|---|---:|---:|---:|
| 0 | 1972-1983 | 63-day | 0.95 | **2.17** |
| 1 | 1983-1994 | 63-day | 1.19 | 1.11 |
| 2 | 1994-2005 | 63-day | 1.13 | 1.33 |
| 3 | 2005-2015 | 21-day | 1.26 | 0.84 |
| 4 | 2015-2026 | **21-day** | 1.36 | **0.43** |

**Every fold's selected lookback shows a positive out-of-sample Sharpe**, including the two most recent folds that matter most for whether this is deployable today. But there's a clear temporal pattern: the earlier folds (1970s-2000s) selected the 63-day lookback and held up strongly out-of-sample (Sharpe 1.11-2.17); the two most recent folds (2005-2026) selected 21 days and show visibly weaker, though still positive, out-of-sample Sharpes (0.84, then 0.43 in the most recent decade). Only 2 of 5 folds (40%) select the project's headline 21-day window at all. This is consistent, not contradictory, with [`recency_regime_analysis.md`](recency_regime_analysis.md)'s separate finding that the broader overnight effect hasn't significantly decayed in aggregate but has rotated across names and eras: the momentum overlay specifically looks to be in a weaker regime in its most recent decade than in its earlier history, while still clearing zero.

## Test 3: Deflated Sharpe Ratio

The Bailey & Lopez de Prado (2014) DSR checks the observed Sharpe against the Sharpe *expected by chance* under the null of "best-of-N independent trials with zero true skill," using each trial's actual skew and kurtosis rather than assuming normality (a plain Sharpe ratio implicitly does). N=3 here (the three lookbacks tested).

| Lookback | Annualized Sharpe (full history) | Skew | Kurtosis | DSR |
|---|---:|---:|---:|---:|
| 5-day | 1.04 | -0.37 | 18.6 | >0.9999 |
| **21-day** | **1.16** | -0.40 | 16.3 | **>0.9999** |
| 63-day | 1.17 | -0.26 | 19.0 | >0.9999 |

The expected maximum Sharpe under the null (best-of-3, zero skill) is **0.0039 daily**, roughly 0.06 annualized, trivially small next to the observed 1.04-1.17. All three DSRs round to 1.0000: essentially zero probability the full-sample Sharpe is explained by chance across only 3 trials plus the fat-tailed (kurtosis 16-19, far above the Gaussian 3) return distribution.

**This does not contradict Tests 1-2, and shouldn't be read as "fully validated."** DSR answers a narrower question than the holdout tests: is the *full-sample* Sharpe explicable by the specific multiple-testing risk of trying 3 lookbacks and picking the best, plus non-normality? No. It does not test, and cannot rule out, genuine performance decay over time, which Tests 1 and 2 both find directly (headline Sharpe roughly halves out-of-sample, and the two most recent walk-forward folds are the weakest in the whole 54-year history). N=3 is also a small multiple-testing burden by construction (unlike the 30-ticker cross-section elsewhere in this project, which needed Benjamini-Hochberg FDR for exactly this reason); a DSR this close to 1.0 mostly reflects that the a-priori search space here was narrow, not that the strategy is guaranteed to repeat its full-sample Sharpe going forward.

## Bottom line

The overnight-momentum overlay is not an artifact of picking the best of three lookbacks after the fact: the 21-day choice would have been the in-sample winner using only 1993-2010 information, and the DSR rules out chance-driven selection bias across those three trials specifically. But the review's caution was correct: **"Sharpe 1.16" is not an achievable, forward-looking number.** A genuine out-of-sample test on 2011-2026 data shows roughly half that Sharpe (0.53) for the headline lookback, and the most recent purged fold (2015-2026) is the weakest result in the strategy's entire 54-year history (Sharpe 0.43). The signal is real and positive in every out-of-sample cut tested, comfortably ahead of the naive equal-weight book, but anyone sizing a position off this overlay should underwrite it around a Sharpe of roughly 0.4-0.7 in the current regime, not the full-sample 1.16 headline figure.
