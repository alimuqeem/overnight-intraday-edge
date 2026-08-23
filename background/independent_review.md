# Independent Review: Is This Analysis Complete?

> **Update:** all five findings below have since been resolved. #1: see [`idle_cash_yield_modeling.md`](idle_cash_yield_modeling.md) -- T-bill data was reachable after all (same TLS-fingerprint fix already used for Yahoo endpoints), and crediting it moves the $50k and $100k+ portfolio-backtest verdicts materially. #2: see [`data_hygiene_bias_filter.md`](data_hygiene_bias_filter.md) -- quantified and re-run two ways; the hypothesized inflation direction turned out to be backwards (excluding the affected days raises the headline number slightly), though a related modern-era-only cut does flip the already-fragile paired significance test. #3: the recency rolling-chart date-misalignment bug is fixed in `scripts/recency_analysis.py` (`rolling_value_at_dates()`); see [`recency_regime_analysis.md`](recency_regime_analysis.md) -- the underlying statistics were never affected, but the chart itself changes materially, and still supports "no visible break at 2021." #4: see [`walk_forward_validation.md`](walk_forward_validation.md) -- a genuine 1993-2010/2011-2026 holdout confirms the review's caution directly: the momentum overlay's out-of-sample Sharpe is 0.53, less than half the in-sample 1.16 headline. #5: see [`portfolio_backtest.md`](portfolio_backtest.md)'s spread-sensitivity sweep (0.5/1.0/1.5bps) -- the sub-$30-40k ruin verdict is robust across the whole range (the $0.35/order minimum dominates regardless of spread), and $50k+ beats SPY's Sharpe at every spread tested, but beating SPY's *CAGR* specifically only holds at the low end (0.5-0.75bps); at 1.0-1.5bps, $50k-$250k+ still beat SPY on Sharpe but fall back below SPY's CAGR, and $50k's Sharpe advantage itself nearly vanishes at 1.5bps. The findings below are left as originally written, as the historical record of what was flagged and why.

An outside audit of this project as of the [correlation/tail-risk, VIX-regime, and overnight-momentum](../report.md) additions (commit `8e9ff2b`), done by re-reading every script and report and re-deriving key numbers from the committed data rather than trusting the write-up at face value. Verdict below, then the findings, then what's already handled well (so nothing here double-counts what the project already discloses).

## Verdict

**Sound as descriptive/scientific research; not yet decision-ready as trading research.**

The core finding — the overnight effect is real, broad-based (26/30 tickers survive FDR), factor-distinct from momentum, sector-concentrated, and marginal-to-unprofitable net of realistic costs below ~$100k — is well-supported and matches the published literature (French-Roll, Berkman et al. 2012, Lou-Polk-Skouras 2019). This project already does most of what a skeptical reviewer checks for: HAC-robust standard errors, BH-FDR correction, a Fama-French+momentum factor regression, no-lookahead signal construction, and an already-fixed dividend-adjustment bug from an earlier version.

Five things stand between this and being decision-ready for real capital, in priority order.

## 1. Idle cash yield is the single highest-leverage missing number

