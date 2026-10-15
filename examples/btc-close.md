# BTC/USD close on 17 October 2026: forward practice

Forecast evidence timestamp: **15 October 2026, 00:00 UTC**. This is a offline forward exercise on a question whose tournament submission window closed on 7 October. It contributes **zero tournament predictions and zero scored results**.

The target is CoinGecko's BTC/USD “Close Price” for the row dated 17 October 2026. The time horizon used here ends at 18 October 00:00 UTC.

CoinGecko quoted **$81,563**, updated at 14 October 23:59:02 UTC; Coinbase independently quoted **$81,582.015** at retrieval. Coinbase returned 92 daily candles. The newly opened 15 October candle is excluded, leaving 91 complete candles and 90 close-to-close returns through 14 October.

The daily log-return standard deviations are **2.0816% over 30 returns** and **2.2960% over 60**. The forecast uses the larger estimate, scaled by the square root of the three-day horizon. The log-price center is the current CoinGecko quote. A 90% ordinary-volatility / 10% double-volatility mixture reserves weight for jumps and volatility-estimation error. Directional drift is set to zero over this short horizon.

The BLS schedule places September CPI on 14 October, before the snapshot, and PPI on 15 October plus import/export prices on 16 October. Upcoming macro releases and weekend trading motivate the wider component. The current quote already incorporates trading after CPI.

The saved 201-point CDF uses the actual question's $60,000–$110,000 grid and open-tail probability floors. Its exact percentile outputs and parameters are in `btc-close.json`. Forecast accuracy will be recorded against the specified source row when published.

Sources:
- https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_last_updated_at=true
- https://api.coinbase.com/v2/prices/BTC-USD/spot
- https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=2026-07-16T00%3A00%3A00Z&end=2026-10-15T00%3A00%3A00Z
- https://www.bls.gov/schedule/2026/10_sched.htm
- https://www.metaculus.com/questions/45947/
