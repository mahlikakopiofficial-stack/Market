from __future__ import annotations
import hmac, logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, create_engine, desc, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .market_math import build_indicators

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("imi")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    database_url: str = "sqlite:///./imi_local.db"
    twelve_data_api_key: str = ""
    twelve_data_base_url: str = "https://api.twelvedata.com"
    cors_origins: str = "http://localhost:5173"
    app_env: str = "development"
    ingestion_token: str = ""

settings = Settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
Session = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase): pass
class Provider(Base):
    __tablename__ = "data_providers"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    data_kind: Mapped[str] = mapped_column(String(40))
class Instrument(Base):
    __tablename__ = "instruments"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    asset_class: Mapped[str] = mapped_column(String(20))
    canonical_symbol: Mapped[str] = mapped_column(String(40))
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    exchange_code: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("asset_class","canonical_symbol","exchange_code"),)
class Bar(Base):
    __tablename__ = "ohlcv_bars"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("data_providers.id"))
    timeframe: Mapped[str] = mapped_column(String(12))
    candle_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[Decimal] = mapped_column(Numeric(24,10))
    high: Mapped[Decimal] = mapped_column(Numeric(24,10))
    low: Mapped[Decimal] = mapped_column(Numeric(24,10))
    close: Mapped[Decimal] = mapped_column(Numeric(24,10))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(30,10), nullable=True)
    data_status: Mapped[str] = mapped_column(String(20), default="historical")
    quality_status: Mapped[str] = mapped_column(String(20), default="valid")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("instrument_id","provider_id","timeframe","candle_time"), Index("ix_bars_lookup","instrument_id","timeframe","candle_time"))
class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("data_providers.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    records_received: Mapped[int] = mapped_column(default=0)
    records_upserted: Mapped[int] = mapped_column(default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
class ResearchNote(Base):
    __tablename__ = "research_notes"
    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id", ondelete="SET NULL"), nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(12), nullable=True)
    note_type: Mapped[str] = mapped_column(String(30), default="observation")
    note_text: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

TIMEFRAMES = {"1m":"1min","5m":"5min","15m":"15min","30m":"30min","1h":"1h","4h":"4h","1d":"1day","1w":"1week"}
DEFAULTS = [
 ("forex","EUR/USD","Euro / US Dollar",None),("forex","GBP/USD","British Pound / US Dollar",None),
 ("forex","USD/JPY","US Dollar / Japanese Yen",None),("forex","AUD/USD","Australian Dollar / US Dollar",None),
 ("forex","USD/CAD","US Dollar / Canadian Dollar",None),("forex","USD/CHF","US Dollar / Swiss Franc",None),
 ("forex","NZD/USD","New Zealand Dollar / US Dollar",None),
 ("equity","AAPL","Apple Inc.","NASDAQ"),("equity","MSFT","Microsoft Corp.","NASDAQ"),
 ("equity","NVDA","NVIDIA Corp.","NASDAQ"),("equity","TSLA","Tesla Inc.","NASDAQ"),
 ("equity","AMZN","Amazon.com Inc.","NASDAQ"),("equity","GOOGL","Alphabet Inc.","NASDAQ"),
 ("equity","META","Meta Platforms Inc.","NASDAQ")]
app = FastAPI(title="IMI Market Intelligence API", version="1.0.0", description="Read-only market monitoring. No trade execution.")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()], allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["Content-Type","X-Ingestion-Token"])

def as_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z","+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

def seed():
    with Session.begin() as db:
        if db.scalar(select(Provider).where(Provider.code=="twelvedata")) is None:
            db.add(Provider(code="twelvedata",display_name="Twelve Data",data_kind="historical_ohlcv"))
        for kind,symbol,name,exchange in DEFAULTS:
            q=select(Instrument).where(Instrument.asset_class==kind,Instrument.canonical_symbol==symbol,Instrument.exchange_code==exchange)
            if db.scalar(q) is None: db.add(Instrument(asset_class=kind,canonical_symbol=symbol,display_name=name,exchange_code=exchange))
@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    seed()

def find_instrument(db, symbol: str, asset_class: str | None = None):
    q=select(Instrument).where(Instrument.canonical_symbol==symbol,Instrument.is_active.is_(True))
    if asset_class: q=q.where(Instrument.asset_class==asset_class)
    rows=db.scalars(q.limit(2)).all()
    if not rows: raise HTTPException(404,detail=f"Unknown instrument: {symbol}")
    if len(rows)>1: raise HTTPException(409,detail="Symbol is ambiguous; specify asset_class.")
    return rows[0]

