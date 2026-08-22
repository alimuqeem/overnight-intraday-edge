# Execution Mechanics: How Would This Actually Work?

Everything in [`../report.md`](../report.md) is built on official auction print-to-print returns: `open[t] / close[t-1] - 1`. This note covers what it actually takes to achieve those prices in practice, and where the gap between backtest and real execution shows up.

## The two order types this strategy needs

- **Buying the close = a Market-on-Close (MOC) order**, not a market order placed in the last seconds of the session. MOC orders must be submitted before an exchange cutoff, roughly **3:50pm ET** on both NYSE and Nasdaq, and fill at the official closing-auction print, the same price used as "close" throughout this project. You cannot submit one literally at 3:59pm; the auction imbalance window closes before that.
- **Selling the open = a Market-on-Open (MOO) order**, submitted before the opening-auction cutoff, roughly **9:28am ET**, filling at the official opening print, the same price used as "open" throughout this project.
- **LOC / LOO** (limit-on-close / limit-on-open) are the price-capped versions of the same orders: you specify a worst acceptable price instead of taking whatever the auction clears at, at the cost of sometimes not getting filled.
- **A plain market order placed near the bell is not the same thing.** Buying right before 4:00pm close or selling right after 9:30am open approximates the auction prints, but doesn't guarantee them, and can get materially worse fills in the first seconds after the open when spreads are at their widest for the session. This project's numbers assume the actual auction print; naive market orders introduce slippage on top of that.
- **Exchange cutoff times shift periodically with rule changes.** The figures above are current as of this writing but should be verified against the exchange's own current rules, not treated as permanently fixed.

## Broker support isn't universal

Not every retail broker offers MOC/LOO order types. Before relying on this strategy, confirm your broker actually supports them; if not, you're stuck approximating with regular market orders near the bell, which directly eats into the median ~4.2bps breakeven cushion found in [`../report.md` §5](../report.md#5-does-it-survive-costs-and-time-partially), a strategy with that thin a margin cannot absorb sloppy execution.

### UK-accessible brokers, checked directly

Checked each broker's own published order-type documentation rather than assuming; current as of this writing, not guaranteed to stay current as platforms change.

| Broker | MOC / MOO support |
|---|---|
| **Interactive Brokers (IBKR UK)** | **Yes.** Both Market-on-Close and Market-on-Open are standard, explicitly documented order types for US stocks. |
| **Saxo Markets** | **MOC confirmed** (Trade Type: Algo → Strategy: Market on Close). MOO not independently confirmed via the same menu; verify directly in-app before relying on it. |
| **Robinhood (UK and US)** | **No.** Stated explicitly in their own support docs: *"Robinhood Financial doesn't currently support short selling, bracket orders, Market-on-Close orders, or Market-on-Open orders."* |
| **Freetrade** | Not found. Documented order types stop at Queued, Instant, Limit, Stop Loss, Triggered, Extended hours. |
| **Trading 212** | Not found. Documented order types stop at Market, Limit, Stop, Stop-Limit, OCO. |
| **Hargreaves Lansdown** | Not found. Documented order types stop at "At Best," Fill or Kill, Limit, Stop Loss. |
| **Interactive Investor (ii)** | Not found. Documented order types stop at Limit, Market, Stop Loss, "at best." |
| **DEGIRO** | Not found. Documented order types stop at Market, Limit, Stop Loss, Stop Limit, Trailing Stop. |

"Not found" means the order type doesn't appear in that broker's own published documentation, not a confirmed absence from every corner of their platform; a live chat with the broker's support desk is the only way to be certain. Among UK-accessible brokers, Interactive Brokers is the practical answer if precise auction-price execution matters; every broker below Saxo in this table would mean approximating with a plain market or limit order near the bell instead, reintroducing the slippage this section already flags as eating into an already-thin margin.

### What would this actually cost, in practice? IBKR Pro vs. Robinhood

