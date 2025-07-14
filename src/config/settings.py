import os
from dotenv import load_dotenv

load_dotenv() 

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
BOT_LOG_TOKEN = os.getenv("BOT_LOG_TOKEN")
CHANNEL_LOG_ID = os.getenv("CHANNEL_LOG_ID")
SHEET_ID = os.getenv("SHEET_ID")