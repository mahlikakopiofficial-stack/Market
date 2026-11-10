from fastapi.testclient import TestClient
from app.main import app

def test_read_only_api():
    with TestClient(app) as c:
        assert c.get("/api/health").json()["status"]=="ok"
        state=c.get("/api/status").json()
        assert state["execution"]["enabled"] is False
        assert state["orderflow_footprint"]["status"]=="not_connected"
        assert len(c.get("/api/instruments").json()["items"])>=10
        assert c.get("/api/candles?symbol=EUR%2FUSD&timeframe=15m").status_code==200
        assert c.get("/api/candles?symbol=EUR%2FUSD&timeframe=2m").status_code==400
