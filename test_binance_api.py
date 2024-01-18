import os
import requests
import ccxt
import asyncio
from binance.spot import Spot
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

api_key = os.environ.get('API_KEY')
api_secret = os.environ.get('API_SECRET_KEY')

client = Spot()

# API key/secret are required for user data endpoints
client = Spot(api_key=api_key, api_secret=api_secret)


def check_account_balance():
    # Fetch account information
    account_info = client.account()

    # Initialize an empty dictionary to store balances
    balances_dict = {}

    # Filter assets with a balance and add them to the dictionary
    for balance in account_info['balances']:
        if float(balance['free']) > 0.0 or float(balance['locked']) > 0.0:
            balances_dict[balance['asset']] = {
                'free': balance['free'],
                'locked': balance['locked']
            }

    return balances_dict

def check_OHLC(symbol, interval):

    # Fetch OHLC data
    candlesticks = client.klines(symbol, interval)

    # Initialize the dict

    ohlc_dict = {}

    # ohlc data

    ohlc_data = {
            'open_time':candlesticks[-1][0],
            'open':candlesticks[-1][1],
            'high':candlesticks[-1][2],
            'low':candlesticks[-1][3],
            'close':candlesticks[-1][4],
            'volume':candlesticks[-1][5],
            'close_time':candlesticks[-1][6]
        }

    ohlc_dict[symbol] = ohlc_data

    return ohlc_dict

def check_OHLC_history(symbol, interval):
    # Fetch OHLC data
    candlesticks = client.klines(symbol, interval)

    # Initialize an empty dictionary to store OHLC data
    ohlc_dict = {}

    # Process each candlestick and add it to the dictionary
    for candle in candlesticks:

        open_time = candle[0]

        ohlc_data = {
            'open_time':candle[0],
            'open': candle[1],
            'high': candle[2],
            'low': candle[3],
            'close': candle[4],
            'volume': candle[5],
            'close_time':candle[6],
        }

        ohlc_dict[open_time] = ohlc_data

    return ohlc_dict

def get_top_gainers(interval='15m', top_n=20):
    
    print("Running...")

    # Binance API endpoint for historical candlestick data
    url = "https://api.binance.com/api/v3/klines"

    # Get the list of symbols from the exchange information endpoint
    symbols_response = requests.get("https://api.binance.com/api/v3/exchangeInfo")
    symbols = [symbol['symbol'] for symbol in symbols_response.json()['symbols'] if 'USDT' in symbol['symbol']]

    gainers = []

    for symbol in symbols:
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': 1  # We only need the latest candlestick
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()

            if data and len(data) > 0:
                open_price = float(data[0][1])
                close_price = float(data[0][4])
                percent_change = ((close_price - open_price) / open_price) * 100

                # Add the symbol, its closing price, and the percentage change to the list
                gainers.append((symbol, close_price, percent_change))

    # Sort the symbols by their percentage price change
    top_gainers = sorted(gainers, key=lambda x: x[2], reverse=True)

    # Return the top N gainers
    return top_gainers[:top_n]

# Get and print the top 20 gainers for the 15-minute interval
# top_gainers_15m = get_top_gainers('15m', 20)
# print(top_gainers_15m)






# print(check_account_balance())

print(check_OHLC("TOMOUSDT","1m"))

# print(check_OHLC_history("BTCUSDT","1m"))







