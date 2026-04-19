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

BALANCE = 20.0
TRADE_PERCENT = 0.3   # 30% per trade

TP = 0.01   # 1%
SL = 0.005  # 0.5%

active_trades = {}

# =========================
# SAFE DATA FUNCTIONS
# =========================
def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        res = requests.get(url, timeout=5).json()

        if "price" not in res:
            return None

        return float(res["price"])
    except:
        return None


def get_klines(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
        data = requests.get(url, timeout=5).json()

        if not isinstance(data, list):
            return None

        closes = []
        for x in data:
            if len(x) > 4:
                closes.append(float(x[4]))

        if len(closes) < 20:
            return None

        return pd.Series(closes)

    except:
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
# STRATEGY
# =========================
def analyze(data):
    try:
        price = data.iloc[-1]

        ema9 = data.ewm(span=9).mean().iloc[-1]
        ema21 = data.ewm(span=21).mean().iloc[-1]
        r = rsi(data).iloc[-1]

        # Better filtered signals
        if ema9 > ema21 and r < 40:
            return "BUY", price

        elif ema9 < ema21 and r > 60:
            return "SELL", price

        return "HOLD", price

    except:
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
        return

    signal, price = analyze(data)

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

            to_close.append(symbol)

    for s in to_close:
        del active_trades[s]

# =========================
# MAIN LOOP
# =========================
def main():
    send("🚀 PAPER TRADING BOT STARTED")

    while True:
        try:
            for symbol in SYMBOLS:
                open_trade(symbol)

            check_trades()

            time.sleep(15)

        except Exception as e:
            print("Error:", e)
            time.sleep(10)

# =========================
# START
# =========================
if __name__ == "__main__":
    main()
