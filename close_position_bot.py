import os
import math
import time
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
from trading_execution import close_positions_based_on_profit_loss

# Load environment variables
load_dotenv()

api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET_KEY')

# Initialize the Binance Client for Futures
client = Client(api_key, api_secret)

while True:
    print("Checking to close position on profit/loss.......")
    try:
        close_positions_based_on_profit_loss(client, profit_threshold=0.0125, loss_threshold=-0.0125)#profit and loss threshold must devise for leverage level
    except BinanceAPIException as e:
        print(f"Binance API Exception occurred: {e}")
        # Handle the specific Binance API exception (e.g., log the error, retry with exponential backoff)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Handle other unexpected exceptions (e.g., log the error, notify the user)
    
    time.sleep(5)