import time
import asyncio
from binance import BinanceSocketManager
from models.log_handler import log
from models.alert_handler import alert_handler

THRESHOLD = 20
TIME_WINDOW = 2 * 60 * 60 + 10 * 60
LOG_INTERVAL = 600
GROUP_SIZE = 200

async def handle_websocket_group(client, coins_group, price_history, group_id, alert_queue, stop_event):
    """
    Handles a single websocket connection for a group of coins.
    Procesa mensajes de forma no bloqueante y delega alertas a una cola.
    Se detiene cuando stop_event es activado.
    """
    
    bm = BinanceSocketManager(client)
    
    streams = [f"{coin.lower()}@ticker" for coin in coins_group]
    ts = bm.multiplex_socket(streams)

    last_log_time = time.time()
    messages_processed = 0

    try:
        await log(f"[Grupo {group_id}] Creando websocket para {len(coins_group)} monedas.")
        
        async with ts as tscm:
            while not stop_event.is_set():
                try:
                    # Timeout corto para poder verificar stop_event regularmente
                    msg = await asyncio.wait_for(tscm.recv(), timeout=1.0)
                    messages_processed += 1
                    
                except asyncio.TimeoutError:
                    # Timeout normal, continuar el loop
                    continue
                
                # Validación rápida del mensaje
                if 'data' not in msg or not isinstance(msg['data'], dict):
                    continue
                
                ticker_data = msg['data']
                
                # Solo procesar mensajes de ticker
                if ticker_data.get('e') != '24hrTicker':
                    continue
                
                symbol = ticker_data.get('s')
                
                # Verificar que la moneda está en nuestro tracking
                if symbol not in price_history:
                    continue
                
                # Procesar precio de forma rápida
                try:
                    price = float(ticker_data['c'])
                    volume = round(float(ticker_data['q']) / 1000000, 1)
                    now = time.time()
                    
                    # Actualizar historial de precios
                    price_history[symbol].append((now, price))
                    
                    # Limpiar datos antiguos (solo si hay muchos para evitar overhead)
                    if len(price_history[symbol]) > 10:
                        price_history[symbol] = [
                            p for p in price_history[symbol] 
                            if now - p[0] <= TIME_WINDOW
                        ]
                    
                    # Calcular cambio porcentual si hay suficiente historial
                    if len(price_history[symbol]) >= 2:
                        old_price = price_history[symbol][0][1]
                        percentage_change = ((price - old_price) / old_price) * 100
                        
                        # Si supera el umbral, enviar a la cola de alertas
                        if abs(percentage_change) >= THRESHOLD:
                            emoji = ("🟢", "📈") if percentage_change > 0 else ("🔴", "📉")
                            
                            # Enviar a la cola sin esperar (non-blocking)
                            try:
                                alert_queue.put_nowait({
                                    'symbol': symbol,
                                    'percentage_change': percentage_change,
                                    'price': price,
                                    'emoji': emoji,
                                    'volume': volume,
                                    'group_id': group_id
                                })
                            except asyncio.QueueFull:
                                await log(f"[Grupo {group_id}][WARNING] Cola de alertas llena, descartando alerta de {symbol}")
                            
                            # Resetear historial después de alerta
                            price_history[symbol] = []
                
                except (ValueError, KeyError, TypeError):
                    # Ignorar mensajes malformados sin bloquear
                    continue
                
                # Log periódico (sin bloquear el procesamiento)
                current_time = time.time()
                if current_time - last_log_time >= LOG_INTERVAL:
                    elapsed = current_time - last_log_time
                    rate = messages_processed / elapsed if elapsed > 0 else 0
                    last_log_time = current_time
                    messages_processed = 0
                    
                    # Log asíncrono sin await para no bloquear
                    asyncio.create_task(
                        log(f"[Grupo {group_id}] 🔍 Chequeando {len(coins_group)} monedas | {rate:.1f} msg/s")
                    )

    except asyncio.CancelledError:
        await log(f"[Grupo {group_id}] Websocket cancelado.")
        raise
    except Exception as e:
        await log(f"[Grupo {group_id}][ERROR] Error crítico en el grupo de websocket: {e}")
        raise
    finally:
        await log(f"[Grupo {group_id}] El websocket se ha cerrado.")

