import asyncio
from models.log_handler import log
from models.alert_handler import tp_sl_alert_handler 

TP1_PERCENTAGE = 0.05  # 5%
TP2_PERCENTAGE = 0.1   # 10%
TP3_PERCENTAGE = 0.15  # 15%
TP4_PERCENTAGE = 0.05  # 20%
SL_PERCENTAGE = 0.05  # 5%


async def trade_handler(bm, symbol, percentage_change, price, original_message_id):
    """
    Maneja el monitoreo de un trade individual para TP/SL
    después de una alerta de 20%.
    """
    
    # 1. Determinar Dirección y Niveles de TP/SL
    direction = "LONG" if percentage_change > 0 else "SHORT"
    entry_price = price
    
    if direction == "LONG":
        tp1_price = entry_price * (1 - TP1_PERCENTAGE)
        tp2_price = entry_price * (1 - TP2_PERCENTAGE)
        tp3_price = entry_price * (1 - TP3_PERCENTAGE)
        tp4_price = entry_price * (1 - TP4_PERCENTAGE)
        sl_price = entry_price * (1 + SL_PERCENTAGE)
    else: # SHORT
        tp1_price = entry_price * (1 + TP1_PERCENTAGE)
        tp2_price = entry_price * (1 + TP2_PERCENTAGE)
        tp3_price = entry_price * (1 + TP3_PERCENTAGE)
        tp4_price = entry_price * (1 + TP4_PERCENTAGE)
        sl_price = entry_price * (1 - SL_PERCENTAGE)

    await log(f"TRADE HANDLER: Monitoreando {symbol} ({direction})")

    stream = [f"{symbol.lower()}@ticker"]
    ts = bm.futures_multiplex_socket(stream)
    
    hit = None # Almacenará si fue "TP" o "SL"
    hit_price = None

    try:
        async with ts as tscm:
            while hit is None:
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
                
                if direction == "LONG":
                    if current_price <= tp1_price:
                        hit = "✅ TP1 (+5%)"
                        hit_price = current_price
                    elif current_price >= sl_price:
                        hit = "❌ SL (-5%)"
                        hit_price = current_price
                        
                elif direction == "SHORT":
                    if current_price >= tp1_price:
                        hit = "✅ TP1 (+5%)"
                        hit_price = current_price
                    elif current_price <= sl_price:
                        hit = "❌ SL (-5%)"
                        hit_price = current_price

    except asyncio.CancelledError:
        await log(f"TRADE HANDLER: Monitoreo de {symbol} cancelado.")
        return # Salir si la tarea principal se cancela
    except Exception as e:
        await log(f"TRADE HANDLER: [ERROR] en socket de {symbol}: {e}")
        return # Salir en caso de error

    # 5. Si se alcanzó un objetivo, notificar y cerrar
    if hit:
        await log(f"¡{hit} ALCANZADO! {symbol} a ${hit_price}")
        
        try:
            # Llama a la función de alerta con todos los parámetros
            await tp_sl_alert_handler(
                hit=hit,
                original_message_id=original_message_id
            )
        except Exception as e:
            await log(f"TRADE HANDLER: [ERROR] al enviar alerta TP/SL para {symbol}: {e}")

    await log(f"TRADE HANDLER: Finalizado monitoreo de {symbol}.")


    # TRADE HANDLER: [ERROR] al enviar alerta TP/SL para UAIUSDT: tp_sl_alert_handler() got an unexpected keyword argument 'reply_to_id'