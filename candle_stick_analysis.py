import requests
import asyncio
import numpy as np
import pandas as pd
import pandas_ta as ta
from orderbook_analysis import fetch_order_book

def fetch_historical_data(symbol, interval):
    """
    Fetch historical candlestick data for a given symbol and interval from Binance API.

    :param symbol: String, the symbol to fetch data for (e.g., 'BTCUSDT').
    :param interval: String, the time interval (e.g., '15m' for 15 minutes).
    :return: List of dictionaries with historical data or None if an error occurs.
    """
    base_url = "https://api.binance.com"
    endpoint = "/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': 1000  # Maximum number of data points (adjust as needed)
    }

    try:
        response = requests.get(base_url + endpoint, params=params)
        response.raise_for_status()
        data = response.json()

        # Convert data to a more usable format
        historical_data = []
        for kline in data:
            entry = {
                'open_time': kline[0],
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5]),
                'close_time': kline[6]
            }
            historical_data.append(entry)

        return historical_data

    except requests.RequestException as e:
        print(f"Error fetching historical data: {e}")
        return None

def estimate_price_movement(symbol, interval, order_book):
    """
    Estimate price movement based on technical indicators and order book analysis.
    Returns 1 for estimated increase, -1 for decrease, and 0 for no clear signal.
    """
    # Step 1: Fetch historical price data
    historical_data = fetch_historical_data(symbol, interval)

    # Check if historical data is sufficient
    if historical_data is None or len(historical_data) < 50:  # Ensure enough data for analysis
        return 0

    # Convert historical data to a DataFrame
    df = pd.DataFrame(historical_data)

    # Define the indicators to be calculated
    indicator_strategy = ta.Strategy(
        name="Basic Indicators",
        description="SMA 14, EMA 14, RSI 14, MACD",
        ta=[
            {"kind": "sma", "length": 14},
            {"kind": "ema", "length": 14},
            {"kind": "rsi", "length": 14},
            {"kind": "macd", "fast": 12, "slow": 26, "signal": 9}
        ]
    )

    # Apply the strategy to the DataFrame
    df.ta.strategy(indicator_strategy)

    # Ensure the indicators are calculated
    if 'SMA_14' not in df or 'EMA_14' not in df:
        print("Required indicators not calculated.")
        return 0

    # Get the latest values
    latest_close = df['close'].iloc[-1]
    sma = df['SMA_14'].iloc[-1]
    ema = df['EMA_14'].iloc[-1]
    rsi = df['RSI_14'].iloc[-1]
    macd_current = df['MACD_12_26_9'].iloc[-1]
    macdsignal_current = df['MACDs_12_26_9'].iloc[-1]

    # Step 3: Order book analysis for bid/ask ratio
    bid_volume = sum(float(bid[1]) for bid in order_book['bids'])
    ask_volume = sum(float(ask[1]) for ask in order_book['asks'])
    bid_ask_ratio = bid_volume / ask_volume

    # Step 4: Combine signals
    uptrend_signals = 0
    downtrend_signals = 0

    # Check price against moving averages
    if latest_close > sma and latest_close > ema:
        uptrend_signals += 1
    elif latest_close < sma and latest_close < ema:
        downtrend_signals += 1

    # Check RSI
    if rsi > 70:
        downtrend_signals += 1
    elif rsi < 30:
        uptrend_signals += 1

    # Check MACD
    if macd_current > macdsignal_current:
        uptrend_signals += 1
    elif macd_current < macdsignal_current:
        downtrend_signals += 1

    # Check Bid/Ask Ratio
    if bid_ask_ratio > 1:
        uptrend_signals += 1
    elif bid_ask_ratio < 1:
        downtrend_signals += 1

    # Final decision
    decision = 0
    if uptrend_signals > downtrend_signals:
        decision = 1
    elif downtrend_signals > uptrend_signals:
        decision = -1

    # Return a dictionary with all the data
    return {
        'Symbol':symbol,
        'RSI': rsi,
        'MACD_Current': macd_current,
        'MACDSignal_Current': macdsignal_current,
        'Bid_Ask_Ratio': bid_ask_ratio,
        'Uptrend_Signals': uptrend_signals,
        'Downtrend_Signals': downtrend_signals,
        'Final_Decision': decision
    }

# def main():
#     # Example usage
#     historical_data = fetch_historical_data("BTCUSDT", "15m")
#     orderbook = fetch_order_book("BTCUSDT", 500)
#     signal = estimate_price_movement("BTCUSDT", "15m", orderbook)
#     print(signal)

# if __name__ == '__main__':
#     main()


