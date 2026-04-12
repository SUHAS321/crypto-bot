import time
import requests
import numpy as np
import pandas as pd
import os

# =========================
# TELEGRAM CONFIG
# =========================
TELEGRAM_TOKEN = os.getenv("8725264690:AAE6xjCAyXyc2qsTRMk9eeuy6_cWXOy8uFA")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram error:", e)


# =========================
# COINS (COINGECKO IDs)
# =========================
SYMBOLS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "binancecoin": "BNB",
    "solana": "SOL",
    "ripple": "XRP"
}


# =========================
# FETCH DATA (SAFE VERSION)
# =========================
def get_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=1"

        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"API failed for {coin_id}")
            return None

        data = response.json()

        # SAFE CHECK
        if "prices" not in data:
            print(f"No price data for {coin_id}")
            return None

        prices = [x[1] for x in data["prices"]]

        if len(prices) < 20:
            print(f"Not enough data for {coin_id}")
            return None

        return pd.Series(prices[-50:])

    except Exception as e:
        print(f"Error fetching {coin_id}: {e}")
        return None


# =========================
# RSI
# =========================
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =========================
# ANALYSIS (SMART FILTER)
# =========================
def analyze(close):
    price = close.iloc[-1]

    rsi = calculate_rsi(close).iloc[-1]
    ma_short = close.rolling(5).mean().iloc[-1]
    ma_long = close.rolling(20).mean().iloc[-1]

    trend = (ma_short - ma_long) / price

    if rsi < 40 and ma_short > ma_long and trend > 0:
        signal = "BUY"
    elif rsi > 60 and ma_short < ma_long and trend < 0:
        signal = "SELL"
    else:
        signal = "HOLD"

    confidence = abs(rsi - 50) + abs(trend * 1000)

    return signal, confidence, price


# =========================
# STOP LOSS / TARGET
# =========================
def risk_management(signal, price):
    if signal == "BUY":
        sl = price * 0.99
        tp = price * 1.02
    else:
        sl = price * 1.01
        tp = price * 0.98

    return round(sl, 2), round(tp, 2)


# =========================
# MAIN BOT
# =========================
print("🚀 BOT STARTED")
send_telegram("🚀 AI Trading Bot Started")

last_signal = None

while True:
    try:
        print("\nScanning market...")

        best_trade = None
        best_score = 0

        for coin_id, symbol in SYMBOLS.items():
            close = get_data(coin_id)

            if close is None:
                continue

            signal, confidence, price = analyze(close)

            print(f"{symbol} → {signal} | Score: {confidence:.2f}")

            if signal != "HOLD" and confidence > best_score:
                best_score = confidence
                best_trade = (symbol, signal, price, confidence)

        if best_trade:
            symbol, signal, price, confidence = best_trade
            sl, tp = risk_management(signal, price)

            message = (
                f"🔥 BEST TRADE SIGNAL\n\n"
                f"Coin: {symbol}\n"
                f"Signal: {signal}\n"
                f"Entry: {price:.2f}\n"
                f"Stop Loss: {sl}\n"
                f"Target: {tp}\n"
                f"Confidence: {confidence:.2f}%"
            )

            print("\n>>> SIGNAL <<<")
            print(message)

            if last_signal != message:
                send_telegram(message)
                last_signal = message

        time.sleep(15)

    except Exception as e:
        print("Error:", e)
        send_telegram(f"❌ Error: {e}")
        time.sleep(15)
