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


def execute_order_based_on_signal_and_balance(trading_signal, client):
    
    symbol = trading_signal['Symbol']
    # print("Symbol in execute order: ", symbol)

    # Fetch futures symbols list
    futures_symbols = fetch_futures_symbols()
    # print("Futures_symbols: ", futures_symbols)

     # Check for existing positions
    if has_open_positions(symbol, client):
        return {'error': f'Existing open position for {symbol}, cannot place new order.'}

    if symbol in futures_symbols:

        try:
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
            print("adjust_quantity_precision: ", adjusted_quantity)
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

    else:
        return {f'{symbol} is not supported for futures trading.'}



def close_positions_based_on_profit_loss(client, profit_threshold=0.03):
    closed_positions = []
    no_action_positions = []

    try:
        # Get current open positions
        account_info = client.futures_account()
        positions = account_info.get('positions', [])
        for position in positions:
            print("position in close position function: ", position)
            positionAmt = float(position.get('positionAmt', 0))
            if positionAmt != 0:
                symbol = position.get('symbol')
                entryPrice = float(position.get('entryPrice', '0'))
                markPrice = float(position.get('markPrice', '0'))
                unRealizedProfit = float(position.get('unrealizedProfit', '0'))
                notional = abs(positionAmt * markPrice)  # Using markPrice for notional calculation

                # Calculate PnL percentage based on notional and unrealizedProfit
                pnl_percentage = (unRealizedProfit / notional) if notional else 0

                if pnl_percentage >= profit_threshold:
                    # Determine the correct side for closing the position
                    side = 'SELL' if positionAmt > 0 else 'BUY'
                    quantity = abs(positionAmt)
                    # Execute market order to close the position
                    order_response = client.futures_create_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
                    closed_positions.append({
                        'symbol': symbol,
                        'positionAmt': positionAmt,
                        'entryPrice': entryPrice,
                        'closingPrice': markPrice,
                        'pnl_percentage': pnl_percentage,
                        'order_response': order_response
                    })
                else:
                    # Append to no action positions if PnL threshold is not met
                    no_action_positions.append({
                        'symbol': symbol,
                        'positionAmt': positionAmt,
                        'entryPrice': entryPrice,
                        'currentPrice': markPrice,
                        'pnl_percentage': pnl_percentage,
                        'action': 'No action taken'
                    })

    except BinanceAPIException as e:
        print(f"Error closing positions: {e}")
        return {'error': str(e)}

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

# print(adjust_quantity_precision('JUPUSDT', 1000, client))