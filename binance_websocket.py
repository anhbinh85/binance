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


# Load environment variables from .env file
load_dotenv()

database_url = os.environ.get('database_url')

# MongoDB setup
client = pymongo.MongoClient(database_url)
db = client["binance"]
collection = db["binance_gainers_15m"]

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
    print("Message received: ", message)
    try:
        data = json.loads(message)
        symbol = data['data']['s']
        price = float(data['data']['c'])
        timestamp = datetime.utcfromtimestamp(data['data']['E'] / 1000.0)

        # Log the received message
        print(f"Message received for {symbol}: Price: {price}, Timestamp: {timestamp}")

        collection.insert_one({
        "symbol": symbol,
        "price": price,
        "timestamp": timestamp
        })

        print(f"Inserted new record for {symbol} at {timestamp}")

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
        {"$group": {"_id": "$symbol", "startPrice": {"$first": "$price"}, "endPrice": {"$last": "$price"}}},
        {"$project": {
            "symbol": "$_id",
            "_id": 0,
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

    # Return the top gainers
    print(f"Top gainers: {top_gainers}")
    return top_gainers

def cleanup_old_data(hours_old=3):
    """
    Delete records from the collection that are older than the specified number of hours.
    """
    # Calculate the cutoff date
    cutoff_date = datetime.utcnow() - timedelta(hours=hours_old)

    # Delete documents older than the cutoff date
    result = collection.delete_many({"timestamp": {"$lt": cutoff_date}})
    print(f"Deleted {result.deleted_count} old records (older than {hours_old} hours).")

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
    Write the list of top gainers to a text file.
    """
    try:
        with open(filename, 'w') as file:
            for gainer in top_gainers:
                file.write(f"{gainer}\n")
        print(f"Top gainers successfully written to {filename}")
    except Exception as e:
        print(f"Error writing to file: {e}")

async def main():
    print("Starting main function...")
    # Fetch all symbols from Binance
    all_symbols = fetch_all_binance_symbols()

    # Start the WebSocket connection with all symbols
    ws_task = asyncio.create_task(binance_ws(all_symbols, collection))

    # Initial wait period to collect some data
    await asyncio.sleep(120)  # 5 minutes (300 seconds)

    # Schedule database cleanup every 6 hours
    cleanup_interval = 6 * 60 * 60  # 6 hours in seconds
    last_cleanup_time = time.time()

    while True:
        try:
            current_time = time.time()
            if current_time - last_cleanup_time >= cleanup_interval:
                cleanup_old_data()
                last_cleanup_time = current_time

            # Calculate top gainers
            top_gainers = calculate_top_gainers(top_n=10)
            write_top_gainers_to_file(top_gainers)
            top_gainer_symbols = [item['symbol'] for item in top_gainers]

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
        await asyncio.sleep(240)  # 15 minutes

if __name__ == "__main__":
    asyncio.run(main())

# print(count_records(collection))


# cleanup_old_data(hours_old=0)

