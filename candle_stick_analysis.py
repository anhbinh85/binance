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

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    df['EMA_Fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
    df['EMA_Slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
    df['MACD'] = df['EMA_Fast'] - df['EMA_Slow']
    df['MACD_Signal'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()


def estimate_price_movement(symbol, interval, order_book):
    # Fetch historical price data
    historical_data = fetch_historical_data(symbol, interval)

    if historical_data is None or len(historical_data) < 50:
        return 0

    # Convert historical data to a DataFrame
    df = pd.DataFrame(historical_data)

    # Calculate SMA, EMA, RSI, and MACD manually or using pandas_ta
    df['SMA_14'] = df['close'].rolling(window=14).mean()
    df['EMA_14'] = df['close'].ewm(span=14, adjust=False).mean()
    df['RSI_14'] = ta.momentum.rsi(df['close'], length=14)

    calculate_macd(df)

    df['Middle_Band'] = df['close'].rolling(window=20).mean()
    df['STD'] = df['close'].rolling(window=20).std()
    df['Upper_Band'] = df['Middle_Band'] + (df['STD'] * 2)
    df['Lower_Band'] = df['Middle_Band'] - (df['STD'] * 2)

    latest = df.iloc[-1]
    rsi = latest['RSI_14']
    macd_current = latest['MACD']
    macdsignal_current = latest['MACD_Signal']
    upper_band = latest['Upper_Band']
    lower_band = latest['Lower_Band']
    latest_close = latest['close']

    # Order book analysis for bid/ask ratio
    bid_volume = sum(float(bid[1]) for bid in order_book['bids'])
    ask_volume = sum(float(ask[1]) for ask in order_book['asks'])
    bid_ask_ratio = bid_volume / ask_volume

    # Bollinger Bands Signals
    bb_signal = 0
    if latest_close > upper_band:
        bb_signal = -1  # Price might be overbought
    elif latest_close < lower_band:
        bb_signal = 1  # Price might be oversold

    # Combine signals
    uptrend_signals = 0
    downtrend_signals = 0

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

    # Incorporating Bollinger Band signals
    if bb_signal == 1:
        uptrend_signals += 1
    elif bb_signal == -1:
        downtrend_signals += 1

    # Final decision
    decision = 0
    if uptrend_signals > downtrend_signals:
        decision = 1
    elif downtrend_signals > uptrend_signals:
        decision = -1

    return {
        'Symbol': symbol,
        'RSI': rsi,
        'MACD_Current': macd_current,
        'MACDSignal_Current': macdsignal_current,
        'Bid_Ask_Ratio': bid_ask_ratio,
        'Uptrend_Signals': uptrend_signals,
        'Downtrend_Signals': downtrend_signals,
        'latest_close':latest_close,
        'Bollinger_Upper': upper_band,
        'Bollinger_Lower': lower_band,
        'Bollinger_Signal': bb_signal,
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


