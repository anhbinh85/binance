import os
import math
import time
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

def set_leverage(symbol, leverage=4):

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

def is_symbol_supported_for_futures(symbol):
    futures_symbols = fetch_futures_symbols()
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

def has_open_positions(symbol, client):
    """Check if there are open positions for a given symbol."""
    positions = client.futures_account()["positions"]
    for position in positions:
        if position['symbol'] == symbol and float(position['positionAmt']) != 0:
            return True
    return False


def execute_order_based_on_signal_and_balance(trading_signal, client,
                                             trading_decision):

    symbol = trading_signal['Symbol']

    # Fetch futures symbols list
    futures_symbols = fetch_futures_symbols()

    # Check for existing positions
    if has_open_positions(symbol, client):
        return {
            'error':
            f'Existing open position for {symbol}, cannot place new order.'
        }

    if symbol in futures_symbols:

        try:
            # Attempt to set leverage, but do not stop the process if it fails
            leverage_response = set_leverage(symbol)

            if not leverage_response['success']:
                # Log the failure but do not return an error to allow the order process to continue
                print(
                    f"Proceeding without setting leverage for {symbol}. Reason: {leverage_response.get('error', 'Unknown error')}"
                )

            # Continue with order execution
            balances = check_futures_account_balance()
            trade_decision = can_trade_based_on_balance(
                trading_signal, balances)
            if not trade_decision['can_trade']:
                return {'error': 'Insufficient balance for trading.'}

            market_price = get_market_price(symbol)
            usd_amount = 6  # Define the USD amount to trade
            initial_quantity = calculate_quantity_for_usd_amount(
                usd_amount, market_price)
            # Ensure to adjust the quantity precision based on the symbol's requirements
            adjusted_quantity = adjust_quantity_precision(
                symbol, initial_quantity, client)
            print("adjust_quantity_precision: ", adjusted_quantity)

            # Place the order based on the trading_signal and trading_decision
            if trading_signal[
                    'Long Position'] == 1 and trading_decision in (
                        "Strong Long", "Long", "Weak Long", "Hold (Potential Long)"):
                order_response = client.futures_create_order(
                    symbol=symbol,
                    side='BUY',#CORRECT LOGIC IS BUY
                    type='MARKET',
                    quantity=adjusted_quantity)
            elif trading_signal[
                    'Short Position'] == 1 and trading_decision in (
                        "Strong Short", "Short", "Weak Short", "Hold (Potential Short)"):
                order_response = client.futures_create_order(
                    symbol=symbol,
                    side='SELL',#CORRECT LOGIC IS SELL
                    type='MARKET',
                    quantity=adjusted_quantity)
            else:
                return {
                    'error':
                    'No trade signal generated or trading decision does not match.'
                }

            return order_response

        except Exception as e:
            return {'error': str(e)}

    else:
        return {f'{symbol} is not supported for futures trading.'}


def close_positions_based_on_profit_loss(client, profit_threshold=0.05, loss_threshold=-0.05):
    closed_positions = []
    no_action_positions = []

    total_unrealized_profit = 0.0
    total_notional = 0.0

    try:
        # Get current open positions
        account_info = client.futures_account()
        positions = account_info.get('positions', [])
        
        # First, calculate total unrealized profit and total notional
        for position in positions:

            positionAmt = float(position.get('positionAmt', 0))

            if positionAmt != 0:
                print("Position in close function:", position)
                unRealizedProfit = float(position.get('unrealizedProfit', '0'))
                symbol = position.get('symbol')
                entryPrice = float(position.get('entryPrice', '0'))
                current_price_info = client.futures_symbol_ticker(symbol=symbol)
                markPrice = float(current_price_info['price']) if current_price_info else 0
                notional = abs(positionAmt * markPrice)
                total_unrealized_profit += unRealizedProfit
                total_notional += notional

                # Calculate PnL percentage
                pnl_percentage = (unRealizedProfit / notional) if notional else 0



                if pnl_percentage >= profit_threshold or pnl_percentage <= loss_threshold:

                    side = 'SELL' if positionAmt > 0 else 'BUY'
                    quantity = abs(positionAmt)
                    print(f"Attempting to close {symbol} | Side: {side} | Quantity: {quantity}")
                    order_response = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)

                    print(f"Order response for {symbol}: {order_response}")

                    closed_positions.append({
                        'symbol': symbol,
                        'positionAmt': positionAmt,
                        'entryPrice': entryPrice,
                        'closingPrice': markPrice,
                        'pnl_percentage': pnl_percentage,
                        'order_response': order_response
                    })
                else:
                    print(f"No action taken for {symbol}: PnL%={pnl_percentage*100:.2f}%")
                    no_action_positions.append({
                        'symbol': symbol,
                        'positionAmt': positionAmt,
                        'entryPrice': entryPrice,
                        'currentPrice': markPrice,
                        'pnl_percentage': pnl_percentage,
                        'action': 'No action taken'
                    })

        

        # Calculate overall PnL percentage
        overall_pnl_percentage = (total_unrealized_profit / total_notional) if total_notional else 0
        print(f"Overall PnL Percentage: {overall_pnl_percentage*100:.2f}%")


        # Check if overall profit exceeds the threshold or if there are losses but total profit is positive
        if overall_pnl_percentage >= 0.05:
            for position in positions:
                positionAmt = float(position.get('positionAmt', 0))
                if positionAmt != 0:
                    symbol = position.get('symbol')
                    entryPrice = float(position.get('entryPrice', '0'))
                    current_price_info = client.futures_symbol_ticker(symbol=symbol)
                    markPrice = float(current_price_info['price']) if current_price_info else 0
                    side = 'SELL' if positionAmt > 0 else 'BUY'
                    quantity = abs(positionAmt)
                    
                    # Execute market order to close the position
                    order_response = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
                    
                    closed_positions.append({
                        'symbol': symbol,
                        'positionAmt': positionAmt,
                        'entryPrice': entryPrice,
                        'closingPrice': markPrice,
                        'pnl_percentage': overall_pnl_percentage,
                        'order_response': order_response
                    })
                    print(f"Closed position for {symbol} due to overall profit.")
        else:
            # If the overall profit does not meet the threshold, list positions for no action
            for position in positions:
                positionAmt = float(position.get('positionAmt', 0))
                if positionAmt != 0:
                    symbol = position.get('symbol')
                    no_action_positions.append({
                        'symbol': symbol,
                        'positionAmt': positionAmt,
                        'action': 'No action taken due to insufficient overall profit'
                    })
                    print(f"No action taken for {symbol} due to insufficient overall profit.")
    
    except BinanceAPIException as e:
        print(f"Error while attempting to close positions: {e}")
        return {'error': str(e)}

    return {
        'closed_positions': closed_positions,
        'no_action_positions': no_action_positions
    }