def serialize(b: Bar) -> dict[str,Any]:
    dt=b.candle_time if b.candle_time.tzinfo else b.candle_time.replace(tzinfo=timezone.utc)
    return {"time":int(dt.timestamp()),"datetime":dt.isoformat(),"open":float(b.open),"high":float(b.high),"low":float(b.low),"close":float(b.close),"volume":float(b.volume) if b.volume is not None else None,"source":"Twelve Data","status":b.data_status,"quality":b.quality_status}

def check_ingestion_token(token: str | None):
    if settings.app_env.lower()=="production" and not settings.ingestion_token:
        raise HTTPException(503,detail="Configure INGESTION_TOKEN before production ingestion.")
    if settings.ingestion_token and not hmac.compare_digest(token or "",settings.ingestion_token):
        raise HTTPException(401,detail="Valid X-Ingestion-Token header required.")

@app.get("/api/health")
def health():
    try:
        with engine.connect() as c: c.exec_driver_sql("SELECT 1")
        return {"status":"ok","database":"connected","mode":"read_only_monitoring"}
    except Exception as exc:
        log.exception("Health check failed")
        raise HTTPException(503,detail=f"Database unavailable: {type(exc).__name__}")

@app.get("/api/status")
def status():
    with Session() as db:
        total=db.query(Bar).count()
        last=db.scalar(select(Bar).order_by(desc(Bar.ingested_at)).limit(1))
    return {"application":"IMI","mode":"read_only","historical_ohlcv":{"provider":"Twelve Data","configured":bool(settings.twelve_data_api_key),"stored_bars":total,"last_ingested_at":last.ingested_at.isoformat() if last else None},"live_streaming":{"status":"not_connected"},"orderflow_footprint":{"status":"not_connected","requires":"Executed trade prints with aggressor-side classification"},"liquidity_heatmap":{"status":"not_connected","requires":"Timestamped Level 2 order-book depth"},"options_flow":{"status":"not_connected","requires":"Options trades, quotes and contract reference data"},"execution":{"enabled":False}}

@app.get("/api/instruments")
def instruments(asset_class: str | None = None):
    with Session() as db:
        q=select(Instrument).where(Instrument.is_active.is_(True))
        if asset_class:
            if asset_class not in {"forex","equity","index","etf"}: raise HTTPException(400,detail="Unsupported asset_class")
            q=q.where(Instrument.asset_class==asset_class)
        rows=db.scalars(q.order_by(Instrument.asset_class,Instrument.canonical_symbol)).all()
        return {"items":[{"id":x.id,"asset_class":x.asset_class,"symbol":x.canonical_symbol,"name":x.display_name,"exchange":x.exchange_code} for x in rows]}

@app.get("/api/candles")
def candles(symbol: str="EUR/USD",timeframe: str="15m",limit: int=Query(500,ge=10,le=5000),asset_class: str|None=None):
    if timeframe not in TIMEFRAMES: raise HTTPException(400,detail=f"Unsupported timeframe. Choose {', '.join(TIMEFRAMES)}")
    with Session() as db:
        inst=find_instrument(db,symbol,asset_class)
        provider=db.scalar(select(Provider).where(Provider.code=="twelvedata"))
        if provider is None: raise HTTPException(503,detail="Provider metadata not initialized")
        rows=db.scalars(select(Bar).where(Bar.instrument_id==inst.id,Bar.provider_id==provider.id,Bar.timeframe==timeframe).order_by(desc(Bar.candle_time)).limit(limit)).all()
        rows.reverse()
        return {"symbol":symbol,"asset_class":inst.asset_class,"timeframe":timeframe,"items":[serialize(x) for x in rows],"count":len(rows),"source":"Twelve Data","data_status":"historical" if rows else "no_data"}

