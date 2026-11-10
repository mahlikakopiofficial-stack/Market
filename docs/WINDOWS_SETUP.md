# Windows setup (PowerShell)

## Prerequisites
- Windows 10/11
- Git for Windows
- Python 3.12 (64-bit)
- Node.js 20+ (22 LTS recommended)
- A managed PostgreSQL database reachable by your local machine and hosted backend
- A Twelve Data API key with access to the symbols and intervals you plan to request

## 1. Clone and configure
Run from the folder where you keep projects:

```powershell
git clone https://github.com/mahlikakopiofficial-stack/Market.git
cd Market
Copy-Item .env.example .env
notepad .env
```

Set these values in the root `.env` file:
- `DATABASE_URL`: PostgreSQL connection string from your database provider. Use TLS/SSL.
- `TWELVE_DATA_API_KEY`: your private Twelve Data key.
- `CORS_ORIGINS`: local frontend origin; add your deployed frontend origin when needed.

Never commit `.env`, put secrets in frontend variables, or paste credentials into chat. The repository includes only a placeholder template.

## 2. Start the backend
Open PowerShell in the repository root:

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install --upgrade pip
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

The backend loads the root `.env` file and connects to the shared PostgreSQL database. On first start it creates the initial tables and seeds the default instrument list.

Check:
- Health: http://127.0.0.1:8000/api/health
- API docs: http://127.0.0.1:8000/docs

## 3. Start the frontend
Open a second PowerShell window in the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## 4. Load historical data
Choose an instrument and timeframe, then click **Fetch historical candles**. The backend requests historical OHLCV from Twelve Data and stores the returned bars in PostgreSQL. Other dashboard instances using the same backend/database can then read those bars.

## 5. Optional Docker development
Docker Desktop must be installed and running. Configure the root `.env` first, then run from the repository root:

```powershell
docker compose up --build
```

Open http://localhost:5173. The Docker frontend proxy targets the API service by its Compose DNS name.

## Important limitations
- The current milestone is historical OHLCV monitoring only; live streaming is not implemented.
- Genuine order flow requires trade prints with aggressor-side classification; a candle feed cannot provide it.
- A genuine liquidity heatmap requires historical Level 2 order-book depth; Twelve Data candle data is not a substitute.
- Options flow requires listed-options trades/quotes and contract metadata from an appropriate provider; it is not included in this build.
- Forex volume is often tick volume or unavailable, so VWAP must be labelled as a proxy when the source does not provide exchange-traded volume.
- This project is strictly read-only. It does not connect to broker execution, place orders, or automate trading.
