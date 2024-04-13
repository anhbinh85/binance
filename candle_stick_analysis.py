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

def detect_harami_and_cross(historical_data):
    if len(historical_data) < 2:
        return "Insufficient data for pattern detection."

    # Get the last two candles
    prev_candle = historical_data[-2]
    last_candle = historical_data[-1]

    prev_body = abs(prev_candle['close'] - prev_candle['open'])
    last_body = abs(last_candle['close'] - last_candle['open'])

    # Determine the direction of the candles
    prev_bullish = prev_candle['close'] > prev_candle['open']
    last_bullish = last_candle['close'] > last_candle['open']

    # Check for Harami pattern
    # Last candle's body is fully within the previous candle's body, but direction is opposite
    if (last_candle['open'] > prev_candle['open'] and last_candle['close'] < prev_candle['close']) or \
       (last_candle['open'] < prev_candle['open'] and last_candle['close'] > prev_candle['close']):
        if prev_bullish != last_bullish:
            # Bullish Harami: previous candle is bearish, last is bullish
            if not prev_bullish and last_bullish:
                return "Bullish Harami"
            # Bearish Harami: previous candle is bullish, last is bearish
            else:
                return "Bearish Harami"

    # Check for Harami Cross pattern
    # Last candle is a Doji and is within the body of the previous candle
    if (last_body / (last_candle['high'] - last_candle['low']) <= 0.1) and \
       (last_candle['high'] < prev_candle['high'] and last_candle['low'] > prev_candle['low']):
        if prev_bullish:
            return "Bearish Harami Cross"
        else:
            return "Bullish Harami Cross"

    return "No recognizable pattern"

def check_tweezers_top(historical_data):
    """Checks if the latest two candles form a Tweezers Top pattern."""
    if len(historical_data) < 2:
        return "Insufficient data for pattern detection."

    # Get the last two candlesticks
    prev_candle = historical_data[-2]
    last_candle = historical_data[-1]

    # Criteria for Tweezers Top: both candles reach the same high price point
    if (prev_candle['high'] == last_candle['high'] and
            prev_candle['close'] > prev_candle['open'] and
            last_candle['close'] < last_candle['open']):
        return "Tweezers Top detected"
    return "No Tweezers Top detected"

def check_tweezers_bottom(historical_data):
    """Checks if the latest two candles form a Tweezers Bottom pattern."""
    if len(historical_data) < 2:
        return "Insufficient data for pattern detection."

    # Get the last two candlesticks
    prev_candle = historical_data[-2]
    last_candle = historical_data[-1]

    # Criteria for Tweezers Bottom: both candles reach the same low price point
    if (prev_candle['low'] == last_candle['low'] and
            prev_candle['close'] < prev_candle['open'] and
            last_candle['close'] > last_candle['open']):
        return "Tweezers Bottom detected"
    return "No Tweezers Bottom detected"

def check_belt_hold(historical_data):
    """Checks for a Belt-hold (bullish or bearish) pattern in the latest candle."""
    if len(historical_data) < 1:
        return "Insufficient data for pattern detection."

    # Get the latest candle
    last_candle = historical_data[-1]

    # Criteria for Belt-hold
    body_length = abs(last_candle['close'] - last_candle['open'])
    total_length = last_candle['high'] - last_candle['low']

    # A large body, small shadows
    if body_length / total_length > 0.8:
        if last_candle['close'] > last_candle['open']:
            return "Bullish Belt-hold detected"
        elif last_candle['close'] < last_candle['open']:
            return "Bearish Belt-hold detected"
    return "No Belt-hold detected"

def check_upside_gap_two_crows(historical_data):
    """Checks for an Upside-Gap Two Crows pattern in the latest three candles."""
    if len(historical_data) < 3:
        return "Insufficient data for pattern detection."

    first_candle = historical_data[-3]
    second_candle = historical_data[-2]
    last_candle = historical_data[-1]

    # Criteria for Upside-Gap Two Crows
    if (first_candle['close'] > first_candle['open'] and  # First candle is bullish
        second_candle['open'] > first_candle['close'] and  # Gap up
        second_candle['close'] < second_candle['open'] and  # Second candle is bearish
        last_candle['open'] > first_candle['close'] and
        last_candle['close'] < second_candle['open'] and  # Fills the gap
        last_candle['close'] > first_candle['open']):
        return "Upside-Gap Two Crows detected"
    return "No Upside-Gap Two Crows detected"

def check_three_black_crows(historical_data):
    """Checks for a Three Black Crows pattern."""
    if len(historical_data) < 3:
        return "Insufficient data for pattern detection."

    three_crows = historical_data[-3:]

    # All three candles are bearish and each closes progressively lower
    if all(candle['close'] < candle['open'] for candle in three_crows) and \
       all(three_crows[i]['close'] < three_crows[i-1]['close'] for i in range(1, 3)):
        return "Three Black Crows detected"
    return "No Three Black Crows detected"

