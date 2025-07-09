import asyncio
from binance.client import Client
from telegram import Bot

from bot.price_tracker import price_tracker
from logs import log_message
from config.settings import (
    API_KEY, API_SECRET,
    BOT_TOKEN, CHANNEL_ID,
)

async def main():
    client = Client(API_KEY, API_SECRET)
    bot = Bot(token=BOT_TOKEN)

    await log_message(message="🤖 BOT ACTIVATED")
    await price_tracker(client, bot, CHANNEL_ID)

if __name__ == "__main__":
    asyncio.run(main())