from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from signal_utils import fetch_ohlcv, calculate_williams_r, detect_signals
from telegram_utils import send_telegram_message
from dotenv import load_dotenv
import threading
import time
import os

load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

COINS = ["BTCUSDT","ETHUSDT","BNBUSDT","PEPEUSDT","TURBOUSDT","WIFUSDT","BONKUSDT","BONEUSDT","FLOKIUSDT","SHIBUSDT","SOLUSDT","NEARUSDT","FTMUSDT","ATOMUSDT","ALGOUSDT","ETCUSDT","EGLDUSDT","KAVAUSDT","OPUSDT","ADAUSDT","XRPUSDT","DOGEUSDT","DOTUSDT","AVAXUSDT","LTCUSDT","UNIUSDT","AAVEUSDT","SUSHIUSDT","COMPUSDT","CRVUSDT","SNXUSDT","YFIUSDT","1INCHUSDT","KNCUSDT","NEARUSDT","FTMUSDT","ATOMUSDT","ALGOUSDT","KAVAUSDT","KSMUSDT","OPUSDT"]
INTERVAL = "1h"
latest_signals = {}

def scan_all_coins():
    global latest_signals
    while True:
        temp_signals = {}
        for symbol in COINS:
            try:
                df = fetch_ohlcv(symbol, interval=INTERVAL)
                df = calculate_williams_r(df)
                signal = detect_signals(df)
                temp_signals[symbol] = signal

                if signal["signal"]:
                    message = (
                        f"📊 <b>Tín hiệu {signal['signal']}</b>\n"
                        f"Coin: {symbol}\n"
                        f"%R: {signal['williams_r']}\n"
                        f"Entry: {signal['entry']}\n"
                        f"TP: {signal['tp']}\n"
                        f"SL: {signal['sl']}"
                    )
                    send_telegram_message(message)
            except Exception as e:
                print(f"Lỗi xử lý {symbol}: {e}")

        latest_signals = temp_signals
        socketio.emit("update_signals", latest_signals)
        time.sleep(60)

@app.route("/")
def index():
    return render_template("index.html", signals=latest_signals)

@socketio.on("connect")
def handle_connect():
    emit("update_signals", latest_signals)

# === Dùng background thread + Gunicorn ===
def start_background_thread():
    thread = threading.Thread(target=scan_all_coins, daemon=True)
    thread.start()

start_background_thread()

# Cho gunicorn sử dụng
gunicorn_app = app
