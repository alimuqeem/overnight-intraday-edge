# Overnight vs. Intraday Returns: Is There a General Edge?

A test of whether Micron's viral "buy the close, sell the open" chart is a market-wide edge or a single-stock fluke, using 33 sector-diversified large-caps and their full available price history (1962-2026 depending on listing date).

## Why this exists

A chart claimed MU is up **+138,330,342%** since 1990 if you only held it overnight (close→open), and **-99.92%** if you only held it during the trading day (open→close). That claim [checks out](report.md#appendix-the-original-mu-claim) against real data. This project asks the harder question: **does that generalize into a real, tradable edge, or is MU an outlier?**

**→ [Read the full report](report.md)**

## Headline result

| Question | Answer |
|---|---|
| Is the MU chart's math right? | Yes — independently reproduced. |
| Does MU's *extreme* pattern (huge overnight gain, losing intraday) generalize? | **No.** Only MU, BAC, and FCX show it out of 33 names. |
| Is there a real, general overnight-return effect? | **Yes** — 72.7% of 33 sector-diverse large-caps show a statistically significant positive overnight return (t=5.78, p<0.0001 cross-sectionally), matching published academic literature. |
| Does it concentrate anywhere? | **Yes** — growth/high-attention sectors (Tech, Consumer Discretionary, Comm Services, Financials). It *reverses* in Staples, Utilities, Energy, Health Care. |
| Is it persistent over time? | Reasonably — 0.65 cross-sectional correlation between first-half and second-half overnight returns per ticker. |
| Is it a free lunch net of costs? | **No.** Median breakeven round-trip cost is ~5bps; even the best cases (MU, TSLA, NVDA) only tolerate ~13-15bps before the entire multi-decade edge disappears. |

**Bottom line:** the overnight effect is real and academically well-documented (Berkman et al. 2012; Lou, Polk & Skouras 2019), but it's a growth-stock/retail-attention characteristic concentrated in about a third of the market, not a market-wide law, and it's economically thin enough that realistic trading costs erase it for most individual names. MU is the extreme tail of a real distribution, not a template.

## Reproduce it (fully offline)

`data/*.csv` (33 tickers, ~27MB, full available history per ticker) is committed to this repo, so the analysis and every chart reproduce **offline, deterministically, with no network access or API keys**:

```bash
pip install numpy scipy matplotlib   # only the offline-analysis deps, see requirements.txt
python3 scripts/analyze.py       # overnight/intraday decomposition + significance tests -> reports/
python3 scripts/make_charts.py   # -> charts/
```

`scripts/fetch_data.py` (which pulls fresh data from Yahoo Finance via `yfinance`/`curl_cffi`) is only needed to refresh the dataset or add tickers — it skips any ticker whose CSV already exists in `data/`, and is not required to reproduce the existing report.

## Layout

```
report.md                     full write-up (start here)
scripts/fetch_data.py         pulls full daily OHLC for the 33-ticker universe (yfinance via curl_cffi)
scripts/analyze.py            overnight/intraday decomposition, t-tests, breakeven cost, sub-period split
scripts/make_charts.py        generates every chart in report.md
data/                         cached daily OHLC per ticker + universe.json (sector map)
reports/                      per_ticker_results.json, summary.json
charts/                       generated figures
background/                   research notes on the academic literature behind the overnight effect
```

## Disclaimer

Research only, not investment advice. See [report.md](report.md#limitations) for limitations (no taxes/execution-mechanics modeled, flat-cost assumption, survivorship within "still-large-cap-today" names).
