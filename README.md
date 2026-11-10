# IMI — Institutional Market Intelligence

Standalone, read-only market research and paper-analysis dashboard for global equities and forex.

## Repository role
This repository is the canonical source-code and documentation home for IMI.

## Planned architecture
- `frontend/`: dashboard UI and charting
- `backend/`: API, market-data adapters, normalization and analytics
- `data/`: schemas and small non-sensitive fixtures only
- `docs/`: architecture, provider notes and operating guides
- `deploy/`: local Windows setup and optional DigitalOcean deployment

## Data storage policy
- Do not commit API keys, passwords, account credentials, or private user data.
- Do not commit continuous tick streams or large historical market datasets.
- Store local development data in an ignored local database.
- Use a dedicated database service/volume for hosted datasets.
- Keep provider, exchange, timestamp, delay/entitlement and data-quality metadata with every dataset.

## Initial scope
- Global stocks and forex
- Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
- Historical OHLCV data integration
- Educational VWAP, EMA, RSI, ATR and volume analysis
- Clearly labelled sample/replay modules for order-flow, options-flow and liquidity visualizations until suitable licensed datasets are available
- Paper-only records; no broker execution

## Development status
Repository initialized. Application source and data-provider integrations are to be added in subsequent commits.
