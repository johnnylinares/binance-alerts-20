import time
import asyncio
from binance import BinanceSocketManager

from models.price_handler import price_tracker

async def coin_handler(b_client):
    print("'coin_handler' function started.")

    try:
        exchange_info = await b_client.futures_exchange_info()

        l_coins = [
            s['symbol'] for s in exchange_info['symbols'] if s['symbol'].endswith('USDT') and
            (int(time.time() * 1000) - s.get('onboardDate', 0)) >= (90 * 24 * 60 * 60 * 1000)
        ]

        print(f"Coins listed: {len(l_coins)}")

        f_coins = []
        for symbol in l_coins:
            try:
                ticker = await b_client.futures_ticker(symbol=symbol)
                if float(ticker['quoteVolume']) >= 10_000_000:
                    f_coins.append(symbol)
            except Exception:
                continue
    except Exception as e:
        print(f"Error filtering the coins. {e}")

    print(f"Coins filtered: {len(f_coins)}")

    coins = set(f_coins)
    await price_tracker(coins, b_client)