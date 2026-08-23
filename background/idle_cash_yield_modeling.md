# Idle Cash Yield Modeling: The Highest-Leverage Missing Number

[`background/independent_review.md`](independent_review.md) flagged this as the single highest-leverage number missing from the project: the overnight-only backtest in [`portfolio_backtest.md`](portfolio_backtest.md) held an overnight-only book that is, by construction, uninvested (100% cash) for the ~6.5-hour intraday session every trading day, and credited that cash 0% yield. Both the flat-5bps and IBKR-realistic-cost sections of that backtest were resolved to be "unreachable" for live T-bill data in an earlier pass of this project; that turned out to be the same TLS-fingerprint block already documented for Yahoo's endpoints in [`fetch_data.py`](../scripts/fetch_data.py)/[`fetch_vix.py`](../scripts/fetch_vix.py), not FRED being genuinely unreachable. [`fetch_tbills.py`](../scripts/fetch_tbills.py) pulls it directly via a Chrome-impersonated session and this note documents what changes once it's credited.

## Data source

FRED series `DTB3` (3-month Treasury Bill, secondary market rate, discount basis), fetched via FRED's public `fredgraph.csv` endpoint (no API key required). 8,414 daily observations, 1993-01-04 to 2026-08-20, no gaps within that window. Cached at [`data/factors/tbills_daily.csv`](../data/factors/tbills_daily.csv).

| Era | Mean 3-month T-bill yield |
|---|---:|
| 1993-1999 | 4.60% |
| 2000-2009 | 2.70% |
| 2010-2019 (ZIRP) | 0.57% |
| 2020-2026 | 2.84% |
| Full window | 2.49% |

1,453 of 8,414 days (17.3%) print at or below 0.1%, almost entirely the 2009-2015 and 2020-2021 zero-rate periods; the series briefly goes slightly negative (-0.05%, a 2015 flight-to-safety episode). This matters directly for the tiered model below, since every tier's spread is subtracted from a rate that is at or near zero for roughly a sixth of the sample.

## Mathematical model

Implemented in `run_backtest_with_cash_yield()` in [`scripts/portfolio_backtest.py`](../scripts/portfolio_backtest.py), run alongside (not replacing) the existing flat-5bps and IBKR-realistic-cost-only models.

Each trading day's overnight-only return is the sum of the overnight stock leg (as in the existing realistic-cost model) and a cash leg earned on the same capital during that day's intraday session, when the book holds 100% cash:

$$R_{\text{total}, t} = R_{\text{overnight}, t} + R_{\text{cash}, t}$$
$$R_{\text{cash}, t} = (1 + Y_t)^{1/252} - 1$$

$Y_t$ is the account's effective annualized cash-sweep yield, tiered by starting capital against the day's T-bill rate:

| Tier | Starting capital | $Y_t$ |
|---|---|---|
| 1 | < \$10,000 | 0% (broker cash drag) |
| 2 | \$10,000-\$49,999 | max(0, T-bill − 1.50%) |
| 3 | \$50,000-\$99,999 | max(0, T-bill − 0.50%) |
| 4 | ≥ \$100,000 | max(0, T-bill − 0.25%) |

