import asyncio
import threading
from flask import Flask, jsonify
from binance.client import Client
from telegram import Bot

from bot.price_tracker import price_tracker
from logs import log_message
from config.settings import (
    API_KEY, API_SECRET,
    BOT_TOKEN, CHANNEL_ID,
)

# ===== CONFIGURACIÓN FLASK =====
app = Flask(__name__)

# ===== BOT EN SEGUNDO PLANO =====
async def bot_loop():
    client = Client(API_KEY, API_SECRET)
    bot = Bot(token=BOT_TOKEN)
    await log_message(message="🤖 BOT ACTIVATED")
    await price_tracker(client, bot, CHANNEL_ID)

def run_bot():
    asyncio.run(bot_loop())

# ===== ENDPOINTS WEB =====
@app.route('/')
def home():
    return jsonify({"status": "active", "message": "Binance/Telegram Bot Running"})

@app.route('/ping')
def ping():
    return jsonify({"status": "ok"}), 200

# ===== INICIALIZACIÓN =====
def start_background_services():
    # Inicia el bot en un thread separado
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Opcional: Auto-ping para mantener activo el servicio
    if not app.debug:
        import requests
        def auto_ping():
            import time
            while True:
                try:
                    requests.get("https://tudominio.onrender.com/ping")
                except:
                    pass
                time.sleep(240)  # Ping cada 4 minutos
        
        ping_thread = threading.Thread(target=auto_ping, daemon=True)
        ping_thread.start()

if __name__ == "__main__":
    start_background_services()
    app.run(host='0.0.0.0', port=8000)