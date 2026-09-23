from datetime import datetime, timedelta
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.web.routes import router


def _synthetic_prices(rows: int = 80) -> pd.DataFrame:
    """Deterministic 1-year price history with a Close column and date index."""
    idx = pd.date_range("2025-01-01", periods=rows, freq="B")
    rng = np.random.default_rng(42)
    close = 9000.0 + np.cumsum(rng.normal(0, 50, rows))
    return pd.DataFrame({"Close": close}, index=idx)


def test_root_redirects():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, follow_redirects=False)
    r = client.get("/")
    assert r.status_code == 307 or r.status_code == 302

def test_dashboard_status_200():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/dashboard")
    assert r.status_code == 200

def test_api_stocks_status_200():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/stocks")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_api_portfolio_status_200():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/portfolio")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@patch("app.web.routes.get_cached_or_fetch")
def test_api_chart_status_200(mock_gcof):
    """GET /api/chart/{kode} returns JSON series for the realtime chart."""
    mock_gcof.return_value = {
        "kode": "BBCA.JK",
        "price": 9000.0,
        "error": None,
        "prices_1y": _synthetic_prices(80),
    }

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/chart/BBCA.JK")

    assert r.status_code == 200
    payload = r.json()
    assert set(payload.keys()) == {
        "kode", "timestamps", "prices", "rsi", "ma20", "ma50",
    }
    assert payload["kode"] == "BBCA.JK"
    for key in ("timestamps", "prices", "rsi", "ma20", "ma50"):
        assert isinstance(payload[key], list), f"{key} must be a list"
        assert len(payload[key]) == 80, f"{key} must align with the price history"

    # Timestamps render as YYYY-MM-DD strings, values as floats or nulls.
    assert all(isinstance(t, str) for t in payload["timestamps"])
    assert payload["timestamps"][0] == "2025-01-01"
    for key in ("prices", "rsi", "ma20", "ma50"):
        assert all(v is None or isinstance(v, float) for v in payload[key])

    # Indicators are attached where enough history exists.
    assert payload["ma20"][19] is not None
    assert payload["ma50"][49] is not None
    assert payload["rsi"][-1] is not None

    mock_gcof.assert_called_once()
    assert mock_gcof.call_args.args[0] == "BBCA.JK"


@patch("app.web.routes.get_cached_or_fetch")
def test_api_chart_no_price_data_returns_empty_series(mock_gcof):
    """A fetch error or missing history yields 200 with empty aligned series."""
    mock_gcof.return_value = {
        "kode": "UNKNOWN.JK",
        "price": None,
        "error": "No price data for UNKNOWN.JK",
        "prices_1y": pd.DataFrame(),
    }

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/chart/UNKNOWN.JK")

    assert r.status_code == 200
    payload = r.json()
    assert payload["kode"] == "UNKNOWN.JK"
    for key in ("timestamps", "prices", "rsi", "ma20", "ma50"):
        assert payload[key] == []


@patch("app.web.routes.fetch_stock_data")
@patch("app.web.routes.get_cached_or_fetch")
def test_api_chart_refetches_when_cache_hit_omits_prices(mock_gcof, mock_fetch):
    """Cache hits return metadata only (price is None and prices_1y is None); refetch so the chart renders."""
    mock_gcof.return_value = {
        "kode": "BBCA.JK",
        "price": None,
        "error": None,
        "prices_1y": None,
    }
    mock_fetch.return_value = {
        "kode": "BBCA.JK",
        "price": 9000.0,
        "error": None,
        "prices_1y": _synthetic_prices(80),
    }

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    r = client.get("/api/chart/BBCA.JK")

    assert r.status_code == 200
    payload = r.json()
    assert payload["kode"] == "BBCA.JK"
    assert len(payload["prices"]) == 80
    assert payload["ma50"][49] is not None
    mock_fetch.assert_called_once_with("BBCA.JK")
