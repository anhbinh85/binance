# def calculate_obv(historical_data):
#     """
#     Calculate On-Balance Volume (OBV) from historical candlestick data and add it directly to each entry.

#     :param historical_data: List of dictionaries containing candlestick data.
#     :return: The input list with OBV values added as an additional key for each candlestick.
#     """
#     obv = [0]  # Initialize OBV with the first value set to zero
#     historical_data[0]['OBV'] = obv[0]  # Set the first OBV value

#     for i in range(1, len(historical_data)):
#         current_close = historical_data[i]['close']
#         previous_close = historical_data[i - 1]['close']
#         current_volume = historical_data[i]['volume']

#         if current_close > previous_close:
#             obv.append(obv[-1] + current_volume)
#         elif current_close < previous_close:
#             obv.append(obv[-1] - current_volume)
#         else:
#             obv.append(obv[-1])

#         # Add the calculated OBV value directly into the dictionary
#         historical_data[i]['OBV'] = obv[i]

#     return historical_data

def calculate_obv(historical_data):
    """
    Calculate On-Balance Volume (OBV) from historical candlestick data.

    Args:
        historical_data (list): List of dictionaries containing candlestick data.

    Returns:
        list: A list of OBV values corresponding to each candlestick.
    """
    obv = 0  # Initialize OBV
    obv_values = []  # List to store OBV values

    for i in range(len(historical_data)):
        current_close = historical_data[i]['close']
        previous_close = historical_data[i - 1]['close'] if i > 0 else current_close  # Handle the first candle
        current_volume = historical_data[i]['volume']

        if current_close > previous_close:
            obv += current_volume
        elif current_close < previous_close:
            obv -= current_volume

        obv_values.append(obv)

    return obv_values  # Return the list of OBV values