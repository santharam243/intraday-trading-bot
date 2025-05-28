import os
import requests
import numpy as np
import yfinance as yf
from datetime import datetime
import pytz

# Get Telegram bot info from env (GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send message: {e}")

def get_nifty_50_tickers():
    # Hardcoded current Nifty 50 tickers with NSE suffix for Yahoo Finance
    return [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'KOTAKBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS',
        'LT.NS', 'AXISBANK.NS', 'ITI.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS',
        'MARUTI.NS', 'SUNPHARMA.NS', 'DIVISLAB.NS', 'TITAN.NS', 'ULTRACEMCO.NS',
        'NESTLEIND.NS', 'DRREDDY.NS', 'M&M.NS', 'TECHM.NS', 'POWERGRID.NS',
        'ONGC.NS', 'TATASTEEL.NS', 'HCLTECH.NS', 'WIPRO.NS', 'JSWSTEEL.NS',
        'COALINDIA.NS', 'GRASIM.NS', 'BPCL.NS', 'BAJAJ-AUTO.NS', 'ADANIPORTS.NS',
        'HDFCLIFE.NS', 'HEROMOTOCO.NS', 'TATAMOTORS.NS', 'EICHERMOT.NS',
        'SBILIFE.NS', 'BAJAJFINSV.NS', 'INDUSINDBK.NS', 'TECHM.NS', 'CIPLA.NS',
        'HINDALCO.NS', 'BRITANNIA.NS', 'SHREECEM.NS', 'JSWSTEEL.NS', 'ULTRACEMCO.NS'
    ]

def compute_rsi(series, period=14):
    series = series.squeeze()
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series, fast=12, slow=26, signal=9):
    series = series.squeeze()
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def analyze_stock(ticker):
    try:
        df = yf.download(ticker, period='5d', interval='15m', progress=False)
        if df.empty or len(df) < 50:
            return None

        close = df['Close'].squeeze()

        rsi = compute_rsi(close)
        macd, signal_line, _ = compute_macd(close)
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd.iloc[-1]
        latest_signal = signal_line.iloc[-1]

        # Skip if any nan values in latest indicators
        if np.isnan([latest_rsi, latest_macd, latest_signal]).any():
            return None

        # Loosened Strong Buy signal conditions
        # RSI less than 40, MACD close to crossover (macd just crossed or about to cross signal)
        if (latest_rsi < 40) and (latest_macd >= latest_signal - 0.0005):
            return f"📈 *BUY* signal for {ticker.replace('.NS','')} (RSI: {latest_rsi:.2f}, MACD: {latest_macd:.4f})"

        # Loosened Strong Sell signal conditions
        # RSI greater than 60, MACD close to crossover down (macd just below or about to cross below signal)
        if (latest_rsi > 60) and (latest_macd <= latest_signal + 0.0005):
            return f"📉 *SELL* signal for {ticker.replace('.NS','')} (RSI: {latest_rsi:.2f}, MACD: {latest_macd:.4f})"

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")

    return None

      

def main():
    tickers = get_nifty_50_tickers()
    signals = []

    for ticker in tickers:
        signal = analyze_stock(ticker)
        if signal:
            signals.append(signal)

    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist).strftime('%Y-%m-%d %H:%M')
    if signals:
        message = f"📊 *Intraday Trading Signals* @ {now_ist}\n\n" + "\n".join(signals)
    else:
        message = f"📊 No strong signals @ {now_ist}"

    send_telegram_message(message)
    print(message)

if __name__ == '__main__':
    main()
