import telegram
from config.settings import CHANNEL_ID, BOT_TOKEN

bot = telegram.Bot(token=BOT_TOKEN)

async def send_alert(symbol, percentage_change, price, emoji, volume):
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=f'{emoji[0]} #{symbol} {emoji[1]} {percentage_change:+.2f}%\n{emoji[2]} ${price} {emoji[3]} ${volume}M'
)
    print(f"{symbol} alert sended.")
