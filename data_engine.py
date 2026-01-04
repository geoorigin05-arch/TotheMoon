import yfinance as yf
import pandas as pd
import numpy as np

# ===============================
# Helper RSI
# ===============================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

# ===============================
# Fetch harga lengkap (scan universe)
# ===============================
def fetch_price(symbol: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df.rename(columns={"Close": "Close"}, inplace=True)
        df["MA200"] = df["Close"].rolling(200).mean()
        df["RSI"] = compute_rsi(df["Close"])
        df["Support"] = df["Close"].rolling(20).min()
        df["Resistance"] = df["Close"].rolling(20).max()
        return df
    except:
        return None

# ===============================
# Fetch harga ringan (manual input)
# ===============================
def fetch_price_latest(symbol: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, period="90d", interval="1d", progress=False)
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df["MA200"] = df["Close"].rolling(200).mean()
        df["RSI"] = compute_rsi(df["Close"])
        df["Support"] = df["Close"].rolling(20).min()
        df["Resistance"] = df["Close"].rolling(20).max()
        return df
    except:
        return None

# ===============================
# Scan Universe Top N dengan fallback
# ===============================
def scan_universe(idx_list, limit=10):
    records = []
    for symbol in idx_list:
        df = fetch_price_latest(symbol)
        if df is None or df.empty:
            continue
        last = df.iloc[-1]

        price = float(last["Close"]) if pd.notna(last["Close"]) else None
        ma200 = float(last["MA200"]) if pd.notna(last["MA200"]) else price
        rsi = float(last["RSI"]) if pd.notna(last["RSI"]) else 50
        support = float(last.get("Support", price*0.95))
        resistance = float(last.get("Resistance", price*1.05))

        if price is None:
            continue

        trendscore = price/ma200 if ma200 else 0
        momentum = price - ma200 if ma200 else 0

        records.append({
            "Symbol": symbol,
            "Close": price,
            "MA200": ma200,
            "RSI": rsi,
            "Support": support,
            "Resistance": resistance,
            "TrendScore": trendscore,
            "Momentum": momentum
        })

    df_scan = pd.DataFrame(records)
    df_scan = df_scan.sort_values("TrendScore", ascending=False).head(limit)
    return df_scan