@app.post("/api/ingest/historical")
async def ingest(symbol: str="EUR/USD",timeframe: str="15m",outputsize: int=Query(500,ge=10,le=5000),x_ingestion_token: str|None=Header(default=None)):
    check_ingestion_token(x_ingestion_token)
    if not settings.twelve_data_api_key: raise HTTPException(503,detail="Twelve Data key is not configured on the server.")
    if timeframe not in TIMEFRAMES: raise HTTPException(400,detail="Unsupported timeframe")
    with Session() as db:
        inst=find_instrument(db,symbol)
        provider=db.scalar(select(Provider).where(Provider.code=="twelvedata"))
    run=IngestionRun(provider_id=provider.id,status="running")
    with Session.begin() as db:
        db.add(run); db.flush(); run_id=run.id
    params={"symbol":symbol,"interval":TIMEFRAMES[timeframe],"outputsize":outputsize,"apikey":settings.twelve_data_api_key,"format":"JSON","timezone":"UTC"}
    if inst.exchange_code: params["exchange"]=inst.exchange_code
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20,connect=8)) as client:
            response=await client.get(settings.twelve_data_base_url.rstrip("/")+"/time_series",params=params)
        response.raise_for_status()
        payload=response.json()
        if payload.get("status")=="error" or "values" not in payload: raise ValueError(payload.get("message","Provider returned no values"))
        received=payload["values"]; stored=0
        with Session.begin() as db:
            for v in received:
                try:
                    dt=as_utc(v["datetime"])
                    o,h,l,c=(Decimal(str(v[k])) for k in ("open","high","low","close"))
                    vol=Decimal(str(v["volume"])) if v.get("volume") not in (None,"") else None
                    if not all(x.is_finite() for x in (o,h,l,c)) or h<max(o,c) or l>min(o,c) or h<l: continue
                    q=select(Bar).where(Bar.instrument_id==inst.id,Bar.provider_id==provider.id,Bar.timeframe==timeframe,Bar.candle_time==dt)
                    row=db.scalar(q)
                    if row:
                        row.open,row.high,row.low,row.close,row.volume=o,h,l,c,vol
                    else:
                        db.add(Bar(instrument_id=inst.id,provider_id=provider.id,timeframe=timeframe,candle_time=dt,open=o,high=h,low=l,close=c,volume=vol,data_status="historical",quality_status="valid"))
                    stored+=1
                except (KeyError,ValueError,InvalidOperation,ArithmeticError): continue
        with Session.begin() as db:
            job=db.get(IngestionRun,run_id); job.finished_at=datetime.now(timezone.utc); job.status="success" if stored else "partial"; job.records_received=len(received); job.records_upserted=stored
        return {"status":"ok","symbol":symbol,"timeframe":timeframe,"received":len(received),"stored":stored,"source":"Twelve Data","data_status":"historical"}
    except (httpx.HTTPError,ValueError) as exc:
        with Session.begin() as db:
            job=db.get(IngestionRun,run_id); job.finished_at=datetime.now(timezone.utc); job.status="failed"; job.error_summary=str(exc)[:500]
        raise HTTPException(502,detail=f"Historical import failed: {type(exc).__name__}")

@app.get("/api/analytics")
def analytics(symbol: str="EUR/USD",timeframe: str="15m",limit: int=Query(500,ge=20,le=2000),asset_class: str|None=None):
    data=candles(symbol,timeframe,limit,asset_class); bars=data["items"]
    if not bars: return {"symbol":symbol,"timeframe":timeframe,"bars":0,"items":[],"message":"No stored historical candles."}
    values=build_indicators(bars); out=[]
    for i,b in enumerate(bars):
        out.append({"time":b["time"],"ema20":values["ema20"][i],"ema50":values["ema50"][i],"ema200":values["ema200"][i],"rsi14":values["rsi14"][i],"atr14":values["atr14"][i],"vwap":values["vwap"][i]})
    return {"symbol":symbol,"timeframe":timeframe,"bars":len(bars),"items":out,"latest":out[-1],"notes":{"vwap":"Cumulative over the returned candle window; not session anchored.","forex_volume":"May be tick volume or unavailable; check provider definition.","indicators":"Descriptive calculations, not buy or sell instructions."}}

@app.get("/api/ingestion/status")
def ingestion_status():
    with Session() as db:
        rows=db.scalars(select(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(20)).all()
        return {"items":[{"started_at":x.started_at.isoformat(),"finished_at":x.finished_at.isoformat() if x.finished_at else None,"status":x.status,"received":x.records_received,"stored":x.records_upserted,"error":x.error_summary} for x in rows]}
