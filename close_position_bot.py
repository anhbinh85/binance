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
    close_positions_based_on_profit_loss(client, profit_threshold=0.0005, loss_threshold=-0.05)
    time.sleep(5)