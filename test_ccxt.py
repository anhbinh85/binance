import ccxt

def fetch_tickers(exchange):
    try:
        return exchange.fetch_tickers()
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        return {}

def top_gainers():
    # Initialize Binance exchange
    exchange = ccxt.binance()

    # Fetch tickers
    tickers = fetch_tickers(exchange)

    # Check if tickers is not None and not empty
    if not tickers:
        print("No tickers data received")
        return []

    # Calculate percentage change for each ticker and filter for USDT pairs
    changes = {}
    for symbol, ticker in tickers.items():
        if 'USDT' in symbol and 'percentage' in ticker and ticker['percentage'] is not None and 'last' in ticker:  
            changes[symbol] = (ticker['last'], ticker['percentage'])

    # Sort symbols by percentage change
    top_symbols = sorted(changes, key=lambda x: changes[x][1], reverse=True)

    # Return top 20 gainers
    return [(symbol, changes[symbol][0], changes[symbol][1]) for symbol in top_symbols[:20]]

# Get top gainers
top_gainers_result = top_gainers()

# Print results
for symbol, price, percentage in top_gainers_result:
    print(f"{symbol}: Price = {price} USDT, Change = {percentage}%")

