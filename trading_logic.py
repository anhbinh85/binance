def trading_decision_based_on_conditions(data):
    '''
    Aggressive trading strategy based on RSI and MACD signals.
    1 indicates a buy or enter position (long).
    0 indicates a hold or no action.
    -1 indicates a sell or exit position (short).
    '''
    symbol = data['Symbol']
    rsi = data['RSI']
    macd = data['MACD_Current']
    macd_signal = data['MACDSignal_Current']

    # Initial decision setup
    decision = {
        "Symbol": symbol,
        "Spot Trading": 0,
        "Long Position": 0,
        "Short Position": 0
    }

    # More aggressive RSI-based decision
    if rsi > 60:  # Lowering threshold for overbought condition
        decision["Spot Trading"] = -1
        decision["Short Position"] = 1

    elif rsi < 40:  # Lowering threshold for oversold condition
        decision["Spot Trading"] = 1
        decision["Long Position"] = 1

    # Aggressive MACD-based refinement
    if macd < macd_signal and rsi > 50:  # Bearish MACD, not oversold
        decision["Short Position"] = 1

    elif macd > macd_signal and rsi < 50:  # Bullish MACD, not overbought
        decision["Long Position"] = 1

    return decision
