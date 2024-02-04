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
