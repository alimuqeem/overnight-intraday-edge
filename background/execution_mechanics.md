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

The backtest's numbers are achievable, they're built on real, tradable exchange auction prices for liquid large-caps, not a theoretical construct. But "achievable" requires the right order types (MOC/MOO, ideally with a broker that supports them), acceptance of real overnight gap risk with zero ability to react, and an honest accounting of taxes and execution slippage that this project's headline figures don't include.
