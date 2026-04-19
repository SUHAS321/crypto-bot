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
        pass

# =========================
# SETTINGS
# =========================
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

BALANCE = 20
TRADE_PERCENT = 0.3

TP = 0.01
SL = 0.005

active_trades = {}

# =========================
# DATA
# =========================
def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    return float(requests.get(url).json()["price"])

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
    data = requests.get(url).json()
    closes = [float(x[4]) for x in data]
    return pd.Series(closes)

# =========================
# RSI
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
# STRATEGY
# =========================
def analyze(data):
    price = data.iloc[-1]

    ema9 = data.ewm(span=9).mean().iloc[-1]
    ema21 = data.ewm(span=21).mean().iloc[-1]
    r = rsi(data).iloc[-1]

    if ema9 > ema21 and 35 < r < 45:
        return "BUY", price

    elif ema9 < ema21 and 55 < r < 65:
        return "SELL", price

    return "HOLD", price

# =========================
# OPEN TRADE
# =========================
def open_trade(symbol):
    global BALANCE

    if symbol in active_trades:
        return

    data = get_klines(symbol)
    signal, price = analyze(data)

    if signal == "HOLD":
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

        entry = trade["entry"]
        qty = trade["qty"]
        side = trade["side"]

        if side == "BUY":
            if price >= trade["tp"] or price <= trade["sl"]:
                pnl = (price - entry) * qty
            else:
                continue
        else:
            if price <= trade["tp"] or price >= trade["sl"]:
                pnl = (entry - price) * qty
            else:
                continue

        BALANCE += pnl
        result = "PROFIT" if pnl > 0 else "LOSS"

        send(f"""
📉 PAPER TRADE CLOSED
{symbol}

Result: {result}
PnL: ${pnl:.2f}

💰 New Balance: ${BALANCE:.2f}
""")

        to_close.append(symbol)

    for s in to_close:
        del active_trades[s]

# =========================
# MAIN LOOP
# =========================
send("🚀 PAPER TRADING BOT STARTED")

while True:
    try:
        for s in SYMBOLS:
            open_trade(s)

        check_trades()

        time.sleep(15)

    except Exception as e:
        print("Error:", e)
        time.sleep(15)
