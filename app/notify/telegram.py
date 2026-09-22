import httpx
from app.data.models import Alert

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    if not token or not chat_id:
        return False
    url = TELEGRAM_API.format(token=token, chat_id=chat_id)
    try:
        r = httpx.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
        return r.status_code == 200
    except Exception:
        return False

def check_and_notify(session, scan_results: list, prev_results: dict = None) -> int:
    from app.notify.rules import should_send_alert, build_message
    from app.config import settings
    sent = 0
    prev_results = prev_results or {}
    for sr in scan_results:
        stock = sr.stock
        if not stock:
            continue
        # Score threshold alert
        prev = prev_results.get(stock.kode, {}).get("skor_total", 0)
        if sr.skor_total >= settings.threshold_naik_alert and prev < settings.threshold_naik_alert:
            if should_send_alert(session, stock, "SCORE_ABOVE_THRESHOLD", sr):
                msg = build_message(stock, sr, "SCORE_ABOVE_THRESHOLD", prev)
                if send_telegram_message(settings.telegram_token, settings.telegram_chat_id, msg):
                    session.add(Alert(stock_id=stock.id, alert_type="SCORE_ABOVE_THRESHOLD", message=msg))
                    sent += 1
        # Buy signal
        if sr.macd_signal == "BUY" and (sr.rsi or 0) < 70:
            if should_send_alert(session, stock, "BUY_SIGNAL", sr):
                msg = build_message(stock, sr, "BUY_SIGNAL")
                if send_telegram_message(settings.telegram_token, settings.telegram_chat_id, msg):
                    session.add(Alert(stock_id=stock.id, alert_type="BUY_SIGNAL", message=msg))
                    sent += 1
        # Risk warning for portfolio holdings
        if sr.risk_rating == "HIGH":
            from app.data.models import PortfolioAllocation
            holding = session.query(PortfolioAllocation).filter(
                PortfolioAllocation.stock_id == stock.id,
                PortfolioAllocation.status == "ACTIVE"
            ).first()
            if holding and should_send_alert(session, stock, "RISK_WARNING", sr):
                msg = build_message(stock, sr, "RISK_WARNING")
                if send_telegram_message(settings.telegram_token, settings.telegram_chat_id, msg):
                    session.add(Alert(stock_id=stock.id, alert_type="RISK_WARNING", message=msg))
                    sent += 1
    session.commit()
    return sent
