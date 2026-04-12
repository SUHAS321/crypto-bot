import time
import requests
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
    except:
        pass


# =========================
# BINANCE SYMBOLS
# =========================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]


# =========================
# FETCH DATA (BINANCE)
# =========================
def get_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"
        data = requests.get(url, timeout=10).json()

        closes = [float(x[4]) for x in data]
        return pd.Series(closes)

    except Exception as e:
        print("Error:", e)
        return None


# =========================
# RSI
# =========================
def rsi(data, period=14):
    delta = data.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =========================
# STRATEGY
# =========================
def analyze(data):
    price = data.iloc[-1]
    r = rsi(data).iloc[-1]

    ma5 = data.rolling(5).mean().iloc[-1]
    ma20 = data.rolling(20).mean().iloc[-1]

    if r < 40 and ma5 > ma20:
        return "BUY", price, r
    elif r > 60 and ma5 < ma20:
        return "SELL", price, r
    else:
        return "HOLD", price, r


# =========================
# MAIN LOOP
# =========================
print("🚀 BOT STARTED")
send_telegram("🚀 Trading Bot Started")

last_msg = ""

while True:
    try:
        print("\nScanning market...")

        best = None
        best_score = 0

        for symbol in SYMBOLS:
            data = get_data(symbol)

            if data is None:
                continue

            signal, price, r = analyze(data)

            score = abs(r - 50)

            print(f"{symbol} → {signal} | RSI: {r:.2f}")

            if signal != "HOLD" and score > best_score:
                best = (symbol, signal, price, score)
                best_score = score

        if best:
            symbol, signal, price, score = best

            sl = price * (0.99 if signal == "BUY" else 1.01)
            tp = price * (1.02 if signal == "BUY" else 0.98)

            msg = (
                f"🔥 BEST SIGNAL\n\n"
                f"Coin: {symbol}\n"
                f"Signal: {signal}\n"
                f"Price: {price:.2f}\n"
                f"SL: {sl:.2f}\n"
                f"TP: {tp:.2f}\n"
                f"Confidence: {score:.2f}"
            )

            print(msg)

            if msg != last_msg:
                send_telegram(msg)
                last_msg = msg

        time.sleep(10)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)
