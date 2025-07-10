# ===== LIBRARYS =====
import time
import asyncio
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException

# ===== MODULES =====
from logs import log_message 
from bot.alert_handler import send_alert

# ===== CONSTANTS =====
THRESHOLD = 20 # % alert´s change
LOG_INTERVAL = 900 # 15 minute log interval

# ===== WEBSOCKET TRACKER =====
async def price_tracker(bot, channel_id):
    await log_message("🤖 PRICE TRACKER (WebSocket) ACTIVATED")
    
    price_history = {} # Dictionary to store price history for each symbol
    last_log_time = time.time() 
    
    client = await AsyncClient.create() # For asynchronous Binance client
    bsm = BinanceSocketManager(client)
    
    # ===== COINS =====
    exchange_info = await client.futures_exchange_info()  # Pairs info
    now_ms = int(time.time() * 1000)
    three_months_ms = 90 * 24 * 60 * 60 * 1000  # 90 días en ms

    pair_filter = []
    for s in exchange_info['symbols']:
        if not s['symbol'].endswith('USDT'):
            continue

        onboard_date = s.get('onboardDate', 0)
        if now_ms - onboard_date < three_months_ms:
            continue
        
        try:
            ticker = await client.futures_ticker(symbol=s['symbol'])
            volume_24h = float(ticker['quoteVolume'])  # quoteVolume es en USDT
        except Exception:
            continue
        if volume_24h < 10_000_000:
            continue
        pair_filter.append(s['symbol'])

    usdt_pairs = pair_filter
    
    # ===== WEBSOCKET REQUESTS =====
    socket = bsm.symbol_ticker_socket('!ticker@arr')

    # ===== HANDLE SOCKET MESSAGES =====
    async def handle_socket_message(msg):
        nonlocal last_log_time
        
        try:
            symbol = msg['s']
            price = float(msg['c'])
            now = time.time()
            
            if symbol not in price_history: 
                price_history[symbol] = []
            
            # TRACKING TIME (2H)
            price_history[symbol].append((now, price))
            price_history[symbol] = [p for p in price_history[symbol] if now - p[0] <= 7200]
            
            # PERCENT CHANGE
            if len(price_history[symbol]) >= 2:
                old_price = price_history[symbol][0][1]
                percentage_change = ((price - old_price) / old_price) * 100
                
                if abs(percentage_change) >= THRESHOLD:
                    await log_message(f"📊 COIN FOUND: {symbol}")
                    
                    emoji1 = "🟢" if percentage_change > 0 else "🔴"
                    emoji2 = "📈" if percentage_change > 0 else "📉"
                    
                    # API REST VOLUME
                    try:
                        ticker = await client.futures_ticker(symbol=symbol)
                        volume_24h = round(float(ticker['volume']) / 1000000, 1)
                    except BinanceAPIException:
                        volume_24h = 0.0
                    
                    # ===== SEND ALERT =====
                    await send_alert(symbol, percentage_change, price, emoji1, emoji2, volume_24h)
                    price_history[symbol] = []  # Resetear después de alerta
            
            # Log periódico
            if now - last_log_time >= LOG_INTERVAL:
                await log_message("🔍 Monitoring active WebSockets")
                last_log_time = now
                
        except Exception as e:
            await log_message(f"[WEBSOCKET ERROR] {e}")
    
    async with socket as s:
        while True:
            try:
                msg = await s.recv()
                # msg es una lista de diccionarios, uno por símbolo
                for ticker in msg:
                    symbol = ticker['s']
                    if symbol in usdt_pairs:
                        await handle_socket_message(ticker)
            except Exception as e:
                await log_message(f"[STREAM ERROR] {e}")
                await asyncio.sleep(5)

    await client.close_connection()