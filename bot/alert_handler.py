import telegram
from binance.client import Client
import os

from logs import log_message
from dotenv import load_dotenv

load_dotenv()

client = Client(api_key=os.getenv("API_KEY"), api_secret=os.getenv("BINANCE_API_SECRET"))
bot = telegram.Bot(token=os.getenv("BOT_TOKEN"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def send_alert(symbol, percentage_change, price, emoji1, emoji2, volume_24h):
    await log_message(message="🤖 SEND ALERT ACTIVATED")
    await bot.send_message(chat_id=CHANNEL_ID, text=f'{emoji1} #{symbol} {emoji2} {percentage_change:+.2f}%\n💵 ${price} 💰 ${volume_24h}M')
    await log_message(message=f"✅ {symbol} MESSAGE SENDED")
