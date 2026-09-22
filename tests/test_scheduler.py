from unittest.mock import patch, MagicMock

@patch("app.scheduler.get_cached_or_fetch")
@patch("app.scheduler.check_and_notify")
def test_scan_runs_without_crash(mock_notify, mock_cache):
    mock_cache.return_value = {
        "kode": "BBCA.JK", "error": None, "prices_1y": MagicMock(),
        "price": 9000, "pe": 10, "pbv": 1.0, "roe": 0.2,
        "debt_to_equity": 0.5, "dividend_yield": 0.05,
        "nama": "BCA", "sector": "Perbankan", "market_cap": 1e15
    }
    mock_notify.return_value = 0
    from app.scheduler import run_full_scan
    from app.data.models import get_session
    session = get_session()
    result = run_full_scan(session)
    assert result["scanned"] >= 1
    assert "alerts_sent" in result
    assert isinstance(result["errors"], list)
