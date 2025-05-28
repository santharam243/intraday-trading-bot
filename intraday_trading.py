import os
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- Technical indicators functions ---

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def compute_adx(df, period=14):
    high = df['High']
    low = df['Low']
    close = df['Close']

    plus_dm = high.diff()
    minus_dm = low.diff().abs()

    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period).mean()

    plus_di = 100 * (pd.Series(plus_dm).rolling(window=period).sum() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(window=period).sum() / atr)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=period).mean()

    return adx

# --- Fetch Nifty 50 tickers dynamically ---
def get_nifty50_tickers():
    url = 'https://en.wikipedia.org/wiki/NIFTY_50'
    tables = pd.read_html(url)
    df = tables[1]  # The table with ticker symbols
    tickers = df['Symbol'].tolist()
    tickers = [t + '.NS' for t in tickers]
    return tickers

# --- Telegram message sender ---
def send_telegram_message(bot_token, chat_id, message):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Failed to send Telegram message: {response.text}")

# --- Analyze single stock for signals ---
def analyze_stock(ticker):
    try:
        df = yf.download(ticker, period='5d', interval='15m', progress=False)
        if df.empty or len(df) < 50:
            return None

        close = df['Close']

        rsi = compute_rsi(close)
        macd, signal_line, _ = compute_macd(close)
        adx = compute_adx(df)

        # Latest values
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd.iloc[-1]
        latest_signal = signal_line.iloc[-1]
        latest_adx = adx.iloc[-1]

        if np.isnan([latest_rsi, latest_macd, latest_signal, latest_adx]).any():
            return None

        # Strong Buy condition
        if (latest_rsi < 30) and (latest_macd > latest_signal) and (latest_adx > 20):
            return f"📈 *Strong BUY* signal for {ticker.replace('.NS','')} (RSI: {latest_rsi:.2f}, MACD: {latest_macd:.4f}, ADX: {latest_adx:.2f})"

        # Strong Sell condition
        if (latest_rsi > 70) and (latest_macd < latest_signal) and (latest_adx > 20):
            return f"📉 *Strong SELL* signal for {ticker.replace('.NS','')} (RSI: {latest_rsi:.2f}, MACD: {latest_macd:.4f}, ADX: {latest_adx:.2f})"

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
    return None

def main():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        print("Telegram bot token or chat ID not found in environment variables.")
        return

    tickers = get_nifty50_tickers()
    print(f"Analyzing {len(tickers)} stocks...")

    messages = []
    for ticker in tickers:
        signal = analyze_stock(ticker)
        if signal:
            messages.append(signal)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    if messages:
        message = f"📊 *Nifty 50 Intraday Trading Signals* @ {timestamp}\n\n" + "\n".join(messages)
    else:
        message = f"📊 No strong signals found @ {timestamp}"

    print(message)
    send_telegram_message(bot_token, chat_id, message)

if __name__ == '__main__':
    main()
