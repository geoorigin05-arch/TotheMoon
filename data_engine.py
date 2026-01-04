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
def scan_universe(universe, limit=10):
    results = []
    for sym in universe:
        df = fetch_price_latest(sym)  # 60 hari → cepat
        if df is None or df.empty:
            continue
        last = df.iloc[-1]
        close = float(last["Close"])
        ma200 = float(last.get("MA200", close))
        rsi = float(last.get("RSI", 50))
        support = float(last.get("Support", close*0.95))
        resistance = float(last.get("Resistance", close*1.05))
        trend_score = close / ma200 if ma200 != 0 else 1
        momentum = close - df["Close"].iloc[-2] if len(df)>=2 else 0

        results.append({
            "Symbol": sym,
            "Close": close,
            "RSI": rsi,
            "TrendScore": trend_score,
            "Momentum": momentum,
            "Support": support,
            "Resistance": resistance
        })

    df_result = pd.DataFrame(results)
    df_result = df_result.sort_values("TrendScore", ascending=False).head(limit)
    return df_result

