# Windows setup (PowerShell)

## Requirements
- Git for Windows
- Python 3.12+
- Node.js 20+
- A managed PostgreSQL database (shared by local and hosted backend)
- Twelve Data API key for historical candles

## 1. Clone
```powershell
git clone https://github.com/mahlikakopiofficial-stack/Market.git
cd Market
Copy-Item .env.example .env
```

Edit `.env` in Notepad. Set DATABASE_URL and TWELVE_DATA_API_KEY privately. Never commit .env or paste secrets into chat.

## 2. Backend
```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 3. Frontend (second PowerShell window)
```powershell
cd Market\frontend
npm install
npm run dev
```
Open http://localhost:5173. API docs: http://localhost:8000/docs.

## 4. Fetch historical candles
Choose an instrument and timeframe in the dashboard, then click **Fetch historical candles**. This calls the backend, fetches historical OHLCV from Twelve Data, and stores it in the shared PostgreSQL database. Refreshing another client will read the same stored records.

## Notes
- The initial app is read-only and historical-data focused.
- The database is not provisioned by this repository; create a managed PostgreSQL database and allow connections from the backend hosts only.
- The current dashboard intentionally does not claim to have real order-flow, options-flow or Level 2 liquidity heatmap feeds.
- Streaming subscriptions are not part of this runnable first milestone.
