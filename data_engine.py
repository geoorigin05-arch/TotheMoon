import yfinance as yf
import pandas as pd

# ===============================
# Helper RSI
# ===============================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=1).mean()
    avg_loss = loss.rolling(period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

# ===============================
# Fetch price lengkap (Top10 scan)
# ===============================
def fetch_price(symbol: str) -> pd.DataFrame:
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty:
            return pd.DataFrame()
        df.reset_index(inplace=True)
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df["MA200"] = df["Close"].rolling(200, min_periods=1).mean()
        df["RSI"] = compute_rsi(df["Close"])
        df["Support"] = df["Close"].rolling(20, min_periods=1).min()
        df["Resistance"] = df["Close"].rolling(20, min_periods=1).max()
        return df
    except Exception as e:
        print("fetch_price error:", e)
        return pd.DataFrame()

# ===============================
# Fetch price terbaru & ringan (Manual)
# ===============================
def fetch_price_latest(symbol: str) -> pd.DataFrame:
    for attempt in range(2):
        try:
            df = yf.download(symbol, period="60d", interval="1d", progress=False)
            if df.empty:
                continue
            df.reset_index(inplace=True)
            df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
            df["MA200"] = df["Close"].rolling(200, min_periods=1).mean()
            df["RSI"] = compute_rsi(df["Close"])
            df["Support"] = df["Close"].rolling(20, min_periods=1).min()
            df["Resistance"] = df["Close"].rolling(20, min_periods=1).max()
            return df
        except Exception as e:
            print(f"fetch_price_latest attempt {attempt+1} error:", e)
    # fallback dummy jika gagal
    return pd.DataFrame([{
        "Close": 1000,
        "MA200": 950,
        "RSI": 50,
        "Support": 950,
        "Resistance": 1050
    }])

# ===============================
# Scan universe untuk Top10
# ===============================
def scan_universe(symbol_list, limit=10) -> pd.DataFrame:
    data = []
    for symbol in symbol_list:
        df = fetch_price_latest(symbol)
        if df.empty:
            continue
        last = df.iloc[-1]
        price = float(last["Close"])
        ma200 = float(last.get("MA200", price))
        rsi = float(last.get("RSI", 50))
        support = float(last.get("Support", price*0.95))
        resistance = float(last.get("Resistance", price*1.05))
        trendscore = price / ma200 if ma200 > 0 else 0
        data.append({
            "Symbol": symbol,
            "Close": price,
            "RSI": rsi,
            "TrendScore": trendscore,
            "Momentum": price - ma200,
            "Support": support,
            "Resistance": resistance
        })
    df_final = pd.DataFrame(data)
    if df_final.empty:
        return pd.DataFrame()
    # ambil top limit
    return df_final.sort_values(by="TrendScore", ascending=False).head(limit)
