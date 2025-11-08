import os
from supabase import create_client, Client
from dotenv import load_dotenv
from models.log_handler import log

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

try:
    supabase: Client = create_client(url, key)
    log("[DB_HANDLER] Conexión con Supabase creada.")
except Exception as e:
    log(f"[DB_HANDLER] ERROR al crear cliente de Supabase: {e}")

async def insert_trade(trade_data: dict):
    """
    Inserta un trade COMPLETO en la base de datos.
    """
    try:
        supabase.table('signals-data').insert(trade_data).execute()
    except Exception as e:
        await log(f"[DB_HANDLER] ERROR al insertar trade: {e} | Data: {trade_data}")