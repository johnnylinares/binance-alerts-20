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
    
    direction = "SHORT" if percentage_change > 0 else "LONG"
    entry_price = price
    start_time = time.time()
    created_at_utc = datetime.now(pytz.utc)
    closed_at_utc = None

    if direction == "SHORT":
        tp1_price = entry_price * (1 - TP1_PERCENTAGE)
        tp2_price = entry_price * (1 - TP2_PERCENTAGE)
        tp3_price = entry_price * (1 - TP3_PERCENTAGE)
        tp4_price = entry_price * (1 - TP4_PERCENTAGE)
        sl_price = entry_price * (1 + SL_PERCENTAGE)
    else: # LONG
        tp1_price = entry_price * (1 + TP1_PERCENTAGE)
        tp2_price = entry_price * (1 + TP2_PERCENTAGE)
        tp3_price = entry_price * (1 + TP3_PERCENTAGE)
        tp4_price = entry_price * (1 + TP4_PERCENTAGE)
        sl_price = entry_price * (1 - SL_PERCENTAGE)

    await log(f"TRADE HANDLER: Monitoreando {symbol} ({direction})")

    stream = [f"{symbol.lower()}@ticker"]
    ts = bm.futures_multiplex_socket(stream)
    
    hit = 0 # Data for TP/SL

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
                
                if direction == "SHORT":
                    if hit == 0 and current_price >= sl_price:
                        hit = -1
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)
                    
                    elif hit == 0 and current_price <= tp1_price:
                        hit = 1
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)

                    elif hit == 1 and current_price <= tp2_price:
                        hit = 2
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)

                    elif hit == 2 and current_price <= tp3_price:
                        hit = 3
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)

                    elif hit == 3 and current_price <= tp4_price:
                        hit = 4
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)
                        
                if direction == "LONG":
                    if hit == 0 and current_price <= sl_price:
                        hit = -1
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)

                    elif hit == 0 and current_price >= tp1_price:
                        hit = 1
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)
                        
                    elif hit == 1 and current_price >= tp2_price:
                        hit = 2
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)

                    elif hit == 2 and current_price >= tp3_price:
                        hit = 3
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)

                    elif hit == 3 and current_price >= tp4_price:
                        hit = 4
                        closed_at_utc = datetime.now(pytz.utc)
                        await tp_sl_alert_handler(hit, original_message_id)

            if time.time() - start_time > 7800 and hit == 0:
                closed_at_utc = datetime.now(pytz.utc)
                await tp_sl_alert_handler(hit, original_message_id)
                    
    except asyncio.CancelledError:
        await log(f"TRADE HANDLER: Monitoreo de {symbol} cancelado.")
        return
    except Exception as e:
        await log(f"TRADE HANDLER: [ERROR] en socket de {symbol}: {e}")
        return
    
    finally:
        trade_data = {
            "created_at": created_at_utc.isoformat(),
            "closed_at": closed_at_utc.isoformat(),
            "symbol": symbol,
            "direction": direction,
            "volume": volume,
            "percentage": percentage_change,
            "result": hit * 5,
            "msg_id": original_message_id
        }
        
        await insert_trade(trade_data)
        await log(f"TRADE HANDLER: Finalizado monitoreo de {symbol}.")

    await log(f"TRADE HANDLER: Finalizado monitoreo de {symbol}.")