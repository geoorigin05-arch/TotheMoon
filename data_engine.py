import yfinance as yf
import pandas as pd

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
    return rsi

# ===============================
# Fetch full historical price (untuk scan universe)
# ===============================
def fetch_price(symbol: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df["MA200"] = df["Close"].rolling(200).mean()
        df["RSI"] = compute_rsi(df["Close"])
        df["Support"] = df["Close"].rolling(20).min()
        df["Resistance"] = df["Close"].rolling(20).max()
        return df
    except Exception as e:
        print("fetch_price error:", e)
        return None

# ===============================
# Fetch latest price (ringan) untuk manual input
# ===============================
def fetch_price_latest(symbol: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, period="60d", interval="1d", progress=False)
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df["MA200"] = df["Close"].rolling(200).mean()
        df["RSI"] = compute_rsi(df["Close"])
        df["Support"] = df["Close"].rolling(20).min()
        df["Resistance"] = df["Close"].rolling(20).max()
        return df
    except Exception as e:
        print("fetch_price_latest error:", e)
        return None

# ===============================
# Scan Top N saham
# ===============================
def scan_universe(symbol_list, limit=10):
    result = []
    for sym in symbol_list[:limit]:
        df = fetch_price(sym)
        if df is None or df.empty:
            continue
        last = df.iloc[-1]
        if pd.isna(last["MA200"]):
            continue
        result.append({
            "Symbol": sym,
            "Close": last["Close"],
            "RSI": last["RSI"],
            "TrendScore": last["Close"]/last["MA200"],
            "Momentum": last["Close"]-df["Close"].iloc[-5] if len(df)>=5 else 0,
            "Score": 0,  # placeholder
            "Grade": "A"  # placeholder
        })
    return pd.DataFrame(result)
