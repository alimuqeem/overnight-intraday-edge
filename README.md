# Overnight vs. Intraday Returns: Is There a General Edge?

A test of whether Micron's viral "buy the close, sell the open" chart is a market-wide edge or a single-stock fluke, using 33 sector-diversified large-caps and their full available price history (1962-2026 depending on listing date).

## Why this exists

This started from a viral tweet claiming MU is up **+138,330,342%** since 1990 if you only held it overnight (close→open), and **-99.92%** if you only held it during the trading day (open→close).

<img src="assets/inspiration_tweet.png" alt="Tweet: Micron Technology (MU) overnight returns +138,330,342% vs intraday returns -99.92%, chart since 1990" width="500">

Source: [@wheelieinvestor on X](https://x.com/wheelieinvestor/status/2090827673136472542?s=48). Reproduced here for commentary/attribution purposes as the inspiration for this analysis; all rights to the original post belong to its author.

That claim [checks out](report.md#appendix-the-original-mu-claim) against real data. This project asks the harder question: **does that generalize into a real, tradable edge, or is MU an outlier?**

**→ [Read the full report](report.md)** | **→ [Layperson's Glossary](report.md#12-glossary-of-terms-laypersons-guide)**

> **v2:** rebuilt after an institutional-style methodology review. Fixed a dividend-adjustment bug that was leaking ex-dividend price drops into the overnight leg, added Newey-West HAC-robust significance testing, added a Fama-French factor regression to test whether the effect is repackaged momentum (it isn't), and excluded SPY/QQQ/MU from cross-sectional pooling to remove double-counting/selection bias. Details in [report.md](report.md#1-method).

## Headline result

| Question | Answer |
|---|---|
| Is the MU chart's math right? | Yes, independently reproduced. |
| Does MU's *extreme* pattern (huge overnight gain, losing intraday) generalize? | **No.** Only MU, BAC, and FCX show it out of 33 names. |
| Is there a real, general overnight-return effect? | **Yes.** 26 of 30 sector-diverse large-caps (excl. SPY/QQQ/MU) remain significant after Benjamini-Hochberg FDR correction, vs. ~1.5 expected by chance, matching published academic literature. |
| **Is this idea tradeable?** | **Yes, but only above a specific capital threshold (~$50k+) and with selective sector targeting.** Gross of costs, it is statistically robust (26/30 names significant, not repackaged momentum). Net of costs, small accounts (<$30k-$40k) face total capital ruin from broker minimum ticket fees ($0.35/order eating 15-25+ bps), robust to spread assumption. Crediting real T-bill cash yield on idle capital, accounts $\ge \$50\text{k}$ **beat SPY's Sharpe at every spread level tested** (0.89-1.10 vs. SPY's 0.65); **beating SPY's 10.87% CAGR outright too (9.25%-11.67%) requires real spreads $\le$0.75bps**, per a sensitivity sweep. See [`background/idle_cash_yield_modeling.md`](background/idle_cash_yield_modeling.md) and [`background/portfolio_backtest.md`](background/portfolio_backtest.md#stress-testing-the-spread-assumption). |
| Does it concentrate anywhere? | **Yes**, in growth/high-attention sectors (Tech, Consumer Discretionary, Comm Services, Financials). It *reverses* in Staples, Energy, Utilities. |
| Is it repackaged momentum? | **No.** Momentum-factor loading on the overnight leg is statistically zero (t=0.13) after a HAC-robust 4-factor regression; 16/30 tickers keep significant alpha net of market/size/value/momentum. |
| Is it persistent over time? | Reasonably: 0.65 cross-sectional correlation between first-half and second-half overnight returns per ticker. |
| Is it a free lunch net of costs? | **No.** Median breakeven round-trip cost is ~4.2bps; even the best cases (TSLA, MU, NVDA) only tolerate ~13-15bps before the entire multi-decade edge disappears. |
| Does it matter which weekday you buy the close on? | **Yes.** Monday's close is the strongest of the week (27.4% mean annualized, vs. 15-18% Tue-Thu); Friday's close, the weekend gap, is the weakest (7.8%), both significant (p<0.001). Not independently confirmed in the academic literature, new to this project. See [`background/day_of_week_analysis.md`](background/day_of_week_analysis.md). |
| Is it just a few earnings-like pops? | **No, mostly.** Only ~1.7% of days are extreme gaps (>3 std dev), and 27/30 tickers stay significant with those days removed (mean annualized return only falls 16.4%→14.5%). A handful of names (TSLA, HD, BAC, GOOGL, NVDA, AVGO) lean more heavily on tail events than the average name. See [`background/extreme_gap_analysis.md`](background/extreme_gap_analysis.md). |
| Has the edge decayed recently? | **No, not at the aggregate level.** A NY Fed paper found a narrow overnight futures window vanished post-2021; this project's broader 30-ticker cross-sectional mean shows no significant decay (17.97%→13.24% annualized, p=0.18) and 8/30 tickers stay significant post-2021 after FDR correction (vs. ~1.5 by chance). But it's sector rotation, not stability: TSLA/AAPL/HD/GOOGL faded hard while AVGO/LLY/CAT/CVX/XOM strengthened. See [`background/recency_regime_analysis.md`](background/recency_regime_analysis.md). |
| **Would a real, diversified, cost-aware portfolio actually have made money?** | **It depends entirely on account size, and somewhat on execution quality.** At a flat 5bps assumption (matching the sibling repo's convention), no: CAGR **-0.73%** vs. SPY's **+10.87%**. Rebuilt with IBKR Pro's actual fee schedule ($0.0035/share, $0.35/order minimum) run across a grid of starting capital: **ruinous below ~$30-40k** (total capital loss by ~2004, robust across every spread assumption tested), **marginal at $50k** (3.99% CAGR), **solidly profitable at $100k+** (CAGR converges to **9.20%**, Sharpe **0.88**). Crediting real, tiered T-bill cash yield on idle capital, the single biggest lever tested in this project: **$50k-$250k+ beat SPY's Sharpe at every spread level tested (0.5-1.5bps)**, and **beat SPY's CAGR outright too, but only at spreads of 0.75bps or tighter** (at 1.0-1.5bps, every level still wins on Sharpe but not CAGR). Whether this is tradeable is a dollar threshold conditioned on real execution quality this project can't independently verify. See [`background/portfolio_backtest.md`](background/portfolio_backtest.md) and [`background/idle_cash_yield_modeling.md`](background/idle_cash_yield_modeling.md). |
| How diversified is the 30-name book, really? | **Less than it looks.** The overnight legs behave like ~5 independent bets, not 30 (mean pairwise correlation 0.38); the downside tail is 1.71x fatter than Gaussian predicts, and 8 of the 10 worst single days cluster into 3 systemic-crisis windows. See [`background/correlation_tail_risk_analysis.md`](background/correlation_tail_risk_analysis.md). |
| Is the edge timeable by volatility regime? | **No reliable signal.** VIX-quartile averages tilt mildly higher in high-fear regimes (11.4%→15.0%), but a HAC-robust regression finds no significant relationship (t=0.53). The edge survives stress regimes but isn't timeable by VIX. See [`background/vix_regime_analysis.md`](background/vix_regime_analysis.md). |
| Does past overnight performance predict future overnight performance? | **Yes, strongly, but underwrite it at Sharpe ~0.5, not the 1.16 headline.** A trailing-momentum tercile sort produces a 22.7-28.8%/yr top-minus-bottom spread (t=13.4-16.6, robust across 5/21/63-day lookbacks); a top-tercile overlay beats naive equal-weighting on Sharpe (1.16 full-sample, but that's in-sample). Walk-forward tested (select on 1993-2010, evaluate on 2011-2026): **Sharpe 0.53**, still positive in every out-of-sample fold tested but the most recent decade is the weakest in 54 years. See [`background/overnight_momentum_analysis.md`](background/overnight_momentum_analysis.md) and [`background/walk_forward_validation.md`](background/walk_forward_validation.md). |

**Bottom line:** the overnight effect is real, academically well-documented (Berkman et al. 2012; Lou, Polk & Skouras 2019), survives multiple-comparisons correction, and is not just repackaged momentum exposure. It's a growth-stock/retail-attention characteristic concentrated in about a third of the market, not a market-wide law. The decisive result is the portfolio backtest, rebuilt with real IBKR Pro fees and a real, tiered T-bill cash-sweep yield on idle capital: a diversified, cost-aware implementation of this exact strategy would have been **ruinous below ~$30-40k of capital** (robust to the spread assumption), but **beats SPY's Sharpe from $50k upward at every spread level tested** (0.89-1.10 vs. SPY's 0.65), with outright CAGR outperformance too (9.25%-11.67% vs. SPY's 10.87%) conditional on real spreads landing at 0.75bps or tighter. MU is the extreme tail of a real distribution, not a template, and "real" turns out to mean "tradeable from roughly $50k on a risk-adjusted basis, and dangerous below it."

## Reproduce it (fully offline)

`data/*.csv` (33 tickers, dividend+split adjusted, full available history per ticker), `data/factors/ff_factors_daily.csv` (Fama-French factors), and `data/factors/tbills_daily.csv` (3-month T-bill yield) are committed to this repo, so the analysis and every chart reproduce **offline, deterministically, with no network access or API keys**:

```bash
pip install numpy scipy matplotlib   # only the offline-analysis deps, see requirements.txt
python3 scripts/analyze.py               # overnight/intraday decomposition + HAC t-tests + factor regression -> reports/
python3 scripts/analyze.py --mode B      # same, modern-era only (>=2000) -> reports/summary_mode_b.json
python3 scripts/analyze.py --mode C      # same, flat open==close days excluded -> reports/summary_mode_c.json
python3 scripts/data_cleanse_filter.py   # quantifies the open==close data bias by decade -> reports/data_hygiene_report.json
python3 scripts/day_of_week_analysis.py  # weekday breakdown -> reports/day_of_week_results.json
python3 scripts/extreme_gap_analysis.py  # tail-event decomposition -> reports/extreme_gap_results.json
python3 scripts/recency_analysis.py      # has the edge decayed since 2021? -> reports/recency_results.json
python3 scripts/portfolio_backtest.py    # full equity-curve backtest, incl. real T-bill cash yield -> reports/portfolio_backtest_results.json
python3 scripts/correlation_tail_risk_analysis.py  # diversification & fat-tail risk -> reports/correlation_tail_risk_results.json
python3 scripts/vix_regime_analysis.py   # is the edge timeable by VIX regime? -> reports/vix_regime_results.json
python3 scripts/overnight_momentum_analysis.py     # does trailing overnight momentum predict future returns? -> reports/overnight_momentum_results.json
python3 scripts/walk_forward_validator.py          # out-of-sample validation of the momentum overlay -> reports/walk_forward_results.json
python3 scripts/make_charts.py           # -> charts/
```

`scripts/fetch_data.py` (fresh price data via `yfinance`/`curl_cffi`), `scripts/fetch_factors.py` (fresh Fama-French factors), `scripts/fetch_vix.py` (fresh VIX history), and `scripts/fetch_tbills.py` (fresh 3-month T-bill yield via FRED) are only needed to refresh the dataset; all four skip files that already exist and are not required to reproduce the existing report.

## Layout

```
report.md                     full write-up (start here)
scripts/fetch_data.py         pulls full daily OHLC for the 33-ticker universe, dividend+split adjusted
scripts/fetch_factors.py      pulls Fama-French daily factors (Mkt-RF, SMB, HML, Momentum)
scripts/fetch_tbills.py       pulls the 3-month T-bill yield (FRED DTB3) for the cash-yield model
scripts/stats_utils.py        Newey-West HAC-robust OLS/mean-test implementation
scripts/analyze.py            overnight/intraday decomposition, HAC t-tests, breakeven cost, sub-period split, factor regression; --mode B/C for data-hygiene sensitivity
scripts/data_cleanse_filter.py  quantifies the open==close data-hygiene bias by ticker/decade
scripts/day_of_week_analysis.py  breaks the overnight leg down by weekday of the close bought
scripts/extreme_gap_analysis.py  tests how much of the edge depends on tail-event (earnings-like) gap days
scripts/recency_analysis.py   tests whether the edge has decayed since the NY Fed's 2021 "disappearing drift" break date
scripts/portfolio_backtest.py full day-by-day equity-curve backtest: overnight-only vs intraday-only vs SPY buy & hold, incl. a real T-bill cash-yield model
scripts/correlation_tail_risk_analysis.py  diversification (effective independent bets) and fat-tail/CVaR risk profile
scripts/fetch_vix.py           pulls full daily VIX history via direct Yahoo chart-API request
scripts/vix_regime_analysis.py conditions the overnight edge on VIX level/regime
scripts/overnight_momentum_analysis.py  trailing overnight-momentum tercile sort and equity-curve overlay
scripts/walk_forward_validator.py  out-of-sample validation (holdout, purged k-fold, Deflated Sharpe Ratio) of the momentum overlay
scripts/make_charts.py        generates every chart in report.md
data/                         cached daily OHLC per ticker + universe.json (sector map) + factors/ (Fama-French + T-bills) + VIX.csv
reports/                      per_ticker_results.json, summary.json (+ _mode_b/_mode_c variants), data_hygiene_report.json, day_of_week_results.json, extreme_gap_results.json, recency_results.json, portfolio_backtest_results.json, portfolio_backtest_ledger.csv, portfolio_realistic_cost_ledger.csv, portfolio_cash_yield_ledger.csv, correlation_tail_risk_results.json, vix_regime_results.json, overnight_momentum_results.json, overnight_momentum_ledger.csv
charts/                       generated figures
background/mu_claim_validation.md      the research trail that led to this repo
background/literature_review.md        7-paper literature review of the overnight-return anomaly, 1986-2025, with links
background/youtube_videos.md           popular YouTube coverage of the overnight-return effect, summarized
background/day_of_week_analysis.md     does it matter which weekday you buy the close on?
background/extreme_gap_analysis.md     is the edge just a few earnings-like pops?
background/execution_mechanics.md      how this actually works operationally: order types, broker support, risks, taxes
background/recency_regime_analysis.md  has the edge decayed recently? (motivated by the NY Fed's "disappearing overnight drift")
background/portfolio_backtest.md       is this actually tradeable? full equity-curve backtest with realistic costs
background/idle_cash_yield_modeling.md  crediting real T-bill cash yield on idle capital: the single biggest lever on the marginal-account verdict
background/data_hygiene_bias_filter.md  quantifying the open==close data bias and re-running the headline number both ways
background/correlation_tail_risk_analysis.md  how much real diversification and tail risk does the 30-name book have?
background/vix_regime_analysis.md      is the edge stronger in high-VIX regimes, and is it timeable?
background/overnight_momentum_analysis.md  does a stock's own trailing overnight return predict its future overnight return?
background/walk_forward_validation.md  out-of-sample validation of the momentum overlay: holdout test, purged k-fold, Deflated Sharpe Ratio
background/independent_review.md       outside audit: is this analysis complete before trading real capital?
```

## Disclaimer

Research only, not investment advice. See [report.md](report.md#limitations) for limitations (no taxes/execution-mechanics modeled, flat-cost assumption, survivorship within "still-large-cap-today" names) and [background/execution_mechanics.md](background/execution_mechanics.md) for what it would actually take to trade this (order types, broker support, gap risk, taxes). See [background/independent_review.md](background/independent_review.md) for an outside audit of whether the analysis is complete; its `open==close` data-bias, idle-cash-yield, and momentum-overlay OOS-validation findings have since been resolved and re-run (see [background/data_hygiene_bias_filter.md](background/data_hygiene_bias_filter.md), [background/idle_cash_yield_modeling.md](background/idle_cash_yield_modeling.md), and [background/walk_forward_validation.md](background/walk_forward_validation.md)), and all three meaningfully moved a headline number.
