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
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        ticker = yf.Ticker(kode, session=session)
        
        info = {}
        try:
            info = ticker.info or {}
        except Exception as info_err:
            # yfinance quoteSummary endpoints fail frequently on 429 / Crumb errors
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
        except Exception as hist_err:
            pass

        # Fallback to direct chart API if ticker.info / ticker.history hit 429 rate-limit
        if result["price"] is None:
            try:
                url = f"https://query2.finance.yahoo.com/v8/finance/chart/{kode}?range=1y&interval=1d"
                resp = session.get(url, timeout=10)
                if resp.status_code == 200:
                    chart_data = resp.json()
                    chart_res = chart_data.get("chart", {}).get("result", [])
                    if chart_res:
                        meta = chart_res[0].get("meta", {})
                        result["price"] = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
                        
                        timestamps = chart_res[0].get("timestamp", [])
                        indicators = chart_res[0].get("indicators", {}).get("quote", [{}])[0]
                        if timestamps and indicators:
                            df = pd.DataFrame(indicators, index=pd.to_datetime(timestamps, unit='s'))
                            df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
                            result["prices_1y"] = df
            except Exception as chart_err:
                pass

        if result["price"] is None:
            result["error"] = f"Unable to fetch price data for {kode}"
    except Exception as e:
        result["error"] = str(e)
    return result
