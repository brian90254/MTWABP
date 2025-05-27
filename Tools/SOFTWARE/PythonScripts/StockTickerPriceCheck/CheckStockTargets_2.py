# BRIAN COX 2025
# USES PYTHON 3.9
# EXAMPLE USE:
# OPEN TERMINAL, NAVIGATE TO THE DIRECTORY WHERE THE SCRIPT "PingYfinance_1.py" IS LOCATED
# IN THE TERMINAL, TYPE "python3.9 CheckStockTargets_1.py" AND HIT RETURN

import yfinance as yf

def load_targets(filename):
    targets = []
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 3:
                continue  # skip malformed lines
            symbol, price_str, condition = parts
            try:
                price = float(price_str)
                condition = condition.upper()
                if condition in ['LESS', 'MORE']:
                    targets.append((symbol.upper(), price, condition))
            except ValueError:
                continue  # skip lines with invalid numbers
    return targets

def check_prices(targets):
    for symbol, target_price, condition in targets:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.info
            price = data.get('currentPrice', 'N/A')
            # price = ticker.fast_info.get('last_price', None)
            if price is None:
                print(f"{symbol}: Unable to retrieve price")
                continue

            status = ""
            if condition == 'LESS' and price < target_price:
                status = "✅ Triggered: price is LESS"
            elif condition == 'MORE' and price > target_price:
                status = "✅ Triggered: price is MORE"
            else:
                status = "⏸ Not Triggered"

            print(f"{symbol}: Current = {price:.2f}, Target = {target_price} ({condition}) → {status}")
        except Exception as e:
            print(f"{symbol}: Error checking price → {e}")

if __name__ == "__main__":
    target_file = "TargetStockPrices.txt"
    targets = load_targets(target_file)
    check_prices(targets)

