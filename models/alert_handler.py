import telegram
import os

from dotenv import load_dotenv

load_dotenv()

bot = telegram.Bot(token=os.getenv("BOT_TOKEN"))

async def alert_handler(symbol, percentage_change, price, emoji1, emoji2, volume):
    await bot.send_message(
        chat_id=os.getenv("CHANNEL_ID"),
        text=f'{emoji1} #{symbol} {emoji2} {percentage_change:+.2f}%\n💵 ${price:.2f} 💰 ${volume}M'
    )
    print(f"{symbol} alert sended.")
