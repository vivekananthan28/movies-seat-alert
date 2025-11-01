import os
from dotenv import load_dotenv

load_dotenv()

BASE = "https://www.district.in/gw"
CITY_ID = 7
CITY_KEY = os.getenv("CITY_KEY", "chennai")
LAT = float(os.getenv("LAT", 12.94063577797741))
LNG = float(os.getenv("LNG", 80.23532394691959))

PRICE_LIMIT = float(os.getenv("PRICE_LIMIT", 60))
CHECK_INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MIN", 5))

# Your tokens
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Add the required cookies and headers (fill from your curl)
HEADERS = {
    "accept": "*/*",
    "api_source": "district",
    "x-app-type": "ed_web",
    "user-agent": "Mozilla/5.0",
    "x-is-movies-supported": "true",
    "x-user-lat": str(LAT),
    "x-user-lng": str(LNG),
}

COOKIES = {
    "x-access-token": os.getenv("X_ACCESS_TOKEN"),
    "x-device-id": os.getenv("X_DEVICE_ID"),
}
