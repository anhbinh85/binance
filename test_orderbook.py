import requests

def get_order_book(symbol, limit=100):
    """
    Get the order book depth for a specific symbol (pair) from Binance.
    """
    url = "https://api.binance.com/api/v3/depth"
    params = {'symbol': symbol, 'limit': limit}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching order book:", response.status_code)
        return None

def calculate_supply_demand(order_book):
    """
    Calculate total supply and demand from the order book.
    """
    total_demand = sum([float(ask[1]) for ask in order_book['asks']])
    total_supply = sum([float(bid[1]) for bid in order_book['bids']])

    return total_supply, total_demand

def forecast_price_movement(symbol, limit=100):
    """
    Forecast price movement based on the order book depth.
    """
    order_book = get_order_book(symbol, limit)
    if order_book:
        supply, demand = calculate_supply_demand(order_book)
        if demand > supply:
            forecast = "Price might increase due to higher demand."
        elif supply > demand:
            forecast = "Price might decrease due to higher supply."
        else:
            forecast = "No clear price movement direction."
        return forecast
    else:
        return "Unable to fetch order book data."

# Example usage
symbol = 'BTCUSDT'
forecast = forecast_price_movement(symbol, 100)
print(f"Forecast for {symbol}: {forecast}")
