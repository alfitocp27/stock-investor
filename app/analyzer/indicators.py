import pandas as pd
import numpy as np

def calculate_indicators(prices_df: pd.DataFrame) -> dict:
    """
    Hitung indikator teknikal dari DataFrame harga historis.
    Memerlukan kolom 'Close' (opsional High, Low, Volume).
    Returns dict dengan RSI, MACD signal, trend, volume ratio, ATR, volatility.
    """
    if prices_df is None or prices_df.empty or len(prices_df) < 30:
        return {
            "rsi": None,
            "macd_signal": "NEUTRAL",
            "trend": "SIDEWAYS",
            "volume_avg_ratio": None,
            "atr": None,
            "volatility_30d": None,
        }

    close = prices_df["Close"]
    high = prices_df.get("High", close)
    low = prices_df.get("Low", close)
    volume = prices_df.get("Volume", pd.Series(0, index=close.index))

    # --- RSI(14) ---
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_vals = 100 - (100 / (1 + rs))
    rsi_val = float(rsi_vals.iloc[-1]) if not rsi_vals.isna().iloc[-1] else 50.0
    rsi_val = max(0.0, min(100.0, rsi_val))

    # --- MACD(12,26,9) ---
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9).mean()
    if len(macd_line) < 2 or len(signal_line) < 2:
        macd_signal = "NEUTRAL"
    elif macd_line.iloc[-1] > signal_line.iloc[-1]:
        macd_signal = "BUY"
    else:
        macd_signal = "SELL"

    # --- Trend (MA crossover) ---
    if len(close) >= 50:
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        if not (ma20.isna().iloc[-1] or ma50.isna().iloc[-1]):
            if close.iloc[-1] > ma20.iloc[-1] > ma50.iloc[-1]:
                trend = "BULL"
            elif close.iloc[-1] < ma20.iloc[-1] < ma50.iloc[-1]:
                trend = "BEAR"
            else:
                trend = "SIDEWAYS"
        else:
            trend = "SIDEWAYS"
    elif len(close) >= 20:
        ma20 = close.rolling(20).mean()
        if not ma20.isna().iloc[-1]:
            if close.iloc[-1] > ma20.iloc[-1]:
                trend = "BULL"
            elif close.iloc[-1] < ma20.iloc[-1]:
                trend = "BEAR"
            else:
                trend = "SIDEWAYS"
        else:
            trend = "SIDEWAYS"
    else:
        trend = "SIDEWAYS"

    # --- Volume ratio ---
    vol_avg_20 = volume.rolling(20).mean()
    vol_today = volume.iloc[-1]
    vol_avg_val = float(vol_avg_20.iloc[-1]) if not vol_avg_20.isna().iloc[-1] else 1.0
    volume_avg_ratio = float(vol_today / max(vol_avg_val, 1))

    # --- ATR(14) ---
    if len(high) >= 14:
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr_val = tr.rolling(14).mean().iloc[-1]
        atr = float(atr_val) if not np.isnan(atr_val) else None
    else:
        atr = None

    # --- Volatility 30d ---
    if len(close) >= 30:
        returns = close.pct_change().rolling(30).std()
        vol = float(returns.iloc[-1]) if not returns.isna().iloc[-1] else 0.0
    else:
        vol = 0.0

    return {
        "rsi": rsi_val,
        "macd_signal": macd_signal,
        "trend": trend,
        "volume_avg_ratio": volume_avg_ratio,
        "atr": atr,
        "volatility_30d": vol,
    }
