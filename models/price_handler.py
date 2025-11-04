import time
import asyncio
from models.log_handler import log
from models.alert_handler import alert_handler

# --- Constantes de Configuración ---

# Umbral de alerta en porcentaje
THRESHOLD = 20

# 2 horas y 10 minutos en segundos (2 * 60 * 60 + 10 * 60)
TIME_WINDOW = 7800 

# Tamaño del grupo de monedas por conexión de websocket.
# 50 es un valor seguro para evitar que la URL de conexión sea rechazada.
GROUP_SIZE = 50

# --- Lógica del Websocket ---

async def _handle_websocket_stream(client, streams: list, price_history: dict, group_id: int):
    """
    Función interna que maneja un único stream multiplexado para un grupo de monedas.
    Esta tarea está diseñada para ser iniciada y cancelada externamente por price_handler.
    
    *** CAMBIO CLAVE: Esta función ahora recibe 'client' en lugar de 'bm' ***
    """
    
    await log(f"[Grupo {group_id}] Creando websocket para {len(streams)} monedas.")
    
    # --- ¡ESTA ES LA CORRECCIÓN! ---
    # Usamos el método del cliente para sockets de FUTUROS,
    # en lugar de crear un BinanceSocketManager (que es de SPOT).
    ts = client.futures_multiplex_socket(streams)
    # --------------------------------

    try:
        async with ts as tscm:
            # Bucle infinito. Se romperá cuando la tarea sea cancelada.
            while True:
                try:
                    msg = await asyncio.wait_for(tscm.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue

                # --- Procesamiento del Mensaje ---
                if 'data' not in msg or not isinstance(msg['data'], dict):
                    continue
                
                ticker_data = msg['data']
                
                if ticker_data.get('e') != '24hrTicker':
                    continue
                
                symbol = ticker_data.get('s')
                
                if symbol not in price_history:
                    continue
                
                try:
                    price = float(ticker_data['c'])
                    volume = round(float(ticker_data['q']) / 1000000, 1)
                    now = time.time()
                    
                    history = price_history[symbol]
                    history.append((now, price))
                    
                    while history and (now - history[0][0]) > TIME_WINDOW:
                        history.pop(0)
                    
                    if len(history) < 2:
                        continue

                    # --- Lógica de Alerta ---
                    old_price = history[0][1]
                    percentage_change = ((price - old_price) / old_price) * 100
                    
                    if abs(percentage_change) >= THRESHOLD:
                        emoji = ("🟢", "📈") if percentage_change > 0 else ("🔴", "📉")
                        log_msg = f"[Grupo {group_id}] 📊 COIN FOUND: {symbol} ({percentage_change:+.2f}%)"
                        
                        asyncio.create_task(log(log_msg))
                        asyncio.create_task(alert_handler(
                            symbol,
                            percentage_change,
                            price,
                            emoji,
                            volume
                        ))
                        
                        price_history[symbol] = []
                
                except (ValueError, KeyError, TypeError) as e:
                    asyncio.create_task(log(f"[Grupo {group_id}] Error procesando data: {e} | Data: {ticker_data}"))
                    continue

    except asyncio.CancelledError:
        await log(f"[Grupo {group_id}] Websocket cancelado (cierre normal).")
        
    except Exception as e:
        # Aquí es donde veías el error 400. Ahora no debería aparecer.
        await log(f"[Grupo {group_id}][ERROR] Error crítico en websocket: {e}")
        
    finally:
        await log(f"[Grupo {group_id}] Websocket cerrado.")

# --- Función Pública (Handler Principal) ---

async def price_handler(client, coins, duration_seconds):
    """
    Función principal para gestionar los websockets de precios.
    
    Args:
        client: Cliente AsyncClient de Binance
        coins: Set de monedas a monitorear
        duration_seconds: Duración total del monitoreo antes de refrescar
    """
    await log("🤖 PRICE TRACKER ACTIVADO (v2.2 Corregido)")

    # 1. Inicializar historial compartido
    price_history = {coin: [] for coin in coins}
    
    # 2. --- ¡CAMBIO! Ya no creamos 'bm = BinanceSocketManager(client)' ---
    # El 'client' se pasará directamente a las tareas.

    # 3. Dividir monedas en grupos
    coins_list = list(coins)
    groups = [coins_list[i:i + GROUP_SIZE] for i in range(0, len(coins_list), GROUP_SIZE)]
    
    await log(f"Monedas filtradas: {len(coins)}. Creando {len(groups)} grupos (Max {GROUP_SIZE} monedas/grupo)...")
    await log(f"⏰ Duración del ciclo: {duration_seconds/3600:.1f} horas")

    # 4. Crear una tarea de asyncio por cada grupo
    websocket_tasks = []
    for i, group_coins in enumerate(groups):
        group_id = i + 1
        streams = [f"{coin.lower()}@ticker" for coin in group_coins]
        
        if not streams:
            await log(f"[Grupo {group_id}] Omitido (sin monedas).")
            continue
        
        # --- ¡CAMBIO! Pasamos 'client' a la tarea ---
        task = asyncio.create_task(
            _handle_websocket_stream(client, streams, price_history, group_id)
        )
        websocket_tasks.append(task)

    if not websocket_tasks:
        await log("[WARNING] No se crearon tareas de websocket (lista de monedas vacía).")
        await asyncio.sleep(duration_seconds)
        return

    # 5. Esperar la duración del ciclo
    try:
        await asyncio.sleep(duration_seconds)
        
    except asyncio.CancelledError:
        await log("[PRICE_HANDLER] Ciclo principal cancelado externamente.")
        raise
        
    finally:
        # 6. Cierre Limpio (Graceful Shutdown)
        await log("⏰ Tiempo de ciclo alcanzado. Cerrando todos los websockets...")
        
        for task in websocket_tasks:
            task.cancel()
        
        results = await asyncio.gather(*websocket_tasks, return_exceptions=True)
        
        for i, res in enumerate(results):
            if isinstance(res, Exception) and not isinstance(res, asyncio.CancelledError):
                await log(f"[ERROR] Tarea de Websocket {i+1} finalizó con error: {res}")
                
        await log("✅ Todos los websockets cerrados. Price handler finalizado.")