from models.log_handler import log
from models.price_handler import price_handler

async def coin_handler(client):
    """
    Filter & listener coin function.
    """

    await log("🟡 coin_handler function started.")
    
    try:
        all_tickers = await client.futures_ticker()

        await log(f"🟡 Coins listed: {len(all_tickers)}")

        f_coins = []
        for ticker in all_tickers:
            if ticker['symbol'].endswith('USDT'):
                try:
                    volume = float(ticker['quoteVolume'])
                    if 10_000_000 <= volume <= 1_000_000_000:
                        f_coins.append(ticker['symbol'])
                except Exception:
                    continue
        
        await log(f"🟢 Coins filtered: {len(f_coins)}")

        coins = set(f_coins)
        await price_handler(client, coins)

    except Exception as e:
        await log(f"🔴 Error filtering the coins. {e}")