import time
import asyncio
from binance import BinanceSocketManager
from models.log_handler import log
from models.alert_handler import alert_handler

THRESHOLD = 20
TIME_WINDOW = 7800 
GROUP_SIZE = 50

async def _handle_websocket_stream(bm: BinanceSocketManager, streams: list, price_history: dict, group_id: int):
    """
    Función interna que maneja un único stream multiplexado para un grupo de monedas.
    Esta tarea está diseñada para ser iniciada y cancelada externamente por price_handler.
    """
    
    await log(f"[Grupo {group_id}] Creando websocket para {len(streams)} monedas.")
    ts = bm.multiplex_socket(streams)

    try:
        async with ts as tscm:
            # Bucle infinito. Se romperá cuando la tarea sea cancelada.
            while True:
                try:
                    # Esperamos por un mensaje con un timeout
                    # Esto permite que la tarea sea "cancelable"
                    msg = await asyncio.wait_for(tscm.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    # No llegó mensaje, es normal. Volvemos a esperar.
                    continue

                # --- Procesamiento del Mensaje ---
                if 'data' not in msg or not isinstance(msg['data'], dict):
                    continue
                
                ticker_data = msg['data']
                
                if ticker_data.get('e') != '24hrTicker':
                    continue
                
                symbol = ticker_data.get('s')
                
                # Si el símbolo no está en nuestro historial (ej. de un ciclo anterior), ignorar
                if symbol not in price_history:
                    continue
                
                try:
                    price = float(ticker_data['c'])
                    volume = round(float(ticker_data['q']) / 1000000, 1)
                    now = time.time()
                    
                    history = price_history[symbol]
                    history.append((now, price))
                    
                    # --- Limpieza eficiente del historial ---
                    # Elimina datos antiguos del inicio de la lista
                    while history and (now - history[0][0]) > TIME_WINDOW:
                        history.pop(0)
                    
                    # Si no hay historial suficiente, continuar
                    if len(history) < 2:
                        continue

                    # --- Lógica de Alerta ---
                    old_price = history[0][1]
                    percentage_change = ((price - old_price) / old_price) * 100
                    
                    if abs(percentage_change) >= THRESHOLD:
                        emoji = ("🟢", "📈") if percentage_change > 0 else ("🔴", "📉")
                        
                        # Preparamos el log
                        log_msg = f"[Grupo {group_id}] 📊 COIN FOUND: {symbol} ({percentage_change:+.2f}%)"
                        
                        # Usamos "fire-and-forget" para las alertas.
                        # Esto NO bloquea el bucle del websocket.
                        asyncio.create_task(log(log_msg))
                        asyncio.create_task(alert_handler(
                            symbol,
                            percentage_change,
                            price,
                            emoji,
                            volume
                        ))
                        
                        # Resetear historial para evitar spam
                        price_history[symbol] = []
                
                except (ValueError, KeyError, TypeError) as e:
                    # Error procesando un ticker específico, no debe tumbar el socket
                    asyncio.create_task(log(f"[Grupo {group_id}] Error procesando data: {e} | Data: {ticker_data}"))
                    continue

    except asyncio.CancelledError:
        # Esto es esperado cuando main.py termina el ciclo
        await log(f"[Grupo {group_id}] Websocket cancelado (cierre normal).")
        
    except Exception as e:
        # Error crítico que tumba la conexión de este grupo
        await log(f"[Grupo {group_id}][ERROR] Error crítico en websocket: {e}")
        
    finally:
        # Asegura que el log se escriba al cerrar
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
    await log("🤖 PRICE TRACKER ACTIVADO (v2 Refactorizado)")

    # 1. Inicializar historial compartido
    price_history = {coin: [] for coin in coins}
    
    # 2. Crear UN solo BinanceSocketManager
    bm = BinanceSocketManager(client)

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
            continue # Omitir si el grupo está vacío
            
        task = asyncio.create_task(
            _handle_websocket_stream(bm, streams, price_history, group_id)
        )
        websocket_tasks.append(task)

    if not websocket_tasks:
        await log("[WARNING] No se crearon tareas de websocket (lista de monedas vacía).")
        await asyncio.sleep(duration_seconds) # Respetar el tiempo de espera
        return

    # 5. Esperar la duración del ciclo
    # Esta es la línea principal que "mantiene vivo" el handler.
    # Las tareas de websocket corren en segundo plano.
    try:
        await asyncio.sleep(duration_seconds)
        
    except asyncio.CancelledError:
        # Ocurre si el 'main.py' cancela el 'coin_handler'
        await log("[PRICE_HANDLER] Ciclo principal cancelado externamente.")
        raise # Propagar la cancelación para un cierre limpio
        
    finally:
        # 6. Cierre Limpio (Graceful Shutdown)
        # Se ejecuta cuando el sleep() termina o si es cancelado
        await log("⏰ Tiempo de ciclo alcanzado. Cerrando todos los websockets...")
        
        # Enviar señal de cancelación a todas las tareas
        for task in websocket_tasks:
            task.cancel()
        
        # Esperar a que todas las tareas terminen (y capturar sus excepciones si las hubo)
        results = await asyncio.gather(*websocket_tasks, return_exceptions=True)
        
        # Opcional: Loguear si alguna tarea falló con un error inesperado
        for i, res in enumerate(results):
            if isinstance(res, Exception) and not isinstance(res, asyncio.CancelledError):
                await log(f"[ERROR] Tarea de Websocket {i+1} finalizó con error: {res}")
                
        await log("✅ Todos los websockets cerrados. Price handler finalizado.")