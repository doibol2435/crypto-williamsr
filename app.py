### app.py
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from markupsafe import Markup
from signal_utils import fetch_ohlcv, calculate_williams_r, detect_signals
from telegram_utils import send_telegram_message
from dotenv import load_dotenv
import threading
import time
import os
import csv
import requests
import plotly.graph_objs as go

load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "PEPEUSDT", "TURBOUSDT", "WIFUSDT",
    "BONKUSDT", "BONEUSDT", "FLOKIUSDT", "SHIBUSDT", "SOLUSDT", "NEARUSDT",
    "FTMUSDT", "ATOMUSDT", "ALGOUSDT", "ETCUSDT", "EGLDUSDT", "KAVAUSDT",
    "OPUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT",
    "LTCUSDT", "UNIUSDT", "AAVEUSDT", "SUSHIUSDT", "COMPUSDT", "CRVUSDT",
    "SNXUSDT", "YFIUSDT", "1INCHUSDT", "KNCUSDT", "KSMUSDT"
]
INTERVAL = "1h"
latest_signals = {}

def log_signal_to_file(symbol, signal):
    with open("signals.log", "a") as f:
        line = f"{symbol},{signal['signal']},{signal['entry']},{signal['tp']},{signal['sl']},{signal['williams_r']},{time.strftime('%Y-%m-%d %H:%M')},waiting\n"
        f.write(line)

def scan_all_coins():
    global latest_signals
    while True:
        temp_signals = {}
        for symbol in COINS:
            try:
                df = fetch_ohlcv(symbol, interval=INTERVAL)
                if df.empty or len(df) < 30:
                    print(f"⚠️ Dữ liệu trống hoặc thiếu cho {symbol}, bỏ qua")
                    continue

                df = calculate_williams_r(df)
                signal = detect_signals(df)
                temp_signals[symbol] = signal

                if signal["signal"]:
                    message = (
                        f"\U0001F4CA <b>Tín hiệu {signal['signal']}</b>\n"
                        f"Coin: {symbol}\n"
                        f"%R: {signal['williams_r']}\n"
                        f"Entry: {signal['entry']}\n"
                        f"TP: {signal['tp']}\n"
                        f"SL: {signal['sl']}"
                    )
                    send_telegram_message(message)
                    log_signal_to_file(symbol, signal)
            except Exception as e:
                print(f"Lỗi xử lý {symbol}: {e}")

        latest_signals = temp_signals
        socketio.emit("update_signals", latest_signals)
        time.sleep(60)

def get_current_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        res = requests.get(url, timeout=5).json()
        return float(res["price"])
    except:
        return None

def check_signals_status():
    while True:
        if not os.path.exists("signals.log"):
            time.sleep(120)
            continue

        updated_rows = []
        changed = False

        with open("signals.log", "r") as f:
            rows = f.readlines()

        for row in rows:
            parts = row.strip().split(",")
            if len(parts) < 8:
                continue

            symbol, signal, entry, tp, sl, willr, time_str, status = parts

            if status == "waiting":
                current_price = get_current_price(symbol)
                if current_price:
                    if signal == "Long" and (current_price >= float(tp)):
                        status = "hit"
                        changed = True
                    elif signal == "Long" and (current_price <= float(sl)):
                        status = "fail"
                        changed = True
                    elif signal == "Short" and (current_price <= float(tp)):
                        status = "hit"
                        changed = True
                    elif signal == "Short" and (current_price >= float(sl)):
                        status = "fail"
                        changed = True

            updated_row = ",".join([symbol, signal, entry, tp, sl, willr, time_str, status])
            updated_rows.append(updated_row)

        if changed:
            with open("signals.log", "w") as f:
                for line in updated_rows:
                    f.write(line + "\n")

        time.sleep(120)

@app.route("/")
def index():
    return render_template("index.html", signals=latest_signals)

@app.route("/stats")
def stats():
    rows = []
    if os.path.exists("signals.log"):
        with open("signals.log", "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 8:
                    rows.append({
                        "symbol": row[0], "signal": row[1], "entry": row[2], "tp": row[3],
                        "sl": row[4], "williams_r": row[5], "time": row[6], "status": row[7]
                    })
    return render_template("stats.html", rows=rows[::-1])

@app.route("/pnl")
def pnl_chart():
    if not os.path.exists("signals.log"):
        return "No signal data."

    pnl_list = []
    times = []
    equity = 100

    with open("signals.log", "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 8:
                continue
            symbol, signal, entry, tp, sl, willr, time_str, status = parts
            if status == "hit": pnl = 2
            elif status == "fail": pnl = -2
            else: continue
            equity *= (1 + pnl / 100)
            pnl_list.append(round(equity, 2))
            times.append(time_str)

    trace = go.Scatter(x=times, y=pnl_list, mode="lines+markers", name="Equity")
    layout = go.Layout(title="\U0001F4C8 Lịch sử tăng trưởng vốn", xaxis_title="Thời gian", yaxis_title="Vốn")
    fig = go.Figure(data=[trace], layout=layout)
    return f"<h2>\U0001F4C8 Lịch sử tăng trưởng vốn</h2>{Markup(fig.to_html(full_html=False))}"

@socketio.on("connect")
def handle_connect():
    emit("update_signals", latest_signals)

def start_background_thread():
    threading.Thread(target=scan_all_coins, daemon=True).start()
    threading.Thread(target=check_signals_status, daemon=True).start()

start_background_thread()
gunicorn_app = app
