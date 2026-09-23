import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import joinedload
from app.data.cache import get_cached_or_fetch
from app.data.fetcher import fetch_stock_data
from app.data.models import get_session, Stock, ScanResult
from app.risk.allocator import allocate_portfolio
import numpy as np


def _clean_float(v):
    """Convert a numpy scalar to a JSON-safe float, or None when missing."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if np.isnan(f) or np.isinf(f):
        return None
    return f

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

router = APIRouter()

@router.get("/")
async def root():
    return RedirectResponse("/dashboard")

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session = get_session()
    try:
        latest = session.query(ScanResult).options(joinedload(ScanResult.stock)).order_by(ScanResult.timestamp.desc()).limit(50).all()
        stocks_data = [
            {
                "kode": r.stock.kode if r.stock else "N/A",
                "nama": r.stock.nama if r.stock else "N/A",
                "skor": r.skor_total,
                "risk": r.risk_rating,
                "trend": r.trend,
                "macd": r.macd_signal,
                "harga": r.price,
                "rsi": r.rsi,
            }
            for r in latest
        ]
        alloc = allocate_portfolio(latest)
        try:
            return templates.TemplateResponse(request=request, name="dashboard.html", context={"stocks": stocks_data, "alloc": alloc})
        except Exception:
            # Fallback if dashboard.html not yet created (Task 11)
            html = f"<html><body><h1>Dashboard</h1><pre>{stocks_data}</pre></body></html>"
            return HTMLResponse(content=html)
    finally:
        session.close()

@router.get("/saham/{kode}", response_class=HTMLResponse)
async def stock_detail(kode: str, request: Request):
    session = get_session()
    try:
        stock = session.query(Stock).filter_by(kode=kode).first()
        if not stock:
            raise HTTPException(404, "Saham tidak ditemukan")
        latest = session.query(ScanResult).filter_by(stock_id=stock.id).order_by(ScanResult.timestamp.desc()).first()
        try:
            return templates.TemplateResponse(request=request, name="stock_detail.html", context={"stock": stock, "scan": latest})
        except Exception:
            html = f"<html><body><h1>Stock Detail: {kode}</h1></body></html>"
            return HTMLResponse(content=html)
    finally:
        session.close()

@router.get("/portofolio", response_class=HTMLResponse)
async def portfolio_page(request: Request):
    session = get_session()
    try:
        latest = session.query(ScanResult).options(joinedload(ScanResult.stock)).order_by(ScanResult.timestamp.desc()).limit(50).all()
        alloc = allocate_portfolio(latest)
        try:
            return templates.TemplateResponse(request=request, name="portfolio.html", context={"alloc": alloc})
        except Exception:
            html = f"<html><body><h1>Portfolio</h1><pre>{alloc}</pre></body></html>"
            return HTMLResponse(content=html)
    finally:
        session.close()

@router.get("/api/chart/{kode}")
async def api_chart(kode: str):
    """Data seri harga + indikator (MA20, MA50, RSI) untuk chart interaktif realtime."""
    session = get_session()
    try:
        data = get_cached_or_fetch(kode, session=session)
    finally:
        session.close()

    prices_1y = data.get("prices_1y")

    if prices_1y is None or getattr(prices_1y, "empty", True) or "Close" not in prices_1y.columns:
        # Cache hits return metadata only (prices_1y is not persisted), so
        # refetch to obtain the actual price series for the chart.
        if data.get("error") is None:
            data = fetch_stock_data(kode)
            prices_1y = data.get("prices_1y")

    if prices_1y is None or getattr(prices_1y, "empty", True) or "Close" not in prices_1y.columns:
        return {
            "kode": data.get("kode") or kode,
            "timestamps": [],
            "prices": [],
            "rsi": [],
            "ma20": [],
            "ma50": [],
        }

    close = prices_1y["Close"]

    # Simple-moving-average (SMA20 / SMA50)
    ma20 = close.rolling(20, min_periods=1).mean()
    ma50 = close.rolling(50, min_periods=1).mean()

    # RSI(14)
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    return {
        "kode": data.get("kode") or kode,
        "timestamps": [ts.strftime("%Y-%m-%d") for ts in prices_1y.index],
        "prices": [_clean_float(v) for v in close],
        "rsi": [_clean_float(v) for v in rsi],
        "ma20": [_clean_float(v) for v in ma20],
        "ma50": [_clean_float(v) for v in ma50],
    }


@router.post("/scan")
async def trigger_scan():
    session = get_session()
    try:
        try:
            import app.scheduler as scheduler_mod
            result = scheduler_mod.run_full_scan(session)
        except Exception as e:
            result = {"scanned": 0, "alerts_sent": 0, "errors": [str(e)]}
        return {"status": "ok", **result}
    finally:
        session.close()

@router.get("/api/stocks")
async def api_stocks():
    session = get_session()
    try:
        latest = session.query(ScanResult).options(joinedload(ScanResult.stock)).order_by(ScanResult.timestamp.desc()).limit(50).all()
        return [
            {
                "kode": r.stock.kode if r.stock else "N/A",
                "skor": r.skor_total,
                "risk": r.risk_rating,
                "trend": r.trend,
            }
            for r in latest
        ]
    finally:
        session.close()

@router.get("/api/portfolio")
async def api_portfolio():
    session = get_session()
    try:
        latest = session.query(ScanResult).options(joinedload(ScanResult.stock)).order_by(ScanResult.timestamp.desc()).limit(50).all()
        return allocate_portfolio(latest)
    finally:
        session.close()
