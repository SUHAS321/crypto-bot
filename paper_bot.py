import time
import requests
import pandas as pd
from pybit.unified_trading import HTTP

# =========================
# CONFIG
# =========================
BYBIT_API_KEY = "YgoxC6A9aWOAoRvJKb"
BYBIT_SECRET_KEY = "bZyXL8kuS5uiikGrc4t01nbcAo8pCXcRtUC9"

TELEGRAM_TOKEN = "8725264690:AAE6xjCAyXyc2qsTRMk9eeuy6_cWXOy8uFA"
CHAT_ID = "1345617133"

SYMBOLS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
    "SOLUSDT": "solana"
}

RISK = 0.20
TP = 0.01
SL = 0.005

# =========================
# BYBIT SESSION
# =========================
session = HTTP(
    testnet=False,
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_SECRET_KEY
)

# =========================
# TELEGRAM
# =========================
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg}
        )
    except:
        print("Telegram error", flush=True)

# =========================
# PRICE (COINGECKO)
# =========================
def get_price(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        res = requests.get(url).json()
        return float(res[coin]["usd"])
    except:
        return None

# =========================
# KLINES (COINGECKO)
# =========================
def get_klines(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=1"
        res = requests.get(url).json()

        prices = res["prices"]
        closes = [p[1] for p in prices[-100:]]

        return pd.Series(closes)

    except:
        return None

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

    if ema9 > ema21 and r < 40:
        return "Buy", price
    elif ema9 < ema21 and r > 60:
        return "Sell", price
    else:
        return "Hold", price

# =========================
# BALANCE
# =========================
def get_balance():
    try:
        res = session.get_wallet_balance(accountType="UNIFIED")
        return float(res["result"]["list"][0]["totalWalletBalance"])
    except:
        return 0

# =========================
# ORDER
# =========================
def place_trade(symbol, side):
    price = get_price(symbol)
    balance = get_balance()

    if price is None or balance == 0:
        return

    qty = round((balance * RISK) / price, 3)

    if qty <= 0:
        return

    if side == "Buy":
        tp = price * (1 + TP)
        sl = price * (1 - SL)
    else:
        tp = price * (1 - TP)
        sl = price * (1 + SL)

    try:
        session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            takeProfit=str(round(tp, 2)),
            stopLoss=str(round(sl, 2))
        )

        send(f"""
🚀 TRADE EXECUTED
{symbol} {side}

Entry: {price:.2f}
TP: {tp:.2f}
SL: {sl:.2f}

Balance: {balance:.2f}
""")

    except Exception as e:
        send(f"Order error: {e}")

# =========================
# MAIN LOOP
# =========================
def main():
    print("BOT STARTED", flush=True)
    send("🚀 BOT STARTED")

    while True:
        try:
            print("Running...", flush=True)

            for symbol in SYMBOLS:
                data = get_klines(symbol)

                if data is None:
                    print(f"No data {symbol}", flush=True)
                    continue

                signal, price = analyze(data)

                print(symbol, signal, flush=True)

                if signal != "Hold":
                    place_trade(symbol, signal)

            time.sleep(30)

        except Exception as e:
            print("ERROR:", e, flush=True)
            time.sleep(10)

if __name__ == "__main__":
    main()
