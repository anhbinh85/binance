import os
import requests
from binance.client import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv('API_KEY')
api_secret = os.getenv('API_SECRET_KEY')

# Initialize the Binance Client for Futures
client = Client(api_key, api_secret)

def check_futures_account_balance():
    futures_balance = client.futures_account_balance()
    balances_dict = {balance['asset']: {'free': balance['balance'], 'locked': balance['crossWalletBalance']} for balance in futures_balance}
    return balances_dict

def can_trade_based_on_balance(trading_signal, balances):
    symbol = trading_signal['Symbol']
    can_trade = False
    trade_with = None

    # Check USDT balance for long position or opening a short position
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

def execute_order_based_on_signal_and_balance(trading_signal):
    balances = check_futures_account_balance()
    trade_decision = can_trade_based_on_balance(trading_signal, balances)

    if not trade_decision['can_trade']:
        return {'error': 'Insufficient balance for trading.'}

    market_price = get_market_price(trading_signal['Symbol'])
    usd_amount = 10  # USD amount to trade
    quantity = calculate_quantity_for_usd_amount(usd_amount, market_price)

    try:
        if trading_signal['Long Position'] == 1:
            # Open a long position
            order_response = client.futures_create_order(symbol=trading_signal['Symbol'], side='BUY', type='MARKET', quantity=quantity)
        elif trading_signal['Short Position'] == 1:
            # Open a short position
            order_response = client.futures_create_order(symbol=trading_signal['Symbol'], side='SELL', type='MARKET', quantity=quantity)
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
# trading_signal = {'Symbol': 'BTCUSDT', 'Spot Trading': -1, 'Long Position': 0, 'Short Position': 1}
# order_result = execute_order_based_on_signal_and_balance(trading_signal)
# print(order_result)


# Example: Get futures account balance
# futures_balance = client.futures_account_balance()
# print(futures_balance)
