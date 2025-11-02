from models.log_handler import log
from models.price_handler import price_handler

async def coin_handler(client, duration_seconds):
    """
    Filter & listener coin function.
    """
    
    try:
        all_tickers = await client.futures_ticker()

        await log(f"[FILTER] Coins listed: {len(all_tickers)}")

        f_coins = []
        for ticker in all_tickers:
            if ticker['symbol'].endswith('USDT'):
                try:
                    volume = float(ticker['quoteVolume'])
                    if 10_000_000 <= volume <= 1_000_000_000:
                        f_coins.append(ticker['symbol'])
                except (ValueError, KeyError, TypeError):
                    continue
        
        await log(f"[FILTER] Coins filtered: {len(f_coins)}")

        coins = set(f_coins)
        
        await price_handler(client, coins, duration_seconds)

    except Exception as e:
        await log(f"[FILTER] Error filtering the coins. {e}")
        raise