These are not double-counted against the overnight stock leg: `overnight_ret` for day `t` is the close(t-1)→open(t) return (the night *before* day `t`'s open), and `cash_ret` for day `t` is the same day's open→close cash-holding period. The two are sequential, non-overlapping windows spanning close(t-1)→close(t), so adding them is a same-day compounding approximation, not a double credit (the omitted `overnight_ret × cash_ret` cross-term is on the order of 10⁻⁶ and immaterial). Tier is fixed by *starting* capital, not the day's live balance, matching how real broker cash-sweep programs price off account size rather than intraday balance.

## Result: this moves the headline verdict, exactly as flagged

| Starting capital | CAGR (no cash yield) | CAGR (with cash yield) | Sharpe (no cash yield) | Sharpe (with cash yield) |
|---|---:|---:|---:|---:|
| \$10,000 | -100% (wiped ~1996) | -100% (wiped ~1996) | -0.36 | -0.21 |
| \$25,000 | -100% (wiped 2003-06) | -100% (wiped 2005-10) | -0.33 | -0.29 |
| **\$50,000** | **3.99%** | **9.25%** | **0.42** | **0.89** |
| **\$100,000** | **8.43%** | **11.28%** | **0.82** | **1.06** |
| \$250,000+ | 9.20% | 11.67% | 0.88 | 1.10 |

SPY buy & hold over the same window: **10.87% CAGR, 0.65 Sharpe**.

1. **The \$50k tier flips from "marginal" to solidly profitable and now beats SPY on Sharpe by a wide margin** (0.89 vs. 0.65), though CAGR (9.25%) still trails SPY's 10.87%. Under the no-cash-yield model this tier was the weakest profitable case (3.99% CAGR, a rougher ride); crediting real cash yield very roughly doubles its CAGR and more than doubles its Sharpe.
2. **The \$100k+ tier now beats SPY outright on both CAGR and Sharpe**, not just on a risk-adjusted basis. Under the no-cash-yield model, \$100k+ was competitive but still trailed SPY's CAGR (8.43-9.20% vs. 10.87%) while winning on Sharpe (0.82-0.88 vs. 0.65); crediting cash yield pushes CAGR past SPY too (11.28-11.67%).
3. **The sub-\$30-40k ruin verdict does not flip.** \$10k and \$25k still lose everything: the $0.35-per-order minimum drives round-trip costs of 60-420+bps at that notional, an order of magnitude larger than any plausible cash yield (max observed here: 6.24%/yr), so cash income cannot outrun a cost structure that severe. Cash yield does delay the wipe-out somewhat (the \$25k account survives to 2005-10 instead of 2003-06), but the terminal outcome is identical: total capital loss.

This matches the independent review's prediction almost exactly: idle cash yield was the single biggest unresolved lever on the marginal-account verdict, and crediting it moves the \$50k tier from marginal to solid and the \$100k+ tier from "competitive on Sharpe, behind on CAGR" to beating SPY on both. It does not rescue the sub-\$30-40k ruin case, which remains the correct read: this strategy is genuinely dangerous below roughly \$30-40k regardless of cash yield.

## Caveats

- **Tier spreads (1.50% / 0.50% / 0.25% below T-bill) are this project's own estimate of typical broker cash-sweep discounts by account size, not a specific broker's published rate card.** They're directionally standard (retail sweep programs pay well below the risk-free rate; institutional accounts closer to it), but a specific broker at a specific date could differ meaningfully from any of these three numbers.
- **Tier is fixed by starting capital for the whole 33-year run**, not the account's actual balance at each point in time; a real account crossing a tier boundary (e.g. growing from \$40k to \$60k) would receive a better rate partway through, which this model doesn't capture.
- **The \$0.35 IBKR Pro order minimum and 0.75bps spread assumption are unchanged from the existing realistic-cost model** (see [`portfolio_backtest.md`](portfolio_backtest.md)); this note only adds the cash leg on top, it doesn't revisit those inputs.
- **Cash yield here assumes the full uninvested period earns the money-market rate with no additional friction** (e.g. sweep timing lags, minimum balance requirements); this is the standard simplifying assumption the independent review itself used when raising this as the top-priority gap.

## Bottom line

Crediting a real, tiered T-bill-based cash yield on the overnight-only book's idle daytime cash is not a rounding-error adjustment: it moves the \$50k tier from "survives, but barely" to "solidly beats SPY on Sharpe," and moves the \$100k+ tier from "beats SPY on risk-adjusted terms only" to "beats SPY outright on both CAGR and Sharpe." It does not change the sub-\$30-40k verdict, which remains ruinous on cost structure alone. The overall tradeability threshold identified in [`portfolio_backtest.md`](portfolio_backtest.md) and [`../report.md` §9](../report.md#9-is-this-actually-tradeable-a-full-portfolio-backtest) should be read as more favorable than previously stated at and above \$50k, once idle cash is put to work.

**Caveat added after this note was written:** the numbers above use the project's 0.75bps spread assumption. A subsequent sensitivity sweep found the Sharpe-outperformance claim above is robust across 0.5-1.5bps, but the CAGR-outperformance claim specifically only holds at 0.75bps or tighter; see [`portfolio_backtest.md`](portfolio_backtest.md#stress-testing-the-spread-assumption) for the full breakdown.
