# 🤖 Binance Scalping Signals Bot

A bot that uses the Binance API to monitor futures coins and send automatic alerts when it detects significant movements of 20% or more.

## 📊 Features

- **Real-Time Monitoring**: Tracks cryptocurrency prices using Binance WebSockets
- **Smart Alerts**: Automatically notifies of price changes ≥20% within 2h 10m windows
- **Batch Processing**: Efficiently handles multiple symbols while respecting Binance limits
- **24/7 Uptime**: Integrated web server to keep the bot active continuously

## 🛠️ Technologies Used

- **Python 3.12.4+**
- **Binance API**: For real-time market data
- **Telegram Bot API**: For sending alerts
- **Flask**: Web server for uptime
- **AsyncIO**: Asynchronous programming for better performance

## 📋 Prerequisites

1.  **Binance account** with API enabled
2.  **Telegram Bot** created with @BotFather
3.  **Telegram Channel/Group** to receive alerts

## ⚙️ Configuration

### 1\. Clone the repository

```bash
git clone https://github.com/johnnylinares/binance-scalping-signals-bot.git
cd binance-scalping-signals-bot
```

### 2\. Install dependencies

```bash
pip install -r requirements.txt
```

### 3\. Configure environment variables

Create a `.env` file in the project's root:

```env
# Binance API
API_KEY="your_binance_api_key"
API_SECRET="your_binance_api_secret"

# Main Telegram Bot
BOT_TOKEN="your_bot_token"
CHANNEL_ID="your_channel_id"
```

### 4\. Get the necessary credentials

#### Binance API:

1.  Go to [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2.  Create a new API Key
3.  Enable "Enable Reading" (you don't need trading permissions)
4.  Save your API Key and Secret Key

#### Telegram Bot:

1.  Talk to [@BotFather](https://t.me/botfather) on Telegram
2.  Use `/newbot` to create a new bot
3.  Save the token it provides
4.  Add the bot to your channel/group and make it an administrator
5.  Get the channel ID using [@userinfobot](https://t.me/userinfobot)

## 🚀 Usage

### Run locally

```bash
python main.py
```

### Run in production

The bot includes a Flask server that responds on port 8000 to maintain uptime:

```bash
python main.py
```

The server will be available at `http://localhost:8000`

## 📊 How it Works

1.  **Connection**: The bot connects to the Binance API using WebSockets
2.  **Monitoring**: It tracks prices of multiple cryptocurrencies in real time
3.  **Analysis**: It calculates percentage changes in 2-hour windows
4.  **Alerts**: It sends notifications when it detects changes ≥20%
5.  **Filtering**: It prevents spam with a time bucket system

## 📱 Alert Format

```
🟢 #BTCUSDT 📈 +25.67%
💵 $45,230.50 💰 $1,234.56M
```

- 🟢📈 = Price increase
- 🔴📉 = Price decrease
- Cryptocurrency symbol
- Percentage change
- Current price
- Volume in millions

## ⚡ Advanced Configuration

### Modify the alert threshold

In `price_handler.py`, change the constant:

```python
THRESHOLD = 20.0  # Change to your desired percentage
```

### Modify the time window

```python
TIME_WINDOW = 7800 # 2h 10m in seconds
```

## 🔧 Project Structure

```
binance-scalping-signals-bot/
├── main.py                 # Main entry point
├── config/
│   └── settings.py         # Configuration and environment variables
├── models/
│   ├── alert_handler.py    # Telegram alert handling
│   ├── coin_handler.py     # Price monitoring logic
│   ├── log_handler.py      # Simple log function
│   └── price_handler.py    # Cryptocurrency symbol management
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (do not include in git)
└── README.md               # This file
```

## 🐛 Troubleshooting

### Connection error to Binance

- Verify that your API Key and Secret are correct
- Make sure the API Key has reading permissions enabled
- Check that you haven't exceeded Binance's rate limits

### Bot doesn't send messages

- Confirm that the bot is an administrator of the channel
- Verify that the CHANNEL_ID is correct (it must include the `-` for channels)
- Check that the BOT_TOKEN is valid

### Performance issues

- The bot automatically handles multiple symbols in batches
- If you experience lag, reduce the number of monitored symbols

## 🤝 Contribute

1.  Fork the project
2.  Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## ⚠️ Disclaimer

This bot is for educational and informational purposes only. It does not constitute financial advice. Always do your own research before making investment decisions.

## 📞 Support

If you have problems or questions:

- Open an [Issue](https://github.com/johnnylinares/binance-scalping-signals-bot/issues)

---

⭐ If this project is useful to you, don't forget to give it a star\!
