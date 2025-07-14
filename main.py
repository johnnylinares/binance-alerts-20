# ===== LIBRARYS =====
import asyncio # For asynchronous operations
import threading # HTTPS request for 24/7 uptime
from flask import Flask, jsonify # For web server
from telegram import Bot # For Telegram Bot API

# ===== MODULES =====
from src.models.price_tracker import price_tracker
from src.config.logs import logging
from src.config.settings import (
    BOT_TOKEN, CHANNEL_ID
)

# ===== MAIN CODE =====
async def start_bot():
    """Function to start the bot and price tracker."""
    bot = Bot(token=BOT_TOKEN)
    logging.info("Bot activated successfully.")
    await price_tracker(bot, CHANNEL_ID)

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
