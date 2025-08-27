import asyncio
import threading
import os
import pytz
from datetime import datetime, time, timedelta
from contextlib import asynccontextmanager
from flask import Flask, jsonify
from binance import AsyncClient, BinanceSocketManager

from models.coin_handler import coin_handler
from models.log_handler import log

async def binance_client():
    """
    Binance client creator.
    """

    await log("Creando cliente de Binance...")

    client = await AsyncClient.create(
        api_key=os.getenv("API_KEY"), 
        api_secret=os.getenv("API_SECRET")
    )

    await log("Cliente creado exitosamente")
    return client

async def main():
    client = None
    try:
        client = await binance_client()
        timezone_caracas = pytz.timezone('America/Caracas')

        await coin_handler(client)

        while True:
            now = datetime.now(timezone_caracas)
            target_time_today = timezone_caracas.localize(
                datetime.combine(now.date(), time(23, 59))
            )
            
            if now > target_time_today:
                target_time = target_time_today + timedelta(days=1)
            else:
                target_time = target_time_today
            
            wait_seconds = (target_time - now).total_seconds()
            
            await asyncio.sleep(wait_seconds)
            
            await log("🔄 Hora de la re-ejecución diaria. Actualizando lista de monedas...")
            await coin_handler(client)

    except Exception as e:
        await log(f"[ERROR CRÍTICO] Error en la función main: {e}")
    finally:
        if client:
            await client.close_connection()
            await log("Conexión cerrada.")

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