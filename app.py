import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ======================================================
# PAGE
# ======================================================
st.set_page_config(page_title="IDX Professional Trading System", layout="wide")
st.title("📊 IDX Professional Trading System")
st.caption("Decision Support • Technical • Risk Managed")

# ======================================================
# 🔥 AUTO IDX UNIVERSE (INFO ONLY - DI ATAS)
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
    df = yf.download(ticker, period="1y", progress=False)
    if df.empty or len(df) < 200:
        return None

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    last = df.iloc[-1]

    bullish = (
        last["Close"] > last["MA50"] and
        last["MA50"] > last["MA200"]
    )

    return {
        "ticker": ticker,
        "price": last["Close"],
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
            f"Alasan: Trend naik jangka menengah"
        )
else:
    st.info("Belum ada saham IDX yang memenuhi kriteria strong trend hari ini")

st.divider()

# ======================================================
# 🎯 MAIN ANALYSIS (TETAP PAKE LOGIKA INPUT)
# ======================================================
st.sidebar.header("⚙️ Analisa Saham")
symbol = st.sidebar.text_input("Kode Saham (.JK)", "BBCA.JK")
modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=1_000_000)
risk_pct = st.sidebar.slider("Risk (%)", 1, 10, 2)

df = yf.download(symbol, period="1y", progress=False)

if df.empty or len(df) < 200:
    st.error("❌ Data tidak cukup untuk analisa")
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

# ======================================================
# SUPPORT RESISTANCE
# ======================================================
support = float(df["Low"].rolling(20).min().iloc[-1])
resistance = float(df["High"].rolling(20).max().iloc[-1])

# ======================================================
# DECISION LOGIC (PRO)
# ======================================================
reasons_buy = []
reasons_sell = []
reasons_wait = []

if price > last["MA50"] > last["MA200"]:
    reasons_buy.append("Trend naik (MA50 > MA200)")
else:
    reasons_wait.append("Trend belum jelas")

if last["RSI"] < 70:
    reasons_buy.append("RSI masih sehat")
else:
    reasons_sell.append("RSI overbought")

if price < support * 1.02:
    reasons_buy.append("Harga dekat support")

if price > resistance * 0.98:
    reasons_sell.append("Harga dekat resistance")

# ======================================================
# FINAL DECISION
# ======================================================
if len(reasons_buy) >= 3:
    decision = "BUY"
elif len(reasons_sell) >= 2:
    decision = "SELL"
else:
    decision = "WAIT"

# ======================================================
# OUTPUT
# ======================================================
st.subheader(f"📌 Decision: **{decision}**")

col1, col2, col3 = st.columns(3)
col1.metric("Harga", f"{int(price):,}")
col2.metric("RSI", f"{last['RSI']:.1f}")
col3.metric("Trend", "BULLISH" if price > last["MA200"] else "BEARISH")

st.divider()

st.subheader("🧠 Alasan Keputusan")

if decision == "BUY":
    for r in reasons_buy:
        st.success(r)

elif decision == "SELL":
    for r in reasons_sell:
        st.error(r)

else:
    for r in reasons_wait:
        st.info(r)

# ======================================================
# RISK MANAGEMENT
# ======================================================
risk_amount = modal * (risk_pct / 100)
risk_per_share = max(price - support, 1)
max_lot = int(risk_amount / risk_per_share / 100)

st.divider()
st.subheader("📉 Risk Management")
st.metric("Stop Loss", f"{int(support):,}")
st.metric("Max Lot", f"{max_lot:,}")

st.caption("System ini hanya memberikan decision support, bukan rekomendasi mutlak.")
