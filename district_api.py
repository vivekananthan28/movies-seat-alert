import requests
from config import BASE, CITY_ID, CITY_KEY, LAT, LNG, HEADERS, COOKIES


def get_movies():
    url = f"{BASE}/web/get_discovery_results"
    body = {
        "location": {
            "city_id": CITY_ID,
            "user_lng": LNG,
            "user_lat": LAT,
            "gps_lng": LNG,
            "gps_lat": LAT,
        },
        "layout_type": "movies_home_v2",
        "request_type": "tab_switch",
    }
    r = requests.post(url, headers=HEADERS, cookies=COOKIES, json=body, timeout=15)
    j = r.json()
    movies = []

    def walk(obj):
        if isinstance(obj, dict):
            if "entity_id" in obj:
                name = (
                    obj.get("name")
                    or obj.get("title")
                    or obj.get("ItemDetails", {}).get("MovieData", {}).get("name")
                )
                if name:
                    movies.append((name, obj["entity_id"]))
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(j)
    return set(movies)


def get_theatre_sessions(content_id: int, date=None):
    url = f"{BASE}/consumer/movies/v5/movie"
    params = {
        "version": 3,
        "site_id": 1,
        "channel": "web",
        "child_site_id": 1,
        "platform": "district",
        "city_key": CITY_KEY,
        "content_id": content_id,
        "latitude": LAT,
        "longitude": LNG,
        "cinemaOrderLogic": 3,
    }
    if date:
        params["date"] = date
    r = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params, timeout=15)
    return r.json()


def get_seat_status(cinema_id: int, session_id: int, provider_id: int, content_id: int, moviecode: str):
    url = f"{BASE}/consumer/movies/v1/select-seat"
    body = {
        "cinemaId": cinema_id,
        "sessionId": session_id,
        "providerId": provider_id,
        "screenOnTop": True,
        "freeSeating": False,
        "screenFormat": "2D",
        "moviecode": moviecode,
        "config": {"socialDistancing": 1},
        "contentId": content_id,
    }
    r = requests.post(url, headers=HEADERS, cookies=COOKIES, json=body, timeout=15)
    return r.json()
