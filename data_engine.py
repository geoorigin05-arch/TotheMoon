import yfinance as yf
import pandas as pd
import numpy as np

def fetch_price(symbol, period="1y"):
    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
    if df.empty or len(df) < 210:
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

    return df.dropna()

def scan_universe(symbols, limit=15):
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

        if close > ma50 and ma50 > ma200 and rsi < 70:
            results.append({
                "Symbol": s,
                "Close": close,
                "RSI": rsi,
                "TrendScore": (ma50 / ma200)
            })

        if len(results) >= limit:
            break

    return pd.DataFrame(results)
