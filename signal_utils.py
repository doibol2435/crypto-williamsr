import pandas as pd
import requests

def fetch_ohlcv(symbol="BTCUSDT", interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url, timeout=5)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades", "taker_base", "taker_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

def calculate_williams_r(df, period=14):
    highest_high = df['high'].rolling(window=period).max()
    lowest_low = df['low'].rolling(window=period).min()
    df["williams_r"] = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
    return df

def detect_signals(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    signal = None
    entry = last["close"]
    willr_now = round(last["williams_r"], 2)
    willr_prev = round(prev["williams_r"], 2)

    volume_avg = df["volume"].rolling(window=20).mean().iloc[-1]
    volume_now = last["volume"]
    tp = sl = None

    # ==== Lọc tín hiệu LONG ====
    if (
        willr_now < -98 and
        willr_now > willr_prev and
        last["close"] > prev["close"] and
        volume_now > 1.2 * volume_avg
    ):
        signal = "Long"
        tp = entry * 1.02
        sl = entry * 0.98

    # ==== Lọc tín hiệu SHORT ====
    elif (
        willr_now > -2 and
        willr_now < willr_prev and
        last["close"] < prev["close"] and
        volume_now > 1.2 * volume_avg
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
import pandas as pd
import requests

def fetch_ohlcv(symbol="BTCUSDT", interval="1h", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url, timeout=5)
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "trades", "taker_base", "taker_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

def calculate_williams_r(df, period=14):
    highest_high = df['high'].rolling(window=period).max()
    lowest_low = df['low'].rolling(window=period).min()
    df["williams_r"] = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
    return df

def detect_signals(df):
    # ============== TÍNH BB + ATR ==============
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

    # ============== LẤY GIÁ TRỊ MỚI NHẤT ==============
    last = df.iloc[-1]
    prev = df.iloc[-2]

    willr_now = round(last["williams_r"], 2)
    willr_prev = round(prev["williams_r"], 2)
    entry = last["close"]
    volume_avg = df["volume"].rolling(window=20).mean().iloc[-1]
    volume_now = last["volume"]
    tp = sl = None
    signal = None

    ATR_MIN = last["atr"] * 0.7  # hoặc đặt ngưỡng cố định như 0.5 nếu muốn

    # ============== LỌC TÍN HIỆU LONG ==============
    if (
        willr_now < -98 and
        willr_now > willr_prev and
        last["close"] > prev["close"] and
        volume_now > 1.2 * volume_avg and
        last["close"] <= last["lower_band"] and
        last["atr"] > ATR_MIN
    ):
        signal = "Long"
        tp = entry * 1.02
        sl = entry * 0.98

    # ============== LỌC TÍN HIỆU SHORT ==============
    elif (
        willr_now > -2 and
        willr_now < willr_prev and
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
