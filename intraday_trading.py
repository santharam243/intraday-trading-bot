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
        'SBILIFE.NS', 'BAJAJFINSV.NS', 'INDUSINDBK.NS', 'CIPLA.NS',
        'HINDALCO.NS', 'BRITANNIA.NS', 'SHREECEM.NS'
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

def compute_stochastic_oscillator(df, k_period=14, d_period=3):
    low_min = df['Low'].rolling(window=k_period).min()
    high_max = df['High'].rolling(window=k_period).max()
    stoch_k = 100 * ((df['Close'] - low_min) / (high_max - low_min))
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return stoch_k, stoch_d

def analyze_stock(ticker):
    try:
        df = yf.download(ticker, period='5d', interval='15m', progress=False)
        if df.empty or len(df) < 50:
            return None

        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()

        rsi = compute_rsi(close)
        macd, signal_line, _ = compute_macd(close)
        stoch_k, stoch_d = compute_stochastic_oscillator(df)

        latest_rsi = float(rsi.iloc[-1])
        latest_macd = float(macd.iloc[-1])
        latest_signal = float(signal_line.iloc[-1])
        prev_macd = float(macd.iloc[-2])
        prev_signal = float(signal_line.iloc[-2])
        latest_stoch_k = float(stoch_k.iloc[-1])
        latest_stoch_d = float(stoch_d.iloc[-1])
        latest_volume = float(volume.iloc[-1])

        # Check for NaNs in indicators
        if any(np.isnan([latest_rsi, latest_macd, latest_signal, prev_macd, prev_signal, latest_stoch_k, latest_stoch_d])):
            return None

        # MACD cross up
        macd_cross_up = (prev_macd < prev_signal) and (latest_macd > latest_signal)
        # MACD cross down
        macd_cross_down = (prev_macd > prev_signal) and (latest_macd < latest_signal)

        # Buy signal
        if macd_cross_up and latest_rsi < 40 and latest_stoch_k > latest_stoch_d and latest_volume > 0:
            return f"📈 *BUY* signal for {ticker.replace('.NS','')} (RSI: {latest_rsi:.2f}, MACD: {latest_macd:.4f}, Stoch: {latest_stoch_k:.2f})"

        # Sell signal
        if macd_cross_down and latest_rsi > 60 and latest_stoch_k < latest_stoch_d and latest_volume > 0:
            return f"📉 *SELL* signal for {ticker.replace('.NS','')} (RSI: {latest_rsi:.2f}, MACD: {latest_macd:.4f}, Stoch: {latest_stoch_k:.2f})"

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
    now_ist = datetime.now(ist).strftime('%-d %b %Y %I:%M %p').lower()
    if signals:
        message = f"📊 *Intraday Trading Signals* @ {now_ist}\n\n" + "\n".join(signals)
    else:
        message = f"📊 No strong signals @ {now_ist}"

    send_telegram_message(message)
    print(message)

if __name__ == '__main__':
    main()
