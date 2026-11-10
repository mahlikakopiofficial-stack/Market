from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint, create_engine, desc, select
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./imi_local.db"
    twelve_data_api_key: str = ""
    twelve_data_base_url: str = "https://api.twelvedata.com"
    cors_origins: str = "http://localhost:5173"
    app_env: str = "development"


settings = Settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
Session = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Provider(Base):
    __tablename__ = "data_providers"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    data_kind: Mapped[str] = mapped_column(String(40))


class Instrument(Base):
    __tablename__ = "instruments"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(__import__("sqlalchemy").Integer, "sqlite"), primary_key=True)
    asset_class: Mapped[str] = mapped_column(String(20))
    canonical_symbol: Mapped[str] = mapped_column(String(40))
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    exchange_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("asset_class", "canonical_symbol", "exchange_code"),)


class Bar(Base):
    __tablename__ = "ohlcv_bars"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(__import__("sqlalchemy").Integer, "sqlite"), primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"))
    timeframe: Mapped[str] = mapped_column(String(12))
    candle_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    high: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    low: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    close: Mapped[Decimal] = mapped_column(Numeric(24, 10))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 10), nullable=True)
    data_status: Mapped[str] = mapped_column(String(20), default="historical")
    quality_status: Mapped[str] = mapped_column(String(20), default="valid")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("instrument_id", "provider_id", "timeframe", "candle_time"),)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(__import__("sqlalchemy").Integer, "sqlite"), primary_key=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("data_providers.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    records_received: Mapped[int] = mapped_column(default=0)
    records_upserted: Mapped[int] = mapped_column(default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResearchNote(Base):
    __tablename__ = "paper_research_notes"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(__import__("sqlalchemy").Integer, "sqlite"), primary_key=True)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(12), nullable=True)
    note_type: Mapped[str] = mapped_column(String(30), default="observation")
    note_text: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


TIMEFRAMES = {"1m":"1min","5m":"5min","15m":"15min","30m":"30min","1h":"1h","4h":"4h","1d":"1day","1w":"1week"}
DEFAULT_SYMBOLS = [
    ("forex","EUR/USD","EUR/USD",None),("forex","GBP/USD","GBP/USD",None),
    ("forex","USD/JPY","USD/JPY",None),("forex","AUD/USD","AUD/USD",None),
    ("equity","AAPL","Apple Inc.","NASDAQ"),("equity","MSFT","Microsoft","NASDAQ"),
    ("equity","NVDA","NVIDIA","NASDAQ"),("equity","TSLA","Tesla","NASDAQ"),
]


def seed_metadata() -> None:
    with Session.begin() as db:
        provider = db.scalar(select(Provider).where(Provider.code == "twelvedata"))
        if provider is None:
            db.add(Provider(code="twelvedata", display_name="Twelve Data", data_kind="historical_ohlcv"))
        for kind, symbol, name, exchange in DEFAULT_SYMBOLS:
            existing = db.scalar(select(Instrument).where(
                Instrument.asset_class == kind,
                Instrument.canonical_symbol == symbol,
                Instrument.exchange_code == exchange
            ))
            if existing is None:
                db.add(Instrument(asset_class=kind, canonical_symbol=symbol, display_name=name, exchange_code=exchange))


app = FastAPI(title="IMI Market Data API", version="0.1.0", description="Read-only historical market research API. No order execution.")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()], allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["*"])


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    seed_metadata()


def provider_symbol(symbol: str) -> str:
    return symbol.replace("/", "/")


def serialize_bar(b: Bar) -> dict[str, Any]:
    dt = b.candle_time if b.candle_time.tzinfo else b.candle_time.replace(tzinfo=timezone.utc)
    return {"time": int(dt.timestamp()), "datetime": dt.isoformat(),
            "open": float(b.open), "high": float(b.high), "low": float(b.low),
            "close": float(b.close), "volume": float(b.volume or 0),
            "source": "Twelve Data", "status": b.data_status}


@app.get("/api/health")
def health():
    try:
        with engine.connect() as c:
            c.exec_driver_sql("SELECT 1")
        return {"status":"ok","database":"connected","mode":"historical_read_only"}
    except Exception as e:
        raise HTTPException(503, detail=f"Database unavailable: {type(e).__name__}")


@app.get("/api/instruments")
def instruments():
    with Session() as db:
        rows = db.scalars(select(Instrument).where(Instrument.is_active.is_(True)).order_by(Instrument.asset_class, Instrument.canonical_symbol)).all()
        return {"items":[{"id":x.id,"asset_class":x.asset_class,"symbol":x.canonical_symbol,"name":x.display_name,"exchange":x.exchange_code} for x in rows]}


