import telegram
import os
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

CHANNEL_LOG_ID = os.getenv("CHANNEL_LOG_ID") 
bot_log = telegram.Bot(token=os.getenv("BOT_LOG_TOKEN"))

async def log_message(message):
    now = datetime.now()
    timestamp = now.strftime("%H:%M:%S")
    message_final = f"`{message}\n[{timestamp}]`"

    await bot_log.send_message(chat_id=CHANNEL_LOG_ID, text=message_final, parse_mode="MarkdownV2")