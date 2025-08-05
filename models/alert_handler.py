import telegram
from config.settings import CHANNEL_ID, BOT_TOKEN

bot = telegram.Bot(token=BOT_TOKEN)

async def send_alert(symbol, percentage_change, price, emoji1, emoji2, volume):
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=f'{emoji1} #{symbol} {emoji2} {percentage_change:+.2f}%\n💵 ${price:.2f} 💰 ${volume}M'
    )
    print(f"{symbol} alert sended.")
