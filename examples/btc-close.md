# BTC/USD close on 17 October 2026: forward practice

Forecast evidence timestamp: **15 October 2026, 00:00 UTC**. This is an offline forward exercise on a question whose tournament submission window closed on 7 October. Tournament entry status: **offline exercise**.

The target is CoinGecko's BTC/USD “Close Price” for the row dated 17 October 2026. The time horizon used here ends at 18 October 00:00 UTC.

CoinGecko quoted **$81,563**, updated at 14 October 23:59:02 UTC; Coinbase independently quoted **$81,582.015** at retrieval. Coinbase returned 92 daily candles. The newly opened 15 October candle is excluded, leaving 91 complete candles and 90 close-to-close returns through 14 October.

The daily log-return standard deviations are **2.0816% over 30 returns** and **2.2960% over 60**. The forecast uses the larger estimate, scaled by the square root of the three-day horizon. The log-price center is the current CoinGecko quote. A 90% ordinary-volatility / 10% double-volatility mixture reserves weight for jumps and volatility-estimation error. Directional drift is set to zero over this short horizon.

The BLS schedule places September CPI on 14 October, before the snapshot, and PPI on 15 October plus import/export prices on 16 October. Upcoming macro releases and weekend trading motivate the wider component. The current quote already incorporates trading after CPI.

The saved 201-point CDF uses the actual question's $60,000–$110,000 grid and open-tail probability floors. Its exact percentile outputs and parameters are in `btc-close.json`; the original forecast remains fixed.

## Observed result — 18 October 2026

CoinGecko's historical table reports **$81,408** in the **2026-10-17 Close** row. The page states that selected dates use UTC; the following 2026-10-18 row still showed `N/A` when retrieved at 00:29:58 UTC on 18 October. This is the exact source row selected by the question's resolution criteria.

| Diagnostic | Result |
| --- | --- |
| Frozen forecast median | $81,569.05 |
| Median absolute error | $161.05 / 0.198% |
| CDF at the observed value (PIT) | 48.138% |
| Frozen central 80% interval | $77,140.16–$86,267.35; observed value inside |
| Flat-price point baseline, frozen at $81,563 | $155 absolute error |

The signed log-price error, `ln(forecast median / observed close)`, is **0.00197635**. Pinball losses for the frozen 10th, 50th and 90th percentiles are **$426.784 / $80.525 / $485.935**, respectively. PIT is linearly interpolated between the original $250 CDF grid points.

This single forward observation is an offline accuracy record. Multiple settled tournament questions and their official peer scores will guide skill and parameter assessment.

Sources:
- https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_last_updated_at=true
- https://api.coinbase.com/v2/prices/BTC-USD/spot
- https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start=2026-07-16T00%3A00%3A00Z&end=2026-10-15T00%3A00%3A00Z
- https://www.bls.gov/schedule/2026/10_sched.htm
- https://www.metaculus.com/questions/45947/
- https://www.coingecko.com/en/coins/bitcoin/historical_data
