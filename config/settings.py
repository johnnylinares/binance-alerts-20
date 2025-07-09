import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()  # Esto lee el archivo .env y carga las variables de entorno

# Ahora puedes acceder a las variables de entorno
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
BOT_LOG_TOKEN = os.getenv("BOT_LOG_TOKEN")
CHANNEL_LOG_ID = os.getenv("CHANNEL_LOG_ID")