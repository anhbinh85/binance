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
from trading_logic import trading_decision_based_on_conditions, generate_trading_decision
from orderbook_analysis import fetch_order_book, analyze_order_book
from trading_execution import client as client_binance, execute_order_based_on_signal_and_balance, close_positions_based_on_profit_loss
from talib_analysis import TA_Candle_Stick_Recognition
from candle_stick_analysis import *
from candle_stick_with_trend_line import Candle_Stick_Combine_Trend_Line
from candle_stick_with_technical_indicators import TechnicalIndicators
from volume_analysis import calculate_obv

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
        print("Client:", client)
        db = client["binance"]  # Database name
        print("db:", db)
        collection = db["binance_gainers_15m"]  # Collection name
        print("collection:", collection)
        one_doc = collection.find_one()
        print("one_doc:",one_doc)
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
        print(f"Error processing message at handle_message: {e}")


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
            print(f"Error processing message at binance_ws: {e}")

        print("Attempting to reconnect in 5 seconds...")
        
        await asyncio.sleep(5)  # Wait for 5 seconds before attempting to reconnect


def calculate_top_gainers(top_n=20):
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
        print(f"An error occurred at cleanup_old_data: {e}")

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

        limit = 100 #100 candle stick 15m

        # Fetch order book data
        order_book = fetch_order_book(symbol)

        # Analyze the order book
        order_book_trend = analyze_order_book(order_book)

        # Fetch Historical data
        historical_data = fetch_historical_data(symbol, interval, limit)

        # Calculate price statistics
        lookback_period = 48
        average_price = np.mean([entry['close'] for entry in historical_data[-lookback_period:]])
        min_price = min([entry['low'] for entry in historical_data[-lookback_period:]])
        max_price = max([entry['high'] for entry in historical_data[-lookback_period:]])

        #Add OBV into historical_data:
        # historical_data_added_OBV = calculate_obv(historical_data)
        # obv_data = {symbol:historical_data_added_OBV["OBV"]}
        # print("**********OBV*****************")
        # print(obv_data)
        # Calculate OBV
        obv_values = calculate_obv(historical_data)
        # print("Obv Values: ", obv_values)

        # Ta_lib:

        # print(f"Pattern Recognition from TA-LIB....for {symbol}")
        # candle_stick_recognition = TA_Candle_Stick_Recognition(historical_data[-5:])
        # candle_stick_recognition.detect_patterns()

        # Technical Indicatiors Analysis
        print("Technical Indicatiors Analysis ...")
        ti = TechnicalIndicators(historical_data)
        technical_analysis = ti.execute()


        # Candle_stick_with_trend_line:
        print("Candle stick with trend line ... using TA-LIB")
        print(f"Pattern Recognition from TA-LIB....for {symbol}")
        candle_with_trend = Candle_Stick_Combine_Trend_Line(historical_data)
        ta_lib_data = candle_with_trend.execute()

        print("Candle stick pattern by TA: ", ta_lib_data)


        # Fetch the latest candle stick 15m:
        # print("Pattern Recognition from manual analysis...")
        latest_candlestick = historical_data[-1]

        context, average_close = determine_trend(symbol, interval, limit)

        check_hammer_or_hangingman = is_hammer_or_hangingman(latest_candlestick, context)

        engulfing_pattern = check_for_engulfing_pattern(historical_data)

        check_dark_cloud = is_dark_cloud_cover(historical_data)

        check_piercing_pattern = detect_candlestick_piercing_on_in_neck_thrusting_pattern(historical_data)

        check_stars_pattern = detect_stars_patterns(historical_data)

        check_harami = detect_harami_and_cross(historical_data)

        tweezers_top = check_tweezers_top(historical_data)

        tweezers_bottom = check_tweezers_bottom(historical_data)

        belt_hold = check_belt_hold(historical_data)

        upside_gap_two_crows = check_upside_gap_two_crows(historical_data)

        three_black_crows = check_three_black_crows(historical_data)

        three_advancing_white_soldiers = check_three_advancing_white_soldiers(historical_data)

        buddha_top_bottom = check_buddha_top_bottom(historical_data, top=True)

        counterattack_lines = check_counterattack_lines(historical_data)

        dumpling_top = check_dumpling_top(historical_data)

        frypan_bottom = check_frypan_bottom(historical_data)

        tower_top = check_tower_top(historical_data)

        tower_bottom = check_tower_bottom(historical_data)

        window_gaps = detect_window_gaps(historical_data)

        tasuki_patterns = detect_tasuki_patterns(historical_data)

        gapping_plays = detect_gapping_plays(historical_data)

        gapping_side_by_side_white_lines = detect_gapping_side_by_side_white_lines(historical_data)

        rising_falling_three_methods = detect_rising_falling_three_methods(historical_data)

        separating_lines = detect_separating_lines(historical_data)

        doji_types = detect_doji_types(historical_data)

        manual_analysis = {
        "Symbol": symbol,
        "Latest Candle": str(latest_candlestick),
        "Trend": context,
        "Average Close Price": average_close,
        "Manual Patterns": {
            "Hammer or Hangingman": check_hammer_or_hangingman,
            "Engulfing Pattern": engulfing_pattern,
            "Dark Cloud Cover": check_dark_cloud,
            "Piercing, On-Neck, In-Neck, Thrusting": check_piercing_pattern,
            "Stars Pattern": check_stars_pattern,
            "Harami and Cross": check_harami,
            "Tweezers Top": tweezers_top,
            "Tweezers Bottom": tweezers_bottom,
            "Belt Hold": belt_hold,
            "Upside-Gap Two Crows": upside_gap_two_crows,
            "Three Black Crows": three_black_crows,
            "Three Advancing White Soldiers": three_advancing_white_soldiers,
            "Buddha Top/Bottom": buddha_top_bottom,
            "Counterattack Lines": counterattack_lines,
            "Dumpling Top": dumpling_top,
            "Frypan Bottom": frypan_bottom,
            "Tower Top": tower_top,
            "Tower Bottom": tower_bottom,
            "Window Gaps": window_gaps,
            "Tasuki Patterns": tasuki_patterns,
            "Gapping Plays": gapping_plays,
            "Gapping Side-by-Side White Lines": gapping_side_by_side_white_lines,
            "Rising and Falling Three Methods": rising_falling_three_methods,
            "Separating Lines": separating_lines,
            "Doji Types": doji_types
            } 
        }

        master_data = {
            "manual_analysis": manual_analysis,
            "ta_lib_data": ta_lib_data,
            "technical_analysis":technical_analysis
        }

        # print("Manual Candle stick patterns: ", master_data["manual_analysis"])

        # Estimate price movement

        price_movement = estimate_price_movement(symbol, interval, order_book, limit)

        trading_signal = trading_decision_based_on_conditions(price_movement, order_book_trend[0])

        print("Trading Signal: ", trading_signal)

        # Generate the result dictionary for each symbol
        result = {
            "symbol": symbol,
            "price_increase_percentage": gainer['priceChangePercent'],
            "orderbook": order_book_trend,
            "price_movement": price_movement,
            "trading_signal": trading_signal,
            "ta_lib_data" : master_data["ta_lib_data"],
            "technical_analysis": master_data["technical_analysis"],
            "obv_values":obv_values,
            "average_price":average_price,
            "min_price":min_price,
            "max_price":max_price
        }

        trading_decision = generate_trading_decision(result) 

        result["trading_decision"] = trading_decision

        print("Trading Decision: ", result["trading_decision"])

        results.append(result)

    return results

