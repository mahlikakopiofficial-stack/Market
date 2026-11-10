-- IMI initial PostgreSQL schema.
-- Store timestamps in UTC. Apply through versioned migrations in production.

CREATE TABLE IF NOT EXISTS data_providers (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    data_kind TEXT NOT NULL,
    entitlement_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS instruments (
    id BIGSERIAL PRIMARY KEY,
    asset_class TEXT NOT NULL CHECK (asset_class IN ('equity', 'forex', 'index', 'etf')),
    canonical_symbol TEXT NOT NULL,
    display_name TEXT,
    base_currency TEXT,
    quote_currency TEXT,
    exchange_code TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (asset_class, canonical_symbol, exchange_code)
);

CREATE TABLE IF NOT EXISTS ohlcv_bars (
    id BIGSERIAL PRIMARY KEY,
    instrument_id BIGINT NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    provider_id BIGINT NOT NULL REFERENCES data_providers(id),
    timeframe TEXT NOT NULL CHECK (timeframe IN ('1min','5min','15min','30min','1h','4h','1day','1week')),
    candle_time TIMESTAMPTZ NOT NULL,
    open NUMERIC(24,10) NOT NULL,
    high NUMERIC(24,10) NOT NULL,
    low NUMERIC(24,10) NOT NULL,
    close NUMERIC(24,10) NOT NULL,
    volume NUMERIC(30,10),
    data_status TEXT NOT NULL DEFAULT 'historical'
        CHECK (data_status IN ('historical','delayed','streaming','replay','synthetic')),
    quality_status TEXT NOT NULL DEFAULT 'unchecked'
        CHECK (quality_status IN ('unchecked','valid','warning','rejected')),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (high >= low),
    CHECK (high >= GREATEST(open, close)),
    CHECK (low <= LEAST(open, close)),
    UNIQUE (instrument_id, provider_id, timeframe, candle_time)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_lookup
    ON ohlcv_bars (instrument_id, timeframe, candle_time DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_ingested
    ON ohlcv_bars (ingested_at DESC);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    provider_id BIGINT REFERENCES data_providers(id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running','success','partial','failed')),
    records_received INTEGER NOT NULL DEFAULT 0,
    records_upserted INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);

CREATE TABLE IF NOT EXISTS paper_research_notes (
    id BIGSERIAL PRIMARY KEY,
    instrument_id BIGINT REFERENCES instruments(id) ON DELETE SET NULL,
    timeframe TEXT,
    note_type TEXT NOT NULL DEFAULT 'observation',
    note_text TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_notes_observed
    ON paper_research_notes (observed_at DESC);
