# ===== LIBRARYS =====
import asyncio
import time
from collections import defaultdict

# ===== MODULES =====
from models.alert_handler import send_alert

# ===== CONSTANTS =====
THRESHOLD = 20.0  # % alert's change
TIME_WINDOW = 3 * 60 * 60  # 3 hours in seconds (10800 like original)
MAX_BATCH_SIZE = 200  # Maximum symbols per stream (Binance limit)

class PriceTracker:
    def __init__(self):
        # Store price history for each symbol: [(timestamp, price), ...] - like original
        self.price_history = defaultdict(list)
        # Track last log time
        self.last_log_time = time.time()
        self.log_interval = 600  # 10 minutes like original
        
    def add_price_data(self, symbol, price, volume, timestamp):
        """Add new price data and clean old data - following original logic"""
        # Add to history - like original
        self.price_history[symbol].append((timestamp, price))
        
        # Clean old data (older than TIME_WINDOW) - exactly like original
        self.price_history[symbol] = [
            p for p in self.price_history[symbol] 
            if timestamp - p[0] <= TIME_WINDOW
        ]
    
    async def check_price_change(self, symbol, current_price, volume_24h):
        """Check price change - following original logic exactly"""
        # Need at least 2 data points - like original
        if len(self.price_history[symbol]) < 2:
            return
            
        # Get old price (first/oldest in history) - like original
        old_price = self.price_history[symbol][0][1]
        
        # Calculate percentage change - exactly like original
        percentage_change = ((current_price - old_price) / old_price) * 100
        
        # Check if exceeds threshold - like original
        if abs(percentage_change) >= THRESHOLD:
            print(f"📊 COIN FOUND: {symbol}")
            
            # Determine emojis - like original
            if percentage_change > 0:
                emoji1 = "🟢"
                emoji2 = "📈"
            else:
                emoji1 = "🔴"
                emoji2 = "📉"
            
            # Send alert - like original
            await send_alert(symbol, percentage_change, current_price, emoji1, emoji2, volume_24h)
            
            # Clear history after alert - exactly like original
            self.price_history[symbol] = []
    
    async def log_status(self):
        """Log status periodically - like original"""
        now = time.time()
        if now - self.last_log_time >= self.log_interval:
            print("🔍 Checking coins")
            self.last_log_time = now

async def create_multiplex_stream(bsm, symbols):
    """Create a multiplex stream for multiple symbols"""
    streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
    multiplex_socket = bsm.multiplex_socket(streams)
    return multiplex_socket

async def process_ticker_data(data, tracker):
    """Process ticker data from WebSocket"""
    try:
        if 's' in data and 'c' in data and 'q' in data:
            symbol = data['s']  # Symbol
            price = float(data['c'])  # Current price
            volume_24h = round(float(data['q']) / 1_000_000, 1)  # Volume in millions like original
            timestamp = int(time.time())
            
            # Add data to tracker
            tracker.add_price_data(symbol, price, volume_24h, timestamp)
            
            # Check for price changes - using original logic
            await tracker.check_price_change(symbol, price, volume_24h)
            
            # Log status periodically
            await tracker.log_status()
                
    except Exception as e:
        print(f"Error processing ticker data: {e}")

async def handle_socket_stream(socket, tracker):
    """Handle WebSocket stream messages"""
    try:
        async with socket as stream:
            while True:
                try:
                    msg = await stream.recv()
                    if msg:
                        # Handle multiplex stream format
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

async def price_handler(bsm, b_client, coins):
    """Main price handler function - using original logic with WebSockets"""
    print("🤖 PRICE TRACKER ACTIVATED")
    print(f"🎯 Alert threshold: {THRESHOLD}%")
    print(f"⏰ Time window: {TIME_WINDOW/3600:.1f} hours")
    print(f"📦 Max batch size: {MAX_BATCH_SIZE}")
    
    # Initialize price tracker
    tracker = PriceTracker()
    
    # Convert coins set to list for processing
    coins_list = list(coins)
    
    # Split coins into batches to respect Binance limits
    batches = []
    for i in range(0, len(coins_list), MAX_BATCH_SIZE):
        batch = coins_list[i:i + MAX_BATCH_SIZE]
        batches.append(batch)
    
    print(f"📦 Created {len(batches)} batches for processing")
    
    # Create tasks for each batch
    tasks = []
    for i, batch in enumerate(batches):
        print(f"🔄 Starting batch {i+1}/{len(batches)} with {len(batch)} symbols")
        
        try:
            # Create multiplex stream for this batch
            socket = await create_multiplex_stream(bsm, batch)
            
            # Create task to handle this stream
            task = asyncio.create_task(
                handle_socket_stream(socket, tracker),
                name=f"batch_{i+1}"
            )
            tasks.append(task)
            
            # Small delay between batch creations
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
        # Run all streams concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        print(f"❌ Error in price handler: {e}")
    finally:
        # Cancel any remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        
        print("🛑 Price handler stopped")