Already flagged as a limitation in [`report.md` §9](../report.md#9-would-this-have-actually-made-money-a-full-portfolio-backtest) and [`portfolio_backtest.md`](portfolio_backtest.md) — this isn't a new finding, but it deserves more weight than a footnote. The entire tradeability verdict rests on a razor-thin margin: the portfolio's own solved breakeven is **4.71bps** against a **5bps** assumed cost. An overnight-only book is uninvested roughly half of every 24-hour cycle; crediting even a conservative 3-4%/yr money-market yield on that idle half is a real, compounding tailwind that could plausibly move the marginal-account verdict, and possibly the sub-$50k verdict, from unprofitable to profitable. Given how close to the breakeven line the headline result already sits, this number — not another robustness cut — is what should be resolved next. (The write-up notes ^IRX and FRED were both unreachable in-sandbox; worth a retry outside that environment, or a hand-built historical 3-month T-bill series from a static source.)

## 2. `open == close` days mechanically inflate the overnight leg — undisclosed, and biased in the direction of the thesis

Not previously documented. `scripts/fetch_data.py`'s `load_ticker` does not filter or flag rows where the recorded open equals the recorded close. Since the decomposition is `overnight = open[t]/close[t-1] - 1` and `intraday = close[t]/open[t] - 1`, any such day dumps 100% of that day's return into the overnight leg and forces the intraday leg to exactly zero.

Checked directly against the committed `data/*.csv`:

| Ticker | `open==close`, full history | earliest 20% of history | latest 20% |
|---|---:|---:|---:|
| AAPL | 6.1% | **22.3%** | 0.2% |
| KO | 5.6% | 11.3% | 0.9% |
| MU | 4.0% | 13.0% | 0.3% |
| XOM / JNJ / CAT / PG | ~5.5% | ~9-12% | ~0.4% |

This is concentrated almost entirely in the pre-2000 portion of each ticker's history (a known Yahoo Finance artifact: missing recorded opens, or split-adjustment rounding collapsing adjusted open/close to the same value at high split ratios) and is clean by the modern era. It contaminates:

- every **full-history per-ticker** number in [§2 and §5](../report.md), in the direction of a larger overnight leg and smaller intraday leg — i.e. it inflates exactly the effect being measured;
- the **sector conclusions in §3**, since the old-economy names used to argue the effect "reverses" in defensives (KO, XOM, JNJ, PG, CAT) all have 1962-era starts with ~10% early-period contamination;
- the **MU appendix** (+182,299,386% overnight, compounded from 1990 with 13% of the earliest days affected).

Modern-era numbers (the momentum-tercile analysis, recency analysis, and most of the portfolio backtest) draw mostly on post-2000 data where contamination is 0.2-0.9%, so the *qualitative* conclusions likely survive. But the magnitudes don't have a documented margin of error for this, and it should: flag or drop `open==close` days in `load_ticker` and re-run §2/§3/§5 and the MU appendix to see how much of the reported edge is real vs. artifact.

## 3. Recency cross-sectional chart is index-aligned, not date-aligned (chart bug, not a conclusion bug)

In `scripts/recency_analysis.py` (~L177-189), the cross-sectional rolling-mean line averages `all_rolling[t][i]` across tickers at the same **positional index `i`**, plotted against SPY's date axis. Each ticker's rolling series starts at a different calendar date (AAPL's ~1982 vs. SPY's ~1995), so index `i` corresponds to a different real date per ticker — the plotted line in the recency chart is averaging mismatched dates. The underlying statistical result it's meant to illustrate (pre-2021 17.97% vs. post-2021 13.24%, paired t=1.38, p=0.18) is computed separately via explicit date masks and is unaffected, but the chart currently misrepresents what it claims to show and shouldn't be cited as visual confirmation until fixed.

## 4. The most-touted lever (momentum overlay, Sharpe 1.16) is correctly flagged as in-sample, but there's no OOS validation anywhere in the project to compare it against

[`report.md`'s limitations](../report.md#limitations) already disclose this signal is in-sample. Worth being explicit about the fuller picture: **there is no out-of-sample or walk-forward test anywhere in this project.** The sub-period split in §5 is each ticker's own first-half/second-half (a persistence check, not a shared OOS date). The day-of-week, VIX-regime, extreme-gap, and momentum sub-analyses are each in-sample, explored somewhat independently, with no project-wide multiple-testing correction across that whole search (only the core 30-ticker cross-section gets BH-FDR). None of this invalidates the momentum finding — it's directionally consistent with known persistence literature — but "Sharpe 1.16" shouldn't be treated as an achievable number until it's tested on a genuine holdout period.

## 5. Execution-cost assumptions drive the entire verdict but aren't stress-tested

`scripts/portfolio_backtest.py`'s realistic-cost model hardcodes a $150 assumed share price (~L161) and a 0.75bps round-trip spread (~L199) across the full mega-cap universe to produce the "profitable above $100k" conclusion, with no sensitivity band shown around that 0.75bps figure. Auction-specific slippage (execution vs. the official MOC/MOO print, which can differ from simple quoted spread) and capacity/crowding are discussed qualitatively in [`execution_mechanics.md`](execution_mechanics.md) but not modeled quantitatively. Since the whole tradeability question is a cost question at this point, a sensitivity sweep on the spread assumption (e.g. 0.5/0.75/1.0/1.5bps) would show how fragile the $100k threshold actually is.

## What's already handled well (not re-litigated above)

- Lookahead: momentum signal, portfolio backtest entry timing, and the extreme-gap threshold are all correctly constructed or explicitly caveated where they aren't (the `>3σ` full-sample threshold is framed as descriptive, not tradeable).
- The `overnight × intraday ≈ buy-and-hold` identity is used as a running internal consistency check, including across the dividend fix.
- Survivorship bias is disclosed plainly rather than hidden, with concrete mitigations (factor-neutrality, dividend fix) and an honest statement of what remains ("conditioned on large-cap today").
- BH-FDR correction is applied to the core cross-sectional test, with expected-false-positive counts reported alongside actual significant counts.
- The dividend-adjustment bug in an earlier version was caught and fixed by the project itself, and documented rather than quietly patched.
- The tradeability conclusion is not oversold: "ruinous below ~$30-40k, marginal at $50k, works at $100k+" is an honest, correctly-shaped answer rather than a pitch.

## If this is going to inform real capital

Do these two first, since they're the ones that could move the headline number: (1) get a real T-bill yield series and credit it to idle cash in the portfolio backtest — this is the single biggest lever on the marginal-account verdict; (2) filter `open==close` days out of `load_ticker` and re-run the full-history tables to see how much of the reported edge is data artifact vs. real. Then, before sizing anything off the momentum overlay specifically, hold out a genuine OOS window and re-test it.
