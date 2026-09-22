import yfinance as yf
import pandas as pd

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_stock_data(kode: str, lookback_days: int = 365) -> dict:
    """
    Ambil data saham IDX dari Yahoo Finance.
    Returns dict with fundamental + price history. Handles 429/crumb rate limits gracefully.
    """
    result = {
        "kode": kode,
        "price": None,
        "pe": None,
        "pbv": None,
        "roe": None,
        "debt_to_equity": None,
        "dividend_yield": None,
        "sector": None,
        "market_cap": None,
        "prices_1y": pd.DataFrame(),
        "error": None,
    }

    # Try the pinned yfinance stack first (uses curl_cffi TLS fingerprinting,
    # which is currently the only reliable way past Yahoo's rate limits).
    try:
        ticker = yf.Ticker(kode)

        info = {}
        try:
            info = ticker.info or {}
        except Exception:
            # yfinance quoteSummary endpoints fail frequently on 429 / crumb errors
            pass

        result["price"] = info.get("currentPrice") or info.get("previousClose")
        result["pe"] = info.get("trailingPE")
        result["pbv"] = info.get("priceToBook")
        result["roe"] = info.get("returnOnEquity")
        result["debt_to_equity"] = info.get("debtToEquity")
        result["dividend_yield"] = info.get("dividendYield")
        result["sector"] = info.get("sector")
        result["market_cap"] = info.get("marketCap")

        try:
            hist = ticker.history(period=f"{lookback_days}d")
            result["prices_1y"] = hist
            if not hist.empty and result["price"] is None:
                result["price"] = float(hist["Close"].iloc[-1])
        except Exception:
            pass

        if result["price"] is not None:
            return result
    except Exception as e:
        last_yf_error = str(e)
    else:
        last_yf_error = None

    # Fallback: direct Yahoo chart API (public, no crumb required).
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{kode}?range=1y&interval=1d"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            chart_res = resp.json().get("chart", {}).get("result", [])
            if chart_res:
                meta = chart_res[0].get("meta", {})
                result["price"] = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")

                timestamps = chart_res[0].get("timestamp", [])
                indicators = chart_res[0].get("indicators", {}).get("quote", [{}])[0]
                if timestamps and indicators:
                    df = pd.DataFrame(indicators, index=pd.to_datetime(timestamps, unit="s"))
                    df.rename(
                        columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"},
                        inplace=True,
                    )
                    result["prices_1y"] = df
    except Exception as chart_err:
        last_yf_error = last_yf_error or str(chart_err)

    if result["price"] is None:
        result["error"] = last_yf_error or f"No price data for {kode}"
    return result
