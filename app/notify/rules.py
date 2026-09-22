from datetime import datetime, timedelta
from app.config import settings

def should_send_alert(session, stock, alert_type, scan_result) -> bool:
    """Check dedup: skip if same stock+type sent in last 24h."""
    from app.data.models import Alert
    cutoff = datetime.utcnow() - timedelta(hours=24)
    existing = session.query(Alert).filter(
        Alert.stock_id == stock.id,
        Alert.alert_type == alert_type,
        Alert.sent_at > cutoff
    ).first()
    return existing is None

def build_message(stock, scan_result, alert_type, prev_score=None) -> str:
    emoji = {"SCORE_ABOVE_THRESHOLD": "📈", "BUY_SIGNAL": "💡", "RISK_WARNING": "⚠️"}.get(alert_type, "📊")
    trend = f"↑ dari {prev_score:.0f}" if prev_score else ""
    price_str = f"Rp {scan_result.price:,.0f}" if getattr(scan_result, "price", None) else "N/A"
    rsi_val = getattr(scan_result, "rsi", None)
    rsi_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
    
    msg = f"""{emoji} *{stock.kode}* — {alert_type.replace("_", " ").title()} {trend}
Skor: {scan_result.skor_total}/100 | Risk: {scan_result.risk_rating}
Harga: {price_str}
RSI: {rsi_str} | MACD: {scan_result.macd_signal}
Trend: {scan_result.trend}"""
    return msg
