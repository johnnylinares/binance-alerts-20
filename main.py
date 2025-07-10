# ===== LIBRARYS =====
import asyncio # For asynchronous operations
import threading # HTTPS request for 24/7 uptime
from flask import Flask, jsonify # For web server
from binance.client import Client # For Binance API
from telegram import Bot # For Telegram Bot API

# ===== MODULES =====
from bot.price_tracker import price_tracker
from logs import log_message
from config.settings import (
    API_KEY, API_SECRET,
    BOT_TOKEN, CHANNEL_ID,
)

# ===== MAIN CODE =====
async def start_bot():
    """Function to start the bot and price tracker."""
    client = Client(API_KEY, API_SECRET)
    bot = Bot(token=BOT_TOKEN)
    await log_message(message="🤖 BOT ACTIVATED")
    await price_tracker(client, bot, CHANNEL_ID)

def run_bot():
    asyncio.run(start_bot())

def keep_bot():
    """Starts the bot in a separate thread to keep it running."""
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

# ===== HTTPS REQUEST =====
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "active", "message": "Binance/Telegram Bot Running"})

@app.route('/ping')
def ping():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    keep_bot()
    app.run(host='0.0.0.0', port=8000)
