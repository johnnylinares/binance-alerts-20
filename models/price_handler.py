import asyncio
import time
from collections import defaultdict

from models.alert_handler import send_alert

THRESHOLD = 20.0
TIME_WINDOW = 3 * 60 * 60  # 3 horas
MAX_BATCH_SIZE = 200

class PriceTracker:
    def __init__(self):
        self.price_history = defaultdict(list)
        self.last_log_time = time.time()
        self.log_interval = 600  # 10 minutos
        
    def add_price_data(self, symbol, price, timestamp):
        """Agregar nuevo precio y limpiar datos antiguos"""
        self.price_history[symbol].append((timestamp, price))
        # Mantener solo datos dentro de la ventana de tiempo
        cutoff_time = timestamp - TIME_WINDOW
        self.price_history[symbol] = [
            (t, p) for t, p in self.price_history[symbol] 
            if t > cutoff_time
        ]
    
    async def check_price_change(self, symbol, current_price, volume_24h):
        """Verificar cambio de precio y enviar alerta si es necesario"""
        if len(self.price_history[symbol]) < 2:
            return
            
        # Obtener el precio más antiguo en la ventana de tiempo
        oldest_price = self.price_history[symbol][0][1]
        
        # Calcular cambio porcentual
        percentage_change = ((current_price - oldest_price) / oldest_price) * 100
        
        if abs(percentage_change) >= THRESHOLD:
            print(f"📊 MONEDA ENCONTRADA: {symbol} - Cambio: {percentage_change:+.2f}%")
            
            # Determinar emojis según el cambio
            if percentage_change > 0:
                emoji1, emoji2 = "🟢", "📈"
            else:
                emoji1, emoji2 = "🔴", "📉"
            
            # Enviar alerta
            await send_alert(symbol, percentage_change, current_price, emoji1, emoji2, volume_24h)
            
            # Limpiar historial para evitar alertas duplicadas
            self.price_history[symbol] = []
    
    def log_status(self):
        """Mostrar estado cada cierto tiempo"""
        now = time.time()
        if now - self.last_log_time >= self.log_interval:
            active_symbols = len([s for s in self.price_history if len(self.price_history[s]) > 0])
            print(f"🔍 Monitoreando {active_symbols} símbolos activos")
            self.last_log_time = now

async def price_handler(bsm, coins, b_client):
    """Función principal para monitorear precios"""
    print("🤖 RASTREADOR DE PRECIOS ACTIVADO")
    print(f"🎯 Umbral de alerta: {THRESHOLD}%")
    print(f"⏰ Ventana de tiempo: {TIME_WINDOW/3600:.1f} horas")
    print(f"📦 Tamaño máximo de lote: {MAX_BATCH_SIZE}")
    
    tracker = PriceTracker()
    coins_list = list(coins)
    
    # Dividir monedas en lotes para no sobrecargar la API
    batches = []
    for i in range(0, len(coins_list), MAX_BATCH_SIZE):
        batch = coins_list[i:i + MAX_BATCH_SIZE]
        batches.append(batch)
    
    print(f"📦 Creados {len(batches)} lotes para procesar")
    
    # Procesar cada lote
    tasks = []
    for i, batch in enumerate(batches):
        print(f"🔄 Iniciando lote {i+1}/{len(batches)} con {len(batch)} símbolos")
        
        try:
            # Crear streams para el lote
            streams = [f"{symbol.lower()}@ticker" for symbol in batch]
            socket = bsm.multiplex_socket(streams)
            
            # Crear tarea para manejar este lote
            task = asyncio.create_task(
                handle_batch_stream(socket, tracker, batch),
                name=f"batch_{i+1}"
            )
            tasks.append(task)
            
            # Pequeña pausa entre lotes
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"❌ Error creando stream para lote {i+1}: {e}")
            continue
    
    if not tasks:
        print("❌ No se pudieron crear streams")
        return
    
    print(f"✅ {len(tasks)} streams creados exitosamente")
    print("🟢 Bot monitoreando activamente...")
    
    try:
        # Ejecutar todas las tareas
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"❌ Error en price handler: {e}")
    finally:
        # Limpiar tareas
        for task in tasks:
            if not task.done():
                task.cancel()
        print("🛑 Rastreador de precios detenido")

async def handle_batch_stream(socket, tracker, batch_symbols):
    """Manejar stream de un lote de símbolos"""
    try:
        async with socket as stream:
            while True:
                try:
                    msg = await stream.recv()
                    if not msg:
                        continue
                    
                    # Procesar mensaje
                    data = msg.get('data', msg)
                    
                    if 's' not in data or 'c' not in data or 'q' not in data:
                        continue
                    
                    symbol = data['s']
                    current_price = float(data['c'])
                    volume_24h = round(float(data['q']) / 1_000_000, 1)
                    timestamp = int(time.time())
                    
                    # Agregar datos de precio
                    tracker.add_price_data(symbol, current_price, timestamp)
                    
                    # Verificar cambios de precio
                    await tracker.check_price_change(symbol, current_price, volume_24h)
                    
                    # Mostrar estado periódicamente
                    tracker.log_status()
                    
                except Exception as msg_error:
                    print(f"❌ Error procesando mensaje: {msg_error}")
                    await asyncio.sleep(0.01)
                    
    except Exception as e:
        print(f"❌ Error en stream del lote: {e}")
        await asyncio.sleep(5)