import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ======================================================
# PAGE
# ======================================================
st.set_page_config(page_title="IDX Professional Trading System", layout="wide")
st.title("📊 IDX Professional Trading System")
st.caption("Market Insight (Auto IDX) + Decision Support (Input Saham)")

# ======================================================
# 🔥 AUTO IDX UNIVERSE (INFO ONLY)
# ======================================================
@st.cache_data
def load_idx_universe():
    df = pd.read_csv("idx_universe.csv")
    df["listingDate"] = pd.to_datetime(df["listingDate"], errors="coerce")
    df["listing_years"] = (pd.Timestamp.today() - df["listingDate"]).dt.days / 365

    df = df[
        (df["listingBoard"] == "Utama") &
        (df["listing_years"] >= 3) &
        (df["shares"] > 500_000_000)
    ]

    return [f"{c}.JK" for c in df["code"].unique()]

@st.cache_data
def scan_market(ticker):
    df = yf.download(ticker, period="1y", progress=False, auto_adjust=True)

    if df.empty or len(df) < 220:
        return None

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df.dropna(inplace=True)

    if df.empty:
        return None

    last = df.iloc[-1]

    close = float(last["Close"])
    ma50  = float(last["MA50"])
    ma200 = float(last["MA200"])

    bullish = close > ma50 > ma200

    return {
        "ticker": ticker,
        "price": close,
        "bullish": bullish
    }

st.subheader("🔥 Saham Potensial IDX (Auto – Market Insight)")

candidates = []
for t in load_idx_universe():
    r = scan_market(t)
    if r and r["bullish"]:
        candidates.append(r)

if candidates:
    for r in candidates[:3]:
        st.success(
            f"**{r['ticker']}**\n"
            f"Harga: {int(r['price']):,}\n"
            f"Alasan: Trend naik MA50 > MA200"
        )
else:
    st.info("Belum ada saham IDX dengan trend kuat saat ini")

st.divider()

# ======================================================
# 🎯 MAIN ANALYSIS (SAHAM INPUT)
# ======================================================
st.sidebar.header("⚙️ Analisa Saham")
symbol = st.sidebar.text_input("Kode Saham (.JK)", "BBCA.JK")
modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=1_000_000)
risk_pct = st.sidebar.slider("Risk (%)", 1, 10, 2)

df = yf.download(symbol, period="1y", progress=False, auto_adjust=True)

if df.empty or len(df) < 220:
    st.error("❌ Data tidak cukup untuk analisa profesional")
    st.stop()

# ======================================================
# INDICATORS
# ======================================================
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()
df["MA200"] = df["Close"].rolling(200).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
rs = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

df.dropna(inplace=True)

last = df.iloc[-1]

price = float(last["Close"])
ma50 = float(last["MA50"])
ma200 = float(last["MA200"])
rsi = float(last["RSI"])

support = float(df["Low"].rolling(20).min().iloc[-1])
resistance = float(df["High"].rolling(20).max().iloc[-1])

# ======================================================
# DECISION LOGIC
# ======================================================
buy, sell, wait = [], [], []

if price > ma50 > ma200:
    buy.append("Trend naik (MA50 > MA200)")
else:
    wait.append("Trend belum konfirmasi")

if rsi < 70:
    buy.append("RSI sehat")
elif rsi > 70:
    sell.append("RSI overbought")

if price <= support * 1.02:
    buy.append("Harga dekat support")

if price >= resistance * 0.98:
    sell.append("Harga dekat resistance")

if len(buy) >= 3:
    decision = "BUY"
elif len(sell) >= 2:
    decision = "SELL"
else:
    decision = "WAIT"

# ======================================================
# OUTPUT
# ======================================================
st.subheader(f"📌 Decision: **{decision}**")

c1, c2, c3 = st.columns(3)
c1.metric("Harga", f"{int(price):,}")
c2.metric("RSI", f"{rsi:.1f}")
c3.metric("Trend", "BULLISH" if price > ma200 else "BEARISH")

st.divider()
st.subheader("🧠 Alasan Keputusan")

if decision == "BUY":
    for r in buy:
        st.success(r)
elif decision == "SELL":
    for r in sell:
        st.error(r)
else:
    for r in wait:
        st.info(r)

# ======================================================
# RISK MANAGEMENT
# ======================================================
risk_amount = modal * (risk_pct / 100)
risk_per_share = max(price - support, 1)
max_lot = int(risk_amount / (risk_per_share * 100))

st.divider()
st.subheader("📉 Risk Management")
st.metric("Stop Loss", f"{int(support):,}")
st.metric("Max Lot", f"{max_lot:,}")

st.caption("Decision support system — bukan rekomendasi mutlak.")