async def main():
    print("Starting main function...")
    # Fetch all symbols from Binance
    all_symbols = fetch_all_binance_symbols()
    print("all symbols: ", all_symbols)

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
            top_gainers = calculate_top_gainers(top_n=20)
            record_top_gainers(top_gainers)
            write_top_gainers_to_file(top_gainers)
            top_gainer_symbols = [item['symbol'] for item in top_gainers]
            print("top_gainer_symbols: ", top_gainer_symbols)

            # Analyze the top gainer and its order book
            
            results = await analyze_all_gainers_order_book(top_gainers)
            # print("top_gainer_analysis: ", top_gainer_analysis)
        
            # Format and send the analysis to Telegram
            
            formatted_message = format_message(results)
            
            try:
                await send_telegram_message(bot, telegram_chat_id, formatted_message)
            except Exception as e:
                print(f"Error occurred in sending telegram: {e}")

            # Here is where you'd integrate the trading execution logic
            # Execute trading decisions based on the analysis and trading signal
            # Make sure to check your account balance and trading conditions before executing
            #################
            for result in results:
                print("signal for symbol: ", result['trading_signal']['Symbol'])
                trading_decision = result["trading_decision"]
                trade_response = execute_order_based_on_signal_and_balance(result['trading_signal'], client_binance, trading_decision)
                print(f"Trade execution response: {trade_response}")

            # This function checks all your open positions and decides whether to close them
            # print("Start to check and close position...")
            # close_positions_response = close_positions_based_on_profit_loss(client_binance)
            # print(f"Close positions response: {close_positions_response}")
            ##################

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
            print(f"Error occurred at main: {e}")

        # Wait for the next interval
        await asyncio.sleep(300)  # 5 minutes

if __name__ == "__main__":
    asyncio.run(main())


# test_mongodb_connection()