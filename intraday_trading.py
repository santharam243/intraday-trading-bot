import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Telegram bot token or chat id environment variables not set.")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram send error: {e}")

def add_indicators(df):
    # Make sure index is sorted and continuous for intraday data
    df = df.sort_index()
    
    # EMA 12 and EMA 26
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()

    # Align before subtracting to avoid misalignment error
    df['EMA12'], df['EMA26'] = df['EMA12'].align(df['EMA26'], join='inner')

    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # RSI Calculation
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD20'] = df['Close'].rolling(window=20).std()
    # Align before adding/subtracting
    df['MA20'], df['STD20'] = df['MA20'].align(df['STD20'], join='inner')
    df['BB_Upper'] = df['MA20'] + (df['STD20'] * 2)
    df['BB_Lower'] = df['MA20'] - (df['STD20'] * 2)

    # Volume spike
    df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
    df['Vol_Spike'] = df['Volume'] > 1.5 * df['Vol_MA20']

    return df

def get_signal(df):
    if len(df) < 30:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    buy_cond = (
        (last['MACD'] > last['MACD_Signal']) and
        (prev['MACD'] <= prev['MACD_Signal']) and
        (last['RSI'] > 50) and
        (last['Close'] > last['EMA12']) and
        (last['Close'] > last['MA20']) and
        (last['Vol_Spike']) and
        (last['Close'] < last['BB_Upper'])
    )

    sell_cond = (
        (last['MACD'] < last['MACD_Signal']) and
        (prev['MACD'] >= prev['MACD_Signal']) and
        (last['RSI'] < 50) and
        (last['Close'] < last['EMA12']) and
        (last['Close'] < last['MA20']) and
        (last['Vol_Spike']) and
        (last['Close'] > last['BB_Lower'])
    )

    if buy_cond:
        return 'STRONG BUY'
    elif sell_cond:
        return 'STRONG SELL'
    else:
        return None

def scan_stocks(stock_list):
    signals = []
    for ticker in stock_list:
        ticker = ticker.strip()
        if not ticker:
            continue

        try:
            df = yf.download(ticker, period="5d", interval="15m", progress=False, auto_adjust=True)
            if df.empty:
                print(f"No data for {ticker}")
                continue

            df = add_indicators(df)

            # Drop rows with NaNs after indicators calculation
            df.dropna(inplace=True)

            if df.empty:
                print(f"Not enough data after processing for {ticker}")
                continue

            signal = get_signal(df)
            if signal:
                signals.append((ticker, signal))
                print(f"{ticker}: {signal}")
            else:
                print(f"{ticker}: No strong signal")

        except Exception as e:
            print(f"Error checking {ticker}: {e}")

    return signals

if __name__ == "__main__":
    with open("stocks.txt", "r") as f:
        stocks = f.readlines()

    signals = scan_stocks(stocks)

    if signals:
        message = "*Strong Buy/Sell Signals*\n"
        message += "\n".join([f"{t}: {s}" for t, s in signals])
        message += f"\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(message)
    else:
        print("No strong signals found now.")
