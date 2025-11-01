import asyncio
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram_utils import telegram_alert, save_chat_id
from monitor import monitor_seats
from district_api import get_movies
import datetime
import shlex
from telegram.ext import CallbackQueryHandler
import difflib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# You can adjust this interval if needed
CHECK_INTERVAL = 10  # seconds (time between Telegram replies when monitoring starts)


# /start command — greeting
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    save_chat_id(chat.id, chat.full_name)
    await update.message.reply_text(
        f"👋 Hi {chat.first_name}! You're now subscribed for movie seat alerts.\n\n"
        'Use /track  "<movie>" "<theatre>" [date in YYYY-MM-DD format] to start monitoring.'
    )
    print(f"✅ User connected: {chat.id} ({chat.full_name})")


active_monitors = {}


# /track command — start monitoring a movie
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    chat_name = update.message.chat.full_name

    try:
        # Reconstruct the message and parse with shlex
        text = update.message.text.replace("/track", "", 1).strip()
        args = shlex.split(text)
    except Exception:
        await update.message.reply_text(
            "⚠️ Couldn't parse input. Use quotes for multi-word names."
        )
        return

    if len(args) < 2:
        await update.message.reply_text('Usage: /track "<movie>" "<theatre>" [date]')
        return

    movie = args[0]
    theatre = args[1]
    date = args[2] if len(args) >= 3 else datetime.now().strftime("%Y-%m-%d")

    movies = get_movies()
    all_movie_names = [name for name, _ in movies]
    matched = next(
        ((name, cid) for name, cid in movies if movie.lower() in name.lower()), None
    )

    if not matched:
        suggestions = difflib.get_close_matches(movie, all_movie_names, n=3, cutoff=0.5)
        if suggestions:
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"🎬 {s}", callback_data=f"track|{s}|{theatre}|{date}"
                    )
                ]
                for s in suggestions
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"❌ Movie '{movie}' not found.\nDid you mean one of these?",
                reply_markup=reply_markup,
            )
        else:
            await update.message.reply_text(
                f"❌ Movie '{movie}' not found. Please check spelling."
            )
        return

    movie_name, content_id = matched

    await update.message.reply_text(
        f"🎬 Tracking started for *{movie}* at *{theatre}* ({date})",
        parse_mode="Markdown",
    )
    print(f"🚀 {chat_name} ({chat_id}) started tracking: {movie} | {theatre}")

    # if an old monitor is running for this user, stop it first
    if chat_id in active_monitors:
        active_monitors[chat_id]["running"] = False

    # start a new one
    monitor = threading.Thread(
        target=monitor_seats,
        args=(movie, theatre, date, chat_id),
        daemon=True,
    )
    active_monitors[chat_id] = {"thread": monitor, "running": True}
    monitor.start()


async def run_monitor(movie_name, theatre_name, date=None):
    """Wrapper to call monitor_seats() safely in background"""
    try:
        print(f"🚀 Started monitoring: {movie_name} | {theatre_name} | {date}")
        await asyncio.to_thread(monitor_seats, movie_name, theatre_name, date)
    except Exception as e:
        print(f"⚠️ Error in monitor task: {e}")


# /broadcast command — send a manual message to all users
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    telegram_alert(f"📢 {message}")
    await update.message.reply_text("✅ Message sent to all active users.")


# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Available Commands:\n"
        "/start — Show introduction\n"
        "/track <movie> <theatre> [date] — Start monitoring seats\n"
        "/broadcast <message> — Send message to all users\n"
        "/help — Show this help message"
    )


async def suggestion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    if len(data) < 4:
        await query.edit_message_text("⚠️ Invalid selection.")
        return

    _, movie, theatre, date = data
    chat_id = query.message.chat_id
    chat_name = query.message.chat.full_name

    await query.edit_message_text(f"✅ You selected: {movie}\nStarting tracking now…")
    asyncio.create_task(asyncio.to_thread(monitor_seats, movie, theatre, date, chat_id))


def main():
    from config import TELEGRAM_BOT_TOKEN

    print("🤖 Telegram bot starting...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", track))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(suggestion_callback, pattern=r"^track\|"))

    print("✅ Bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
