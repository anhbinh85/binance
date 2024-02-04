import os
import math
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET_KEY')

# Initialize the Binance Client for Futures
client = Client(api_key, api_secret)

def set_leverage(symbol, leverage=2):

    if not is_symbol_supported_for_futures(symbol):
        print(f"{symbol} is not supported for futures trading. Skipping leverage setting.")
        return {'success': True, 'response': f"{symbol} not supported for futures."}
    try:
        response = client.futures_change_leverage(symbol=symbol, leverage=leverage)
        print(f"Leverage set to {leverage} for {symbol}.")
        return {'success': True, 'response': response}
    except Exception as e:
        print(f"Error setting leverage for {symbol}: {e}")
        return {'success': False, 'error': str(e)}


def adjust_quantity_precision(symbol, quantity, client):

    try:
        # Fetch exchange information
        exchange_info = client.futures_exchange_info()
        symbol_info = next((item for item in exchange_info['symbols'] if item['symbol'] == symbol), None)
        
        if symbol_info is not None:
            # Find the LOT_SIZE filter for the symbol, which contains the stepSize
            lot_size_filter = next((filter for filter in symbol_info['filters'] if filter['filterType'] == 'LOT_SIZE'), None)
            if lot_size_filter:
                step_size = float(lot_size_filter['stepSize'])
                # Calculate the quantity precision as the number of decimal places allowed by the stepSize
                quantity_precision = int(-math.log10(step_size))
                # Adjust the quantity to match the required precision
                adjusted_quantity = round(quantity, quantity_precision)
                return adjusted_quantity
        
        # If symbol info is not found or LOT_SIZE filter is missing, return the original quantity
        return quantity

    except Exception as e:
        print(f"Error adjusting quantity precision for {symbol}: {e}")
        return quantity  # Return the original quantity in case of any

def fetch_futures_symbols():
    try:
        exchange_info = client.futures_exchange_info()
        futures_symbols = [symbol['symbol'] for symbol in exchange_info['symbols']]
        return futures_symbols
    except Exception as e:
        print(f"Failed to fetch futures symbols: {e}")
        return []

def is_symbol_supported_for_futures(symbol, futures_symbols):
    return symbol in futures_symbols

def check_futures_account_balance():
    futures_balance = client.futures_account_balance()
    balances_dict = {}
    for balance in futures_balance:
        if float(balance['balance']) > 0.0 or float(balance['crossWalletBalance']) > 0.0:
            balances_dict[balance['asset']] = {
                'free': balance['balance'],
                'locked': balance['crossWalletBalance']
            }
    return balances_dict

def can_trade_based_on_balance(trading_signal, balances):
    symbol = trading_signal['Symbol']
    can_trade = False
    trade_with = None
    if 'USDT' in balances and float(balances['USDT']['free']) > 0:
        can_trade = True
        trade_with = 'USDT'
    return {'can_trade': can_trade, 'trade_with': trade_with}

def get_market_price(symbol):
    latest_price_info = client.futures_symbol_ticker(symbol=symbol)
    return float(latest_price_info['price'])

def calculate_quantity_for_usd_amount(usd_amount, market_price):
    quantity = usd_amount / market_price
    return round(quantity, 6)


def execute_order_based_on_signal_and_balance(trading_signal, client):
    
    symbol = trading_signal['Symbol']

    # Fetch futures symbols list
    futures_symbols = fetch_futures_symbols()
    print("Futures_symbols: ", futures_symbols)
 
    # Check if the symbol is supported for futures trading
    if not is_symbol_supported_for_futures(symbol, futures_symbols):
        return {'error': f'{symbol} is not supported for futures trading.'}
    
    # Attempt to set leverage, but do not stop the process if it fails
    leverage_response = set_leverage(symbol)
    if not leverage_response['success']:
        # Log the failure but do not return an error to allow the order process to continue
        print(f"Proceeding without setting leverage for {symbol}. Reason: {leverage_response.get('error', 'Unknown error')}")
    
    # Continue with order execution
    balances = check_futures_account_balance()
    trade_decision = can_trade_based_on_balance(trading_signal, balances)
    if not trade_decision['can_trade']:
        return {'error': 'Insufficient balance for trading.'}
    
    market_price = get_market_price(symbol)
    usd_amount = 5  # Define the USD amount to trade
    initial_quantity = calculate_quantity_for_usd_amount(usd_amount, market_price)
    # Ensure to adjust the quantity precision based on the symbol's requirements
    adjusted_quantity = adjust_quantity_precision(symbol, initial_quantity, client)
    
    try:
        # Place the order based on the trading signal, without relying on leverage being set
        if trading_signal['Long Position'] == 1:
            order_response = client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=adjusted_quantity)
        elif trading_signal['Short Position'] == 1:
            order_response = client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=adjusted_quantity)
        else:
            return {'error': 'Invalid trading signal provided.'}
        return order_response
    except Exception as e:
        return {'error': str(e)}



def close_positions_based_on_profit_loss(client, profit_threshold=0.03, loss_threshold=-0.03):
    """
    Closes open futures positions based on profit or loss thresholds. Also, reports positions that did not meet the threshold.

    Parameters:
    - client: Initialized Binance futures client.
    - profit_threshold: The profit percentage at which to close the position (e.g., 0.03 for 3%).
    - loss_threshold: The loss percentage at which to close the position (e.g., -0.03 for -3%).

    Returns:
    - A dictionary with lists of closed positions and positions not meeting the threshold.
    """
    closed_positions = []
    no_action_positions = []

    # Get current open positions
    positions = client.futures_account()['positions']
    for position in positions:
        if float(position['positionAmt']) == 0:
            continue  # Skip if no open position
        
        symbol = position['symbol']
        entryPrice = float(position['entryPrice'])
        markPrice = float(position['markPrice'])
        positionAmt = float(position['positionAmt'])
        unRealizedProfit = float(position['unRealizedProfit'])
        pnl_percentage = unRealizedProfit / (entryPrice * abs(positionAmt))

        # Check if the PnL meets the threshold to close the position
        if pnl_percentage >= profit_threshold or pnl_percentage <= loss_threshold:
            # Determine side based on whether the position is long or short
            side = 'SELL' if positionAmt > 0 else 'BUY'
            quantity = abs(positionAmt)
            
            # Close the position
            order_response = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
            
            # Add details to the closed positions list
            closed_positions.append({
                'symbol': symbol,
                'entryPrice': entryPrice,
                'closingPrice': markPrice,
                'quantity': positionAmt,
                'pnl_percentage': pnl_percentage,
                'order_response': order_response
            })
        else:
            # Position does not meet the threshold, add to no_action_positions list
            no_action_positions.append({
                'symbol': symbol,
                'entryPrice': entryPrice,
                'currentPrice': markPrice,
                'quantity': positionAmt,
                'pnl_percentage': pnl_percentage,
                'action': 'No action taken'
            })

    return {
        'closed_positions': closed_positions,
        'no_action_positions': no_action_positions
    }



# Example usage
# trading_signal = {'Symbol': 'PYTHUSDT', 'Spot Trading': -1, 'Long Position': 0, 'Short Position': 1}
# balances = check_futures_account_balance()
# print(can_trade_based_on_balance(trading_signal, balances))


# futures_symbols = fetch_futures_symbols()
# print(futures_symbols)

# print(is_symbol_supported_for_futures("TROYUSDT", futures_symbols))