import yfinance as yf
import pandas as pd
import numpy as np
import time
import requests
import os
from datetime import datetime

# Fetch Telegram credentials from GitHub Actions Secrets
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_nifty50_tickers():
    return [
        'ADANIPORTS.NS', 'ASIANPAINT.NS', 'AXISBANK.NS', 'BAJAJ-AUTO.NS', 'BAJFINANCE.NS',
        'BAJAJFINSV.NS', 'BPCL.NS', 'BHARTIARTL.NS', 'BRITANNIA.NS', 'CIPLA.NS',
        'COALINDIA.NS', 'DIVISLAB.NS', 'DRREDDY.NS', 'EICHERMOT.NS', 'GRASIM.NS',
        'HCLTECH.NS', 'HDFCBANK.NS', 'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS',
        'HINDUNILVR.NS', 'ICICIBANK.NS', 'ITC.NS', 'INDUSINDBK.NS', 'INFY.NS',
        'JSWSTEEL.NS', 'KOTAKBANK.NS', 'LT.NS', 'M&M.NS', 'MARUTI.NS',
        'NESTLEIND.NS', 'NTPC.NS', 'ONGC.NS', 'POWERGRID.NS', 'RELIANCE.NS',
        'SBILIFE.NS', 'SBIN.NS', 'SHREECEM.NS', 'SUNPHARMA.NS', 'TATAMOTORS.NS',
        'TATASTEEL.NS', 'TCS.NS', 'TECHM.NS', 'TITAN.NS', 'ULTRACEMCO.NS',
        'UPL.NS', 'WIPRO.NS'
    ]

def calculate_indicators(df):
    df['EMA12'] = df['Close'].ewm(span=12).mean()
    df['EMA26'] = df['Close'].ewm(span=26).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    delta = df['Close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['UpperBand'] = df['MA20'] + (2 * df['STD'])
    df['LowerBand'] = df['MA20'] - (2 * df['STD'])
    df['ADX'] = calculate_adx(df)
    return df

def calculate_adx(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    plus_dm = high.diff()
    minus_dm = low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift()))
    tr3 = pd.DataFrame(abs(low - close.shift()))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = abs(100 * (minus_dm.rolling(window=period).mean() / atr))
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()
    return adx

def analyze_stock(ticker):
    try:
        df = yf.download(ticker, period='5d', interval='15m')
        if df.empty or len(df) < 50:
            return None
        df = calculate_indicators(df)
        latest = df.iloc[-1]

        # Score system
        score = 0
        if latest['RSI'] < 40: score += 1
        if latest['MACD'] > latest['Signal']: score += 1
        if latest['EMA12'] > latest['EMA26']: score += 1
        if latest['Close'] < latest['LowerBand']: score += 1
        if latest['ADX'] > 20: score += 1

        # Debug print
        print(f"[{ticker}] Score: {score} | RSI: {latest['RSI']:.2f}, MACD: {latest['MACD']:.2f}, Signal: {latest['Signal']:.2f}, EMA12: {latest['EMA12']:.2f}, EMA26: {latest['EMA26']:.2f}, Close: {latest['Close']:.2f}, LBand: {latest['LowerBand']:.2f}, ADX: {latest['ADX']:.2f}")

        if score >= 4:
            return f"📈 Strong BUY: {ticker} (Score: {score}/5)"
        elif score <= 1:
            return f"📉 Strong SELL: {ticker} (Score: {score}/5)"
        else:
            return None
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials not set.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload)
        print(f"Telegram: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Telegram send error: {e}")

def main():
    tickers = get_nifty50_tickers()
    signals = []

    for ticker in tickers:
        signal = analyze_stock(ticker)
        if signal:
            signals.append(signal)

    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    if signals:
        message = f"📊 Signals @ {now}:\n\n" + "\n".join(signals)
    else:
        message = f"📊 No strong signals @ {now}"

    send_telegram_message(message)

# Run every 15 minutes
if __name__ == "__main__":
    main()
