import json
import asyncio
import websockets
import os
import pymongo
import requests
import time
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime, timedelta
from aiogram import Bot
from telegram import send_telegram_message, format_message
from trading_logic import trading_decision_based_on_conditions
from orderbook_analysis import fetch_order_book, analyze_order_book
from candle_stick_analysis import fetch_historical_data, estimate_price_movement
from trading_execution import client, execute_order_based_on_signal_and_balance, close_positions_based_on_profit_loss



# Load environment variables from .env file
load_dotenv()

database_url = os.environ.get('database_url')
telegram_chat_id = os.environ.get('YOUR_CHAT_ID')
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')

# print(f"telegram_chat_id: {telegram_chat_id}")
# print(f"telegram_bot_token: {telegram_bot_token}")


# MongoDB setup
client = pymongo.MongoClient(database_url)
db = client["binance"]
collection = db["binance_gainers_15m"]# to store websocket data
collection_selected_gainers = db["selected_gainers"]

def test_mongodb_connection():
    try:
        # Attempt to fetch a small amount of data
        # Connect to MongoDB
        client = MongoClient(database_url)
        db = client["binance"]  # Database name
        collection = db["binance_gainers_15m"]  # Collection name
        one_doc = collection.find_one()
        print("Successfully connected to MongoDB. Document found:", one_doc)
    except Exception as e:
        print("Failed to connect to MongoDB:", e)

def fetch_all_binance_symbols():
    print("Fetching all Binance symbols...")
    url = "https://api.binance.com/api/v3/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    symbols = [symbol['symbol'] for symbol in data['symbols'] if 'USDT' in symbol['symbol']]
    print(f"Fetched {len(symbols)} symbols.")
    return symbols


async def handle_message(message, collection):
    """
    Process each WebSocket message. Update existing data in MongoDB or insert new data.
    """
    # print("Message received: ", message)
    try:
        data = json.loads(message)
        symbol = data['data']['s']
        price = float(data['data']['c'])
        timestamp = datetime.utcfromtimestamp(data['data']['E'] / 1000.0)

        # Log the received message
        # print(f"Message received for {symbol}: Price: {price}, Timestamp: {timestamp}")

        collection.insert_one({
        "symbol": symbol,
        "price": price,
        "timestamp": timestamp
        })

        # print(f"Inserted new record for {symbol} at {timestamp}")

    except Exception as e:
        print(f"Error processing message: {e}")


async def binance_ws(symbols, collection):
    """
    Establish WebSocket connection with Binance and process every message as it arrives.
    """

    while True:

        print("Establishing WebSocket connection...")
        stream_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join([f'{symbol.lower()}@ticker' for symbol in symbols])}"

        try:

            async with websockets.connect(stream_url) as websocket:
                while True:
                    message = await websocket.recv()
                    await handle_message(message, collection)

        except websockets.exceptions.ConnectionClosed as e: 
            print(f"WebSocket connection closed: {e}")

        except Exception as e:
            print(f"Error processing message: {e}")

        print("Attempting to reconnect in 5 seconds...")
        
        await asyncio.sleep(5)  # Wait for 5 seconds before attempting to reconnect


def calculate_top_gainers(top_n=10):
    print("Calculating top gainers...")
    # Define the time range for the 15-minute interval
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=15)

    # MongoDB aggregation pipeline
    pipeline = [
        {"$match": {"timestamp": {"$gte": start_time, "$lte": end_time}}},
        {"$group": {
            "_id": "$symbol", 
            "startPrice": {"$first": "$price"},
            "endPrice": {"$last": "$price"},
            "startTime": {"$first": "$timestamp"},
            "endTime": {"$last": "$timestamp"}
        }},
        {"$project": {
            "symbol": "$_id",
            "_id": 0,
            "startPrice": 1,
            "endPrice": 1,
            "startTime": 1,
            "endTime": 1,
            "priceChangePercent": {
                "$multiply": [
                    {"$divide": [
                        {"$subtract": ["$endPrice", "$startPrice"]},
                        "$startPrice"
                    ]},
                    100
                ]
            }
        }},
        {"$sort": {"priceChangePercent": -1}},  # Sort by descending order of price change
        {"$limit": top_n}  # Limit to top N gainers
    ]

    # Execute the aggregation pipeline
    top_gainers = list(collection.aggregate(pipeline))

    # Format startTime and endTime as strings
    for gainer in top_gainers:
        gainer['startTime'] = gainer['startTime'].strftime("%Y-%m-%d %H:%M:%S.%f")
        gainer['endTime'] = gainer['endTime'].strftime("%Y-%m-%d %H:%M:%S.%f")

    # Return the top gainers
    print(f"Top gainers: {top_gainers}")
    return top_gainers

