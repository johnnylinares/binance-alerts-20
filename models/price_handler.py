import time
import asyncio
from binance import BinanceSocketManager
from models.log_handler import log
from models.alert_handler import alert_handler

async def price_handler(client, coins):
    """
    Maneja el monitoreo de precios usando websockets para detectar movimientos del 20%
    Solo se suscribe a las monedas proporcionadas en la lista 'coins'.
    """
    
    await log("🤖 PRICE TRACKER ACTIVATED")

    price_history = {}
    threshold = 20
    time_window = 2 * 60 * 60 + 10 * 60
    log_interval = 600

    last_log_time = time.time()
    
    bm = BinanceSocketManager(client)
    
    async def handle_socket_message(msg):
        """Procesa cada mensaje del websocket."""
        nonlocal last_log_time
        
        try:
            # Añadimos esta verificación para asegurarnos de que el mensaje
            # tenga la clave 'data' antes de procesarlo.
            if 'data' in msg and isinstance(msg['data'], dict):
                ticker_data = msg['data']
            else:
                # Si el mensaje no tiene el formato esperado, lo ignoramos y lo registramos.
                await log(f"[DEBUG] Mensaje de control o inesperado recibido: {msg}")
                return
            
            # Ahora el código es más simple, ya que 'ticker_data' siempre es un diccionario.
            if ticker_data['e'] == '24hrTicker':
                symbol = ticker_data['s']
                
                # Solo procesamos si el símbolo está en nuestra lista de interés.
                # Nota: Aunque ya nos suscribimos solo a estas monedas,
                # esta es una buena práctica de seguridad.
                if symbol in coins:
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
            
    # --- CAMBIO CRÍTICO: Usar multiplex_socket para las monedas específicas ---
    # Convertimos los símbolos de la lista 'coins' a minúsculas y agregamos '@ticker'
    # para crear los nombres de los streams del websocket.
    streams = [f"{coin.lower()}@ticker" for coin in coins]
    ts = bm.multiplex_socket(streams)
    
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
