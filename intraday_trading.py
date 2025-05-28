import os
import requests
import numpy as np
import yfinance as yf
from datetime import datetime
import pytz

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send message: {e}")

def get_nifty_50_tickers():
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
        'HINDALCO.NS', 'BRITANNIA.NS', 'SHREECEM.NS', 'ULTRACEMCO.NS'
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

        latest_rsi = float(rsi.iloc[-1].item()) if not rsi.empty else 0.0
        latest_macd = float(macd.iloc[-1].item()) if not macd.empty else 0.0
        latest_signal = float(signal_line.iloc[-1].item()) if not signal_line.empty else 0.0
        prev_macd = float(macd.iloc[-2].item()) if len(macd) > 1 else 0.0
        prev_signal = float(signal_line.iloc[-2].item()) if len(signal_line) > 1 else 0.0
        latest_stoch_k = float(stoch_k.iloc[-1].item()) if not stoch_k.empty else 0.0
        latest_stoch_d = float(stoch_d.iloc[-1].item()) if not stoch_d.empty else 0.0
        avg_volume = float(volume.rolling(window=20).mean().iloc[-1].item()) if len(volume) >= 20 else 0.0
        latest_volume = float(volume.iloc[-1].item()) if not volume.empty else 0.0

        if any(np.isnan([latest_rsi, latest_macd, late]()
