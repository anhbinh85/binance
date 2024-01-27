import os
import requests
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

def can_trade_based_on_balance(trading_signal, balances):
    """
    Check if the trading signal can be executed based on the current account balance.

    Parameters:
    trading_signal (dict): Trading signal containing the symbol and the decision.
    balances (dict): Dictionary of current balances.

    Returns:
    dict: A dictionary indicating whether you can trade and which asset (coin or USDT) you can use.
    """
    symbol = trading_signal['Symbol']
    coin = symbol.replace('USDT', '')  # Extract the coin name from the symbol

    can_trade = False
    trade_with = None

    # Check for Long or Short signal
    if trading_signal['Long Position'] == 1 or trading_signal['Short Position'] == -1:
        # Check if the coin balance is available for the trade
        if coin in balances and float(balances[coin]['free']) > 0:
            can_trade = True
            trade_with = coin
        elif 'USDT' in balances and float(balances['USDT']['free']) > 0:
            # Check if USDT balance is available
            can_trade = True
            trade_with = 'USDT'

    return {
        'can_trade': can_trade,
        'trade_with': trade_with
    }

# Example usage
# balances = check_account_balance()
# trading_signal = {'Symbol': 'BTCUSDT', 'Long Position': 1, 'Short Position': 0}
# trade_decision = can_trade_based_on_balance(trading_signal, balances)

# print(trade_decision)
