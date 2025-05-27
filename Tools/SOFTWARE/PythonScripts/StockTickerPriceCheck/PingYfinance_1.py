# BRIAN COX 2025
# USES PYTHON 3.9
# EXAMPLE USE:
# OPEN TERMINAL, NAVIGATE TO THE DIRECTORY WHERE THE SCRIPT "PingYfinance_1.py" IS LOCATED
# IN THE TERMINAL, TYPE "python3.9 PingYfinance_1.py" AND HIT RETURN
# SCRIPT WILL PROMT YOU FOR A TICKER SYMBOL
# ENTER TICKER SYMBOL AND HIT RETURN

import yfinance as yf

def get_stock_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.info
        print(f"--- {symbol.upper()} Stock Data (Yahoo Finance) ---")
        print(f"Current Price: {data.get('currentPrice', 'N/A')}")
        print(f"Previous Close: {data.get('previousClose', 'N/A')}")
        print(f"Open: {data.get('open', 'N/A')}")
        print(f"Day High: {data.get('dayHigh', 'N/A')}")
        print(f"Day Low: {data.get('dayLow', 'N/A')}")
    except Exception as e:
        print(f"Error retrieving data for {symbol}: {e}")

# Example usage
if __name__ == "__main__":
    stock_symbol = input("Enter stock ticker symbol: ").strip().upper()
    get_stock_price(stock_symbol)
