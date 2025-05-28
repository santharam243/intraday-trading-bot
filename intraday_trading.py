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

        # Check if any indicator is NaN
        if any(np.isnan([latest_rsi, latest_macd, latest_signal, prev_macd, prev_signal, latest_stoch_k, latest_stoch_d])):
            return None

        # Confirm MACD crossover up (from below to above signal line)
        macd_cross_up = (prev_macd < prev_signal) and (latest_macd > latest_signal)
        # Confirm MACD crossover down (from above to below signal line)
        macd_cross_down = (prev_macd > prev_signal) and (latest_macd < latest_signal)

        # Buy conditions: MACD crossover up + RSI below 40 + Stochastic K above D + volume > 0
        if macd_cross_up and latest_rsi < 40 and latest_stoch_k > latest_stoch_d and latest_volume > 0:
            return f"📈 *BUY* signal for {ticker.replace('.NS','')} (RSI: {latest_rsi:.2f}, MACD: {latest_macd:.4f}, Stoch: {latest_stoch_k:.2f})"

        # Sell conditions: MACD crossover down + RSI above 60 + Stochastic K below D + volume > 0
        if macd_cross_down and latest_rsi > 60 and latest_stoch_k < latest_stoch_d and latest_volume > 0:
            return f"📉 *SELL* signal for {ticker.replace('.NS','')} (RSI: {latest_rsi:.2f}, MACD: {latest_macd:.4f}, Stoch: {latest_stoch_k:.2f})"

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")

    return None
