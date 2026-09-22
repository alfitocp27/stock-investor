import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import joinedload
from app.data.models import get_session, Stock, ScanResult
from app.risk.allocator import allocate_portfolio

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
