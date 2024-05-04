import numpy as np
import talib

class Candle_Stick_Combine_Trend_Line:

    def __init__(self, historical_data):
        self.opens = np.array([data['open'] for data in historical_data])
        self.highs = np.array([data['high'] for data in historical_data])
        self.lows = np.array([data['low'] for data in historical_data])
        self.closes = np.array([data['close'] for data in historical_data])

    def detect_trend(self):
        """
        Simplistic trend detection for the last 6 candlesticks.
        """
        if len(self.closes) < 6:
            return "Insufficient data for trend analysis"
        
        # Use simple linear regression slope as a trend indicator
        x = np.arange(6)
        y = self.closes[-6:]
        slope = np.polyfit(x, y, 1)[0]
        return "upward" if slope > 0 else "downward" if slope < 0 else "flat"

    def detect_springs_and_upthrusts(self):
        """
        Detect Springs and Upthrusts within the last few candles based on simplified support and resistance identification.
        """
        if len(self.closes) < 2:
            return {}

        # Simplified Support/Resistance Detection for illustration
        recent_low = min(self.lows[-6:])
        recent_high = max(self.highs[-6:])

        last_close = self.closes[-1]
        second_last_close = self.closes[-2]

        results = {}
        # Spring: Close below recent low but close back above it
        if second_last_close < recent_low < last_close:
            results['Spring'] = "Bullish signal: Price dipped below support but closed above, indicating a potential upward reversal."

        # Upthrust: Close above recent high but close back below it
        if second_last_close > recent_high > last_close:
            results['Upthrust'] = "Bearish signal: Price broke above resistance but closed below, indicating a potential downward reversal."

        return results

    def detect_candlestick_patterns(self):
        """
        Detects various candlestick patterns and considers trend context for the last 6 candles.
        """
        trend = self.detect_trend()
        patterns = self.base_pattern_detection()
        patterns.update(self.detect_springs_and_upthrusts())  # Include springs and upthrusts

        return patterns

    def base_pattern_detection(self):

        """
        Base patterns detection using TA-Lib.
        """
        functions = {
            'Hammer': talib.CDLHAMMER,
            'Hanging Man': talib.CDLHANGINGMAN,
            'Shooting Star': talib.CDLSHOOTINGSTAR,
            'Engulfing': talib.CDLENGULFING,
            'Dark Cloud Cover': talib.CDLDARKCLOUDCOVER,
            'Piercing': talib.CDLPIERCING,
            'In Neck': talib.CDLINNECK,
            'On Neck': talib.CDLONNECK,
            'Thrusting': talib.CDLTHRUSTING,
            'Morning Stars': talib.CDLMORNINGSTAR,
            'Morning Doji Stars': talib.CDLMORNINGDOJISTAR,
            'Evening Stars': talib.CDLEVENINGSTAR,
            'Evening Doji Stars': talib.CDLEVENINGDOJISTAR,
            'Harami': talib.CDLHARAMI,
            'Harami Cross': talib.CDLHARAMICROSS,
            'Belt Hold': talib.CDLBELTHOLD,
            'Upside Gap Two Crows': talib.CDLUPSIDEGAP2CROWS,
            'Three Black Crows': talib.CDL3BLACKCROWS,
            'Three Advancing White Soldiers': talib.CDL3WHITESOLDIERS,
            'Counterattack': talib.CDLCOUNTERATTACK,
            'Tasuki Gap': talib.CDLTASUKIGAP,
            'Gapping Side-by-Side White Lines': talib.CDLGAPSIDESIDEWHITE,
            'Rising Three Methods': talib.CDLRISEFALL3METHODS,
            'Falling Three Methods': talib.CDLRISEFALL3METHODS,
            'Separating Lines': talib.CDLSEPARATINGLINES,
            'Dragonfly Doji': talib.CDLDRAGONFLYDOJI,
            'Gravestone Doji': talib.CDLGRAVESTONEDOJI,
            'Long Legged Doji': talib.CDLLONGLEGGEDDOJI
        }

        results = {"Trend":self.detect_trend()}
        for name, function in functions.items():
            result = function(self.opens, self.highs, self.lows, self.closes)
            if result[-1] != 0:
                results[name] = "Detected" if result[-1] > 0 else "Detected (Bearish)"
            else:
                results[name] = "Not Detected"

        return results

    def execute(self):
        try:
            pattern_results = self.detect_candlestick_patterns()
            # print(pattern_results)
            return pattern_results
        except Exception as e:
            print("Error processing candlestick data:", str(e))
            return None
