from datetime import datetime
import pandas as pd
from app.analyzer.indicators import calculate_indicators
from app.analyzer.fundamental import calculate_fundamental_score
from app.data.models import ScanResult
from app.config import settings

def score_stock(data: dict) -> ScanResult:
    prices_df = data.get("prices_1y")
    if prices_df is None:
        prices_df = pd.DataFrame()
        
    tech = calculate_indicators(prices_df)

    fund_score, breakdown = calculate_fundamental_score(data)
    tech_score = tech["rsi"] if tech["rsi"] is not None else 50.0  # default 50 if no RSI

    # Normalize technical to 0-100 (RSI already is)
    # MACD: BUY = +15 bonus, SELL = -15 penalty
    macd_bonus = {"BUY": 15, "SELL": -15, "NEUTRAL": 0}.get(tech["macd_signal"], 0)
    tech_score = max(0.0, min(100.0, float(tech_score + macd_bonus)))

    skor_total = settings.w_fundamental * fund_score + settings.w_technical * tech_score

    # Risk rating
    de = data.get("debt_to_equity")
    vol = tech.get("volatility_30d")
    pe = data.get("pe")
    roe = data.get("roe")

    de_val = de if de is not None else 0.0
    vol_val = vol if vol is not None else 0.0
    pe_val = pe if pe is not None else 0.0
    roe_val = roe if roe is not None else 0.0

    if de_val < 1.0 and vol_val < 0.02 and pe_val < 30 and roe_val > 0.05:
        risk_rating = "LOW"
    elif de_val > 2.0 or vol_val > 0.05 or roe_val < 0:
        risk_rating = "HIGH"
    else:
        risk_rating = "MEDIUM"

    return ScanResult(
        skor_total=round(skor_total, 2),
        skor_fundamental=round(fund_score, 2),
        skor_technical=round(tech_score, 2),
        risk_rating=risk_rating,
        price=data.get("price"),
        pe=data.get("pe"),
        pbv=data.get("pbv"),
        roe=data.get("roe"),
        debt_ratio=de,
        dividend_yield=data.get("dividend_yield"),
        rsi=tech.get("rsi"),
        macd_signal=tech["macd_signal"],
        trend=tech["trend"],
        timestamp=datetime.utcnow(),
    )
