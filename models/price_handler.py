import time
import asyncio
from binance import BinanceSocketManager
from models.log_handler import log
from models.alert_handler import alert_handler

THRESHOLD = 20
TIME_WINDOW = 2 * 60 * 60 + 10 * 60
LOG_INTERVAL = 600
GROUP_SIZE = 50

async def handle_websocket_group(client, coins_group, price_history, log_timestamp):
    bm = BinanceSocketManager(client)
    
    streams = [f"{coin.lower()}@ticker" for coin in coins_group]
    ts = bm.multiplex_socket(streams)

    try:
        await log(f"Creando websocket para {len(coins_group)} monedas.")
        
        async with ts as tscm:
            while True:
                msg = await tscm.recv()
                
                if 'data' in msg and isinstance(msg['data'], dict):
                    ticker_data = msg['data']
                    
                    if ticker_data.get('e') == '24hrTicker':
                        symbol = ticker_data.get('s')
                        
                        if symbol in price_history:
                            price = float(ticker_data['c'])
                            volume = round(float(ticker_data['v']) / 1000000, 1)
                            now = time.time()
                            
                            price_history[symbol].append((now, price))
                            
                            price_history[symbol] = [
                                p for p in price_history[symbol] 
                                if now - p[0] <= TIME_WINDOW
                            ]
                            
                            if len(price_history[symbol]) >= 2:
                                old_price = price_history[symbol][0][1]
                                percentage_change = ((price - old_price) / old_price) * 100
                                
                                if abs(percentage_change) >= THRESHOLD:
                                    await log(f"📊 Moneda encontrada: {symbol}")
                                    
                                    if percentage_change > 0:
                                        emoji = "🟢📈"
                                    else:
                                        emoji = "🔴📉"

                                    await alert_handler(symbol, percentage_change, price, emoji, volume)
                                    
                                    price_history[symbol] = []
                else:
                    await log(f"[DEBUG] Mensaje inesperado recibido: {msg}")
                
                current_time = time.time()
                if current_time - log_timestamp['last_log'] >= LOG_INTERVAL:
                    await log("🔍 Chequeando monedas...")
                    log_timestamp['last_log'] = current_time

    except Exception as e:
        await log(f"[ERROR] Error crítico en el grupo de websocket: {e}")

async def price_handler(client, coins):
    await log("🤖 PRICE TRACKER ACTIVADO")

    price_history = {coin: [] for coin in coins}
    
    log_timestamp = {'last_log': time.time()}

    coins_list = list(coins)
    groups = [coins_list[i:i + GROUP_SIZE] for i in range(0, len(coins_list), GROUP_SIZE)]
    
    await log(f"Monedas filtradas: {len(coins)}. Creando {len(groups)} grupos de websockets...")

    tasks = [
        asyncio.create_task(
            handle_websocket_group(client, group, price_history, log_timestamp)
        ) for group in groups
    ]
    
    await asyncio.gather(*tasks)
