import asyncio
import threading
import os
import pytz

from datetime import datetime, time, timedelta
from flask import Flask, jsonify
from binance import AsyncClient

from models.coin_handler import coin_handler
from models.log_handler import log

async def binance_client():
    """
    Binance client creator.
    """

    client = await AsyncClient.create(
        api_key=os.getenv("API_KEY"), 
        api_secret=os.getenv("API_SECRET")
    )

    await log("🟢 Binance client created sucessfully.")
    return client

async def main():
    await log("🟢 Bot started.")

    client = None
    try:
        client = await binance_client()
        timezone_caracas = pytz.timezone('America/Caracas')

        while True:
            try:
                await log("🔄 Iniciando ciclo de tracking de precios...")
                
                now = datetime.now(timezone_caracas)
                target_time_today = timezone_caracas.localize(
                    datetime.combine(now.date(), time(23, 59))
                )
                
                if now > target_time_today:
                    target_time = target_time_today + timedelta(days=1)
                else:
                    target_time = target_time_today
                
                wait_seconds = (target_time - now).total_seconds()
                
                await log(f"⏰ Próxima actualización de monedas en {wait_seconds/3600:.1f} horas (a las 23:59)")
            
                try:
                    await asyncio.wait_for(
                        coin_handler(client, wait_seconds),
                        timeout=wait_seconds + 60 
                    )
                except asyncio.TimeoutError:
                    await log("⏰ Timeout alcanzado. Reiniciando tracking de precios...")
                
                await log("🔄 Ciclo completado. Actualizando lista de monedas...")
                
            except Exception as e:
                await log(f"[ERROR] Error in tracking cycle: {e}")
                await log("[RETRY] Waiting 60 seconds before retrying...")
                await asyncio.sleep(60)

    except Exception as e:
        await log(f"[ERROR] Error en la función main: {e}")
    finally:
        if client:
            await client.close_connection()
            await log("[CLIENT] Binance client closed.")

def run_bot():
    """
    Ejecuta el bot en el event loop de asyncio.
    """
    asyncio.run(main())

def keep_bot():
    """
    Mantiene el bot corriendo en un thread separado.
    """
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    return bot_thread

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "active", "message": "Binance/Telegram Bot Running"})

@app.route('/ping')
def ping():
    return jsonify({"status": "ok"}), 200

@app.route('/health')
def health():
    """
    Endpoint adicional para health checks de Render.
    """
    return jsonify({
        "status": "healthy",
        "service": "binance-telegram-bot",
        "timestamp": datetime.now().isoformat()
    }), 200

if __name__ == "__main__":
    bot_thread = keep_bot()
    
    port = int(os.getenv("PORT", 8000))
    app.run(host='0.0.0.0', port=port)