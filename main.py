import asyncio
import threading
from binance.client import Client
from telegram import Bot

from bot.price_tracker import price_tracker
from logs import log_message
from config.settings import (
    API_KEY, API_SECRET,
    BOT_TOKEN, CHANNEL_ID,
)

# ===== KEEP ALIVE ASÍNCRONO =====
async def keep_alive():
    while True:
        print("🔄 Bot activo (Render 24/7)", flush=True)
        await asyncio.sleep(300)  # Cada 5 minutos (300 segundos)

def run_keep_alive():
    asyncio.run(keep_alive())

# Inicia el thread en segundo plano (para asyncio)
threading.Thread(
    target=lambda: asyncio.run(keep_alive()),
    daemon=True
).start()

# ===== CÓDIGO PRINCIPAL =====
async def main():
    client = Client(API_KEY, API_SECRET)
    bot = Bot(token=BOT_TOKEN)

    await log_message(message="🤖 BOT ACTIVATED")
    await price_tracker(client, bot, CHANNEL_ID)

if __name__ == "__main__":
    asyncio.run(main())