import os
from fastapi import APIRouter, Request, HTTPException, Query
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
        stocks_data = []
        for r in latest:
            kode = r.stock.kode if r.stock else "N/A"
            stocks_data.append({
                "kode": kode,
                "nama": r.stock.nama if r.stock else "N/A",
                "skor": r.skor_total,
                "risk": r.risk_rating,
                "trend": r.trend,
                "macd": r.macd_signal,
                "harga": r.price,
                "rsi": r.rsi,
            })
        alloc = allocate_portfolio(latest)
        total_dana = sum(a["alokasi_rp"] for a in alloc)
        try:
            return templates.TemplateResponse(request=request, name="dashboard.html", context={"stocks": stocks_data, "alloc": alloc, "total_alokasi": total_dana})
        except Exception:
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
async def api_chart(kode: str, timeframe: str = Query("1D")):
    """
    Data seri harga + indikator (MA20, MA50, RSI) untuk chart interaktif realtime.
    Dukungan timeframe intraday menit (1m, 5m, 15m, 1h) dan harian (1D, 1W, 1Y).
    """
    if timeframe in ("1m", "5m", "15m", "1h"):
        data = fetch_stock_data(kode, interval=timeframe)
        prices_1y = data.get("prices_1y")
    else:
        session = get_session()
        try:
            data = get_cached_or_fetch(kode, session=session)
        finally:
            session.close()

        prices_1y = data.get("prices_1y")
        if prices_1y is None or getattr(prices_1y, "empty", True) or "Close" not in prices_1y.columns:
            if data.get("error") is None:
                data = fetch_stock_data(kode, interval="1d")
                prices_1y = data.get("prices_1y")

    if prices_1y is None or getattr(prices_1y, "empty", True) or "Close" not in prices_1y.columns:
        return {
            "kode": data.get("kode") or kode,
            "timeframe": timeframe,
            "timestamps": [],
            "prices": [],
            "rsi": [],
            "ma20": [],
            "ma50": [],
        }

    close = prices_1y["Close"]

    # Slice data based on timeframe requested
    limit_map = {
        "1m": 10,
        "5m": 25,
        "15m": 40,
        "1h": 60,
        "1D": 90,
        "1W": 180,
        "1Y": len(close)
    }
    limit = limit_map.get(timeframe, len(close))
    
    # Calculate indicators
    ma20 = close.rolling(20, min_periods=1).mean()
    ma50 = close.rolling(50, min_periods=1).mean()

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # Apply slice after indicators calculation
    sliced_index = prices_1y.index[-limit:]
    sliced_close = close.iloc[-limit:]
    sliced_rsi = rsi.iloc[-limit:]
    sliced_ma20 = ma20.iloc[-limit:]
    sliced_ma50 = ma50.iloc[-limit:]

    # Format timestamp depending on Intraday vs Daily
    formatted_ts = []
    for ts in sliced_index:
        try:
            formatted_ts.append(ts.strftime("%H:%M") if timeframe in ("1m", "5m", "15m", "1h") else ts.strftime("%Y-%m-%d"))
        except Exception:
            formatted_ts.append(str(ts))

    return {
        "kode": data.get("kode") or kode,
        "timeframe": timeframe,
        "timestamps": formatted_ts,
        "prices": [_clean_float(v) for v in sliced_close],
        "rsi": [_clean_float(v) for v in sliced_rsi],
        "ma20": [_clean_float(v) for v in sliced_ma20],
        "ma50": [_clean_float(v) for v in sliced_ma50],
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
