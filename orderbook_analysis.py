import requests

def fetch_order_book(symbol, limit=500):
    """
    Fetch the order book for a given symbol from Binance.
    """
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={limit}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching order book for {symbol}: {response.status_code}")
        return None

def analyze_order_book(order_book):
    """
    Analyze the order book to estimate supply, demand, and potential price movement.
    """
    if not order_book:
        return None, {}

    bids = order_book['bids']  # List of [price, quantity]
    asks = order_book['asks']  # List of [price, quantity]

    # Calculate the total volumes for bids and asks
    total_bid_volume = sum(float(bid[1]) for bid in bids)
    total_ask_volume = sum(float(ask[1]) for ask in asks)

    trend = ""
    ratio_dict = {}

    if total_bid_volume > total_ask_volume:
        trend = "Possible Uptrend"
        ratio_dict['ratio bid/ask'] = total_bid_volume / total_ask_volume
    elif total_ask_volume > total_bid_volume:
        trend = "Possible Downtrend"
        ratio_dict['ratio ask/bid'] = total_ask_volume / total_bid_volume
    else:
        trend = "Equilibrium"
        ratio_dict['ratio'] = 1  # Equal volumes

    return trend, ratio_dict





