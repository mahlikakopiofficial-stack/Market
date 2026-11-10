# IMI — Institutional Market Intelligence

IMI is a read-only market monitoring and research terminal for global equities and forex. It has no broker integration, account access, order placement or automated execution.

## Included
- React, TypeScript, Vite and Lightweight Charts frontend.
- FastAPI backend and SQLAlchemy data layer.
- PostgreSQL schema; SQLite supported for local smoke tests only.
- Twelve Data historical OHLCV import adapter.
- Multi-timeframe candles: 1m, 5m, 15m, 30m, 1h, 4h, 1d and 1w.
- EMA 20/50/200, RSI 14, ATR 14 and candle-window VWAP.
- Ingestion job status and API health/capability endpoints.
- CI tests and Windows/Docker/hosting documentation.

## Real feed status
| Feature | State | Requirement |
|---|---|---|
| Historical OHLCV | Adapter implemented; requires key and entitlement | Historical candle API |
| Live streaming | Not connected | Licensed real-time stream/WebSocket |
| Footprint/order flow | Not connected | Trade prints with aggressor-side classification |
| Liquidity heatmap | Not connected | Timestamped Level 2 order-book depth |
| Options flow | Not connected | Options trades, quotes and contract reference data |
| News/calendar | Not connected | Licensed news and economic calendar feed |

Do not infer unavailable feeds as zero activity. Do not fabricate order flow, book depth or options flow from candles. Forex volume may be tick volume. VWAP is cumulative over the loaded candle window, not exchange-session anchored.

## Quick start — Windows PowerShell
1. Install Python 3.12, Node.js 22 and Git.
2. Clone: git clone https://github.com/mahlikakopiofficial-stack/Market.git
3. From the repository root, copy .env.example to .env and set DATABASE_URL and TWELVE_DATA_API_KEY. Keep .env private.
4. Backend: cd backend; py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
5. In another terminal: cd frontend; npm install; npm run dev
6. Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs.

For a local SQLite test, set DATABASE_URL=sqlite:///./imi_local.db. Use PostgreSQL for shared local/hosted data.

## Docker
Copy .env.example to .env, configure the database/provider, then run docker compose up --build. Frontend: http://localhost:5173. This Compose frontend is for development, not production.

## DigitalOcean deployment
Use a Linux Droplet or App Platform, managed PostgreSQL with TLS, and a production static frontend build. Configure DATABASE_URL, APP_ENV=production, CORS_ORIGINS, TWELVE_DATA_API_KEY and a strong INGESTION_TOKEN as private deployment secrets. Serve frontend dist through a web server/reverse proxy and route /api to FastAPI. Restrict database access, enable HTTPS, backups and monitoring.

## API
GET /api/health — database health.
GET /api/status — actual provider/feed capability status.
GET /api/instruments — watchlist.
GET /api/candles — stored OHLCV.
GET /api/analytics — EMA, RSI, ATR and VWAP.
POST /api/ingest/historical — historical import; requires server-side Twelve Data key and X-Ingestion-Token when configured.
GET /api/ingestion/status — recent import runs.

Provider symbol, exchange, interval, rate and licensing entitlements must be checked with the vendor. A successful CI build is not proof of live data entitlement or low latency. This is informational software, not financial advice.