async def alert_worker(alert_queue, stop_event):
    """
    Worker independiente que procesa alertas de la cola sin bloquear los websockets.
    Se detiene cuando stop_event es activado y la cola está vacía.
    """
    await log("🟢 Alert worker iniciado.")
    alerts_sent = 0
    
    try:
        while not stop_event.is_set():
            try:
                # Esperar por alertas con timeout para poder verificar stop_event
                alert_data = await asyncio.wait_for(alert_queue.get(), timeout=1.0)
                
                try:
                    # Procesar la alerta
                    await log(f"[Grupo {alert_data['group_id']}] 📊 COIN FOUND: {alert_data['symbol']} ({alert_data['percentage_change']:+.2f}%)")
                    
                    await alert_handler(
                        alert_data['symbol'],
                        alert_data['percentage_change'],
                        alert_data['price'],
                        alert_data['emoji'],
                        alert_data['volume']
                    )
                    
                    alerts_sent += 1
                    
                except Exception as e:
                    await log(f"[ERROR] Error enviando alerta para {alert_data['symbol']}: {e}")
                finally:
                    # Marcar tarea como completada
                    alert_queue.task_done()
                    
            except asyncio.TimeoutError:
                # Timeout normal, continuar verificando
                continue
        
        # Procesar alertas pendientes antes de cerrar
        await log(f"⏸️ Alert worker cerrando. Alertas enviadas en este ciclo: {alerts_sent}")
        
        pending = 0
        while not alert_queue.empty():
            try:
                alert_data = await asyncio.wait_for(alert_queue.get(), timeout=0.1)
                try:
                    await alert_handler(
                        alert_data['symbol'],
                        alert_data['percentage_change'],
                        alert_data['price'],
                        alert_data['emoji'],
                        alert_data['volume']
                    )
                    pending += 1
                except Exception as e:
                    await log(f"[ERROR] Error enviando alerta pendiente: {e}")
                finally:
                    alert_queue.task_done()
            except asyncio.TimeoutError:
                break
        
        if pending > 0:
            await log(f"✅ {pending} alertas pendientes procesadas.")
        
        await log(f"🔴 Alert worker cerrado. Total alertas: {alerts_sent + pending}")
        
    except asyncio.CancelledError:
        await log("Alert worker cancelado.")
        raise
    except Exception as e:
        await log(f"[ERROR] Error en alert_worker: {e}")
        raise

async def price_handler(client, coins, duration_seconds):
    """
    Main function to manage multiple websocket groups concurrently.
    Usa una cola de alertas para no bloquear el procesamiento de mensajes.
    
    Args:
        client: Binance AsyncClient instance
        coins: Set de símbolos de monedas a trackear
        duration_seconds: Duración en segundos antes de detenerse automáticamente
    """
    await log("🤖 PRICE TRACKER ACTIVATED")

    # Inicializar estructuras de datos compartidas
    price_history = {coin: [] for coin in coins}
    
    # Cola para manejar alertas de forma asíncrona
    alert_queue = asyncio.Queue(maxsize=1000)
    
    # Evento para señalar detención
    stop_event = asyncio.Event()

    # Dividir monedas en grupos de 200
    coins_list = list(coins)
    groups = [coins_list[i:i + GROUP_SIZE] for i in range(0, len(coins_list), GROUP_SIZE)]
    
    await log(f"Monedas filtradas: {len(coins)}. Creando {len(groups)} grupos de websockets...")
    await log(f"⏰ Duración del ciclo: {duration_seconds/3600:.1f} horas")

    # Crear tareas para cada grupo de websockets
    websocket_tasks = [
        asyncio.create_task(
            handle_websocket_group(client, group, price_history, i+1, alert_queue, stop_event)
        ) for i, group in enumerate(groups)
    ]
    
    # Crear worker para procesar alertas
    alert_task = asyncio.create_task(alert_worker(alert_queue, stop_event))

    try:
        # Esperar la duración especificada
        await asyncio.sleep(duration_seconds)
        
        # Señalar a todas las tareas que deben detenerse
        await log("⏰ Tiempo alcanzado. Iniciando cierre graceful de websockets...")
        stop_event.set()
        
        # Esperar a que todas las tareas terminen gracefully
        await asyncio.wait_for(
            asyncio.gather(alert_task, *websocket_tasks, return_exceptions=True),
            timeout=30.0  # 30 segundos para cerrar gracefully
        )
        
        await log("✅ Todas las conexiones cerradas correctamente.")
        
    except asyncio.TimeoutError:
        await log("⚠️ Timeout en cierre graceful. Forzando cancelación...")
        # Si el cierre graceful falla, cancelar forzadamente
        alert_task.cancel()
        for task in websocket_tasks:
            task.cancel()
        
        await asyncio.gather(alert_task, *websocket_tasks, return_exceptions=True)
        
    except asyncio.CancelledError:
        await log("Las tareas de websockets han sido canceladas externamente.")
        stop_event.set()
        raise
        
    except Exception as e:
        await log(f"[ERROR] Error en la ejecución de las tareas de websockets: {e}")
        stop_event.set()
        raise
        
    finally:
        # Asegurar que todas las tareas estén canceladas
        if not stop_event.is_set():
            stop_event.set()
        
        alert_task.cancel()
        for task in websocket_tasks:
            task.cancel()
        
        await asyncio.gather(alert_task, *websocket_tasks, return_exceptions=True)
        
        await log("🔴 Price handler finalizado.")