# IMI architecture

## Data flow
The React client requests instrument metadata, stored OHLCV and descriptive analytics from FastAPI. The historical import endpoint calls Twelve Data with a server-side key, normalizes timestamps to UTC, validates OHLC values and upserts bars. EMA, RSI, ATR and VWAP are calculated from stored candles.

## Data model
- data_providers: provider and feed type.
- instruments: canonical symbol, asset class and exchange.
- ohlcv_bars: normalized candle history, source status and quality.
- ingestion_runs: import state, counts and errors.
- research_notes: reserved for manual observations, not orders or positions.

## Specialist data adapters
Trade prints must preserve event time, receive time, sequence and aggressor-side classification. Order-book adapters must store Level 2 snapshots and incremental updates with sequence-gap recovery. Options flow requires trades, quotes, contract metadata and venue coverage. Never infer these feeds from candles.

## Operations
Keep credentials backend-only. Configure an ingestion token before production. Use explicit CORS origins, HTTPS, PostgreSQL TLS, restricted database access, backups and monitoring. There is no broker integration or execution route.
