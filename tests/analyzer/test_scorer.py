import pandas as pd
import numpy as np
from app.analyzer.scorer import score_stock

def make_df(days=200):
    dates = pd.date_range("2025-01-01", periods=days)
    np.random.seed(42)
    close = pd.Series(np.cumsum(np.random.randn(days)) + 100, index=dates)
    return pd.DataFrame({"Close": close, "Volume": pd.Series(5_000_000, index=dates)})

def test_low_risk_stock_high_score():
    data = {"kode": "BBCA.JK", "price": 9000, "prices_1y": make_df(),
            "pe": 10, "pbv": 1.0, "roe": 0.20, "debt_to_equity": 0.5,
            "dividend_yield": 0.05, "sector": "Perbankan", "market_cap": 1e15, "error": None}
    result = score_stock(data)
    assert result.skor_total > 50
    assert result.risk_rating in ("LOW", "MEDIUM")

def test_missing_fundamental_graceful():
    data = {"kode": "TEST.JK", "price": 100, "prices_1y": make_df(),
            "pe": None, "pbv": None, "roe": None, "debt_to_equity": None,
            "dividend_yield": None, "error": None}
    result = score_stock(data)
    assert result.skor_fundamental <= 50  # debt missing = 50, rest 0
    assert result.skor_total < 60

def test_high_risk_stock_flagged():
    data = {"kode": "RISKY.JK", "price": 100, "prices_1y": make_df(),
            "pe": 50, "pbv": 5.0, "roe": -0.1, "debt_to_equity": 3.5,
            "dividend_yield": 0.01, "error": None}
    result = score_stock(data)
    assert result.risk_rating == "HIGH"
