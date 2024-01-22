from aiogram.exceptions import TelegramAPIError

async def send_telegram_message(bot, chat_id, message):
    try:
        await bot.send_message(chat_id=chat_id, text=message)
    except TelegramAPIError as e:
        print(f"Telegram API Error: {e}")
        # Handle specific error codes if necessary
        # Example: if e.error_code == 429 (Too Many Requests), implement retry logic


def format_message(message):

    if message:

                formatted_message = "Top Gainers Analysis:\n"

                for data in message:

                    # Determine which ratio key is present
                    ratio_key = 'ratio ask/bid' if 'ratio ask/bid' in data['orderbook'][1] else 'ratio bid/ask'

                    formatted_message += (
                        f"\nSymbol: {data['symbol']}\n"
                        f"Price Increase (%): {data['price_increase_percentage']:.2f}\n"
                        f"Order Book Trend: {data['orderbook'][0]}\n"
                        f"Ratio ({ratio_key}): {data['orderbook'][1][ratio_key]:.2f}\n"
                        f"RSI: {data['price_movement']['RSI']:.2f}\n"
                        f"MACD: {data['price_movement']['MACD_Current']:.6f}\n"
                        f"MACD Signal: {data['price_movement']['MACDSignal_Current']:.6f}\n"
                        f"Bid/Ask Ratio: {data['price_movement']['Bid_Ask_Ratio']:.2f}\n"
                        f"Uptrend Signals: {data['price_movement']['Uptrend_Signals']}\n"
                        f"Downtrend Signals: {data['price_movement']['Downtrend_Signals']}\n"
                        f"Final Decision: {'Increase' if data['price_movement']['Final_Decision'] == 1 else 'Decrease' if data['price_movement']['Final_Decision'] == -1 else 'Neutral'}\n"
                    )

                return formatted_message
                
    else:
        return "No analysis to send."
