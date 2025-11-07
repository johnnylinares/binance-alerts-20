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
    return msg.message_id


async def tp_sl_alert_handler(hit, original_message_id):
    await bot.send_message(
        chat_id=os.getenv("CHANNEL_ID"),

        text=f'{hit}',
        reply_to_message_id=original_message_id
    )
