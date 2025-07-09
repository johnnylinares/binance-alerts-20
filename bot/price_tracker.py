import time
import asyncio
from binance.client import Client

from logs import log_message
from bot.alert_handler import send_alert

async def price_tracker(client: Client, bot, channel_id, threshold=20):
    await log_message(message="🤖 PRICE TRACKER ACTIVATED")

    price_history = {}
    log_interval = 600
    last_log_time = time.time()

    while True:
        try:
            tickers = client.futures_ticker()
            now = time.time()

            for ticker in tickers:
                symbol = ticker['symbol']
                price = float(ticker['lastPrice'])
                volume_24h = round((float(ticker['volume'])) / 1000000, 1)

                if not symbol.endswith("USDT"):
                    continue
                
                if symbol not in price_history:
                    price_history[symbol] = []

                price_history[symbol].append((now, price))
                price_history[symbol] = [p for p in price_history[symbol] if now - p[0] <= 10800]

                if len(price_history[symbol]) >= 2:
                    old_price = price_history[symbol][0][1]
                    percentage_change = ((price - old_price) / old_price) * 100

                    if abs(percentage_change) >= threshold:
                        await log_message(message=f"📊 COIN FOUND: {symbol}")

                        if percentage_change > 0:
                            emoji1 = "🟢"
                            emoji2 = "📈"
                        else:
                            emoji1 = "🔴"
                            emoji2 = "📉"

                        await send_alert(symbol, percentage_change, price, emoji1, emoji2, volume_24h)
                        price_history[symbol] = []
                        
            if now - last_log_time >= log_interval:
                log_message_text = f"🔍 Checking coins"
                await log_message(log_message_text)
                last_log_time = now

            await asyncio.sleep(10)

        except Exception as e:
            await log_message(message=f"[ERROR] {e}")
            await asyncio.sleep(10)
