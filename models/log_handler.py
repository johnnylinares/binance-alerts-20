import os
import telegram
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

async def log(msg):
    print(f"{msg}")