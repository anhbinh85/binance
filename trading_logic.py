def trading_decision_based_on_conditions(price_movement, order_book_trend):
    '''
    Trading strategy prioritizing Uptrend and Downtrend Signals, with a secondary priority on Order Book Trend.
    Additional indicators: RSI, MACD, and Bollinger Bands are used for further refinement.
    1 indicates a buy or enter position (long).
    0 indicates a hold or no action.
    -1 indicates a sell or exit position (short).
    '''
    symbol = price_movement['Symbol']
    rsi = price_movement['RSI']
    macd = price_movement['MACD_Current']
    macd_signal = price_movement['MACDSignal_Current']
    bb_signal = price_movement['Bollinger_Signal']
    uptrend_signals = price_movement['Uptrend_Signals']
    downtrend_signals = price_movement['Downtrend_Signals']

    # Initial decision setup
    decision = {
        "Symbol": symbol,
        "Spot Trading": 0,
        "Long Position": 0,
        "Short Position": 0
    }

    # First priority: Uptrend vs Downtrend Signals
    if uptrend_signals > downtrend_signals:
        decision["Spot Trading"] = 1
        decision["Long Position"] = 1
    elif downtrend_signals > uptrend_signals:
        decision["Spot Trading"] = -1
        decision["Short Position"] = 1
    else:
        # Second priority: Order Book Trend
        if order_book_trend == "Uptrend Expected":
            decision["Spot Trading"] = 1
            decision["Long Position"] = 1
        elif order_book_trend == "Downtrend Expected":
            decision["Spot Trading"] = -1
            decision["Short Position"] = 1
        elif order_book_trend == "Uncertain Market" or order_book_trend == "No clear trend":
            # No action for uncertain market or no clear trend
            decision["Spot Trading"] = 0
        else:
            # If still undecided, use additional indicators as a fallback
            if rsi > 60 or bb_signal == -1:  # Overbought condition
                decision["Spot Trading"] = -1
                decision["Short Position"] = 1
            elif rsi < 40 or bb_signal == 1:  # Oversold condition
                decision["Spot Trading"] = 1
                decision["Long Position"] = 1

            # Tertiary priority: MACD-based refinement
            if macd < macd_signal and rsi > 50:  # Bearish MACD, not oversold
                decision["Short Position"] = 1
            elif macd > macd_signal and rsi < 50:  # Bullish MACD, not overbought
                decision["Long Position"] = 1

    return decision

def generate_trading_decision(result):
    """
    Generates a trading decision based on the analysis results 
    and the Matrix for Trading Decisions.

    Args:
        result (dict): A dictionary containing the analysis results
                       for a single symbol, including candlestick 
                       analysis, technical indicators, etc.

    Returns:
        str: The trading decision ('Strong Long', 'Long', 
             'Weak Long', 'Hold (Potential Long)', 
             'Strong Short', 'Short', 'Weak Short', 
             'Hold (Potential Short)', 'Neutral/Hold', 
             'Hold/Careful Consideration').
    """
    ta_lib_data = result["ta_lib_data"]
    technical_analysis = result["technical_analysis"]
    orderbook = result["orderbook"]

    # Candlestick Pattern
    candlestick_pattern = None
    for pattern in [
            "Engulfing", "Harami", "Belt Hold", "Dark Cloud Cover",
            "Piercing", "Morning Stars", "Evening Stars", "Hammer",
            "Hanging Man", "Shooting Star", "Three Black Crows",
            "Three Advancing White Soldiers"
    ]:
        pattern_result = ta_lib_data.get(pattern)
        if pattern_result == "Detected":
            candlestick_pattern = pattern
            break
        elif pattern_result == "Detected (Bearish)":
            candlestick_pattern = pattern  # Or handle it differently based on your strategy
            break

    # Trend
    trend = ta_lib_data["Trend"]

    # MACD
    macd_cross_above = technical_analysis["MACD_Line_cross_above_Signal"][
        "cross_above"]
    histogram_positive = technical_analysis["Histogram_turns_positive"]
    macd_condition = macd_cross_above and histogram_positive

    # RSI
    rsi_value = technical_analysis["RSI14"]
    rsi_condition = rsi_value > 50

    # EMA
    ema_cross_above_50 = technical_analysis["Price_cross_above_EMA50"][
        "cross_above"]
    ema_cross_above_20 = technical_analysis["Price_cross_above_EMA20"][
        "cross_above"]

    # Stochastic Oscillator
    stochastic_cross_above = technical_analysis[
        "PercentK_cross_above_PercentD"]["cross_above"]
    stochastic_cross_below = technical_analysis[
        "PercentK_cross_below_PercentD"]["cross_below"]

    # OBV 
    obv_increasing = analyze_obv(result)

    # Trading Decision Logic based on the Matrix
    if candlestick_pattern in [
            "Engulfing", "Harami", "Piercing Pattern", "Morning Star",
            "Hammer", "Three White Soldiers"
    ] and trend == "upward":
        if macd_condition and rsi_condition and ema_cross_above_50 and stochastic_cross_above and obv_increasing:
            return "Strong Long"
        elif (candlestick_pattern in ["Engulfing", "Harami", "Hammer"]
              and rsi_condition and obv_increasing):
            return "Long"
        else:
            return "Hold (Potential Long)"

    elif candlestick_pattern in [
            "Engulfing", "Harami", "Dark Cloud Cover", "Evening Star",
            "Hanging Man", "Three Black Crows"
    ] and trend == "downward":
        if macd_condition and not rsi_condition and not ema_cross_above_50 and stochastic_cross_below and not obv_increasing:
            return "Strong Short"
        elif (candlestick_pattern
              in ["Engulfing", "Harami", "Hanging Man", "Shooting Star"]
              and not rsi_condition and not obv_increasing):
            return "Short"
        else:
            return "Hold (Potential Short)"

    elif candlestick_pattern == "Belt Hold":
        if trend == "downward" and histogram_positive:
            return "Long"
        elif trend == "upward" and not histogram_positive:
            return "Short"
        else:
            return "Hold/Careful Consideration"

    # elif candlestick_pattern == "Upside Gap Two Crows":
    #     # You'll need to define 'high_volume' based on your strategy
    #     if trend == "upward" and high_volume:
    #         return "Short"
    #     else:
    #         return "Hold/Careful Consideration"

    elif candlestick_pattern == "Three Black Crows":
        if trend == "upward" and not ema_cross_above_20:
            return "Short"
        else:
            return "Hold/Careful Consideration"

    elif candlestick_pattern == "Three Advancing White Soldiers":
        if trend == "downward" and ema_cross_above_20:
            return "Long"
        else:
            return "Hold/Careful Consideration"

    elif candlestick_pattern in ["Doji", "Spinning Top"]:
        return "Neutral/Hold"

    else:
        return "Hold/Careful Consideration"  # Default to Hold if no specific condition is met


def analyze_obv(result):
    """
    Analyzes OBV data.

    Args:
        result (dict): The analysis result dictionary for a symbol.

    Returns:
        bool: True if OBV is increasing, False otherwise.
    """
    # Assuming your result dictionary now has an 'obv_values' key
    obv_values = result['obv_values']  

    # Implement your OBV analysis logic here
    # For example, you might check if the last few OBV values are increasing
    if len(obv_values) >= 3 and obv_values[-1] > obv_values[-2] > obv_values[-3]:
        return True
    else:
        return False
