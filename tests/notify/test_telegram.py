from unittest.mock import patch, MagicMock
from app.notify.telegram import check_and_notify, send_telegram_message

@patch("app.notify.telegram.send_telegram_message")
def test_dedup_blocks_repeat(mock_send):
    mock_send.return_value = True
    from app.data.models import Stock, Alert
    mock_session = MagicMock()
    mock_stock = MagicMock(); mock_stock.id = 1; mock_stock.kode = "BBCA.JK"
    mock_sr = MagicMock(); mock_sr.stock = mock_stock; mock_sr.skor_total = 70
    mock_sr.risk_rating = "LOW"; mock_sr.macd_signal = "NEUTRAL"; mock_sr.rsi = 55; mock_sr.price = 9000
    
    # Existing alert in last 24h
    mock_session.query.return_value.filter.return_value.first.return_value = MagicMock()
    result = check_and_notify(mock_session, [mock_sr], {})
    assert result == 0
    assert not mock_send.called

def test_send_telegram_empty_credentials_returns_false():
    res = send_telegram_message("", "", "test")
    assert res is False
