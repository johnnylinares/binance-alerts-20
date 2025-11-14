import asyncio
import time
import pytz
from datetime import datetime
from models.log_handler import log
from models.alert_handler import tp_sl_alert_handler 
from models.db_handler import insert_trade

TP1_PERCENTAGE = 0.05  # 05%
TP2_PERCENTAGE = 0.10  # 10%
TP3_PERCENTAGE = 0.15  # 15%
TP4_PERCENTAGE = 0.20  # 20%
SL_PERCENTAGE = 0.05   # -5%

async def trade_handler(bm, symbol, percentage_change, price, original_message_id, volume):
    """
    Maneja el monitoreo de un trade individual para TP/SL
    después de una alerta de 20%.
    """
    
    # DETERMINAR INFORMACIÓN PRINCIPAL
    entry_price = price
    close_price = None
    current_price = entry_price

    # TIEMPOS DE ENTRADA Y SALIDA
    start_time = time.time()
    vzla_utc = pytz.timezone('America/Caracas')
    created_at = datetime.now(vzla_utc).isoformat()
    closed_at = None

    # TP Y SL
    if percentage_change > 0:  # SHORT
        tp_prices = [
            entry_price * (1 - TP1_PERCENTAGE),
            entry_price * (1 - TP2_PERCENTAGE),
            entry_price * (1 - TP3_PERCENTAGE),
            entry_price * (1 - TP4_PERCENTAGE),
        ]
        sl_price = entry_price * (1 + SL_PERCENTAGE)
    else:  # LONG
        tp_prices = [
            entry_price * (1 + TP1_PERCENTAGE),
            entry_price * (1 + TP2_PERCENTAGE),
            entry_price * (1 + TP3_PERCENTAGE),
            entry_price * (1 + TP4_PERCENTAGE),
        ]
        sl_price = entry_price * (1 - SL_PERCENTAGE)

    await log(f"TRADE HANDLER: Monitoreando {symbol} ({percentage_change:+.2f}%)")

    stream = [f"{symbol.lower()}@ticker"]
    ts = bm.futures_multiplex_socket(stream)
    
    hit = 0  # Information TP/SL
    result = 0.0  # Inicializar result

    async def hited(hit_type, entry_price, close_price, percentage_change):
        """Calcula el resultado del trade y envía alerta"""
        if percentage_change > 0:  # SHORT
            calc_result = round(((entry_price / close_price) - 1) * 100, 2)
        else:  # LONG
            calc_result = round(((close_price / entry_price) - 1) * 100, 2)
        
        await tp_sl_alert_handler(hit_type, calc_result, original_message_id)
        return calc_result

    try:
        async with ts as tscm:
            while hit != 4 and hit != -1 and time.time() - start_time < 7800:
                try:
                    msg = await asyncio.wait_for(tscm.recv(), timeout=60.0)
                except asyncio.TimeoutError:
                    continue

                if 'data' not in msg or not isinstance(msg['data'], dict):
                    continue
                
                ticker_data = msg['data']
                
                if ticker_data.get('s') != symbol:
                    continue
                
                try:
                    current_price = float(ticker_data['c'])
                except (ValueError, KeyError, TypeError):
                    continue
                
                # SHORT (percentage_change > 0)
                if percentage_change > 0:
                    if hit == 0 and current_price >= sl_price:
                        hit = -1
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(-1, entry_price, close_price, percentage_change)
                    
                    elif hit == 0 and current_price <= tp_prices[0]:
                        hit = 1
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(1, entry_price, close_price, percentage_change)

                    elif hit == 1 and current_price <= tp_prices[1]:
                        hit = 2
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(2, entry_price, close_price, percentage_change)

                    elif hit == 2 and current_price <= tp_prices[2]:
                        hit = 3
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(3, entry_price, close_price, percentage_change)

                    elif hit == 3 and current_price <= tp_prices[3]:
                        hit = 4
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(4, entry_price, close_price, percentage_change)
                        
                # LONG (percentage_change < 0)
                else:
                    if hit == 0 and current_price <= sl_price:
                        hit = -1
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(-1, entry_price, close_price, percentage_change)

                    elif hit == 0 and current_price >= tp_prices[0]:
                        hit = 1
                        closed_at = datetime.now(vzla_utc).isoformat()
                        result = await hited(1, entry_price, close_price, percentage_change)
                        close_price = current_price
                        
                    elif hit == 1 and current_price >= tp_prices[1]:
                        hit = 2
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(2, entry_price, close_price, percentage_change)

                    elif hit == 2 and current_price >= tp_prices[2]:
                        hit = 3
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(3, entry_price, close_price, percentage_change)

                    elif hit == 3 and current_price >= tp_prices[3]:
                        hit = 4
                        closed_at = datetime.now(vzla_utc).isoformat()
                        close_price = current_price
                        result = await hited(4, entry_price, close_price, percentage_change)

            # Manejar timeout - cerrar trade si no llegó a ningún TP/SL
            if time.time() - start_time >= 7800 and hit == 0:
                closed_at = datetime.now(vzla_utc).isoformat()
                close_price = current_price
                result = await hited(0, entry_price, close_price, percentage_change)
                    
    except asyncio.CancelledError:
        await log(f"TRADE HANDLER: Monitoreo de {symbol} cancelado.")
        if closed_at is None:
            closed_at = datetime.now(vzla_utc).isoformat()
        if close_price is None:
            close_price = current_price
        return
    except Exception as e:
        await log(f"TRADE HANDLER: [ERROR] en socket de {symbol}: {e}")
        if closed_at is None:
            closed_at = datetime.now(vzla_utc).isoformat()
        if close_price is None:
            close_price = current_price
        return

    finally:
        if closed_at is None:
            await log(f"TRADE HANDLER: Monitoreo de {symbol} finalizado sin cierre. No se insertará en DB.")
            return
        
        trade_data = {
            "created_at": created_at,
            "closed_at": closed_at,
            "symbol": symbol,
            "direction": "SHORT" if percentage_change > 0 else "LONG",
            "volume": round(volume, 2),
            "percentage": round(percentage_change, 2),
            "result": result,
            "msg_id": original_message_id,
            "entry_price": entry_price,
            "close_price": close_price,
        }
        
        await insert_trade(trade_data)
        await log(f"TRADE HANDLER: Finalizado monitoreo de {symbol}.")