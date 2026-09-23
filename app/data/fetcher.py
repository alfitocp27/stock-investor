import yfinance as yf
import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_stock_data(kode: str, lookback_days: int = 365, interval: str = "1d") -> dict:
    """
    Ambil data saham IDX dari Yahoo Finance.
    Param `interval`: '1d', '1m', '5m', '15m', '60m' (untuk data menit/intraday realtime).
    """
    period_map = {
        "1m": "1d",
        "5m": "5d",
        "15m": "5d",
        "60m": "1mo",
        "1h": "1mo",
        "1d": f"{lookback_days}d",
        "1D": f"{lookback_days}d",
        "1Y": f"{lookback_days}d",
    }
    period = period_map.get(interval, f"{lookback_days}d")
    yf_interval = "1m" if interval == "1m" else ("5m" if interval == "5m" else ("15m" if interval == "15m" else ("60m" if interval in ("1h", "60m") else "1d")))

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
        ticker = yf.Ticker(kode)

        info = {}
        try:
            info = ticker.info or {}
        except Exception:
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
            hist = ticker.history(period=period, interval=yf_interval)
            result["prices_1y"] = hist
            if not hist.empty and result["price"] is None:
                result["price"] = float(hist["Close"].iloc[-1])
        except Exception:
            pass

        if result["price"] is not None and not result["prices_1y"].empty:
            return result
    except Exception as e:
        last_yf_error = str(e)
    else:
        last_yf_error = None

    # Fallback: direct Yahoo chart API (intraday interval supported)
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{kode}?range={period}&interval={yf_interval}"
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            chart_res = resp.json().get("chart", {}).get("result", [])
            if chart_res:
                meta = chart_res[0].get("meta", {})
                result["price"] = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")

                timestamps = chart_res[0].get("timestamp", [])
                indicators = chart_res[0].get("indicators", {}).get("quote", [{}])[0]
                if timestamps and indicators:
                    df = pd.DataFrame(indicators, index=pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Jakarta"))
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
