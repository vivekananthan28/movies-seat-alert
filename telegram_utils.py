import requests
import json
from config import TELEGRAM_BOT_TOKEN

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
CHAT_FILE = "chat_ids.json"  # local file to store user chat IDs


def save_chat_id(chat_id: int, chat_name: str = ""):
    """Store chat ID and name locally for alerts"""
    try:
        chat_data = load_chat_ids()

        # ensure consistent structure: list of dicts
        if not isinstance(chat_data, list):
            chat_data = []

        # check if user already exists
        if any(item["id"] == chat_id for item in chat_data):
            return  # already saved

        chat_data.append({"id": chat_id, "name": chat_name or "Unknown"})
        with open(CHAT_FILE, "w") as f:
            json.dump(chat_data, f, indent=2)

        print(f"✅ Added new chat: {chat_id} ({chat_name or chat_id})")

    except Exception as e:
        print("⚠️ Error saving chat ID:", e)


def load_chat_ids() -> list[dict]:
    """Load saved chat info list: [{'id': 123, 'name': 'Vivek'}, ...]"""
    try:
        with open(CHAT_FILE, "r") as f:
            content = f.read().strip()
            if not content:  # empty file
                return []
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def telegram_alert(message: str, chat_id: int):
    """Send alert to all saved Telegram chat IDs"""
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        response = requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to send to {chat_id}: {response.text}")
    except Exception as e:
        print(f"⚠️ Telegram error for {chat_id}:", e)
