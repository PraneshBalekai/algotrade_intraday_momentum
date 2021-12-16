# Intraday Momentum Strategy (Buy on Gap model)on NSE: NIFTY500. 

### This project employs one of the intraday trading strategies discussed in Ernest P. Chan's - Algorithmic Trading Winning Strategies and Their Rationale

## ADDITIONS
Since the stragey involves enterting the trades at market open, the prices are prone to high volatility in the first few minutes. 

I added a module to the strategy to calculate impact cost from order book data (as a measure of liquidity) and take buy/no-buy decision based on it.

### Set-up

- Login to kite connect from terminal before starting session

```jtrader zerodha startsession```

### FILES

- Initialize kite connect: `main.py`
- Historical data: `files/*`
- Strategy: `strategies/st_int_mom_v2.py`
- Order book: `order_book/order_book.py`
- Paper trade book: `order_book/paper_trade`
