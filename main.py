import asyncio # For asynchronous operations
import threading # HTTPS request for 24/7 uptime
from contextlib import asynccontextmanager
from flask import Flask, jsonify # For web server
import telegram
from telegram import Bot # For Telegram Bot API
from binance import AsyncClient

# ===== MODULES =====
from models.price_tracker import price_tracker
from config.settings import (
    API_KEY, API_SECRET, BOT_TOKEN
)

@asynccontextmanager
async def binance_client():
    client = None
    try:
        client = await AsyncClient.create(
            api_key=API_KEY,
            api_secret=API_SECRET
        )
        print("Binance client created successfully.")
        yield client
    finally:
        if client:
            await client.close_connection()
            print("Connection closed.")

t_bot = telegram.Bot(token=BOT_TOKEN)

# ===== MAIN CODE =====
async def main():
    try:
        async with binance_client() as b_client:

            await price_tracker(b_client)
            
    except Exception as e:
        print(f"Error en main: {e}")

def run_bot():
    asyncio.run(main())

def keep_bot():
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
