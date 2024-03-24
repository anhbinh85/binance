import requests
import asyncio
import numpy as np
import pandas as pd
import pandas_ta as ta
from orderbook_analysis import fetch_order_book

def fetch_historical_data(symbol, interval, limit):
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
        'limit': limit  # Maximum number of data points (adjust as needed)
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

def calculate_macd(df, fast_period=12, slow_period=24, signal_period=6):
    df['EMA_Fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
    df['EMA_Slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
    df['MACD'] = df['EMA_Fast'] - df['EMA_Slow']
    df['MACD_Signal'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()


def estimate_price_movement(symbol, interval, order_book, limit):
    # Fetch historical price data
    historical_data = fetch_historical_data(symbol, interval, limit)

    if historical_data is None or len(historical_data) < 50:
        return 0

    # Convert historical data to a DataFrame
    df = pd.DataFrame(historical_data)

    # Calculate SMA, EMA, RSI, and MACD manually or using pandas_ta
    df['SMA_12'] = df['close'].rolling(window=12).mean()
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['RSI_12'] = ta.momentum.rsi(df['close'], length=12)
    calculate_macd(df)

    df['Middle_Band'] = df['close'].rolling(window=20).mean()
    df['STD'] = df['close'].rolling(window=20).std()
    df['Upper_Band'] = df['Middle_Band'] + (df['STD'] * 2)
    df['Lower_Band'] = df['Middle_Band'] - (df['STD'] * 2)

    # Calculate Log Returns for Volatility
    df['Log_Return'] = np.log(df['close'] / df['close'].shift(1))
    df['Volatility'] = df['Log_Return'].rolling(window=20).std() * np.sqrt(20)  # Adjusted for 20 periods

    latest = df.iloc[-1]
    rsi = latest['RSI_12']
    macd_current = latest['MACD']
    macdsignal_current = latest['MACD_Signal']
    upper_band = latest['Upper_Band']
    lower_band = latest['Lower_Band']
    latest_close = latest['close']
    volatility = latest['Volatility']

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

    # Incorporate volatility into the signals
    volatility_threshold = df['Volatility'].quantile(0.8)  # 80th percentile as a threshold
    if volatility > volatility_threshold:
        downtrend_signals += 1  # Higher volatility might indicate market fear
    else:
        uptrend_signals += 1  # Lower volatility might indicate stability

    # Final decision
    decision = 0
    if uptrend_signals > downtrend_signals:
        decision = 1  # More signals point towards an uptrend
    elif downtrend_signals > uptrend_signals:
        decision = -1  # More signals point towards a downtrend

    return {
        'Symbol': symbol,
        'RSI': rsi,
        'MACD_Current': macd_current,
        'MACDSignal_Current': macdsignal_current,
        'Bid_Ask_Ratio': bid_ask_ratio,
        'Uptrend_Signals': uptrend_signals,
        'Downtrend_Signals': downtrend_signals,
        'latest_close': latest_close,
        'Bollinger_Upper': upper_band,
        'Bollinger_Lower': lower_band,
        'Bollinger_Signal': bb_signal,
        'Volatility': volatility,
        'Volatility_Threshold': volatility_threshold,
        'Final_Decision': decision
    }

def is_hammer_or_hangingman(candle, context):
    """
    Determines if the provided candle is a hammer or a hanging man based on the context.
    
    :param candle: A dictionary with open, high, low, and close prices
    :param context: The market trend context ("uptrend" or "downtrend")
    :return: Message indicating whether the candle is a hammer, a hanging man, or neither
    """
    body = abs(candle['close'] - candle['open'])  # Absolute body size
    candle_range = candle['high'] - candle['low']  # Total range
    lower_shadow = min(candle['open'], candle['close']) - candle['low']  # Lower shadow length
    upper_shadow = candle['high'] - max(candle['open'], candle['close'])  # Upper shadow length

    if context == "downtrend" and lower_shadow >= 2 * body and upper_shadow <= body * 0.5 and body <= candle_range * 0.33:
        return ["hammer",str(candle)]
    elif context == "uptrend" and lower_shadow >= 2 * body and upper_shadow <= body * 0.5 and body <= candle_range * 0.33:
        return ["hangingman", str(candle)]
    else:
        return "Neither a hammer nor a hanging man candlestick."


def determine_trend_with_moving_average(historical_data, lookback_periods=5):
    
    """
    Determine the trend using a simple moving average of the close prices over the specified lookback period.

    :param historical_data: List of dictionaries containing open, high, low, close, volume data.
    :param lookback_periods: Number of periods to look back for the moving average.
    :return: String indicating the trend ('uptrend', 'downtrend', or 'sideways/uncertain').
    """
    if len(historical_data) < lookback_periods:
        # Not enough data to determine the trend
        return 'sideways/uncertain'

    # Extract close prices and calculate the moving average
    close_prices = [candle['close'] for candle in historical_data[-lookback_periods:]]
    moving_average = sum(close_prices) / lookback_periods

    # Determine the trend based on the last close price relative to the moving average
    last_close_price = historical_data[-1]['close']
    if last_close_price > moving_average:
        return 'uptrend'
    elif last_close_price < moving_average:
        return 'downtrend'
    else:
        return 'sideways/uncertain'

def determine_trend(symbol, interval, lookback_periods):
    """
    Determine if the trend is up or down based on the last 'n' candlesticks.

    :param symbol: String, the symbol to fetch data for (e.g., 'BTCUSDT').
    :param interval: String, the time interval (e.g., '15m' for 15 minutes).
    :param lookback_periods: Integer, the number of candlesticks to consider for trend analysis.
    :return: String indicating the trend ('up', 'down', or 'uncertain').
    """
    historical_data = fetch_historical_data(symbol, interval, lookback_periods)

    if not historical_data:
        return 'uncertain'

    # Calculate the simple moving average of closing prices
    closing_prices = [candle['close'] for candle in historical_data]
    average_close = sum(closing_prices) / len(closing_prices)

    # Compare the latest closing price to the average
    latest_close = closing_prices[-1]
    trend = 'uncertain'
    if latest_close > average_close:
        trend = 'uptrend'
    elif latest_close < average_close:
        trend = 'downtrend'

    return trend, average_close

def detect_engulfing_patterns(historical_data):
    """
    Detect bullish and bearish engulfing patterns in historical candlestick data.

    :param historical_data: List of dictionaries containing candlestick data, including open, high, low, close prices.
    :return: A list of tuples with the index of engulfing patterns and their type ('bullish' or 'bearish').
    """
    patterns = []

    for i in range(1, len(historical_data)):
        current_candle = historical_data[i]
        previous_candle = historical_data[i-1]

        # Determine the direction of each candle
        current_direction = "up" if current_candle['close'] > current_candle['open'] else "down"
        previous_direction = "up" if previous_candle['close'] > previous_candle['open'] else "down"

        # Criteria for bullish engulfing
        if current_direction == "up" and previous_direction == "down":
            if current_candle['open'] < previous_candle['close'] and current_candle['close'] > previous_candle['open']:
                patterns.append((i, 'bullish'))

        # Criteria for bearish engulfing
        if current_direction == "down" and previous_direction == "up":
            if current_candle['open'] > previous_candle['close'] and current_candle['close'] < previous_candle['open']:
                patterns.append((i, 'bearish'))

    return patterns


def check_for_engulfing_pattern(historical_data):
    """
    Check for bullish or bearish Engulfing patterns in the latest candlesticks.

    :param historical_data: List of dictionaries containing candlestick data, including open, high, low, close prices.
    :return: A string indicating the type of Engulfing pattern ('bullish engulfing', 'bearish engulfing', or 'no pattern').
    """
    if len(historical_data) < 2:
        return "Not enough data for pattern detection"

    # Get the last two candlesticks
    previous_candle = historical_data[-2]
    latest_candle = historical_data[-1]

    # Criteria for bullish Engulfing pattern
    if previous_candle['close'] < previous_candle['open'] and \
       latest_candle['close'] > latest_candle['open'] and \
       latest_candle['close'] > previous_candle['open'] and \
       latest_candle['open'] < previous_candle['close']:
        return "bullish engulfing"

    # Criteria for bearish Engulfing pattern
    elif previous_candle['close'] > previous_candle['open'] and \
         latest_candle['close'] < latest_candle['open'] and \
         latest_candle['close'] < previous_candle['open'] and \
         latest_candle['open'] > previous_candle['close']:
        return "bearish engulfing"

    else:
        return "no engulfing pattern"

def is_dark_cloud_cover(historical_data):
    """
    Check if the latest two candles form a Dark Cloud Cover pattern.

    :param previous_candle: A dictionary with open, high, low, and close prices for the previous candle.
    :param latest_candle: A dictionary with open, high, low, and close prices for the latest candle.
    :return: True if the Dark Cloud Cover pattern is detected, False otherwise.
    """

    # Get the last two candlesticks
    previous_candle = historical_data[-2]
    # print("Previous_candle: ", str(previous_candle))
    latest_candle = historical_data[-1]
    # print("Latest_candle: ", str(latest_candle))

    # Criteria for the Dark Cloud Cover pattern
    if previous_candle['close'] > previous_candle['open'] and \
       latest_candle['open'] > previous_candle['high'] and \
       latest_candle['close'] < latest_candle['open'] and \
       latest_candle['close'] < previous_candle['close'] and \
       latest_candle['close'] > previous_candle['open'] and \
       latest_candle['close'] <= (previous_candle['open'] + (previous_candle['close'] - previous_candle['open']) / 2):
        return "dark_cloud"
    else:
        return "no_dark_cloud"

def detect_candlestick_piercing_on_in_neck_thrusting_pattern(historical_data):
    """
    Detects specific candlestick patterns from the latest two candlesticks.

    :param candles: A list of dictionaries, each containing the 'open', 'high', 'low', 'close' prices.
    :return: The detected candlestick pattern.
    """
    if len(historical_data) < 2:
        return "Insufficient data for pattern detection"

    # Latest two candles
    prev_candle = historical_data[-2]
    latest_candle = historical_data[-1]

    # Calculating necessary values
    prev_body = abs(prev_candle['close'] - prev_candle['open'])
    latest_body = abs(latest_candle['close'] - latest_candle['open'])
    prev_is_bearish = prev_candle['close'] < prev_candle['open']
    latest_is_bullish = latest_candle['close'] > latest_candle['open']

    # Piercing Pattern Detection
    if prev_is_bearish and latest_is_bullish:
        if latest_candle['open'] < prev_candle['low'] and latest_candle['close'] > (prev_candle['open'] + prev_body / 2):
            return "Piercing Pattern detected"

    # On-neck & In-neck Pattern Detection
    if prev_is_bearish and not latest_is_bullish:
        if abs(latest_candle['close'] - prev_candle['low']) <= 0.01 * prev_candle['low']:  # Approximation for "near"
            return "On-neck Pattern detected"
        elif latest_candle['close'] > prev_candle['close'] and latest_candle['close'] < prev_candle['open']:
            return "In-neck Pattern detected"

    # Thrusting Pattern Detection
    if prev_is_bearish and latest_is_bullish:
        if latest_candle['open'] < prev_candle['close'] and latest_candle['close'] > prev_candle['close'] and latest_candle['close'] < (prev_candle['open'] + prev_body / 2):
            return "Thrusting Pattern detected"

    return "No specific piercing_on_in_neck_thrusting pattern detected"

def detect_stars_patterns(historical_data):

    if len(historical_data) < 3:
        return "Insufficient data for pattern detection."

    # Latest three candles
    first_candle = historical_data[-3]
    second_candle = historical_data[-2]
    third_candle = historical_data[-1]

    # Common calculations
    first_body = abs(first_candle['close'] - first_candle['open'])
    second_body = abs(second_candle['close'] - second_candle['open'])
    third_body = abs(third_candle['close'] - third_candle['open'])
    
    first_is_bullish = first_candle['close'] > first_candle['open']
    third_is_bullish = third_candle['close'] > third_candle['open']
    
    second_is_doji = second_body <= ((second_candle['high'] - second_candle['low']) * 0.1)

    # Checking for Morning Star and Doji Morning Star
    if not first_is_bullish and third_is_bullish:
        if (second_candle['high'] < first_candle['low'] and third_candle['open'] > second_candle['close'] and
                third_candle['close'] > (first_candle['open'] + (first_body / 2))):
            if second_is_doji:
                return "Doji Morning Star"
            else:
                return "Morning Star"

    # Checking for Evening Star and Doji Evening Star
    if first_is_bullish and not third_is_bullish:
        if (second_candle['high'] > first_candle['high'] and third_candle['open'] < second_candle['close'] and
                third_candle['close'] < (first_candle['close'] - (first_body / 2))):
            if second_is_doji:
                return "Doji Evening Star"
            else:
                return "Evening Star"
    
    # Checking for Shooting Star
    if third_body / (third_candle['high'] - third_candle['low']) <= 0.2:
        # Small body
        upper_shadow = third_candle['high'] - max(third_candle['open'], third_candle['close'])
        lower_shadow = min(third_candle['open'], third_candle['close']) - third_candle['low']
        body_top = max(third_candle['open'], third_candle['close'])
        
        if first_is_bullish and upper_shadow > (2 * third_body) and lower_shadow < third_body:
            return "Shooting Star"

    return "No recognized STARS pattern found."

# historical_data = fetch_historical_data("TRUUSDT", "15m", 100)
# print(historical_data)
# engulfing_pattern = check_for_engulfing_pattern(historical_data)
# print(f"The latest engulfing pattern detected is {engulfing_pattern}.")

# dark_cloud = is_dark_cloud_cover(historical_data)
# print(f"Check dark cloud: {dark_cloud}")

# check_piercing_pattern = detect_candlestick_piercing_on_in_neck_thrusting_pattern(historical_data)
# print(f"check piercing or on_in_neck or thrusting {check_piercing_pattern}")

# check_stars_pattern = detect_stars_patterns(historical_data)
# print(f"stars pattern: {check_stars_pattern}")


# candle_1 = fetch_historical_data("BTCUSDT", "15m", 1)[0]
# candle_2 = fetch_historical_data("BTCUSDT", "15m", 100)[-1]

# print("candle_1: ", candle_1)
# print("candle_2: ", candle_2)

# context, average_close = determine_trend("BTCUSDT", "15m", 100)
# print("trend is: ", context)
# print("average_close is: ", average_close)

# print(is_hammer_or_hangingman(candle_1, context))

# print(is_hammer_or_hangingman(candle_2, context))