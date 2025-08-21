import asyncio
import time
from collections import defaultdict

from models.alert_handler import send_alert

THRESHOLD = 20.0
TIME_WINDOW = 3 * 60 * 60
MAX_BATCH_SIZE = 20
RECONNECT_DELAY = 10
MAX_RECONNECT_ATTEMPTS = 5

class PriceTracker:
    def __init__(self):
        self.price_history = defaultdict(list)
        self.last_alert_time = defaultdict(float)
        self.alert_cooldown = 600
        
    def add_price_data(self, symbol, price, timestamp):
        self.price_history[symbol].append((timestamp, price))
        cutoff_time = timestamp - TIME_WINDOW
        self.price_history[symbol] = [
            (t, p) for t, p in self.price_history[symbol] 
            if t > cutoff_time
        ]
    
    async def check_price_change(self, symbol, current_price, volume_24h):
        if len(self.price_history[symbol]) < 2:
            return
            
        current_time = time.time()
        if current_time - self.last_alert_time[symbol] < self.alert_cooldown:
            return
            
        oldest_price = self.price_history[symbol][0][1]
        percentage_change = ((current_price - oldest_price) / oldest_price) * 100
        
        if abs(percentage_change) >= THRESHOLD:
            print(f"Alert: {symbol} - Change: {percentage_change:+.2f}%")
            
            if percentage_change > 0:
                emoji1, emoji2 = "🟢", "📈"
            else:
                emoji1, emoji2 = "🔴", "📉"
            
            try:
                await send_alert(symbol, percentage_change, current_price, emoji1, emoji2, volume_24h)
                self.last_alert_time[symbol] = current_time
                self.price_history[symbol] = []
            except Exception as e:
                print(f"Error sending alert for {symbol}: {e}")

async def price_handler(bsm, coins, b_client):
    print(f"Starting price tracker - Threshold: {THRESHOLD}% - Window: {TIME_WINDOW/3600:.1f}h")
    
    tracker = PriceTracker()
    coins_list = list(coins)
    
    batches = []
    for i in range(0, len(coins_list), MAX_BATCH_SIZE):
        batch = coins_list[i:i + MAX_BATCH_SIZE]
        batches.append(batch)
    
    print(f"Created {len(batches)} batches of max {MAX_BATCH_SIZE} symbols each")
    
    while True:
        for i, batch in enumerate(batches):
            try:
                print(f"Starting batch {i+1} with {len(batch)} symbols")
                await handle_single_batch(bsm, tracker, batch, i+1)
            except Exception as e:
                print(f"Batch {i+1} failed completely: {e}")
            
            await asyncio.sleep(2)
        
        print("All batches completed, restarting cycle...")
        await asyncio.sleep(5)

async def handle_single_batch(bsm, tracker, batch_symbols, batch_id):
    reconnect_count = 0
    
    while reconnect_count < MAX_RECONNECT_ATTEMPTS:
        try:
            streams = [f"{symbol.lower()}@ticker" for symbol in batch_symbols]
            socket = bsm.multiplex_socket(streams)
            
            message_count = 0
            start_time = time.time()
            
            async with socket as stream:
                while True:
                    try:
                        msg = await asyncio.wait_for(stream.recv(), timeout=20.0)
                        
                        if not msg:
                            await asyncio.sleep(0.01)
                            continue
                        
                        message_count += 1
                        
                        data = msg.get('data', msg)
                        
                        if not all(key in data for key in ['s', 'c', 'q']):
                            continue
                        
                        symbol = data['s']
                        current_price = float(data['c'])
                        volume_24h = round(float(data['q']) / 1_000_000, 1)
                        timestamp = int(time.time())
                        
                        tracker.add_price_data(symbol, current_price, timestamp)
                        await tracker.check_price_change(symbol, current_price, volume_24h)
                        
                        if message_count % 50 == 0:
                            await asyncio.sleep(0.1)
                        
                        if time.time() - start_time > 300:
                            print(f"Batch {batch_id}: Processed {message_count} messages in 5 minutes")
                            return
                            
                    except asyncio.TimeoutError:
                        print(f"Batch {batch_id}: Timeout, ending batch")
                        return
                    except Exception as msg_error:
                        if "BinanceWebsocketQueueOverflow" in str(msg_error):
                            print(f"Batch {batch_id}: Queue overflow detected, ending batch")
                            return
                        print(f"Batch {batch_id} message error: {msg_error}")
                        await asyncio.sleep(0.1)
                        
        except Exception as e:
            reconnect_count += 1
            if "BinanceWebsocketQueueOverflow" in str(e):
                print(f"Batch {batch_id}: Queue overflow, waiting longer before retry...")
                await asyncio.sleep(RECONNECT_DELAY * 2)
            else:
                print(f"Batch {batch_id} error (attempt {reconnect_count}): {e}")
                await asyncio.sleep(RECONNECT_DELAY)
            
            if reconnect_count >= MAX_RECONNECT_ATTEMPTS:
                print(f"Batch {batch_id}: Max reconnect attempts reached, giving up")
                return