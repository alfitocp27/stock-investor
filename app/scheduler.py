from datetime import datetime
from app.config import settings
from app.data.cache import get_cached_or_fetch
from app.analyzer.scorer import score_stock
from app.data.models import ScanResult, Stock
from app.notify.telegram import check_and_notify

def run_full_scan(session) -> dict:
    results = []
    errors = []
    prev_results = {}
    for kode in settings.idx_watchlist:
        try:
            data = get_cached_or_fetch(kode, session=session)
            if data.get("error"):
                errors.append(f"{kode}: {data['error']}")
                continue
            sr = score_stock(data)
            # Upsert stock + attach to SR
            stock = session.query(Stock).filter_by(kode=kode).first()
            if not stock:
                stock = Stock(
                    kode=kode,
                    nama=data.get("nama") or data.get("sector") or kode,
                    sektor=data.get("sector"),
                    market_cap=data.get("market_cap")
                )
                session.add(stock)
                session.flush()
            else:
                if data.get("sector"):
                    stock.sektor = data.get("sector")
                if data.get("market_cap"):
                    stock.market_cap = data.get("market_cap")
                stock.last_updated = datetime.utcnow()

            sr.stock = stock
            sr.stock_id = stock.id
            session.add(sr)
            results.append(sr)
        except Exception as e:
            errors.append(f"{kode}: {e}")
    session.commit()
    alerts_sent = check_and_notify(session, results, prev_results)
    return {"scanned": len(results), "alerts_sent": alerts_sent, "errors": errors}
