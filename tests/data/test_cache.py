import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from app.data.cache import get_cached_or_fetch

@patch("app.data.cache.fetch_stock_data")
@patch("app.data.cache.get_session")
def test_cache_miss_fetches(mock_session, mock_fetch):
    mock_fetch.return_value = {
        "kode": "BBCA.JK", "price": 9000, "error": None,
        "prices_1y": MagicMock(), "sector": "Perbankan", "market_cap": 1e15,
        "pe": 20, "pbv": 2.5, "roe": 0.15, "debt_to_equity": 0.5, "dividend_yield": 0.03
    }
    mock_s = MagicMock()
    mock_s.query.return_value.filter_by.return_value.first.return_value = None
    mock_session.return_value = mock_s

    result = get_cached_or_fetch("BBCA.JK")
    mock_fetch.assert_called_once_with("BBCA.JK")
    assert result["price"] == 9000

@patch("app.data.cache.fetch_stock_data")
@patch("app.data.cache.get_session")
def test_cache_hit_does_not_fetch(mock_session, mock_fetch):
    mock_s = MagicMock()
    mock_stock = MagicMock()
    mock_stock.kode = "BBCA.JK"
    mock_stock.last_updated = datetime.utcnow()
    mock_stock.sektor = "Perbankan"
    mock_stock.market_cap = 1e15
    mock_s.query.return_value.filter_by.return_value.first.return_value = mock_stock
    mock_session.return_value = mock_s

    result = get_cached_or_fetch("BBCA.JK")
    mock_fetch.assert_not_called()
    assert result["sector"] == "Perbankan"

@patch("app.data.cache.fetch_stock_data")
@patch("app.data.cache.get_session")
def test_fetch_error_returns_error(mock_session, mock_fetch):
    mock_fetch.return_value = {"kode": "BBCA.JK", "price": None, "error": "Network timeout", "prices_1y": MagicMock()}
    mock_s = MagicMock()
    mock_s.query.return_value.filter_by.return_value.first.return_value = None
    mock_session.return_value = mock_s

    result = get_cached_or_fetch("BBCA.JK")
    assert result["error"] == "Network timeout"
