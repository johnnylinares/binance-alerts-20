import time
import asyncio
from binance import BinanceSocketManager

from models.alert_handler import send_alert

THRESHOLD = 20
DATA_HOURS = 7200 # Mantenimiento de datos de las últimas 2 horas

# ===== PRICE TRACKER =====
async def price_handler(coins, b_client, bsm):
    print("'price_handler' function started.")

    price_history = {}
   
    socket = bsm.symbol_ticker_socket('!ticker@arr')
    
    async def handle_socket_message(ticker_data):
        try:
            symbol = ticker_data.get('s')
            if not symbol or symbol not in coins:
                return
               
            price = float(ticker_data.get('c', 0))
            if price <= 0:
                return
                
            current_time = time.time()
           
            if symbol not in price_history:
                price_history[symbol] = []
           
            # Mantener solo datos de las últimas 2 horas
            price_history[symbol].append((current_time, price))
            price_history[symbol] = [
                (t, p) for t, p in price_history[symbol]
                if current_time - t <= DATA_HOURS
            ]
           
            if len(price_history[symbol]) >= 2:
                old_price = price_history[symbol][0][1]
                change = ((price - old_price) / old_price) * 100
               
                if abs(change) >= THRESHOLD:
                    emoji = "🟢📈💵💰" if change > 0 else "🔴📉💵💰"

                    try:
                        vol_data = await b_client.futures_ticker(symbol=symbol)
                        volume = round(float(vol_data['volume']) / 1_000_000, 1)
                    except Exception:
                        volume = 0.0
                   
                    await send_alert(symbol, change, price, emoji[0], emoji[1], emoji[2], emoji[3], volume, b_client)
        
                    price_history[symbol] = []
                   
        except Exception as e:
            print(f"Error processing {ticker_data.get('s', 'unknown')}: {str(e)}")
    
    async def websocket_task():
        async with socket as s:
            while True:
                try:
                    all_tickers = await s.recv()
                    
                    if not all_tickers or not isinstance(all_tickers, list):
                        continue
                   
                    tasks = []
                    for ticker in all_tickers:
                        if ticker and ticker.get('s') in coins:
                            tasks.append(handle_socket_message(ticker))
                    
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                   
                except Exception as e:
                    print(f"WebSocket error: {str(e)}")
                    await asyncio.sleep(5)
    
    try:
        await asyncio.gather(
            websocket_task()
        )
    except Exception as e:
        print(f"Main task error: {str(e)}")
    finally:
        await b_client.close_connection()