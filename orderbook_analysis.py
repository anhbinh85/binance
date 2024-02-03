import requests
import pandas as pd
import numpy as np

def fetch_order_book(symbol, limit=500):
    """
    Fetch the order book for a given symbol from Binance.
    """
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={limit}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error fetching order book for {symbol}: {response.status_code}")
        return None

def analyze_order_book(order_book, spread_percentile=90):
    """
    Analyze the order book to estimate supply, demand, and potential price movement, including spread analysis and imbalance.
    """
    if not order_book:
        return "No data", {}

    bids = order_book['bids']  # List of [price, quantity]
    asks = order_book['asks']  # List of [price, quantity]

    # Convert bids and asks to DataFrame
    bids_df = pd.DataFrame(bids, columns=['price', 'quantity'], dtype=float)
    asks_df = pd.DataFrame(asks, columns=['price', 'quantity'], dtype=float)

    # Calculate total volumes and bid-ask spread
    total_bid_volume = bids_df['quantity'].sum()
    total_ask_volume = asks_df['quantity'].sum()
    bid_ask_spread = asks_df['price'].min() - bids_df['price'].max()

    # Imbalance calculation
    imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)

    # Spread threshold calculation
    spread_threshold = np.percentile(asks_df['price'] - bids_df['price'], spread_percentile)

    # Trend prediction based on imbalance and spread threshold
    trend = "No clear trend"
    if imbalance > 0.1 and bid_ask_spread < spread_threshold:
        trend = "Uptrend Expected"
    elif imbalance < -0.1 and bid_ask_spread < spread_threshold:
        trend = "Downtrend Expected"
    elif bid_ask_spread >= spread_threshold:
        trend = "Uncertain Market"

    # Prepare the result dictionary
    ratio_dict = {
        'total_bid_volume': total_bid_volume,
        'total_ask_volume': total_ask_volume,
        'imbalance': imbalance,
        'bid_ask_spread': bid_ask_spread,
        'spread_threshold': spread_threshold,
        'trend': trend
    }

    return trend, ratio_dict



