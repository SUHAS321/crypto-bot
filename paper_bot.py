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

SYMBOLS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana"
}

BALANCE = 20.0
RISK = 0.3

TP = 0.02
SL = 0.008
TRAIL = 0.01

active_trades = {}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= DATA =================
def get_data(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=1"
        data = requests.get(url, headers=HEADERS).json()

        prices = [p[1] for p in data["prices"][-120:]]
        volumes = [v[1] for v in data["total_volumes"][-120:]]

        df = pd.DataFrame({
            "close": prices,
            "volume": volumes
        })

        return df

    except:
        return None

def get_price(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        return float(requests.get(url).json()[coin]["usd"])
    except:
        return None

# ================= INDICATORS =================
def rsi(series):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ================= AI-LIKE SCORE =================
def ai_score(df):
    close = df["close"]

    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()

    r = rsi(close)

    score = 0

    if ema9.iloc[-1] > ema21.iloc[-1]:
        score += 1

    if r.iloc[-1] < 60:
        score += 1

    if df["volume"].iloc[-1] > df["volume"].rolling(20).mean().iloc[-1]:
        score += 1

    return score

# ================= STRATEGY =================
def strategy(df):
    close = df["close"]
    price = close.iloc[-1]

    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()

    score = ai_score(df)

    # only trade if strong score
    if score >= 3:
        if ema9.iloc[-2] < ema21.iloc[-2] and ema9.iloc[-1] > ema21.iloc[-1]:
            return "BUY", price

        if ema9.iloc[-2] > ema21.iloc[-2] and ema9.iloc[-1] < ema21.iloc[-1]:
            return "SELL", price

    return "HOLD", price

# ================= OPEN =================
def open_trade(symbol):
    global BALANCE

    if symbol in active_trades:
        return

    df = get_data(symbol)
    if df is None:
        return

    signal, price = strategy(df)

    print(symbol, signal)

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
        "qty": qty,
        "trail_price": price
    }

    send(f"""
🚀 TRADE OPEN

{symbol} {signal}

Entry: {price:.2f}
TP: {tp:.2f}
SL: {sl:.2f}

Balance: ${BALANCE:.2f}
""")

# ================= CLOSE =================
def check_trades():
    global BALANCE

    for symbol in list(active_trades.keys()):
        t = active_trades[symbol]
        price = get_price(symbol)

        if price is None:
            continue

        entry = t["entry"]
        qty = t["qty"]

        # TRAILING STOP
        if t["side"] == "BUY":
            if price > t["trail_price"]:
                t["trail_price"] = price

            if price < t["trail_price"] * (1 - TRAIL):
                pnl = (price - entry) * qty
                close_trade(symbol, price, pnl)
                continue

        # TP/SL
        if t["side"] == "BUY":
            if price >= t["tp"] or price <= t["sl"]:
                pnl = (price - entry) * qty
                close_trade(symbol, price, pnl)

        else:
            if price <= t["tp"] or price >= t["sl"]:
                pnl = (entry - price) * qty
                close_trade(symbol, price, pnl)

def close_trade(symbol, price, pnl):
    global BALANCE

    t = active_trades[symbol]
    BALANCE += pnl

    result = "PROFIT ✅" if pnl > 0 else "LOSS ❌"

    send(f"""
📉 TRADE CLOSED

{symbol} {t['side']}

Entry: {t['entry']:.2f}
Exit: {price:.2f}

PnL: ${pnl:.2f} ({result})

💰 Balance: ${BALANCE:.2f}
""")

    del active_trades[symbol]

# ================= MAIN =================
def main():
    send("🔥 AI SMART BOT STARTED")

    while True:
        try:
            for s in SYMBOLS:
                open_trade(s)

            check_trades()

            time.sleep(30)

        except Exception as e:
            print("Error:", e)
            time.sleep(10)

if __name__ == "__main__":
    main()
