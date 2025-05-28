import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
import os

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Telegram bot token or chat id environment variables not set.")

# Send message to telegram bot
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram send error: {e}")

# Calculate indicators
def add_indicators(df):
    # EMA (12 and 26)
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()

    # MACD and Signal line
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # RSI
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
    df['BB_Upper'] = df['MA20'] + (df['STD20'] * 2)
    df['BB_Lower'] = df['MA20'] - (df['STD20'] * 2)

    # Volume spike (Volume > 1.5 * 20-period average volume)
    df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
    df['Vol_Spike'] = df['Volume'] > 1.5 * df['Vol_MA20']

    return df

# Generate strong buy/sell signal
def get_signal(df):
    # We consider only the last candle
    if len(df) < 30:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Strong Buy Conditions:
    buy_cond = (
        (last['MACD'] > last['MACD_Signal']) and
        (prev['MACD'] <= prev['MACD_Signal']) and  # MACD crossover up
        (last['RSI'] > 50) and                     # Momentum strong
        (last['Close'] > last['EMA12']) and        # Price above short EMA
        (last['Close'] > last['MA20']) and         # Above 20MA
        (last['Vol_Spike']) and                     # Volume spike
        (last['Close'] < last['BB_Upper'])         # Not overbought in BB
    )

    # Strong Sell Conditions:
    sell_cond = (
        (last['MACD'] < last['MACD_Signal']) and
        (prev['MACD'] >= prev['MACD_Signal']) and  # MACD crossover down
        (last['RSI'] < 50) and                      # Momentum weak
        (last['Close'] < last['EMA12']) and         # Price below short EMA
        (last['Close'] < last['MA20']) and          # Below 20MA
        (last['Vol_Spike']) and                      # Volume spike
        (last['Close'] > last['BB_Lower'])          # Not oversold in BB
    )

    if buy_cond:
        return 'STRONG BUY'
    elif sell_cond:
        return 'STRONG SELL'
    else:
        return None

# Main scanning function
def scan_stocks(stock_list):
    signals = []
    for ticker in stock_list:
        ticker = ticker.strip()
        if not ticker:
            continue

        try:
            # Fetch 15 min intraday data for last 5 days
            df = yf.download(ticker, period="5d", interval="15m", progress=False)
            if df.empty:
                print(f"No data for {ticker}")
                continue

            df = add_indicators(df)

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
    # Read stocks from file
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
