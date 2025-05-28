import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# List of Nifty 50 tickers with ".NS" suffix for Yahoo Finance
nifty50_tickers = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BPCL.NS", "BHARTIARTL.NS",
    "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ITC.NS",
    "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS",
    "M&M.NS", "MARUTI.NS", "NESTLEIND.NS", "NTPC.NS", "ONGC.NS",
    "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS", "SHREECEM.NS",
    "SUNPHARMA.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TCS.NS", "TECHM.NS",
    "TITAN.NS", "ULTRACEMCO.NS", "UPL.NS", "WIPRO.NS"
]

def send_telegram_message(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=payload)
    else:
        print("Missing Telegram credentials")

def analyze_stock(ticker):
    try:
        df = yf.download(ticker, period="5d", interval="15m")
        if df.empty or len(df) < 35:
            return None

        df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        delta = df['Close'].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(window=14).mean()
        avg_loss = pd.Series(loss).rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))

        df['ADX'] = df['High'].rolling(window=14).max() - df['Low'].rolling(window=14).min()
        df['ADX'] = df['ADX'].rolling(window=14).mean()

        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['stddev'] = df['Close'].rolling(window=20).std()
        df['UpperBand'] = df['MA20'] + (2 * df['stddev'])
        df['LowerBand'] = df['MA20'] - (2 * df['stddev'])

        latest = df.iloc[-1]

        strong_buy = (
            latest['RSI'] < 30 and
            latest['MACD'] > latest['Signal'] and
            latest['Close'] < latest['LowerBand'] and
            latest['EMA12'] > latest['EMA26'] and
            latest['ADX'] > 20
        )

        strong_sell = (
            latest['RSI'] > 70 and
            latest['MACD'] < latest['Signal'] and
            latest['Close'] > latest['UpperBand'] and
            latest['EMA12'] < latest['EMA26'] and
            latest['ADX'] > 20
        )

        if strong_buy:
            return f"📈 STRONG BUY: {ticker} at ₹{latest['Close']:.2f}"
        elif strong_sell:
            return f"📉 STRONG SELL: {ticker} at ₹{latest['Close']:.2f}"
        else:
            return None
    except Exception as e:
        return None

def run_analysis():
    messages = []
    for ticker in nifty50_tickers:
        result = analyze_stock(ticker)
        if result:
            messages.append(result)
        time.sleep(1)  # avoid rate limits

    if messages:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_message = f"🕒 {timestamp} - Intraday Signals\n\n" + "\n".join(messages)
    else:
        full_message = f"🕒 {datetime.now().strftime('%H:%M:%S')} - No strong signals found now."

    send_telegram_message(full_message)

if __name__ == "__main__":
    run_analysis()
