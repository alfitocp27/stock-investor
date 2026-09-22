import pandas as pd
import numpy as np
import pytest

def make_price_df(days=200, start_price=100):
    dates = pd.date_range("2025-01-01", periods=days)
    np.random.seed(42)
    close = pd.Series(np.cumsum(np.random.randn(days)) + start_price, index=dates)
    volume = pd.Series(np.random.randint(1_000_000, 10_000_000, days), index=dates)
    return pd.DataFrame({"Close": close, "Volume": volume})

def test_rsi_returns_value_between_0_and_100():
    from app.analyzer.indicators import calculate_indicators
    df = make_price_df()
    result = calculate_indicators(df)
    assert result["rsi"] is not None
    assert 0 <= result["rsi"] <= 100

def test_macd_signal_valid():
    from app.analyzer.indicators import calculate_indicators
    df = make_price_df()
    result = calculate_indicators(df)
    assert result["macd_signal"] in ("BUY", "SELL", "NEUTRAL")

def test_trend_valid():
    from app.analyzer.indicators import calculate_indicators
    df = make_price_df()
    result = calculate_indicators(df)
    assert result["trend"] in ("BULL", "BEAR", "SIDEWAYS")

def test_empty_df_returns_defaults():
    from app.analyzer.indicators import calculate_indicators
    result = calculate_indicators(pd.DataFrame())
    assert result["macd_signal"] == "NEUTRAL"
    assert result["trend"] == "SIDEWAYS"
    assert result["rsi"] is None

def test_short_df_returns_defaults():
    from app.analyzer.indicators import calculate_indicators
    result = calculate_indicators(make_price_df(days=10))
    assert result["macd_signal"] == "NEUTRAL"
    assert result["trend"] == "SIDEWAYS"
