import time
import requests
import pandas as pd

# =========================
# TELEGRAM CONFIG
# =========================
TOKEN = "8725264690:AAE6xjCAyXyc2qsTRMk9eeuy6_cWXOy8uFA"
CHAT_ID = "1345617133"

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        print("Telegram error", flush=True)

# =========================
# SETTINGS
# =========================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

BALANCE = 20.0
TRADE_PERCENT = 0.3

TP = 0.01
SL = 0.005

active_trades = {}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# SAFE DATA FUNCTIONS
# =========================
def get_price(symbol):
    for _ in range(3):
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            res = requests.get(url, headers=HEADERS, timeout=10)
            data = res.json()

            if "price" in data:
                return float(data["price"])

        except Exception as e:
            print(f"Retry price {symbol}", flush=True)

        time.sleep(1)

    return None


def get_klines(symbol):
    for _ in range(3):
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
            res = requests.get(url, headers=HEADERS, timeout=10)
            data = res.json()

            if isinstance(data, list) and len(data) > 20:
                closes = [float(x[4]) for x in data if len(x) > 4]
                return pd.Series(closes)

        except Exception as e:
            print(f"Retry klines {symbol}", flush=True)

        time.sleep(1)

    return None

# =========================
# INDICATORS
# =========================
def rsi(data):
    delta = data.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =========================
# STRATEGY (IMPROVED)
# =========================
def analyze(data):
    try:
        price = data.iloc[-1]

        ema9 = data.ewm(span=9).mean().iloc[-1]
        ema21 = data.ewm(span=21).mean().iloc[-1]
        r = rsi(data).iloc[-1]

        if ema9 > ema21 and r < 40:
            return "BUY", price

        elif ema9 < ema21 and r > 60:
            return "SELL", price

        return "HOLD", price

    except Exception as e:
        print("Analyze error:", e, flush=True)
        return "HOLD", None

# =========================
# OPEN TRADE
# =========================
def open_trade(symbol):
    global BALANCE

    if symbol in active_trades:
        return

    data = get_klines(symbol)
    if data is None:
        print(f"Skip {symbol} (no data)", flush=True)
        return

    signal, price = analyze(data)

    print(f"{symbol} → {signal}", flush=True)

    if signal == "HOLD" or price is None:
        return

    amount = BALANCE * TRADE_PERCENT
    qty = amount / price

    if signal == "BUY":
        tp = price * (1 + TP)
        sl = price * (1 - SL)
    else:
        tp = price * (1 - TP)
        sl = price * (1 + SL)

    active_trades[symbol] = {
        "side": signal,
        "entry": price,
        "tp": tp,
        "sl": sl,
        "qty": qty
    }

    send(f"""
📊 PAPER TRADE OPEN
{symbol} {signal}

Entry: {price:.2f}
TP: {tp:.2f}
SL: {sl:.2f}

💰 Balance: ${BALANCE:.2f}
""")

# =========================
# CLOSE TRADE
# =========================
def check_trades():
    global BALANCE

    to_close = []

    for symbol, trade in active_trades.items():
        price = get_price(symbol)

        if price is None:
            continue

        entry = trade["entry"]
        qty = trade["qty"]
        side = trade["side"]

        closed = False
        pnl = 0

        if side == "BUY":
            if price >= trade["tp"] or price <= trade["sl"]:
                pnl = (price - entry) * qty
                closed = True

        elif side == "SELL":
            if price <= trade["tp"] or price >= trade["sl"]:
                pnl = (entry - price) * qty
                closed = True

        if closed:
            BALANCE += pnl
            result = "PROFIT" if pnl > 0 else "LOSS"

            send(f"""
📉 PAPER TRADE CLOSED
{symbol}

Result: {result}
PnL: ${pnl:.2f}

💰 New Balance: ${BALANCE:.2f}
""")

            print(f"{symbol} CLOSED PnL: {pnl}", flush=True)

            to_close.append(symbol)

    for s in to_close:
        del active_trades[s]

# =========================
# MAIN LOOP
# =========================
def main():
    print("BOT STARTED", flush=True)
    send("🚀 PAPER TRADING BOT STARTED")

    while True:
        try:
            print("Running cycle...", flush=True)

            for symbol in SYMBOLS:
                open_trade(symbol)

            check_trades()

            time.sleep(15)

        except Exception as e:
            print("MAIN ERROR:", e, flush=True)
            time.sleep(10)

# =========================
# START
# =========================
if __name__ == "__main__":
    main()
