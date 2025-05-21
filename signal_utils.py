import pandas as pd
import requests

def fetch_ohlcv(symbol="BTCUSDT", interval="1h", limit=100):
    # Mapping interval to Bitget's format
    interval_map = {
        "1m": "Min1", "5m": "Min5", "15m": "Min15", "30m": "Min30",
        "1h": "H1", "4h": "H4", "1d": "D1"
    }
    bg_interval = interval_map.get(interval, "H1")
    bg_symbol = symbol.replace("USDT", "_USDTSPBL")
    url = f"https://api.bitget.com/api/spot/v1/market/candles?symbol={bg_symbol}&period={bg_interval}&limit={limit}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        candles = data.get("data", [])
        if not candles:
            return pd.DataFrame()

        df = pd.DataFrame(candles, columns=["time", "open", "high", "low", "close", "volume"])
        df = df.iloc[::-1]  # reverse to ascending
        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df.reset_index(drop=True)
    except Exception as e:
        print(f"Lỗi khi lấy dữ liệu từ Bitget: {e}")
        return pd.DataFrame()

def calculate_williams_r(df, period=14):
    if df.empty or len(df) < period:
        df["williams_r"] = None
        return df
    highest_high = df['high'].rolling(window=period).max()
    lowest_low = df['low'].rolling(window=period).min()
    df["williams_r"] = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
    return df

def detect_signals(df):
    df = df.dropna().copy()
    if df.empty or len(df) < 30:
        return {"signal": None, "entry": None, "tp": None, "sl": None, "williams_r": None}

    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    df["ma20"] = df["typical_price"].rolling(window=20).mean()
    df["stddev"] = df["typical_price"].rolling(window=20).std()
    df["upper_band"] = df["ma20"] + 2 * df["stddev"]
    df["lower_band"] = df["ma20"] - 2 * df["stddev"]

    df["high_low"] = df["high"] - df["low"]
    df["high_close_prev"] = abs(df["high"] - df["close"].shift(1))
    df["low_close_prev"] = abs(df["low"] - df["close"].shift(1))
    df["tr"] = df[["high_low", "high_close_prev", "low_close_prev"]].max(axis=1)
    df["atr"] = df["tr"].rolling(window=14).mean()

    try:
        last = df.iloc[-1]
        prev = df.iloc[-2]
    except IndexError:
        return {"signal": None, "entry": None, "tp": None, "sl": None, "williams_r": None}

    willr_now = round(last["williams_r"], 2) if pd.notnull(last["williams_r"]) else None
    willr_prev = round(prev["williams_r"], 2) if pd.notnull(prev["williams_r"]) else None
    entry = last["close"]
    volume_avg = df["volume"].rolling(window=20).mean().iloc[-1]
    volume_now = last["volume"]
    tp = sl = None
    signal = None
    ATR_MIN = last["atr"] * 0.7 if pd.notnull(last["atr"]) else 0

    if (
        willr_now is not None and willr_prev is not None and
        willr_now < -98 and willr_now > willr_prev and
        last["close"] > prev["close"] and
        volume_now > 1.2 * volume_avg and
        last["close"] <= last["lower_band"] and
        last["atr"] > ATR_MIN
    ):
        signal = "Long"
        tp = entry * 1.02
        sl = entry * 0.98

    elif (
        willr_now is not None and willr_prev is not None and
        willr_now > -2 and willr_now < willr_prev and
        last["close"] < prev["close"] and
        volume_now > 1.2 * volume_avg and
        last["close"] >= last["upper_band"] and
        last["atr"] > ATR_MIN
    ):
        signal = "Short"
        tp = entry * 0.98
        sl = entry * 1.02

    return {
        "signal": signal,
        "entry": round(entry, 2) if signal else None,
        "tp": round(tp, 2) if signal else None,
        "sl": round(sl, 2) if signal else None,
        "williams_r": willr_now
    }
