# IMI — Institutional Market Intelligence

A standalone, read-only market-monitoring and analysis dashboard for global stocks and forex.

## Non-negotiable project scope

- **Monitoring and analysis only.** No trade execution, order placement, broker account connection, exchange trading credentials, or automated trading.
- Global equities and forex markets.
- Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w.
- Goal: display market movement and institutional-style market context so a person can independently review price action. The dashboard does not issue guaranteed entry/exit instructions.
- Windows local development and DigitalOcean web hosting, backed by one shared PostgreSQL database.

## Required monitoring modules

| Module | Data required | Current implementation |
|---|---|---|
| Candlestick charts | Real OHLCV/quotes | Historical Twelve Data adapter only |
| VWAP | Intraday price and volume | Basic candle-volume VWAP reference; must disclose volume limitations |
| Order flow / footprint | Executed trades with aggressor-side or bid/ask classification | Not connected |
| Liquidity heatmap | Time-stamped Level 2 order-book depth | Not connected |
| Options flow | Options trades, quotes, contract metadata and volume | Not connected |
| Multi-timeframe context | Historical and streaming market data | Timeframe selector; historical data only |
| Monitoring alerts | Defined price/volume/indicator conditions | Not implemented |

Do not synthesize order flow, depth, or options activity from candles. If a provider/feed is missing, show **Not connected** rather than invented values.

## Architecture

- React/Vite frontend for Windows browser and hosted web access.
- FastAPI backend owns provider connections and data validation.
- Shared PostgreSQL database is the source of truth for stored market data.
- Provider adapters are separate by data type: OHLCV/quotes, trade prints, Level 2 depth, and options.
- Stream ingestion should use WebSockets where the selected provider supports them, with reconnect/backoff, timestamps, sequence/gap checks, health metrics and rate-limit handling.
- Store timestamps in UTC. Record provider, instrument, exchange, feed entitlement, event time and ingestion time.
- Keep all provider credentials and database credentials server-side. Never expose secrets to browser code or commit them to GitHub.

## Current software status

The current code is an **initial historical-data prototype**, not a finished institutional terminal:
- Instrument starter list and historical OHLC candle chart exist.
- Twelve Data historical candle ingestion is implemented but requires a valid key, eligible symbol/interval entitlement and end-to-end credential test.
- PostgreSQL connection is configurable but needs a provisioned database and live connection test.
- Basic candle-volume VWAP reference exists; it is not exchange VWAP when source volume is tick volume or unavailable.
- Live streaming, global symbol discovery, genuine order-flow/footprint, Level 2 heatmap, options flow, and alerts remain to be built and tested.
- Deployment to DigitalOcean remains to be completed.

## External setup still required

1. Twelve Data API key for the existing historical OHLCV adapter.
2. Managed PostgreSQL connection string.
3. Additional provider accounts/entitlements for trade prints, Level 2 depth and options data. Select providers based on target exchanges, coverage, latency, licensing and budget before implementing adapters.
4. DigitalOcean hosting configuration and private environment secrets.

See [Windows setup](docs/WINDOWS_SETUP.md) and [architecture](docs/architecture.md).

## Run on Windows

1. Clone the repository and copy `.env.example` to a private root `.env`.
2. Configure PostgreSQL and Twelve Data credentials.
3. Start FastAPI from the repository root using Python 3.12.
4. Start the Vite frontend using Node.js 22.
5. Open `http://localhost:5173` and fetch historical candles.

Passing CI validates code compilation/build and smoke tests only. It does not prove external provider credentials, data entitlements, streaming latency, or deployment readiness.
