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

RISK = 0.20   # 20% balance per trade
TP = 0.01     # 1% profit
SL = 0.005    # 0.5% stop loss

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =========================
# BYBIT SESSION
# =========================
session = HTTP(
    testnet=False,  # ⚠️ change to True for demo first
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
# DATA (COINGECKO)
# =========================
def get_price(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        return float(res[coin]["usd"])
    except:
        return None


def get_klines(symbol):
    try:
        coin = SYMBOLS[symbol]
        url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days=1"
        res = requests.get(url, headers=HEADERS, timeout=10).json()

        prices = res.get("prices", [])
        if len(prices) < 50:
            return None

        closes = [p[1] for p in prices[-100:]]
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
# STRATEGY (IMPROVED)
# =========================
def analyze(data):
    try:
        price = data.iloc[-1]

        ema9 = data.ewm(span=9).mean().iloc[-1]
        ema21 = data.ewm(span=21).mean().iloc[-1]
        ema50 = data.ewm(span=50).mean().iloc[-1]

        r = rsi(data).iloc[-1]

        # TREND BUY
        if ema9 > ema21 > ema50 and r < 55:
            return "Buy", price

        # TREND SELL
        elif ema9 < ema21 < ema50 and r > 45:
            return "Sell", price

        # SCALP SIGNALS
        elif r < 30:
            return "Buy", price

        elif r > 70:
            return "Sell", price

        return "Hold", price

    except:
        return "Hold", None

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
# ORDER EXECUTION
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

💰 Balance: {balance:.2f}
""")

    except Exception as e:
        send(f"Order error: {e}")

# =========================
# MAIN LOOP
# =========================
def main():
    print("BOT STARTED", flush=True)
    send("🚀 BYBIT BOT STARTED")

    while True:
        try:
            print("Running...", flush=True)

            for symbol in SYMBOLS:
                data = get_klines(symbol)

                if data is None:
                    print(f"No data {symbol}", flush=True)
                    continue

                signal, price = analyze(data)

                print(f"{symbol} → {signal}", flush=True)

                if signal != "Hold":
                    place_trade(symbol, signal)

            time.sleep(30)

        except Exception as e:
            print("MAIN ERROR:", e, flush=True)
            time.sleep(10)

# =========================
# START
# =========================
if __name__ == "__main__":
    main()
