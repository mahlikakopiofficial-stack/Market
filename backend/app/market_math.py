from __future__ import annotations
from typing import Any

def ema(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period < 1: raise ValueError("period must be positive")
    if len(values) < period: return out
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    alpha = 2 / (period + 1)
    for i in range(period, len(values)):
        prev = values[i] * alpha + prev * (1 - alpha)
        out[i] = prev
    return out

def rsi(values: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if period < 1 or len(values) <= period: return out
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(x, 0.0) for x in changes]
    losses = [max(-x, 0.0) for x in changes]
    ag, al = sum(gains[:period]) / period, sum(losses[:period]) / period
    out[period] = 50.0 if ag == 0 and al == 0 else (100.0 if al == 0 else 100 - 100 / (1 + ag / al))
    for i in range(period + 1, len(values)):
        ag = (ag * (period - 1) + gains[i - 1]) / period
        al = (al * (period - 1) + losses[i - 1]) / period
        out[i] = 50.0 if ag == 0 and al == 0 else (100.0 if al == 0 else 100 - 100 / (1 + ag / al))
    return out

def atr(bars: list[dict[str, Any]], period: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    if period < 1 or len(bars) < period: return out
    tr = []
    for i, b in enumerate(bars):
        pc = float(bars[i - 1]["close"]) if i else float(b["close"])
        hi, lo = float(b["high"]), float(b["low"])
        tr.append(max(hi - lo, abs(hi - pc), abs(lo - pc)))
    prev = sum(tr[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(tr)):
        prev = (prev * (period - 1) + tr[i]) / period
        out[i] = prev
    return out

def cumulative_vwap(bars: list[dict[str, Any]]) -> list[float | None]:
    out, pv, volume = [], 0.0, 0.0
    for b in bars:
        vol = max(float(b.get("volume") or 0), 0.0)
        typical = (float(b["high"]) + float(b["low"]) + float(b["close"])) / 3
        pv += typical * vol
        volume += vol
        out.append(pv / volume if volume else None)
    return out

def build_indicators(bars: list[dict[str, Any]]) -> dict[str, list[float | None]]:
    closes = [float(b["close"]) for b in bars]
    return {"ema20": ema(closes, 20), "ema50": ema(closes, 50),
            "ema200": ema(closes, 200), "rsi14": rsi(closes, 14),
            "atr14": atr(bars, 14), "vwap": cumulative_vwap(bars)}
