import talib
import numpy as np
from candle_stick_analysis import fetch_historical_data


# historical_data = fetch_historical_data("REIUSDT", "15m", 94)

# # Extracting OHLC data
# opens = np.array([item['open'] for item in historical_data])
# highs = np.array([item['high'] for item in historical_data])
# lows = np.array([item['low'] for item in historical_data])
# closes = np.array([item['close'] for item in historical_data])

class TA_Candle_Stick_Recognition:

    def __init__(self, historical_data):
        self.historical_data = historical_data
        self.opens = np.array([item['open'] for item in self.historical_data])
        self.highs = np.array([item['high'] for item in self.historical_data])
        self.lows = np.array([item['low'] for item in self.historical_data])
        self.closes = np.array([item['close'] for item in self.historical_data])

    def check_latest_candle_stick(self, pattern_name, pattern_values):
        if pattern_values[-1] != 0:
            print(f"{pattern_name}: YES, value: {pattern_values[-1]}")
        else:
            print(f"{pattern_name}: NO, value: {pattern_values[-1]}")

    def detect_patterns(self):
        # Each method returns an array with the pattern detection result for each candle
        patterns = {
            'Hammer': talib.CDLHAMMER(self.opens, self.highs, self.lows, self.closes),
            'Hanging Man': talib.CDLHANGINGMAN(self.opens, self.highs, self.lows, self.closes),
            'Shooting Star': talib.CDLSHOOTINGSTAR(self.opens, self.highs, self.lows, self.closes),
            'Engulfing': talib.CDLENGULFING(self.opens, self.highs, self.lows, self.closes),
            'Dark Cloud Cover': talib.CDLDARKCLOUDCOVER(self.opens, self.highs, self.lows, self.closes, penetration=0),
            'Piercing': talib.CDLPIERCING(self.opens, self.highs, self.lows, self.closes),
            'In-Neck': talib.CDLINNECK(self.opens, self.highs, self.lows, self.closes),
            'On-Neck': talib.CDLONNECK(self.opens, self.highs, self.lows, self.closes),
            'Thrusting': talib.CDLTHRUSTING(self.opens, self.highs, self.lows, self.closes),
            'Morning Stars': talib.CDLMORNINGSTAR(self.opens, self.highs, self.lows, self.closes),
            'Morning Doji Stars': talib.CDLMORNINGDOJISTAR(self.opens, self.highs, self.lows, self.closes),
            'Evening Stars': talib.CDLEVENINGSTAR(self.opens, self.highs, self.lows, self.closes),
            'Evening Doji Stars': talib.CDLEVENINGDOJISTAR(self.opens, self.highs, self.lows, self.closes),
            'Harami': talib.CDLHARAMI(self.opens, self.highs, self.lows, self.closes),
            'Harami-cross': talib.CDLHARAMICROSS(self.opens, self.highs, self.lows, self.closes)
        }

        # Check each pattern in the latest candle and print result
        for name, pattern in patterns.items():
            self.check_latest_candle_stick(name, pattern)

# historical_data = fetch_historical_data("REIUSDT", "15m", 100)

# Extracting OHLC data
# opens = np.array([item['open'] for item in historical_data])
# highs = np.array([item['high'] for item in historical_data])
# lows = np.array([item['low'] for item in historical_data])
# closes = np.array([item['close'] for item in historical_data])
# candle_stick_recognition = TA_Candle_Stick_Recognition(historical_data)
# candle_stick_recognition.detect_patterns()


# # Detecting Hammer
# hammer = talib.CDLHAMMER(opens, highs, lows, closes)
# print(hammer)

# # Detecting Hanging Man
# hanging_man = talib.CDLHANGINGMAN(opens, highs, lows, closes)
# print(hanging_man)

# Detecting Shooting Star
# shooting_star = talib.CDLSHOOTINGSTAR(opens, highs, lows, closes)
# print(shooting_star)

# # Detecting Bullish Engulfing Pattern
# engulfing = talib.CDLENGULFING(opens, highs, lows, closes)
# print(engulfing)

# # Detecting Dark Cloud Cover
# dark_cloud_cover = talib.CDLDARKCLOUDCOVER(opens, highs, lows, closes, penetration=0)
# print(dark_cloud_cover)

# # Detecting Piercing Pattern
# Piercing = talib.CDLPIERCING(opens, highs, lows, closes)
# print(Piercing)

# # Detecting in_neck Pattern
# in_neck = talib.CDLINNECK(opens, highs, lows, closes)
# print(in_neck)

# # Detecting on_neck Pattern
# on_neck = talib.CDLONNECK(opens, highs, lows, closes)
# print(on_neck)

# # Detecting thrusting Pattern
# thrusting = talib.CDLTHRUSTING(opens, highs, lows, closes)
# print(thrusting)

# # Detecting Morning Stars
# morning_stars = talib.CDLMORNINGSTAR(opens, highs, lows, closes)
# print(morning_stars)

# # Detecting Morning Doji Stars
# morning_doji_stars = talib.CDLMORNINGDOJISTAR(opens, highs, lows, closes)
# print(morning_doji_stars)

# # Detecting Evening Stars
# evening_stars = talib.CDLEVENINGSTAR(opens, highs, lows, closes)
# print(evening_stars)

# # Detecting Eveing Doji Stars
# evening_doji_stars = talib.CDLEVENINGDOJISTAR(opens, highs, lows, closes)
# print(evening_doji_stars)

# # Example of iterating over the results to find patterns
# print("Hammer Signals:")
# for i, value in enumerate(hammer):
#     if value != 0:
#         print(f"Hammer pattern detected at index {i}, value: {value}")

# print("HangingMan Signals:")
# for i, value in enumerate(hanging_man):
#     if value != 0:
#         print(f"Hanging Man pattern detected at index {i}, value: {value}")

# print("\nShooting Star Signals:")
# for i, value in enumerate(shooting_star):
#     if value != 0:
#         print(f"Shooting Star pattern detected at index {i}, value: {value}")

# print("\nEngulfing Signals:")
# for i, value in enumerate(engulfing):
#     if value != 0:
#         print(f"Engulfing pattern detected at index {i}, value: {value}")

# print("\nDark Cloud Signals:")
# for i, value in enumerate(dark_cloud_cover):
#     if value != 0:
#         print(f"dark_cloud_cover pattern detected at index {i}, value: {dark_cloud_cover}")

# print("\nPiercing Signals:")
# for i, value in enumerate(Piercing):
#     if value != 0:
#         print(f"Piercing pattern detected at index {i}, value: {value}")

# # Assuming `hammer` is the array returned by talib.CDLHAMMER(opens, highs, lows, closes)
# if hammer[-1] != 0:
#     print("Hammer pattern detected in the latest candle.")
# else:
#     print("No Hammer pattern detected in the latest candle.")