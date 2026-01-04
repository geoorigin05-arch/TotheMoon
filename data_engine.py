import yfinance as yf
import pandas as pd
import numpy as np

def fetch_price(symbol, period="1y"):
    """
    Fetch historical price data with indicators.
    Returns None jika data kosong / error.
    """
    try:
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)

        if df is None or df.empty:
            return None
        if "Close" not in df.columns:
            return None

        # Indicators
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

    except Exception as e:
        print(f"⚠️ Fetch error {symbol}: {e}")
        return None

def scan_universe(symbols, limit=50):
    """
    Scan IDX universe and return top candidates.
    """
    results = []

    for s in symbols:
        df = fetch_price(s)
        if df is None:
            continue

        last = df.iloc[-1]
        close = float(last["Close"])
        ma50 = float(last["MA50"])
        ma200 = float(last["MA200"])
        rsi = float(last["RSI"])

        # Trend bullish filter, RSI flexible
        if ma50 > ma200:
            trend_score = ma50 / ma200
            momentum = (close - ma50) / ma50
            results.append({
                "Symbol": s,
                "Close": close,
                "RSI": rsi,
                "TrendScore": trend_score,
                "Momentum": momentum
            })

    return pd.DataFrame(results)
