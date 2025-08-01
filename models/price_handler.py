# ===== LIBRARYS =====
import asyncio

# ===== MODULES =====
from models.alert_handler import send_alert

# ===== CONSTANTS =====
THRESHOLD = 0.1 # % alert´s change

async def price_handler(bsm, b_client, coins):
    