@app.get("/api/candles")
def candles(symbol: str = "EUR/USD", timeframe: str = "15m", limit: int = Query(300, ge=10, le=5000)):
    if timeframe not in TIMEFRAMES:
        raise HTTPException(400, detail=f"Unsupported timeframe. Choose {', '.join(TIMEFRAMES)}")
    with Session() as db:
        inst = db.scalar(select(Instrument).where(Instrument.canonical_symbol == symbol))
        prov = db.scalar(select(Provider).where(Provider.code == "twelvedata"))
        if not inst or not prov:
            raise HTTPException(404, detail="Instrument not found")
        rows = db.scalars(select(Bar).where(Bar.instrument_id == inst.id, Bar.provider_id == prov.id, Bar.timeframe == timeframe).order_by(desc(Bar.candle_time)).limit(limit)).all()
        rows.reverse()
        return {"symbol":symbol,"timeframe":timeframe,"items":[serialize_bar(x) for x in rows],"count":len(rows),"source":"Twelve Data","data_status":"historical"}


@app.post("/api/ingest/historical")
async def ingest_historical(symbol: str = "EUR/USD", timeframe: str = "15m", outputsize: int = Query(300, ge=10, le=5000)):
    if not settings.twelve_data_api_key:
        raise HTTPException(503, detail="Twelve Data key is not configured. Add TWELVE_DATA_API_KEY to your private .env.")
    if timeframe not in TIMEFRAMES:
        raise HTTPException(400, detail="Unsupported timeframe")
    with Session() as db:
        inst = db.scalar(select(Instrument).where(Instrument.canonical_symbol == symbol))
        prov = db.scalar(select(Provider).where(Provider.code == "twelvedata"))
        if not inst or not prov:
            raise HTTPException(404, detail="Unknown instrument. Use /api/instruments.")
    params = {"symbol":provider_symbol(symbol),"interval":TIMEFRAMES[timeframe],"outputsize":outputsize,"apikey":settings.twelve_data_api_key,"format":"JSON","timezone":"UTC"}
    if inst.exchange_code:
        params["exchange"] = inst.exchange_code
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{settings.twelve_data_base_url}/time_series", params=params)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as e:
        raise HTTPException(502, detail=f"Market-data provider request failed: {type(e).__name__}")
    if payload.get("status") == "error" or "values" not in payload:
        raise HTTPException(502, detail=payload.get("message","Provider returned no candle values"))
    values = payload["values"]
    count = 0
    with Session.begin() as db:
        for v in values:
            try:
                dt = datetime.fromisoformat(v["datetime"]).replace(tzinfo=timezone.utc)
                o,h,l,c = map(Decimal, (v["open"],v["high"],v["low"],v["close"]))
                vol = Decimal(v["volume"]) if v.get("volume") not in (None,"") else None
                if h < max(o,c) or l > min(o,c) or h < l:
                    continue
                existing = db.scalar(select(Bar).where(Bar.instrument_id==inst.id,Bar.provider_id==prov.id,Bar.timeframe==timeframe,Bar.candle_time==dt))
                if existing:
                    existing.open,existing.high,existing.low,existing.close,existing.volume=o,h,l,c,vol
                else:
                    db.add(Bar(instrument_id=inst.id,provider_id=prov.id,timeframe=timeframe,candle_time=dt,open=o,high=h,low=l,close=c,volume=vol,data_status="historical",quality_status="valid"))
                count += 1
            except (KeyError, ValueError, ArithmeticError):
                continue
    return {"status":"ok","symbol":symbol,"timeframe":timeframe,"received":len(values),"stored":count,"source":"Twelve Data","data_status":"historical"}


@app.get("/api/analytics")
def analytics(symbol: str = "EUR/USD", timeframe: str = "15m", limit: int = Query(300, ge=20, le=2000)):
    data = candles(symbol,timeframe,limit)
    bars = data["items"]
    if not bars:
        return {"symbol":symbol,"timeframe":timeframe,"items":[],"message":"No historical candles stored yet."}
    pv, vv, closes = 0.0, 0.0, []
    out=[]
    for b in bars:
        typical=(b["high"]+b["low"]+b["close"])/3
        vol=b["volume"]
        pv += typical*vol
        vv += vol
        closes.append(b["close"])
        out.append({"time":b["time"],"vwap":pv/vv if vv else None})
    return {"symbol":symbol,"timeframe":timeframe,"vwap":out,"bars":len(bars),"note":"VWAP uses provider-reported candle volume; forex volume may be unavailable or broker-specific."}


@app.get("/api/ingestion/status")
def ingestion_status():
    with Session() as db:
        rows=db.scalars(select(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(20)).all()
        return {"items":[{"started_at":x.started_at.isoformat(),"status":x.status,"received":x.records_received,"stored":x.records_upserted,"error":x.error_summary} for x in rows]}
