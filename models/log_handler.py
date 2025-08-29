import os
import telegram
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

bot = telegram.Bot(token=os.getenv("BOT_TOKEN_LOG"))

async def log(msg):
    print(f"{msg}")