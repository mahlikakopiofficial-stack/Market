from app.market_math import atr, cumulative_vwap, ema, rsi

def test_ema_seed():
    result=ema([1,2,3,4,5],3)
    assert result[:3]==[None,None,2]
def test_rsi_flat_series():
    assert rsi([10.0]*20,14)[14]==100.0
def test_atr():
    bars=[{"high":11,"low":9,"close":10}]*15
    assert atr(bars,14)[13]==2
def test_vwap_missing_volume():
    assert cumulative_vwap([{"high":11,"low":9,"close":10,"volume":None}])==[None]
