import telegram
import os
from telegram import Message

from dotenv import load_dotenv

load_dotenv()

bot = telegram.Bot(token=os.getenv("BOT_TOKEN"))

async def alert_handler(symbol, percentage_change, price, emoji, volume):
    msg : Message = await bot.send_message(
        chat_id=os.getenv("CHANNEL_ID"),
        text=f'{emoji[0]} #{symbol} {emoji[1]} {percentage_change:+.2f}%\n💵 ${price} 💰 ${volume}M'
    )
    print(f"{symbol} alert sended.")
    return msg.message_id, 


async def tp_sl_alert_handler(hit, original_message_id):
    if hit == -1:
        alert = "❌ SL (-5%)"
    elif hit == 0:
        alert = "➖ SIN MOVIMIENTO"
    elif hit == 1:
        alert = "✅ TP1 (+5%)"
    elif hit == 2:
        alert = "✅ TP2 (+10%)"
    elif hit == 3:
        alert = "✅ TP3 (+15%)"
    elif hit == 4:
        alert = "✅ TP4 (+20%)"

    await bot.send_message(
        chat_id=os.getenv("CHANNEL_ID"),

        text=f'{alert}',
        reply_to_message_id=original_message_id
    )
