import numpy as np
import talib

class TechnicalIndicators:

    def __init__(self, historical_data):
        self.opens = np.array([data['open'] for data in historical_data])
        self.highs = np.array([data['high'] for data in historical_data])
        self.lows = np.array([data['low'] for data in historical_data])
        self.closes = np.array([data['close'] for data in historical_data])

    def calculate_rsi(self):
        # Calculate multiple RSI values
        rsi6 = talib.RSI(self.closes, timeperiod=6)
        rsi12 = talib.RSI(self.closes, timeperiod=12)
        rsi14 = talib.RSI(self.closes, timeperiod=14)
        rsi24 = talib.RSI(self.closes, timeperiod=24)
        return rsi6, rsi12, rsi14, rsi24

    def calculate_macd(self):
        # Calculate MACD values
        macd, signal, hist = talib.MACD(self.closes, fastperiod=12, slowperiod=26, signalperiod=9)
        return macd, signal, hist

    def calculate_emas(self):
        # Calculate Exponential Moving Averages
        ema12 = talib.EMA(self.closes, timeperiod=12)
        ema20 = talib.EMA(self.closes, timeperiod=20)
        ema50 = talib.EMA(self.closes, timeperiod=50)
        return ema12, ema20, ema50

    def calculate_stochastic_oscillator(self):
        # Calculate Stochastic Oscillator values
        k, d = talib.STOCH(self.highs, self.lows, self.closes, fastk_period=14, slowk_period=3, slowd_period=3)
        return k, d

    def indicator_checks(self):
        # Calculate all indicators and check specific conditions
        rsi6, rsi12, rsi14, rsi24 = self.calculate_rsi()
        macd, signal, hist = self.calculate_macd()
        ema12, ema20, ema50 = self.calculate_emas()
        k, d = self.calculate_stochastic_oscillator()

        results = {
            'MACD_Line_cross_above_Signal': self.check_cross_above(macd, signal),
            'Price_cross_above_EMA12': self.check_cross_above(self.closes, ema12),
            'Price_cross_above_EMA20': self.check_cross_above(self.closes, ema20),
            'Price_cross_above_EMA50': self.check_cross_above(self.closes, ema50),
            'PercentK_cross_below_PercentD': self.check_cross_below(k, d),
            'PercentK_cross_above_PercentD': self.check_cross_above(k, d),
            'Histogram_turns_positive': hist[-1] > 0,
            'RSI6': rsi6[-1],
            'RSI12': rsi12[-1],
            'RSI14': rsi14[-1],
            'RSI24': rsi24[-1]
        }

        return results

    def check_cross_above(self, data1, data2):
        # Check for cross above condition
        cross_above = (data1[-2] < data2[-2]) and (data1[-1] > data2[-1])
        return {'cross_above':cross_above}

    def check_cross_below(self, data1, data2):
        # Check for cross below condition
        cross_below = (data1[-2] > data2[-2]) and (data1[-1] < data2[-1])
        return {'cross_below': cross_below}

    def execute(self):
        # Execute analysis and print results
        try:
            pattern_results = self.indicator_checks()
            # print(pattern_results)
            return pattern_results
        except Exception as e:
            print("Error processing candlestick data:", str(e))
            return None


