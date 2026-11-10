# IMI — Institutional Market Intelligence

Standalone, read-only market research and paper-analysis dashboard for global equities and forex.

## Project decision

IMI uses one shared managed PostgreSQL database for both Windows/local development and the hosted web dashboard. Both user interfaces communicate with the backend API; browser code never connects directly to PostgreSQL.

## Repository map

- `.env.example` — safe configuration template (no real secrets)
- `database/schema.sql` — initial PostgreSQL schema
- `docs/architecture.md` — shared database, data flow, security, and deployment approach
- `.gitignore` — excludes local secrets, databases, caches, and downloaded data

## Initial scope

- Global equities and forex
- Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
- Historical OHLCV data and transparent provider/status metadata
- VWAP, EMA, RSI, ATR, and volume analysis
- Clearly labelled replay/sample research views for order-flow, liquidity heatmaps, and options-flow until suitable licensed data feeds are selected

## Data and security

- PostgreSQL is the shared source of truth.
- Store timestamps in UTC and upsert candles by instrument/provider/timeframe/time.
- Keep actual API keys, database passwords, and tokens out of GitHub. Copy `.env.example` to a private local `.env`; use the hosting platform's secret manager in production.
- Never expose database credentials or provider API keys in frontend code.
- Do not commit raw tick streams or large downloaded datasets.

## Operating boundary

IMI is a monitoring and paper-research application only. It does not place broker/exchange orders and must not contain execution credentials or order-placement endpoints.

## Next implementation stages

1. Backend service and versioned database migrations.
2. Provider adapter for historical OHLCV and separately identified streaming quotes.
3. API endpoints and ingestion health monitoring.
4. Frontend instrument/watchlist/chart integration.
5. Deployment and database backup/restore verification.

See [docs/architecture.md](docs/architecture.md) for the architecture and Windows setup direction.
