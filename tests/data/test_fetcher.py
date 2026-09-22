import pytest

@pytest.mark.network
def test_fetch_valid_stock_live():
    from app.data.fetcher import fetch_stock_data
    data = fetch_stock_data("BBCA.JK")
    assert data["error"] is None
    assert data["price"] is not None and data["price"] > 0

def test_fetch_invalid_stock_no_crash():
    from app.data.fetcher import fetch_stock_data
    data = fetch_stock_data("TIDAKADAKODE99.JK")
    # Should not raise; should set error
    assert "error" in data

def test_fetch_returns_expected_keys():
    from app.data.fetcher import fetch_stock_data
    data = fetch_stock_data("BBCA.JK")  # may hit network
    expected_keys = {"kode", "price", "pe", "pbv", "roe", "debt_to_equity",
                     "dividend_yield", "sector", "market_cap", "prices_1y", "error"}
    assert expected_keys.issubset(data.keys())