def cleanup_old_data(hours_old):
    
    print("Start deleting old data ........................")

    try:
        # Calculate the cutoff date
        cutoff_date = datetime.utcnow() - timedelta(hours=hours_old)

        print("cut off date: ", cutoff_date)

        # Assume 'client' is your MongoClient instance and 'db' is your database
        collection = client.db.collection  # Replace with your collection name
        
        # Delete documents older than the cutoff date
        result = collection.delete_many({"timestamp": {"$lt": cutoff_date}})
        print(f"Deleted {result.deleted_count} old records (older than {hours_old} hours).")

    except Exception as e:
        print(f"An error occurred: {e}")

def count_records(collection):
    """
    Count the number of records in the given MongoDB collection.
    """
    try:
        count = collection.count_documents({})
        print(f"Total number of records in the collection: {count}")
        return count
    except Exception as e:
        print(f"Error while counting records: {e}")
        return None

def write_top_gainers_to_file(top_gainers, filename="top_gainers.txt"):
    """
    Write the list of top gainers, the count of unique symbols, and the timestamp of file creation to a text file with detailed information.
    """
    try:
        with open(filename, 'w') as file:
            # Write the timestamp of file creation
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"File created on: {current_timestamp}\n")

            # Count unique symbols and write to the file
            unique_symbol_count = count_unique_symbols(collection)
            file.write(f"Total unique symbols: {unique_symbol_count}\n\n")

            # Write top gainers' information
            for gainer in top_gainers:
                file.write(f"Symbol: {gainer['symbol']}, Start Price: {gainer['startPrice']}, Start Time: {gainer['startTime']}, End Price: {gainer['endPrice']}, End Time: {gainer['endTime']}, Price Change (%): {gainer['priceChangePercent']}\n")

            # Write latest top gainers in database
            latest_top_gainers = get_latest_top_gainers()
            file.write(f"latest top gainers in database: {latest_top_gainers}\n\n")

        print(f"Top gainers successfully written to {filename}")
    except Exception as e:
        print(f"Error writing to file: {e}")

def count_unique_symbols(collection):
    try:
        pipeline = [
            {"$group": {"_id": "$symbol"}},
            {"$count": "unique_symbols_count"}
        ]
        result = list(collection.aggregate(pipeline))
        if result:
            count = result[0]["unique_symbols_count"]
            print(f"Total unique symbols: {count}")
            return count
        else:
            print("No unique symbols found.")
            return 0
    except Exception as e:
        print(f"Error while counting unique symbols: {e}")
        return None

def record_top_gainers(top_gainers):
    """
    Record the top gainers into MongoDB with a timestamp.
    """
    try:
        if not top_gainers:
            print("No top gainers data to record.")
            return

        timestamp = datetime.utcnow()
        for gainer in top_gainers:
            gainer['recordedAt'] = timestamp  # Add timestamp to each top gainer
            collection_selected_gainers.insert_one(gainer)

        print(f"Recorded {len(top_gainers)} top gainers at {timestamp}")
    except Exception as e:
        print(f"Error while counting unique symbols: {e}")

