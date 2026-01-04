def fetch_price(symbol, period="1y"):
    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)

    if df is None or df.empty or len(df) < 210:
        return None

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Support"] = df["Low"].rolling(20).min()
    df["Resistance"] = df["High"].rolling(20).max()

    df = df.dropna()

    if df.empty:
        return None

    return df
