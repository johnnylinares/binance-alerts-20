# ===== LIBRARIES =====
import asyncio
import time
from datetime import datetime
from binance import AsyncClient
from typing import Dict, List, Optional

# ===== MODULES =====
from data.google_sheets import add_operation, update_operation_result
from src.config.logs import logging
from src.config.settings import API_KEY, API_SECRET

# ===== CONSTANTS =====
STOP_LOSS_PERCENT = 5  # 5% stop loss
TAKE_PROFIT_LEVELS = {
    'TP1': 5,   # 5% take profit 1
    'TP2': 10,  # 10% take profit 2
    'TP3': 15,  # 15% take profit 3
    'TP4': 20   # 20% take profit 4
}

# ===== GLOBAL VARIABLES =====
active_operations: Dict[str, Dict] = {}  # Almacena operaciones activas
client: Optional[AsyncClient] = None

# ===== OPERATION TRACKING =====
class OperationTracker:
    def __init__(self):
        self.operations = active_operations
    
    async def start_tracking(self, symbol: str, direction: str, entry_price: float):
        """Inicia el seguimiento de una nueva operación"""
        try:
            # Calcular niveles de TP y SL
            if direction.upper() == "LONG":
                sl_price = entry_price * (1 - STOP_LOSS_PERCENT / 100)
                tp_levels = {
                    'TP1': entry_price * (1 + TAKE_PROFIT_LEVELS['TP1'] / 100),
                    'TP2': entry_price * (1 + TAKE_PROFIT_LEVELS['TP2'] / 100),
                    'TP3': entry_price * (1 + TAKE_PROFIT_LEVELS['TP3'] / 100),
                    'TP4': entry_price * (1 + TAKE_PROFIT_LEVELS['TP4'] / 100)
                }
            else:  # SHORT
                sl_price = entry_price * (1 + STOP_LOSS_PERCENT / 100)
                tp_levels = {
                    'TP1': entry_price * (1 - TAKE_PROFIT_LEVELS['TP1'] / 100),
                    'TP2': entry_price * (1 - TAKE_PROFIT_LEVELS['TP2'] / 100),
                    'TP3': entry_price * (1 - TAKE_PROFIT_LEVELS['TP3'] / 100),
                    'TP4': entry_price * (1 - TAKE_PROFIT_LEVELS['TP4'] / 100)
                }
            
            # Crear registro de operación
            operation = {
                'symbol': symbol,
                'direction': direction.upper(),
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_levels': tp_levels,
                'start_time': time.time(),
                'status': 'ACTIVE',
                'tp_reached': [],
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Agregar a operaciones activas
            self.operations[symbol] = operation
            
            # Registrar en Google Sheets
            await add_operation(operation)
            
            logging.info(f"Started tracking {symbol} - {direction} at {entry_price}")
            
        except Exception as e:
            logging.error(f"Error starting tracking for {symbol}: {str(e)}")
    
    async def check_price_levels(self, symbol: str, current_price: float):
        """Verifica si el precio actual ha alcanzado algún nivel de TP o SL"""
        if symbol not in self.operations:
            return
            
        operation = self.operations[symbol]
        
        if operation['status'] != 'ACTIVE':
            return
            
        try:
            direction = operation['direction']
            entry_price = operation['entry_price']
            sl_price = operation['sl_price']
            tp_levels = operation['tp_levels']
            
            # Verificar Stop Loss
            if direction == "LONG":
                if current_price <= sl_price:
                    await self._close_operation(symbol, 'SL', current_price)
                    return
            else:  # SHORT
                if current_price >= sl_price:
                    await self._close_operation(symbol, 'SL', current_price)
                    return
            
            # Verificar Take Profits
            for tp_name, tp_price in tp_levels.items():
                if tp_name not in operation['tp_reached']:
                    if direction == "LONG":
                        if current_price >= tp_price:
                            await self._hit_take_profit(symbol, tp_name, current_price)
                    else:  # SHORT
                        if current_price <= tp_price:
                            await self._hit_take_profit(symbol, tp_name, current_price)
                            
        except Exception as e:
            logging.error(f"Error checking price levels for {symbol}: {str(e)}")
    
    async def _hit_take_profit(self, symbol: str, tp_name: str, price: float):
        """Registra cuando se alcanza un Take Profit"""
        try:
            operation = self.operations[symbol]
            operation['tp_reached'].append(tp_name)
            
            # Calcular profit
            entry_price = operation['entry_price']
            direction = operation['direction']
            
            if direction == "LONG":
                profit_percent = ((price - entry_price) / entry_price) * 100
            else:  # SHORT
                profit_percent = ((entry_price - price) / entry_price) * 100
            
            # Si alcanza TP4, cerrar operación
            if tp_name == 'TP4':
                await self._close_operation(symbol, 'TP4', price)
            else:
                # Actualizar en Google Sheets
                await update_operation_result(symbol, tp_name, profit_percent)
                
            logging.info(f"{symbol} reached {tp_name} at {price} - Profit: {profit_percent:.2f}%")
            
        except Exception as e:
            logging.error(f"Error handling take profit for {symbol}: {str(e)}")
    
    async def _close_operation(self, symbol: str, result: str, close_price: float):
        """Cierra una operación y actualiza el registro"""
        try:
            operation = self.operations[symbol]
            operation['status'] = 'CLOSED'
            operation['close_price'] = close_price
            operation['result'] = result
            operation['close_time'] = time.time()
            
            # Calcular profit final
            entry_price = operation['entry_price']
            direction = operation['direction']
            
            if direction == "LONG":
                profit_percent = ((close_price - entry_price) / entry_price) * 100
            else:  # SHORT
                profit_percent = ((entry_price - close_price) / entry_price) * 100
            
            operation['final_profit'] = profit_percent
            
            # Actualizar en Google Sheets
            await update_operation_result(symbol, result, profit_percent)
            
            # Remover de operaciones activas
            del self.operations[symbol]
            
            logging.info(f"{symbol} closed with {result} at {close_price} - Final Profit: {profit_percent:.2f}%")
            
        except Exception as e:
            logging.error(f"Error closing operation for {symbol}: {str(e)}")
    
    def get_active_operations(self) -> Dict:
        """Retorna las operaciones activas"""
        return self.operations.copy()

# ===== GLOBAL TRACKER INSTANCE =====
tracker = OperationTracker()

# ===== MAIN FUNCTIONS =====
async def initialize_signal_handler():
    """Inicializa el manejador de señales"""
    global client
    try:
        client = await AsyncClient.create(api_key=API_KEY, api_secret=API_SECRET)
        logging.info("Signal handler initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing signal handler: {str(e)}")

async def start_operation_tracking(symbol: str, direction: str, entry_price: float):
    """Inicia el seguimiento de una nueva operación"""
    await tracker.start_tracking(symbol, direction, entry_price)

async def monitor_operations():
    """Función principal para monitorear operaciones activas"""
    global client
    
    if not client:
        await initialize_signal_handler()
    
    while True:
        try:
            active_ops = tracker.get_active_operations()
            
            if not active_ops:
                await asyncio.sleep(5)  # Esperar 5 segundos si no hay operaciones
                continue
            
            # Obtener precios actuales para todas las operaciones activas
            symbols = list(active_ops.keys())
            
            for symbol in symbols:
                try:
                    ticker = await client.futures_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                    
                    await tracker.check_price_levels(symbol, current_price)
                    
                except Exception as e:
                    logging.error(f"Error getting price for {symbol}: {str(e)}")
                    continue
            
            await asyncio.sleep(1)  # Revisar cada segundo
            
        except Exception as e:
            logging.error(f"Error in monitor_operations: {str(e)}")
            await asyncio.sleep(5)

async def close_signal_handler():
    """Cierra el manejador de señales"""
    global client
    if client:
        await client.close_connection()
        logging.info("Signal handler closed")

# ===== MANUAL OPERATION MANAGEMENT =====
async def manual_add_operation(symbol: str, direction: str, entry_price: float):
    """Permite agregar manualmente una operación"""
    await start_operation_tracking(symbol, direction, entry_price)

async def manual_close_operation(symbol: str, result: str = 'MANUAL'):
    """Permite cerrar manualmente una operación"""
    if symbol in active_operations:
        try:
            ticker = await client.futures_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            await tracker._close_operation(symbol, result, current_price)
        except Exception as e:
            logging.error(f"Error closing manual operation for {symbol}: {str(e)}")

def get_operation_status(symbol: str) -> Optional[Dict]:
    """Obtiene el estado actual de una operación"""
    return active_operations.get(symbol)

def get_all_active_operations() -> Dict:
    """Obtiene todas las operaciones activas"""
    return tracker.get_active_operations()