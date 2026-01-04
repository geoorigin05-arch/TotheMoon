import yfinance as yf
import pandas as pd

# ===============================
# Fungsi existing
# ===============================
def fetch_price(symbol: str) -> pd.DataFrame:
    """
    Fetch historical price data lengkap (untuk scan universe)
    """
    try:
        df = yf.download(symbol, period="1y", interval="1d")
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df.rename(columns={"Close": "Close"}, inplace=True)

        # Hitung indikator
        df["MA200"] = df["Close"].rolling(200).mean()
        df["RSI"] = compute_rsi(df["Close"])
        df["Support"] = df["Close"].rolling(20).min()
        df["Resistance"] = df["Close"].rolling(20).max()
        return df
    except Exception as e:
        print("fetch_price error:", e)
        return None

# ===============================
# Fungsi baru untuk manual/live input
# ===============================
def fetch_price_latest(symbol: str) -> pd.DataFrame:
    """
    Fetch harga terbaru + indikator cepat (ringan)
    """
    try:
        df = yf.download(symbol, period="60d", interval="1d")  # data lebih pendek → cepat
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df.rename(columns={"Close": "Close"}, inplace=True)

        # indikator ringan
        df["MA200"] = df["Close"].rolling(200).mean()
        df["RSI"] = compute_rsi(df["Close"])
        df["Support"] = df["Close"].rolling(20).min()
        df["Resistance"] = df["Close"].rolling(20).max()
        return df
    except Exception as e:
        print("fetch_price_latest error:", e)
        return None

# ===============================
# Fungsi RSI helper
# ===============================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta>0,0.0)
    loss = -delta.where(delta<0,0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100/(1+rs))
    return rsi
