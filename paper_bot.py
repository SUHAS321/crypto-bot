import time
import requests
import numpy as np
import pandas as pd

# =========================
# 🔑 TELEGRAM CONFIG
# =========================
TELEGRAM_TOKEN = "8725264690:AAE6xjCAyXyc2qsTRMk9eeuy6_cWXOy8uFA"
CHAT_ID = "1345617133"

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        print("Telegram error")


# =========================
# 🪙 COINS LIST
# =========================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]


# =========================
# 📊 GET DATA
# =========================
def get_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"
        data = requests.get(url, timeout=5).json()

        close = [float(x[4]) for x in data]
        return pd.Series(close)
    except:
        print(f"Error fetching {symbol}")
        return None


# =========================
# 📈 RSI
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
# 🧠 SMART ANALYSIS
# =========================
def analyze(close):
    price = close.iloc[-1]

    rsi = calculate_rsi(close).iloc[-1]

    # Moving averages
    ma_short = close.rolling(5).mean().iloc[-1]
    ma_long = close.rolling(20).mean().iloc[-1]

    # Trend strength
    trend = (ma_short - ma_long) / price

    # 🔥 SAFE LOGIC
    if rsi < 40 and ma_short > ma_long:
        signal = "BUY"
    elif rsi > 60 and ma_short < ma_long:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Confidence score
    confidence = abs(rsi - 50) + abs(trend * 1000)

    return signal, confidence, price


# =========================
# 🚀 START BOT
# =========================
print("🚀 SMART AI BOT STARTED (SAFE MODE)")
send_telegram("🚀 Smart AI Bot Started (Safe Mode)")

last_sent = None

while True:
    try:
        print("\n========================")

        best_trade = None
        best_score = 0

        for symbol in SYMBOLS:
            close = get_data(symbol)

            if close is None:
                continue

            signal, confidence, price = analyze(close)

            print(f"{symbol} → {signal} | Score: {confidence:.2f}")

            # pick best signal only
            if signal != "HOLD" and confidence > best_score:
                best_score = confidence
                best_trade = (symbol, signal, price, confidence)

        # 🔥 SEND ONLY BEST SIGNAL (NO SPAM)
        if best_trade:
            symbol, signal, price, confidence = best_trade

            message = (
                f"🔥 BEST TRADE\n\n"
                f"Coin: {symbol}\n"
                f"Signal: {signal}\n"
                f"Price: {price:.2f}\n"
                f"Confidence: {confidence:.2f}%"
            )

            print("\n>>> BEST SIGNAL FOUND <<<")
            print(message)

            # avoid duplicate spam
            if last_sent != message:
                send_telegram(message)
                last_sent = message

        time.sleep(5)

    except Exception as e:
        print("Error:", e)
        send_telegram(f"❌ Error: {e}")
        time.sleep(5)