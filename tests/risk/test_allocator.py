import pytest
from unittest.mock import MagicMock
from app.risk.allocator import allocate_portfolio

def make_mock_result(kode, skor, risk):
    r = MagicMock()
    r.skor_total = skor
    r.risk_rating = risk
    r.stock = MagicMock()
    r.stock.kode = kode
    return r

def test_allocates_proportionally():
    results = [make_mock_result("BBCA.JK", 80, "LOW"), make_mock_result("BBRI.JK", 60, "LOW")]
    alloc = allocate_portfolio(results, total_dana=5_000_000)
    assert len(alloc) == 2
    total_pct = sum(a["persentase"] for a in alloc)
    assert total_pct <= 85  # 15% buffer

def test_high_risk_excluded():
    results = [make_mock_result("BBCA.JK", 80, "LOW"), make_mock_result("RISKY.JK", 90, "HIGH")]
    alloc = allocate_portfolio(results, total_dana=5_000_000)
    assert all(a["kode"] != "RISKY.JK" for a in alloc)
