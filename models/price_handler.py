import time
import asyncio
from binance import BinanceSocketManager
from models.log_handler import log
from models.alert_handler import alert_handler

async def price_handler(client, coins):
    """
    Maneja el monitoreo de precios usando websockets para detectar movimientos del 20%
    Adaptado de la lógica original de price_tracker pero con websockets
    """
    
    await log("🤖 PRICE TRACKER ACTIVATED")

    price_history = {}
    threshold = 20
    time_window = 2 * 60 * 60 + 10 * 60
    log_interval = 600

    last_log_time = time.time()
    
    bm = BinanceSocketManager(client)
    
    async def handle_socket_message(msg):
        """Procesa cada mensaje del websocket"""
        nonlocal last_log_time
        
        # --- INICIO DE LA CORRECCIÓN ---
        # 1. Comprobamos si el mensaje es una lista (lista de tickers).
        if isinstance(msg, list):
            # Si es una lista, iteramos sobre cada elemento para procesarlo individualmente.
            for item in msg:
                await process_single_ticker(item)
        # 2. Comprobamos si el mensaje es un diccionario (un solo evento o mensaje de error).
        elif isinstance(msg, dict):
            await process_single_ticker(msg)
        # --- FIN DE LA CORRECCIÓN ---
            
    async def process_single_ticker(ticker_data):
        """Procesa los datos de un único ticker."""
        nonlocal last_log_time
        try:
            if ticker_data['e'] == '24hrTicker':
                symbol = ticker_data['s']
                
                price = float(ticker_data['c'])
                volume = round(float(ticker_data['v']) / 1000000, 1)
                now = time.time()
                
                if symbol not in price_history:
                    price_history[symbol] = []
                
                price_history[symbol].append((now, price))
                
                price_history[symbol] = [
                    p for p in price_history[symbol] 
                    if now - p[0] <= time_window
                ]
                
                if len(price_history[symbol]) >= 2:
                    old_price = price_history[symbol][0][1]
                    percentage_change = ((price - old_price) / old_price) * 100
                
                    if abs(percentage_change) >= threshold:
                        await log(f"📊 COIN FOUND: {symbol}")
                        
                        if percentage_change > 0:
                            emoji = "🟢📈"
                        else:
                            emoji = "🔴📉"

                        await alert_handler(symbol, percentage_change, price, emoji, volume)
                        
                        price_history[symbol] = []
                
                current_time = time.time()
                if current_time - last_log_time >= log_interval:
                    await log("🔍 Checking coins")
                    last_log_time = current_time
                    
        except Exception as e:
            await log(f"[ERROR] Error procesando mensaje: {e}")
            
    ts = bm.ticker_socket()
    
    try:
        await log(f"Conectando a websocket para monitorear {len(coins)} monedas...")
        
        async with ts as tscm:
            while True:
                try:
                    msg = await tscm.recv()
                    await handle_socket_message(msg)
                    
                except Exception as e:
                    await log(f"[ERROR] Error en websocket: {e}")
                    await asyncio.sleep(10)
                    break
                    
    except Exception as e:
        await log(f"[ERROR] Error crítico en websocket: {e}")
        raise
    
    finally:
        await log("Cerrando conexión websocket...")
