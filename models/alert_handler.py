# ===== LIBRARIES =====
import telegram
from binance.client import Client
import os

# ===== ENVIRONMENT VARIABLES =====
from dotenv import load_dotenv
load_dotenv()

# ===== CONNECTION =====
client = Client(api_key=os.getenv("API_KEY"), api_secret=os.getenv("BINANCE_API_SECRET"))
bot = telegram.Bot(token=os.getenv("BOT_TOKEN"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

# ===== FUNCTION =====
async def send_alert(symbol, percentage_change, price, emoji1, emoji2, volume_24h):
    print(f"Send alert function called")
    await bot.send_message(chat_id=CHANNEL_ID, text=f'{emoji1} #{symbol} {emoji2} {percentage_change:+.2f}%\n💵 ${price} 💰 ${volume_24h}M')
    print(f"{symbol} message sended")
