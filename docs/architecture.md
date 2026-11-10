# IMI shared data architecture

## Decision

Use one managed PostgreSQL database as the canonical shared store for both:
- the Windows/local dashboard;
- the hosted web dashboard.

Both clients call the IMI backend API. Neither browser nor desktop UI connects directly to PostgreSQL.

## Request/data flow

```text
Market-data provider
        |
        v
Backend ingestion service
        |
        v
Managed PostgreSQL (shared source of truth)
        ^
        |
IMI backend API
   ^         ^
   |         |
Windows UI  Hosted web UI
```

## Configuration

- Keep non-secret defaults in version control.
- Copy `.env.example` to a local `.env` for Windows development.
- Set production values as private environment variables / hosting secrets.
- Never commit API keys, database URLs with passwords, tokens, or certificates.
- Do not put provider credentials in frontend variables (for example, VITE_*).

## Database

PostgreSQL is the initial shared database. Use a managed provider with TLS, automated backups, access controls, and a region close to the backend. The backend should use a connection pool and bounded query timeouts.

The database stores normalized OHLCV bars, instrument/provider metadata, ingestion health, and user-created paper research notes. High-volume raw tick/order-book streams are not stored by default. If later required, evaluate a dedicated time-series or streaming store and licensed provider entitlements first.

## Data integrity

Every market-data record must retain:
- instrument identifier and canonical symbol;
- venue/provider identity where available;
- timeframe and UTC candle-open timestamp;
- OHLCV values and source;
- whether the record is delayed, replayed, synthetic, or live;
- ingestion timestamp and quality status.

Use UTC for storage. Convert to local exchange/user time only in the UI. Upsert bars on the unique key (instrument, provider, timeframe, candle timestamp) so reconnects do not create duplicates.

## Operational separation

The IMI project is monitoring and paper research only. It must not contain broker order placement, exchange trading credentials, or execution endpoints. Keep it isolated from all other trading services and deployments.

## Windows development

1. Install Git, Python, and Node.js.
2. Clone this repository.
3. Copy `.env.example` to `.env` and fill in the private PostgreSQL connection string and provider key locally.
4. Install backend/frontend dependencies using the project setup instructions.
5. Run the backend locally; it connects to the same shared PostgreSQL database as the hosted backend.
6. Run the frontend locally; it calls the local backend API.

## Deployment

Deploy the backend and frontend independently. Configure the hosted backend with the same database and provider settings using the host's secret manager. Do not expose PostgreSQL publicly to browser clients. Restrict database network access to trusted backend environments where the managed database supports it.
