from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.web.routes import router

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
