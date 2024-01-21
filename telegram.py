from aiogram.exceptions import TelegramAPIError

async def send_telegram_message(bot, chat_id, message):
    try:
        await bot.send_message(chat_id=chat_id, text=message)
    except TelegramAPIError as e:
        print(f"Telegram API Error: {e}")
        # Handle specific error codes if necessary
        # Example: if e.error_code == 429 (Too Many Requests), implement retry logic
