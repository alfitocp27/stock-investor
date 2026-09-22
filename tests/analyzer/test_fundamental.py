import pytest
from app.analyzer.fundamental import calculate_fundamental_score

def test_high_score_undervalued():
    data = {"pe": 10, "pbv": 1.0, "roe": 0.20, "debt_to_equity": 0.5, "dividend_yield": 0.05}
    score, breakdown = calculate_fundamental_score(data)
    assert score > 70
    assert breakdown["pe_score"] == 100
    assert breakdown["debt_score"] == 100

def test_missing_fundamental_score_zero():
    data = {"pe": None, "pbv": None, "roe": None, "debt_to_equity": None, "dividend_yield": None}
    score, breakdown = calculate_fundamental_score(data)
    assert score == 10.0  # 50 / 5 = 10.0 (debt missing = 50, rest = 0)
    assert breakdown["debt_score"] == 50

def test_expensive_stock_low_score():
    data = {"pe": 40, "pbv": 5.0, "roe": 0.03, "debt_to_equity": 3.0, "dividend_yield": 0.01}
    score, breakdown = calculate_fundamental_score(data)
    assert score < 30
