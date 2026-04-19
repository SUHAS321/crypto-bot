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
        print("Telegram error")

# =====================
# SETTINGS
# =====================
SYMBOLS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana"
}

BALANCE = 20.0
RISK = 0.3

TP = 0.015   # 1.5%
SL = 0.007   # 0.7%

active_trades = {}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =====================
# DATA
# =====================
def get_data(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=1"
        data = requests.get(url, headers=HEADERS).json()

        prices = data["prices"]
        closes = [p[1] for p in prices[-120:]]

        return pd.Series(closes)

    except:
        return None

def get_price(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        return float(requests.get(url).json()[coin]["usd"])
    except:
        return None

# =====================
# INDICATORS
# =====================
def rsi(data):
    delta = data.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =====================
# STRATEGY (UPGRADED)
# =====================
def strategy(data):
    price = data.iloc[-1]

    ema9 = data.ewm(span=9).mean()
    ema21 = data.ewm(span=21).mean()

    r = rsi(data)

    # CROSSOVER CONFIRMATION
    if ema9.iloc[-2] < ema21.iloc[-2] and ema9.iloc[-1] > ema21.iloc[-1] and r.iloc[-1] < 60:
        return "BUY", price

    if ema9.iloc[-2] > ema21.iloc[-2] and ema9.iloc[-1] < ema21.iloc[-1] and r.iloc[-1] > 40:
        return "SELL", price

    return "HOLD", price

# =====================
# OPEN TRADE
# =====================
def open_trade(symbol):
    global BALANCE

    if symbol in active_trades:
        return

    data = get_data(symbol)
    if data is None:
        return

    signal, price = strategy(data)

    print(f"{symbol} → {signal}")

    if signal == "HOLD":
        return

    amount = BALANCE * RISK
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
📊 TRADE OPEN

{symbol} {signal}

Entry: {price:.2f}
TP: {tp:.2f}
SL: {sl:.2f}

💰 Balance: ${BALANCE:.2f}
""")

# =====================
# CLOSE TRADE
# =====================
def check_trades():
    global BALANCE

    to_close = []

    for symbol, t in active_trades.items():
        price = get_price(symbol)
        if price is None:
            continue

        entry = t["entry"]
        qty = t["qty"]

        pnl = 0
        closed = False

        if t["side"] == "BUY":
            if price >= t["tp"] or price <= t["sl"]:
                pnl = (price - entry) * qty
                closed = True

        else:
            if price <= t["tp"] or price >= t["sl"]:
                pnl = (entry - price) * qty
                closed = True

        if closed:
            BALANCE += pnl

            send(f"""
📉 TRADE CLOSED

{symbol} {t['side']}

Entry: {entry:.2f}
Exit: {price:.2f}

PnL: ${pnl:.2f}
💰 Balance: ${BALANCE:.2f}
""")

            to_close.append(symbol)

    for s in to_close:
        del active_trades[s]

# =====================
# MAIN
# =====================
def main():
    send("🚀 BOT STARTED (SMART MODE)")

    while True:
        try:
            print("Running...")

            for s in SYMBOLS:
                open_trade(s)

            check_trades()

            time.sleep(30)

        except Exception as e:
            print("Error:", e)
            time.sleep(10)

if __name__ == "__main__":
    main()