The 5bps round-trip cost used throughout this project (and the portfolio backtest's own solved breakeven of 4.71bps, see [`portfolio_backtest.md`](portfolio_backtest.md)) is a flat modeling assumption, not a quote from either broker. Checked against real fee schedules, the answer turns out to depend more on **position size** than on which broker you pick.

**Interactive Brokers Pro** (needed to access MOC/MOO at all; IBKR Lite uses PFOF routing similar to Robinhood and likely shares its order-type limitations). Tiered commission plan: $0.0035/share, **minimum $0.35 per order**. That minimum dominates at small size:

| Position size per name | Commission (round-trip) |
|---|---:|
| $1,000 | **7.0bps**, already above the 4.71bps breakeven |
| $3,000 | 2.3bps |
| $5,000 | 1.4bps |
| $10,000+ | 0.7bps, converging toward ~0.35bps at larger scale |

On top of commission, add the bid-ask spread: this project's mega-cap universe (AAPL, MSFT, etc.) typically quotes $0.01-0.03 spreads on $100-500 stocks, roughly **0.5-1bps round-trip**; closing/opening auctions for these names are typically at least as tight as continuous-session quotes given their depth. SEC/FINRA regulatory fees (sell-side only) are a negligible fraction of a bp.

**Realistic IBKR Pro total: roughly 1-2bps round-trip at $10k+ per position (comfortably clears the 4.71bps breakeven), rising to 3-8bps+ at $1-3k per position (at or above breakeven).** Position size, not broker choice, is the deciding variable once you're on a platform that supports the right order types at all.

**Robinhood** is moot for the *exact* tested strategy since it doesn't support MOC/MOO (confirmed above). Approximating with plain market orders near the bell instead: $0 visible commission, but Robinhood monetizes via payment-for-order-flow, so cost shows up as execution quality rather than a fee line. Robinhood was fined $65M by the SEC in 2020 specifically for inferior execution quality versus peers, and more recent academic work still finds its price improvement weaker than brokers like TD Ameritrade. On top of that, approximating the auction with a market order carries slippage risk that a true MOC/MOO fill is specifically designed to avoid. No reliable bps estimate is possible without proprietary fill data, but directionally this stacks two extra cost sources on top of whatever IBKR Pro would charge for the same trade.

## The risk the backtest doesn't price: no ability to exit

Once positioned at the close via MOC, there is no way to react to news, an earnings miss, a guidance cut, a macro shock, until the next open. The same mechanism that produces the big up-gaps in this project's data (MU, TSLA, NVDA) produces big down-gaps on bad nights. The breakeven-cost analysis in this project assumes a flat, symmetric per-trade cost; it does not model the fat-tailed, asymmetric risk of a specific bad overnight print. This is a real risk being taken, not just a statistical cost being paid.

## Capital and leverage

Buying shares outright via MOC ties up the full position value overnight (100 shares of a $700 stock is $70,000 of capital, untradeable for ~17.5 hours), with no leverage. An options-based alternative, e.g. buying a deep-ITM short-dated call at the close and selling it at the open, would express the same directional view on the overnight move with defined risk to the premium paid and far less capital tied up, but has its own costs (spread on the option itself, which is typically wider than the underlying's, and time decay over the overnight hold) that this project has not tested.

## Two practical positives

- **This is not a day trade.** The position is held overnight, so Pattern Day Trader rules (which apply to same-day round trips) don't apply here, a genuine advantage if running this frequently in a smaller account.
- **Liquid large-caps have deep, well-arbitraged auctions.** Every name in this project's universe is a liquid mega-cap, so the closing and opening auctions themselves are not a major execution risk the way they would be for a thinly-traded small-cap.

## What isn't modeled anywhere in this project

- **Taxes.** Running this daily generates roughly 250 short-term taxable events a year, each taxed as ordinary short-term capital gains. None of this project's return figures are net of tax.
- **The bid-ask spread on the auction fill itself** for names outside this project's mega-cap universe; the breakeven-cost figures are a flat assumption, not a name-specific quoted spread.
- **Broker-specific auction access and any associated fees**, which vary by broker and aren't uniform across the industry.

## Bottom line

The backtest's numbers are achievable, they're built on real, tradable exchange auction prices for liquid large-caps, not a theoretical construct. But "achievable" requires the right order types (MOC/MOO, ideally with a broker that supports them), acceptance of real overnight gap risk with zero ability to react, and an honest accounting of taxes and execution slippage that this project's headline figures don't include. Sharpened against real fee schedules, IBKR Pro at meaningful position size (roughly $10k+ per name) lands around 1-2bps round-trip, comfortably inside the portfolio backtest's 4.71bps breakeven; the same strategy at small position size, or approximated on a broker without MOC/MOO support, likely does not.
