from datetime import datetime, timedelta
from app.data.models import get_session, Stock
from app.data.fetcher import fetch_stock_data
from app.config import settings

def get_cached_or_fetch(kode: str, session=None) -> dict:
    """
    Cek cache di DB (tabel stocks). Jika TTL expired atau data kosong,
    fetch dari yfinance lalu simpan ke DB.
    Returns dict dari fetch_stock_data (sama shape).
    """
    own_session = False
    if session is None:
        session = get_session()
        own_session = True
    try:
        stock = session.query(Stock).filter_by(kode=kode).first()
        now = datetime.utcnow()
        ttl = timedelta(hours=settings.data_cache_ttl_hours)

        if stock and stock.last_updated and (now - stock.last_updated) < ttl:
            # Cache hit — return stored metadata without calling fetch_stock_data again
            return {
                "kode": kode,
                "price": None,
                "pe": None,
                "pbv": None,
                "roe": None,
                "debt_to_equity": None,
                "dividend_yield": None,
                "sector": stock.sektor,
                "market_cap": stock.market_cap,
                "prices_1y": None,
                "error": None,
            }

        # Cache miss or expired — fetch fresh
        data = fetch_stock_data(kode)
        if data.get("error") is None:
            # Upsert stock metadata
            if not stock:
                stock = Stock(kode=kode)
                session.add(stock)
            stock.nama = data.get("sector") or stock.nama or kode
            stock.sektor = data.get("sector")
            stock.market_cap = data.get("market_cap")
            stock.last_updated = now
            if own_session:
                session.commit()
        return data
    finally:
        if own_session:
            session.close()
