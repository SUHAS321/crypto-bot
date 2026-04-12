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
# COINS (CoinCap IDs)
# =========================
SYMBOLS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "binance-coin": "BNB",
    "solana": "SOL",
    "ripple": "XRP"
}


# =========================
# FETCH DATA (COINCAP)
# =========================
def get_price_history(coin_id):
    try:
        url = f"https://api.coincap.io/v2/assets/{coin_id}/history?interval=m1"
        response = requests.get(url, timeout=10)

        data = response.json()

        if "data" not in data:
            return None

        prices = [float(x["priceUsd"]) for x in data["data"]]

        if len(prices) < 20:
            return None

        return pd.Series(prices[-50:])

    except Exception as e:
        print("Fetch error:", e)
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
# ANALYSIS
# =========================
def analyze(close):
    price = close.iloc[-1]

    rsi = calculate_rsi(close).iloc[-1]
    ma_short = close.rolling(5).mean().iloc[-1]
    ma_long = close.rolling(20).mean().iloc[-1]

    if rsi < 40 and ma_short > ma_long:
        signal = "BUY"
    elif rsi > 60 and ma_short < ma_long:
        signal = "SELL"
    else:
        signal = "HOLD"

    confidence = abs(rsi - 50)

    return signal, confidence, price


# =========================
# STOP LOSS / TARGET
# =========================
def risk(signal, price):
    if signal == "BUY":
        return price * 0.99, price * 1.02
    else:
        return price * 1.01, price * 0.98


# =========================
# MAIN LOOP
# =========================
print("🚀 BOT STARTED")
send_telegram("🚀 Bot Started")

last_signal = None

while True:
    try:
        print("\nScanning market...")

        best = None
        best_score = 0

        for coin_id, symbol in SYMBOLS.items():
            data = get_price_history(coin_id)

            if data is None:
                continue

            signal, score, price = analyze(data)

            print(f"{symbol} → {signal} | Score {score:.2f}")

            if signal != "HOLD" and score > best_score:
                best = (symbol, signal, price, score)
                best_score = score

        if best:
            symbol, signal, price, score = best
            sl, tp = risk(signal, price)

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

            if msg != last_signal:
                send_telegram(msg)
                last_signal = msg

        time.sleep(15)

    except Exception as e:
        print("Error:", e)
        time.sleep(15)
