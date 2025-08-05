# ===== LIBRARYS =====
import asyncio
import time
from collections import defaultdict, deque

# ===== MODULES =====
from models.alert_handler import send_alert

# ===== CONSTANTS =====
THRESHOLD = 20.0  # % alert's change
TIME_WINDOW = 2 * 60 * 60  # 2 hours in seconds
MAX_BATCH_SIZE = 200  # Maximum symbols per stream (Binance limit)

class PriceTracker:
    def __init__(self):
        # Store price history for each symbol (timestamp, price)
        self.price_history = defaultdict(lambda: deque(maxlen=1000))
        # Store current prices
        self.current_prices = {}
        # Store volumes
        self.volumes = {}
        # Track processed alerts to avoid spam
        self.processed_alerts = set()
        # Store initial prices for comparison
        self.initial_prices = {}
        # Track when we started monitoring each symbol
        self.start_times = {}
        
    def add_price_data(self, symbol, price, volume, timestamp):
        """Add new price data and clean old data"""
        current_time = timestamp
        
        # Store initial price and start time if this is the first data point
        if symbol not in self.initial_prices:
            self.initial_prices[symbol] = price
            self.start_times[symbol] = timestamp
            print(f"Started monitoring {symbol} at ${price}")
        
        # Add new data
        self.price_history[symbol].append((timestamp, price))
        self.current_prices[symbol] = price
        self.volumes[symbol] = volume
        
        # Clean old data (older than TIME_WINDOW)
        cutoff_time = current_time - TIME_WINDOW
        while (self.price_history[symbol] and 
               self.price_history[symbol][0][0] < cutoff_time):
            self.price_history[symbol].popleft()
    
    def check_price_change(self, symbol):
        """Check if price changed more than threshold in the time window"""
        if len(self.price_history[symbol]) < 2:
            return None
            
        current_price = self.current_prices[symbol]
        
            oldest_price = self.price_history[symbol][0][1]
            percentage_change_history = ((current_price - oldest_price) / oldest_price) * 100
        
        # Method 2: Compare with initial price if we've been monitoring long enough
        percentage_change_initial = None
        if (symbol in self.initial_prices and 
            current_time - self.start_times[symbol] >= 300):  # At least 5 minutes of monitoring
            initial_price = self.initial_prices[symbol]
            percentage_change_initial = ((current_price - initial_price) / initial_price) * 100
        
        # Use the larger absolute change for detection
        percentage_change = None
        if percentage_change_history is not None and percentage_change_initial is not None:
            if abs(percentage_change_history) >= abs(percentage_change_initial):
                percentage_change = percentage_change_history
            else:
                percentage_change = percentage_change_initial
        elif percentage_change_history is not None:
            percentage_change = percentage_change_history
        elif percentage_change_initial is not None:
            percentage_change = percentage_change_initial
        
        if percentage_change is None:
            return None
        
        # Check if it exceeds threshold
        if abs(percentage_change) >= THRESHOLD:
            print(f"🚨 {symbol}: {percentage_change:+.2f}% change detected (threshold: {THRESHOLD}%)")
            
            alert_key = f"{symbol}_{int(time.time() // 300)}"  # 5-minute buckets to avoid spam
            
            if alert_key not in self.processed_alerts:
                self.processed_alerts.add(alert_key)
                
                # Clean old processed alerts (keep only last hour)
                current_bucket = int(time.time() // 300)
                self.processed_alerts = {
                    key for key in self.processed_alerts 
                    if int(key.split('_')[1]) > current_bucket - 12
                }
                
                return {
                    'symbol': symbol,
                    'percentage_change': percentage_change,
                    'price': current_price,
                    'volume': round(self.volumes.get(symbol, 0) / 1_000_000, 2)  # Convert to millions
                }
            else:
                print(f"⏭️ {symbol}: Alert already sent recently for this time bucket")
        
        return None

async def create_multiplex_stream(bsm, symbols):
    """Create a multiplex stream for multiple symbols"""
    # Convert symbols to lowercase for stream names
    streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
    
    # Create multiplex socket (without socket_manager parameter)
    multiplex_socket = bsm.multiplex_socket(streams)
    
    return multiplex_socket

async def process_ticker_data(data, tracker):
    """Process ticker data from WebSocket"""
    try:
        if 's' in data and 'c' in data and 'q' in data:
            symbol = data['s']  # Symbol
            price = float(data['c'])  # Current price
            volume = float(data['q'])  # Quote volume (24h)
            timestamp = int(time.time())
            
            # Add data to tracker
            tracker.add_price_data(symbol, price, volume, timestamp)
            
            # Check for significant price changes
            alert_data = tracker.check_price_change(symbol)
            
            if alert_data:
                print(f"📤 Sending alert for {alert_data['symbol']}: {alert_data['percentage_change']:+.2f}%")
                
                # Determine emoji based on price change
                emoji = "🟢📈💵💰" if alert_data['percentage_change'] > 0 else "🔴📉💵💰" 
                
                # Send alert
                asyncio.create_task(send_alert(
                    symbol=alert_data['symbol'],
                    percentage_change=alert_data['percentage_change'],
                    price=alert_data['price'],
                    emoji=emoji,
                    volume=alert_data['volume']
                ))
                
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
                        # Message is already a dict, no need to parse JSON
                        data = msg
                        
                        # Handle multiplex stream format
                        if 'stream' in data and 'data' in data:
                            await process_ticker_data(data['data'], tracker)
                        else:
                            await process_ticker_data(data, tracker)
                            
                except Exception as msg_error:
                    print(f"Error processing message: {msg_error}")
                    await asyncio.sleep(0.01)  # Very brief pause to avoid blocking
                        
    except Exception as e:
        print(f"Error in socket stream: {e}")
        await asyncio.sleep(5)  # Wait before potential reconnection

async def price_handler(bsm, b_client, coins):
    """Main price handler function"""
    print(f"🚀 Starting price tracking for {len(coins)} coins with {THRESHOLD}% threshold...")
    
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
            
            # Small delay between batch creations to avoid overwhelming
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"Error creating stream for batch {i+1}: {e}")
            continue
    
    if not tasks:
        print("❌ No streams created successfully")
        return
    
    print(f"✅ Successfully created {len(tasks)} streams. Starting price monitoring...")
    print(f"🎯 Monitoring for changes >= {THRESHOLD}% in {TIME_WINDOW/3600:.1f} hour windows")
    
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