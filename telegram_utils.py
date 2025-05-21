import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ Thiếu cấu hình Telegram.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=payload, timeout=5)
        return response.ok
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")
        return False
