import os
import telegram
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

bot = telegram.Bot(token=os.getenv("BOT_TOKEN_LOG"))

async def log(msg):
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S")
    message = f"`[{timestamp}] {msg}`"

    await bot.send_message(chat_id=os.getenv("CHANNEL_ID_LOG"), text=message, parse_mode="MarkdownV2")