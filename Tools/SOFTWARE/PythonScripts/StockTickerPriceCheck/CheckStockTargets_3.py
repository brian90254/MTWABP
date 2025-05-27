# BRIAN COX 2025
# USES PYTHON 3.9
# EXAMPLE USE:
# OPEN TERMINAL, NAVIGATE TO THE DIRECTORY WHERE THE SCRIPT "PingYfinance_1.py" IS LOCATED
# IN THE TERMINAL, TYPE "python3.9 CheckStockTargets_1.py" AND HIT RETURN

import yfinance as yf
import smtplib
from email.mime.text import MIMEText

def load_targets(filename):
    targets = []
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 3:
                continue
            symbol, price_str, condition = parts
            try:
                price = float(price_str)
                condition = condition.upper()
                if condition in ['LESS', 'MORE']:
                    targets.append((symbol.upper(), price, condition))
            except ValueError:
                continue
    return targets

def send_sms_via_email(subject, message, from_email, app_password, phone_number, carrier):
    # Known carrier email-to-text gateways
    gateways = {
        "att": "@txt.att.net",
        "verizon": "@vtext.com",
        "tmobile": "@tmomail.net",
        "sprint": "@messaging.sprintpcs.com",
        "googlefi": "@msg.fi.google.com"
    }

    carrier = carrier.lower()
    if carrier not in gateways:
        print("❌ Carrier not recognized. Supported: att, verizon, tmobile, sprint, googlefi")
        return

    to_email = phone_number + gateways[carrier]

    msg = MIMEText(message)
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_email, app_password)
            server.send_message(msg)
        print(f"📲 Text alert sent to {phone_number}")
    except Exception as e:
        print("❌ Failed to send text alert:", e)

def check_prices(targets, from_email, app_password, phone_number, carrier):
    for symbol, target_price, condition in targets:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.info
            price = data.get('currentPrice', 'N/A')
            # price = ticker.fast_info.get('last_price', None)
            if price is None:
                print(f"{symbol}: Unable to retrieve price")
                continue

            triggered = False
            if condition == 'LESS' and price < target_price:
                triggered = True
            elif condition == 'MORE' and price > target_price:
                triggered = True

            status = "✅ Triggered" if triggered else "⏸ Not Triggered"
            print(f"{symbol}: Current = {price:.2f}, Target = {target_price} ({condition}) → {status}")

            if triggered:
                message = f"{symbol}: Current = {price:.2f} crossed your target of {target_price} ({condition})"
                send_sms_via_email(f"Stock Alert: {symbol}", message, from_email, app_password, phone_number, carrier)

        except Exception as e:
            print(f"{symbol}: Error checking price → {e}")

if __name__ == "__main__":
    # Prompt for user credentials and alert target
    from_email = input("Enter your Gmail address: ").strip()
    app_password = input("Enter your Gmail app password: ").strip()
    phone_number = input("Enter your 10-digit phone number: ").strip()
    carrier = input("Enter your carrier (att, verizon, tmobile, sprint, googlefi): ").strip()

    # Load targets and check
    target_file = "TargetStockPrices.txt"
    targets = load_targets(target_file)
    check_prices(targets, from_email, app_password, phone_number, carrier)
