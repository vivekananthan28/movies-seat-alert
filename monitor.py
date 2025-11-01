import time
from datetime import datetime, timedelta
from district_api import get_movies, get_theatre_sessions, get_seat_status
from config import PRICE_LIMIT, CHECK_INTERVAL_MIN
from telegram_utils import telegram_alert
import html
import re


def monitor_seats(movie_name, theatre_name, date, chat_id):
    """Monitor specific movie & theatre for available ₹60 seats"""
    print(f"🎬 Monitoring {movie_name} in {theatre_name} for ₹{PRICE_LIMIT} seats...")

    while True:
        try:
            # Find movie
            movies = get_movies()
            matched_movie = next(
                (
                    (name, cid)
                    for name, cid in movies
                    if movie_name.lower() in name.lower()
                ),
                (None, None),
            )
            movie_name_matched, content_id = matched_movie
            if not content_id:
                print(f"❌ Movie '{movie_name}' not found. Retrying in {CHECK_INTERVAL_MIN} min...")
                time.sleep(CHECK_INTERVAL_MIN * 60)
                continue

            data = get_theatre_sessions(content_id, date)
            theatres = data.get("pageData", {}).get("nearbyCinemas", [])
            for theatre in theatres:
                name = theatre["cinemaInfo"]["name"]
                if theatre_name.lower() not in name.lower():
                    continue

                theatre_name = name
                for session in theatre.get("sessions", []):
                    price_areas = [
                        a
                        for a in session.get("areas", [])
                        if a.get("price", 0) <= PRICE_LIMIT
                    ]
                    if not price_areas:
                        continue
                    cinema_id = theatre["id"]
                    session_id = session["sid"]
                    provider_id = session["pid"]
                    movie_code = session["mid"]

                    # 🎯 pick the cheapest price among allowed areas
                    area_price_map = {
                        a["label"].upper().strip(): a.get("price", 0)
                        for a in session.get("areas", [])
                    }

                    seat_data = get_seat_status(
                        cinema_id, session_id, provider_id, content_id, movie_code
                    )

                    normal_available = []
                    executive_available = []

                    for area in seat_data["seatLayout"]["colAreas"]["objArea"]:
                        if len(price_areas) == 1 and area["AreaDesc"] == "EXECUTIVE":
                            continue  # skip EXECUTIVE if multiple price areas
                        area_desc = area["AreaDesc"].upper().strip()
                        for row in area.get("objRow", []):
                            for seat in row.get("objSeat", []):
                                if seat["SeatStatus"] == "0":  # seat is available
                                    seat_label = f"{area_desc} {row['PhyRowId']}{seat['displaySeatNumber']}"
                                    if area_desc == "NORMAL":
                                        normal_available.append(seat_label)
                                    elif area_desc == "EXECUTIVE":
                                        executive_available.append(seat_label)

                    utc_time_str = session["showTime"]
                    try:
                        utc_dt = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M")
                        ist_dt = utc_dt + timedelta(hours=5, minutes=30)
                        show_time_ist = ist_dt.strftime("%I:%M %p, %d %b %Y")
                    except Exception:
                        show_time_ist = utc_time_str

                    # ✅ CASE 1: ₹60 (NORMAL) seats are open
                    if normal_available:
                        normal_price = area_price_map.get("NORMAL", 0)
                        normal_price_str = (
                            f"₹{normal_price:.2f}" if normal_price else "N/A"
                        )
                        msg = (
                            f"🎬 <b>{html.escape(movie_name_matched)}</b>\n"
                            f"🪑 <b>NORMAL seats OPEN!</b>\n"
                            f"🍿 <b>{html.escape(theatre_name)}</b>\n"
                            f"🕒 <b>Showtime:</b> {show_time_ist}\n"
                            f"🎟️ <b>Available:</b> {len(normal_available)} seats\n"
                            f"💰 <b>Price:</b> {normal_price_str}\n"
                            f"Seats: {', '.join(normal_available[:5])}..."
                        )
                        telegram_alert(msg, chat_id)
                        plain_text = re.sub(r"<[^>]+>", "", msg)
                        print(plain_text)

                    # ✅ CASE 2: only EXECUTIVE seats are available
                    elif executive_available:
                        exec_price = area_price_map.get("EXECUTIVE", 0)
                        exec_price_str = f"₹{exec_price:.2f}" if exec_price else "N/A"
                        msg = (
                            f"🎬 <b>{html.escape(movie_name_matched)}</b>\n"
                            f"💺 <b>Higher class (EXECUTIVE) seats only available!</b>\n"
                            f"🍿 <b>{html.escape(theatre_name)}</b>\n"
                            f"🕒 <b>Showtime:</b> {show_time_ist}\n"
                            f"🎟️ <b>Available:</b> {len(executive_available)} seats\n"
                            f"💰 <b>Price:</b> {exec_price_str}\n"
                            f"Seats: {', '.join(executive_available[:5])}..."
                        )
                        telegram_alert(msg, chat_id)
                        plain_text = re.sub(r"<[^>]+>", "", msg)
                        print(plain_text)

                    else:
                        print(
                            f"❌ No seats available for ₹{PRICE_LIMIT} or cheaper at {show_time_ist}. "
                            f"Refreshed at {datetime.now():%I:%M %p, %d %b %Y}."
                        )

            print("-" * 150)
            time.sleep(CHECK_INTERVAL_MIN * 60)
        except Exception as e:
            print(f"⚠️ Error in {chat_id}'s monitor:", e)
            time.sleep(120)
