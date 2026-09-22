import pytest
from unittest.mock import patch, MagicMock

def test_full_scan_flow_mocked():
    """End-to-end integration test with mocked network data."""
    from app.data.models import get_session
    from app.scheduler import run_full_scan
    
    with patch("app.scheduler.get_cached_or_fetch") as mock_fetch:
        mock_fetch.return_value = {
            "kode": "BBCA.JK", "error": None, "prices_1y": MagicMock(),
            "price": 9000, "pe": 10, "pbv": 1.0, "roe": 0.2,
            "debt_to_equity": 0.5, "dividend_yield": 0.05,
            "nama": "Bank Central Asia", "sector": "Perbankan", "market_cap": 1e15
        }
        session = get_session()
        try:
            result = run_full_scan(session)
            assert "scanned" in result
            assert "alerts_sent" in result
            assert "errors" in result
            assert isinstance(result["scanned"], int)
            assert result["scanned"] > 0
        finally:
            session.close()

def test_portfolio_allocator_respects_buffer():
    """Verify allocator never allocates more than 85% total."""
    from app.risk.allocator import allocate_portfolio
    r = MagicMock()
    r.skor_total = 80
    r.risk_rating = "LOW"
    r.stock = MagicMock()
    r.stock.kode = "BBCA.JK"
    alloc = allocate_portfolio([r], total_dana=5_000_000)
    total_pct = sum(a["persentase"] for a in alloc)
    assert total_pct <= 85, f"Buffer violated: {total_pct}% allocated"