def get_latest_top_gainers():
    """
    Get the latest top gainers record from the database.
    """
    try:
        latest_record = collection_selected_gainers.find().sort("recordedAt", -1).limit(1)
        for record in latest_record:
            return record
    except Exception as e:
        print(f"Error retrieving latest top gainers: {e}")
        return None

async def analyze_all_gainers_order_book(top_gainers):
    if not top_gainers:
        print("No top gainers to analyze.")
        return []

    results = []

    for gainer in top_gainers:

        symbol = gainer['symbol']

        interval = "15m"

        # Fetch order book data
        order_book = fetch_order_book(symbol)

        # Analyze the order book
        order_book_trend = analyze_order_book(order_book)

        # Fetch Historical data
        historical_data = fetch_historical_data(symbol, interval)

        # Estimate price movement

        price_movement = estimate_price_movement(symbol, interval, order_book)

        trading_signal = trading_decision_based_on_conditions(price_movement, order_book_trend[0])

        # Generate the result dictionary for each symbol
        result = {
            "symbol": symbol,
            "price_increase_percentage": gainer['priceChangePercent'],
            "orderbook": order_book_trend,
            "price_movement": price_movement,
            "trading_signal": trading_signal
        }
        results.append(result)

    for res in results:
        print(res)

    return results



async def main():
    print("Starting main function...")
    # Fetch all symbols from Binance
    all_symbols = fetch_all_binance_symbols()

    # Start the WebSocket connection with all symbols
    ws_task = asyncio.create_task(binance_ws(all_symbols, collection))

    # Initialize and pass the bot instance
    bot = Bot(token=telegram_bot_token)

    # Initial wait period to collect some data
    await asyncio.sleep(120)  # 5 minutes (300 seconds)

    # Schedule database cleanup every 6 hours
    cleanup_interval = 6 * 60 * 60  # 6 hours in seconds
    last_cleanup_time = time.time()

    while True:
        try:
            current_time = time.time()
            if current_time - last_cleanup_time >= cleanup_interval:
                print('current time:', current_time)
                print('last_cleanup_time:', last_cleanup_time)
                print('Gap:', current_time - last_cleanup_time)
                cleanup_old_data(3)
                last_cleanup_time = current_time

            # Calculate top gainers
            top_gainers = calculate_top_gainers(top_n=10)
            record_top_gainers(top_gainers)
            write_top_gainers_to_file(top_gainers)
            top_gainer_symbols = [item['symbol'] for item in top_gainers]

            # Analyze the top gainer and its order book
            
            top_gainer_analysis = await analyze_all_gainers_order_book(top_gainers)
        
            # Format and send the analysis to Telegram
            
            formatted_message = format_message(top_gainer_analysis)
            
            try:
                await send_telegram_message(bot, telegram_chat_id, formatted_message)
            except Exception as e:
                print(f"Error occurred in sending telegram: {e}")

            # Here is where you'd integrate the trading execution logic
            # Execute trading decisions based on the analysis and trading signal
            # Make sure to check your account balance and trading conditions before executing
            for signal in top_gainer_analysis:
                trade_response = execute_order_based_on_signal_and_balance(signal['trading_signal'], client)
                print(f"Trade execution response: {trade_response}")

            # This function checks all your open positions and decides whether to close them
            close_positions_response = close_positions_based_on_profit_loss(client, profit_threshold=0.03, loss_threshold=-0.03)
            print(f"Close positions response: {close_positions_response}")

            if top_gainer_symbols:
                # Cancel the existing WebSocket task and start a new one with updated symbols
                print(f"Subscribing to symbols: {top_gainer_symbols}")
                ws_task.cancel()
                try:
                    await ws_task
                except asyncio.CancelledError:
                    print("Cancelled existing WebSocket task.")

                ws_task = asyncio.create_task(binance_ws(top_gainer_symbols, collection))

        except Exception as e:
            print(f"Error occurred: {e}")

        # Wait for the next interval
        await asyncio.sleep(300)  # 5 minutes

if __name__ == "__main__":
    asyncio.run(main())

