# BRIAN COX 2025
# USES PYTHON 3.9
# EXAMPLE USE:
# OPEN TERMINAL, NAVIGATE TO THE DIRECTORY WHERE THE SCRIPT "PingYfinance_1.py" IS LOCATED
# IN THE TERMINAL, TYPE "python3.9 CheckStockTargets_4.py" AND HIT RETURN

import yfinance as yf
import smtplib
from email.mime.text import MIMEText
import argparse
import datetime
import time

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

            if price == 'N/A':
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

def wait_until_2pm():
    now = datetime.datetime.now()
    target_time = now.replace(hour=14, minute=0, second=0, microsecond=0)
    if now >= target_time:
        target_time += datetime.timedelta(days=1)
    seconds_to_wait = (target_time - now).total_seconds()
    print(f"⏳ Waiting until {target_time.strftime('%Y-%m-%d %I:%M %p')} to run check...")
    time.sleep(seconds_to_wait)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check stock prices and send text alerts via email-to-SMS.")
    parser.add_argument("--email", required=True, help="Your Gmail address")
    parser.add_argument("--password", required=True, help="Your Gmail app-specific password (use quotes if it has spaces)")
    parser.add_argument("--phone", required=True, help="Your 10-digit phone number (no dashes)")
    parser.add_argument("--carrier", required=True, choices=["att", "verizon", "tmobile", "sprint", "googlefi"], help="Your phone carrier")
    parser.add_argument("--file", default="TargetStockPrices.txt", help="Path to target stock prices file")

    args = parser.parse_args()

    # Loop: wait until 2PM local time, run, then repeat daily
    while True:
        wait_until_2pm()
        print(f"\n🔁 Running stock check at {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')}...\n")
        targets = load_targets(args.file)
        check_prices(targets, args.email, args.password, args.phone, args.carrier)
