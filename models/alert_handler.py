import telegram
import os

from dotenv import load_dotenv
load_dotenv()

bot = telegram.Bot(token=os.getenv("BOT_TOKEN"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

async def send_alert(symbol, percentage_change, price, emoji1, emoji2, volume_24h):
    await bot.send_message(chat_id=CHANNEL_ID, text=f'{emoji1} #{symbol} {emoji2} {percentage_change:+.2f}%\n💵 ${price} 💰 ${volume_24h}M')
    print(f"{symbol} message sended")