# def close_positions_based_on_profit_loss(client, profit_threshold=0.01):

#     closed_positions = []
#     no_action_positions = []

#     try:
#         # Get current open positions
#         account_info = client.futures_account()
#         positions = account_info.get('positions', [])
#         for position in positions:
#             positionAmt = float(position.get('positionAmt', 0))

#             if positionAmt != 0:
#                 symbol = position.get('symbol')
#                 entryPrice = float(position.get('entryPrice', '0'))
#                 # Fetch current markPrice for a more accurate calculation
#                 current_price_info = client.futures_symbol_ticker(symbol=symbol)
#                 markPrice = float(current_price_info['price']) if current_price_info else 0
#                 unRealizedProfit = float(position.get('unrealizedProfit', '0'))

#                 # Calculate notional using markPrice
#                 notional = abs(positionAmt * markPrice)

#                 # Calculate PnL percentage
#                 pnl_percentage = (unRealizedProfit / notional) if notional else 0

#                 print(f"Checking position for {symbol}: PnL%={pnl_percentage*100:.2f}% vs. Threshold={profit_threshold*100}%")

#                 if pnl_percentage >= profit_threshold:
#                     side = 'SELL' if positionAmt > 0 else 'BUY'
#                     quantity = abs(positionAmt)
#                     print(f"Attempting to close {symbol} | Side: {side} | Quantity: {quantity}")
#                     order_response = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)

#                     print(f"Order response for {symbol}: {order_response}")

#                     closed_positions.append({
#                         'symbol': symbol,
#                         'positionAmt': positionAmt,
#                         'entryPrice': entryPrice,
#                         'closingPrice': markPrice,
#                         'pnl_percentage': pnl_percentage,
#                         'order_response': order_response
#                     })
#                 else:
#                     print(f"No action taken for {symbol}: PnL%={pnl_percentage*100:.2f}%")
#                     no_action_positions.append({
#                         'symbol': symbol,
#                         'positionAmt': positionAmt,
#                         'entryPrice': entryPrice,
#                         'currentPrice': markPrice,
#                         'pnl_percentage': pnl_percentage,
#                         'action': 'No action taken'
#                     })
#     except BinanceAPIException as e:
#         print(f"Error closing positions for {symbol}: {e}")
#         return {'error': str(e)}

#     return {
#         'closed_positions': closed_positions,
#         'no_action_positions': no_action_positions
#     }







# Example usage
# trading_signal = {'Symbol': 'PYTHUSDT', 'Spot Trading': -1, 'Long Position': 0, 'Short Position': 1}
# balances = check_futures_account_balance()
# print(can_trade_based_on_balance(trading_signal, balances))


# futures_symbols = fetch_futures_symbols()
# print(futures_symbols)

# print(is_symbol_supported_for_futures("TROYUSDT", futures_symbols))

# print(adjust_quantity_precision('JUPUSDT', 1000, client))