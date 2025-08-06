import asyncio
import threading
from contextlib import asynccontextmanager
from flask import Flask, jsonify
from binance import AsyncClient, BinanceSocketManager

from models.coin_handler import coin_handler
from config.settings import (
    API_KEY, API_SECRET
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

async def main():
    try:
        async with binance_client() as b_client:
            bsm = BinanceSocketManager(b_client)
            await coin_handler(b_client, bsm)
    except Exception as e:
        print(f"Error en main: {e}")

def run_bot():
    asyncio.run(main())

def keep_bot():
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

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