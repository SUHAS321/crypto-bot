import time
import requests
import pandas as pd

# =========================
# TELEGRAM CONFIG
# =========================
TOKEN = "8725264690:AAE6xjCAyXyc2qsTRMk9eeuy6_cWXOy8uFA"
CHAT_ID = "1345617133"

SYMBOLS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana"
}

BALANCE = 20.0
RISK_PER_TRADE = 0.25

TP = 0.015     # 1.5%
SL = 0.008     # 0.8%

COOLDOWN = 300   # 5 min gap per symbol

active_trades = {}
last_trade_time = {}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= TELEGRAM =================
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        pass

# ================= DATA =================
def get_data(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=1"
        data = requests.get(url, headers=HEADERS).json()

        prices = [p[1] for p in data["prices"][-150:]]
        volumes = [v[1] for v in data["total_volumes"][-150:]]

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

# ================= STRATEGY =================
def strategy(df):
    close = df["close"]

    ema50 = close.ewm(span=50).mean()
    ema200 = close.ewm(span=200).mean()
    r = rsi(close)

    volume = df["volume"]

    price = close.iloc[-1]

    # TREND
    uptrend = ema50.iloc[-1] > ema200.iloc[-1]
    downtrend = ema50.iloc[-1] < ema200.iloc[-1]

    # PULLBACK ENTRY
    pullback_buy = close.iloc[-1] < ema50.iloc[-1] * 1.01
    pullback_sell = close.iloc[-1] > ema50.iloc[-1] * 0.99

    # RSI FILTER
    rsi_buy = r.iloc[-1] < 55
    rsi_sell = r.iloc[-1] > 45

    # VOLUME SPIKE
    vol_spike = volume.iloc[-1] > volume.rolling(20).mean().iloc[-1]

    # FINAL DECISION
    if uptrend and pullback_buy and rsi_buy and vol_spike:
        return "BUY", price

    if downtrend and pullback_sell and rsi_sell and vol_spike:
        return "SELL", price

    return "HOLD", price

# ================= OPEN TRADE =================
def open_trade(symbol):
    global BALANCE

    now = time.time()

    if symbol in active_trades:
        return

    if symbol in last_trade_time:
        if now - last_trade_time[symbol] < COOLDOWN:
            return

    df = get_data(symbol)
    if df is None:
        return

    signal, price = strategy(df)

    print(symbol, signal)

    if signal == "HOLD":
        return

    amount = BALANCE * RISK_PER_TRADE
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

    last_trade_time[symbol] = now

    send(f"""
🚀 TRADE OPEN

{symbol} {signal}

Entry: {price:.2f}
TP: {tp:.2f}
SL: {sl:.2f}

💰 Balance: ${BALANCE:.2f}
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

        if t["side"] == "BUY":
            if price >= t["tp"] or price <= t["sl"]:
                pnl = (price - entry) * qty
                close_trade(symbol, price, pnl)

        else:
            if price <= t["tp"] or price >= t["sl"]:
                pnl = (entry - price) * qty
                close_trade(symbol, price, pnl)

# ================= CLOSE FUNCTION =================
def close_trade(symbol, price, pnl):
    global BALANCE

    BALANCE += pnl

    result = "PROFIT ✅" if pnl > 0 else "LOSS ❌"

    send(f"""
📉 TRADE CLOSED

{symbol}

Entry: {active_trades[symbol]['entry']:.2f}
Exit: {price:.2f}

PnL: ${pnl:.2f} ({result})

💰 Updated Balance: ${BALANCE:.2f}
""")

    del active_trades[symbol]

# ================= MAIN =================
def main():
    send("🔥 ACCURATE BOT STARTED")

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
