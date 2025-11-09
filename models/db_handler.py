import os
from supabase import create_client, Client
from dotenv import load_dotenv
from models.log_handler import log

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = None # Inicializa como None

try:
    supabase: Client = create_client(url, key)
    # 1. SOLUCIÓN: Usa print() aquí. Es solo para el arranque.
    print("[DB_HANDLER] Conexión con Supabase creada.")
except Exception as e:
    # 1. SOLUCIÓN: Usa print() aquí también.
    print(f"[DB_HANDLER] ERROR al crear cliente de Supabase: {e}")

async def insert_trade(trade_data: dict):
    """
    Inserta un trade COMPLETO en la base de datos.
    """
    # 2. SOLUCIÓN: Comprobar si la conexión falló al inicio
    if supabase is None:
        await log("[DB_HANDLER] ERROR: Supabase client no está inicializado.")
        return

    try:
        # 3. CORRECCIÓN: ¡Faltaba un 'await' aquí!
        # La librería de Supabase necesita 'await' para no bloquear el bot
        await supabase.table('signals-data').insert(trade_data).execute()
        
        # Este log es opcional, pero es bueno tenerlo
        await log(f"[DB_HANDLER] Trade insertado: {trade_data.get('symbol')} -> {trade_data.get('result')}")
        
    except Exception as e:
        await log(f"[DB_HANDLER] ERROR al insertar trade: {e} | Data: {trade_data}")
