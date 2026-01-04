import yfinance as yf
import pandas as pd

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def fetch_price(symbol: str) -> pd.DataFrame:
    df = yf.download(symbol, period="1y", interval="1d", progress=False)
    if df.empty:
        return None
    df.reset_index(inplace=True)
    df["MA200"] = df["Close"].rolling(200).mean()
    df["RSI"] = compute_rsi(df["Close"])
    df["Support"] = df["Close"].rolling(20).min()
    df["Resistance"] = df["Close"].rolling(20).max()
    return df

def fetch_price_latest(symbol: str) -> pd.DataFrame:
    df = yf.download(symbol, period="60d", interval="1d", progress=False)
    if df.empty:
        return None
    df.reset_index(inplace=True)
    df["MA200"] = df["Close"].rolling(200).mean()
    df["RSI"] = compute_rsi(df["Close"])
    df["Support"] = df["Close"].rolling(20).min()
    df["Resistance"] = df["Close"].rolling(20).max()
    return df

def scan_universe(symbol_list, limit=10):
    result = []
    for sym in symbol_list[:limit]:
        df = fetch_price(sym)
        if df is None or df.empty:
            continue
        last = df.iloc[-1]
        result.append({
            "Symbol": sym,
            "Close": last["Close"],
            "RSI": last["RSI"],
            "TrendScore": last["Close"] / last["MA200"] if last["MA200"] else 0,
            "Momentum": last["Close"] - df["Close"].iloc[-5],
            "Score": 0,  # nanti di-rank
            "Grade": "A"   # placeholder
        })
    return pd.DataFrame(result)