def check_three_advancing_white_soldiers(historical_data):
    """Checks for a Three Advancing White Soldiers pattern."""
    if len(historical_data) < 3:
        return "Insufficient data for pattern detection."

    three_soldiers = historical_data[-3:]

    # All three candles are bullish and each closes progressively higher
    if all(candle['close'] > candle['open'] for candle in three_soldiers) and \
       all(three_soldiers[i]['close'] > three_soldiers[i-1]['close'] for i in range(1, 3)):
        return "Three Advancing White Soldiers detected"
    return "No Three Advancing White Soldiers detected"

def check_buddha_top_bottom(historical_data, top=True):
    """Checks for a Three Buddha Top or Bottom pattern based on whether 'top' is True or False."""
    if len(historical_data) < 3:
        return "Insufficient data for pattern detection."

    # Assuming an arbitrary size and formation for demonstration purposes
    if top:
        # A top is a high peak surrounded by lower highs
        if all(historical_data[i]['high'] < historical_data[i+1]['high'] for i in [-3, -2]) and \
           all(historical_data[i]['high'] > historical_data[i+1]['high'] for i in [-1, 0]):
            return "Three Buddha Top detected"
    else:
        # A bottom is a low trough surrounded by higher lows
        if all(historical_data[i]['low'] > historical_data[i+1]['low'] for i in [-3, -2]) and \
           all(historical_data[i]['low'] < historical_data[i+1]['low'] for i in [-1, 0]):
            return "Three Buddha Bottom detected"
    return "No Buddha Top/Bottom detected"

def check_counterattack_lines(historical_data):
    """Checks for Bullish or Bearish Counterattack line patterns."""
    if len(historical_data) < 2:
        return "Insufficient data for pattern detection."

    prev_candle = historical_data[-2]
    last_candle = historical_data[-1]

    # Bullish Counterattack line
    if prev_candle['close'] < prev_candle['open'] and last_candle['close'] > last_candle['open'] and \
       abs(prev_candle['close'] - last_candle['close']) < 0.01 * last_candle['close']:
        return "Bullish Counterattack line detected"
    # Bearish Counterattack line
    elif prev_candle['close'] > prev_candle['open'] and last_candle['close'] < last_candle['open'] and \
         abs(prev_candle['close'] - last_candle['close']) < 0.01 * last_candle['close']:
        return "Bearish Counterattack line detected"

    return "No Counterattack lines detected"

def check_dumpling_top(historical_data):
    """Checks for a Dumpling Top pattern, characterized by a rounding top formation."""
    if len(historical_data) < 5:
        return "Insufficient data for pattern detection."

    # Looking for a gradual decline after a peak, indicating a rounded top like a dumpling
    peak = max(historical_data, key=lambda x: x['high'])
    peak_index = historical_data.index(peak)

    # Ensure peak is not at the edges
    if 1 < peak_index < len(historical_data) - 3:
        post_peak_candles = historical_data[peak_index + 1:peak_index + 4]
        if all(post_peak_candles[i]['high'] < post_peak_candles[i - 1]['high'] for i in range(1, 3)):
            return "Dumpling Top detected"
    return "No Dumpling Top detected"

def check_frypan_bottom(historical_data):
    """Checks for a Frypan Bottom pattern, characterized by a gradual rounding bottom formation."""
    if len(historical_data) < 5:
        return "Insufficient data for pattern detection."

    # Looking for a gradual increase after a trough, indicating a rounded bottom like a frypan
    trough = min(historical_data, key=lambda x: x['low'])
    trough_index = historical_data.index(trough)

    # Ensure trough is not at the edges
    if 1 < trough_index < len(historical_data) - 3:
        post_trough_candles = historical_data[trough_index + 1:trough_index + 4]
        if all(post_trough_candles[i]['low'] > post_trough_candles[i - 1]['low'] for i in range(1, 3)):
            return "Frypan Bottom detected"
    return "No Frypan Bottom detected"

def check_tower_top(historical_data):
    """Checks for a Tower Top pattern, characterized by a sharp rise followed by a sharp decline."""
    if len(historical_data) < 5:
        return "Insufficient data for pattern detection."

    middle_index = len(historical_data) // 2
    rising_phase = historical_data[:middle_index]
    falling_phase = historical_data[middle_index:]

    if all(rising_phase[i]['close'] > rising_phase[i - 1]['close'] for i in range(1, len(rising_phase))) and \
       all(falling_phase[i]['close'] < falling_phase[i - 1]['close'] for i in range(1, len(falling_phase))):
        return "Tower Top detected"
    return "No Tower Top detected"

def check_tower_bottom(historical_data):
    """Checks for a Tower Bottom pattern, characterized by a sharp decline followed by a sharp rise."""
    if len(historical_data) < 5:
        return "Insufficient data for pattern detection."

    middle_index = len(historical_data) // 2
    falling_phase = historical_data[:middle_index]
    rising_phase = historical_data[middle_index:]

    if all(falling_phase[i]['close'] < falling_phase[i - 1]['close'] for i in range(1, len(falling_phase))) and \
       all(rising_phase[i]['close'] > rising_phase[i - 1]['close'] for i in range(1, len(rising_phase))):
        return "Tower Bottom detected"
    return "No Tower Bottom detected"

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