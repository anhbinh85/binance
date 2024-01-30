def trading_decision_based_on_conditions(data):
    '''
    Trading strategy prioritizing Uptrend and Downtrend Signals. 
    Additional indicators: RSI, MACD, and Bollinger Bands are used for further refinement.
    1 indicates a buy or enter position (long).
    0 indicates a hold or no action.
    -1 indicates a sell or exit position (short).
    '''
    symbol = data['Symbol']
    rsi = data['RSI']
    macd = data['MACD_Current']
    macd_signal = data['MACDSignal_Current']
    bb_signal = data['Bollinger_Signal']
    uptrend_signals = data['Uptrend_Signals']
    downtrend_signals = data['Downtrend_Signals']

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
        # Secondary priority: RSI and Bollinger Band-based decision
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
