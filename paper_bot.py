import time
import requests
import pandas as pd
import os

# TELEGRAM
TOKEN = os.getenv("8725264690:AAE6xjCAyXyc2qsTRMk9eeuy6_cWXOy8uFA")
CHAT_ID = os.getenv("CHAT_ID")

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass


SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]


def get_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"
        res = requests.get(url, timeout=10)

        data = res.json()

        # ✅ FIX ERROR
        if not isinstance(data, list) or len(data) == 0:
            return None

        closes = [float(x[4]) for x in data if len(x) > 4]

        if len(closes) < 20:
            return None

        return pd.Series(closes)

    except:
        return None


def rsi(data):
    delta = data.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


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


print("🚀 BOT STARTED")
send("🚀 Bot Started")

last = ""

while True:
    try:
        print("\nScanning market...")

        best = None
        score_best = 0

        for s in SYMBOLS:
            data = get_data(s)

            if data is None:
                continue

            signal, price, r = analyze(data)

            score = abs(r - 50)

            print(s, signal, round(r, 2))

            if signal != "HOLD" and score > score_best:
                best = (s, signal, price, score)
                score_best = score

        if best:
            s, signal, price, score = best

            sl = price * (0.99 if signal == "BUY" else 1.01)
            tp = price * (1.02 if signal == "BUY" else 0.98)

            msg = f"{s} {signal}\nPrice: {price:.2f}\nSL: {sl:.2f}\nTP: {tp:.2f}\nConfidence: {score:.2f}"

            print(msg)

            if msg != last:
                send(msg)
                last = msg

        time.sleep(10)

    except Exception as e:
        print("Error:", e)
        time.sleep(10)
