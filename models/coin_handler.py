from models.log_handler import log
from models.price_handler import price_handler

async def coin_handler(client):
    """
    Filter & listener coin function.
    """
    
    try:
        exchange_info = await client.futures_exchange_info()

        l_coins = [
            s['symbol'] for s in exchange_info['symbols'] if s['symbol'].endswith('USDT')
        ]

        await log(f"Coins listed: {len(l_coins)}")

        f_coins = []
        for symbol in l_coins:
            try:
                ticker = await client.futures_ticker(symbol=symbol)
                if float(ticker['quoteVolume']) <= 1_000_000_000:
                    f_coins.append(symbol)
            except Exception:
                continue
        
        await log(f"Coins filtered: {len(f_coins)}")

        coins = set(f_coins)
        await price_handler(client, coins)

    except Exception as e:
        log(f"Error filtering the coins. {e}")