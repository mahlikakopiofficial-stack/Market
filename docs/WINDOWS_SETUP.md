# Windows setup

Install Python 3.12, Node.js 22 and Git. From the repository root, copy .env.example to .env and set DATABASE_URL and TWELVE_DATA_API_KEY. Never commit .env.

Backend PowerShell:
```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend in a second terminal:
```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs. The import button fetches historical candles only. Enter the ingestion token in the UI only if the server requires one. The specialist market-structure feeds remain disconnected until licensed provider adapters are configured.

Use PostgreSQL for shared local/hosted data. SQLite is for local smoke tests only.
