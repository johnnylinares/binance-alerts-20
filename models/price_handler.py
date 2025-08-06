import asyncio
import time
from collections import defaultdict

from models.alert_handler import send_alert

THRESHOLD = 20.0
TIME_WINDOW = 3 * 60 * 60
MAX_BATCH_SIZE = 200

class PriceTracker:
    def __init__(self):

        self.price_history = defaultdict(list)
        self.last_log_time = time.time()
        self.log_interval = 600
        
    def add_price_data(self, symbol, price, timestamp):
        """
        Add new price data and clean old data
        """
        
        self.price_history[symbol].append((timestamp, price))
        self.price_history[symbol] = [
            p for p in self.price_history[symbol] 
            if timestamp - p[0] <= TIME_WINDOW
        ]
    
    async def check_price_change(self, symbol, current_price, volume_24h):
        """
        Check price change - following original logic exactly
        """
        
        if len(self.price_history[symbol]) < 2:
            return
            
        old_price = self.price_history[symbol][0][1]
        
        percentage_change = ((current_price - old_price) / old_price) * 100
        
        if abs(percentage_change) >= THRESHOLD:
            print(f"📊 COIN FOUND: {symbol}")
            
            if percentage_change > 0:
                emoji1 = "🟢"
                emoji2 = "📈"
            else:
                emoji1 = "🔴"
                emoji2 = "📉"
            
            await send_alert(symbol, percentage_change, current_price, emoji1, emoji2, volume_24h)
            self.price_history[symbol] = []
    
    async def log_status(self):
        """
        Log status periodically.
        """

        now = time.time()
        if now - self.last_log_time >= self.log_interval:
            print("🔍 Checking coins")
            self.last_log_time = now

async def create_multiplex_stream(bsm, symbols):
    """
    Create a multiplex stream for multiple symbols.
    """
    streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
    multiplex_socket = bsm.multiplex_socket(streams)
    return multiplex_socket

async def process_ticker_data(data, tracker):
    """
    Process ticker data from WebSocket.
    """
    try:
        if 's' in data and 'c' in data and 'q' in data:
            symbol = data['s']
            price = float(data['c'])
            volume_24h = round(float(data['q']) / 1_000_000, 1)
            timestamp = int(time.time())
            
            tracker.add_price_data(symbol, price, volume_24h, timestamp)
            
            await tracker.check_price_change(symbol, price, volume_24h)
            await tracker.log_status()
                
    except Exception as e:
        print(f"Error processing ticker data: {e}")

async def handle_socket_stream(socket, tracker):
    """
    Handle WebSocket stream messages.
    """

    try:
        async with socket as stream:
            while True:
                try:
                    msg = await stream.recv()
                    if msg:
                        if 'stream' in msg and 'data' in msg:
                            await process_ticker_data(msg['data'], tracker)
                        else:
                            await process_ticker_data(msg, tracker)
                            
                except Exception as msg_error:
                    print(f"Error processing message: {msg_error}")
                    await asyncio.sleep(0.01)
                        
    except Exception as e:
        print(f"Error in socket stream: {e}")
        await asyncio.sleep(5)

async def price_handler(bsm, coins):
    """
    Main price handler function.
    """

    print("🤖 PRICE TRACKER ACTIVATED")
    print(f"🎯 Alert threshold: {THRESHOLD}%")
    print(f"⏰ Time window: {TIME_WINDOW/3600:.1f} hours")
    print(f"📦 Max batch size: {MAX_BATCH_SIZE}")
    
    tracker = PriceTracker()
    coins_list = list(coins)
    
    batches = []
    for i in range(0, len(coins_list), MAX_BATCH_SIZE):
        batch = coins_list[i:i + MAX_BATCH_SIZE]
        batches.append(batch)
    
    print(f"📦 Created {len(batches)} batches for processing")
    
    tasks = []
    for i, batch in enumerate(batches):
        print(f"🔄 Starting batch {i+1}/{len(batches)} with {len(batch)} symbols")
        
        try:
            socket = await create_multiplex_stream(bsm, batch)
        
            task = asyncio.create_task(
                handle_socket_stream(socket, tracker),
                name=f"batch_{i+1}"
            )
            tasks.append(task)
        
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"Error creating stream for batch {i+1}: {e}")
            continue
    
    if not tasks:
        print("❌ No streams created successfully")
        return
    
    print(f"✅ Successfully created {len(tasks)} streams")
    print("🟢 Bot is now actively monitoring...")
    
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"❌ Error in price handler: {e}")
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        
        print("🛑 Price handler stopped")