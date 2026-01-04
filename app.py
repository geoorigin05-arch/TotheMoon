import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Professional Trading System", layout="centered")

st.title("📊 Professional Trading Decision System")
st.caption("Disiplin • Risk Management • Data Driven")

# ======================================================
# TOP 3 POTENTIAL STOCKS (STATIC SAFE)
# ======================================================
st.markdown("### 🔥 Saham Potensial (Likuid & Data Stabil)")
st.markdown("""
- **BBCA.JK** → Tren naik stabil, risiko rendah  
- **BRIS.JK** → Momentum kuat, cocok swing  
- **TLKM.JK** → Support kuat, defensive  

_(Berdasarkan struktur tren & likuiditas IDX)_
""")

st.divider()

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.header("⚙️ Trading Parameters")
symbol = st.sidebar.text_input("Kode Saham IDX", "BBCA.JK")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y"], index=1)
modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=500_000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 1, 10, 2)

# ======================================================
# LOAD DATA
# ======================================================
df = yf.download(symbol, period=period, interval="1d", auto_adjust=True)

if df.empty or len(df) < 30:
    st.error("❌ Data tidak cukup")
    st.stop()

# ======================================================
# INDICATORS
# ======================================================
df["MA_fast"] = df["Close"].rolling(20).mean()
df["MA_slow"] = df["Close"].rolling(50).mean()
df["MA_trend"] = df["Close"].rolling(100).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
rs = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

ema12 = df["Close"].ewm(span=12).mean()
ema26 = df["Close"].ewm(span=26).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9).mean()

df.dropna(inplace=True)

# ======================================================
# SCALAR
# ======================================================
price = float(df["Close"].iloc[-1])
ma_fast = float(df["MA_fast"].iloc[-1])
ma_slow = float(df["MA_slow"].iloc[-1])
ma_trend = float(df["MA_trend"].iloc[-1])
rsi = float(df["RSI"].iloc[-1])
macd = float(df["MACD"].iloc[-1])
signal = float(df["Signal"].iloc[-1])

support = float(df["Low"].rolling(20).min().iloc[-1])
resistance = float(df["High"].rolling(20).max().iloc[-1])

# ======================================================
# SCORING 12 POINT SYSTEM
# ======================================================
reasons_buy = []
reasons_sell = []
reasons_wait = []

if price > ma_trend:
    reasons_buy.append("Harga di atas MA_trend (tren sehat)")
else:
    reasons_wait.append("Harga di bawah MA_trend")

if ma_fast > ma_slow:
    reasons_buy.append("MA_fast > MA_slow (momentum naik)")
else:
    reasons_wait.append("Momentum belum kuat")

if macd > signal:
    reasons_buy.append("MACD bullish")
else:
    reasons_sell.append("MACD melemah")

if 40 <= rsi <= 65:
    reasons_buy.append("RSI sehat")
elif rsi > 70:
    reasons_sell.append("RSI overbought")
else:
    reasons_wait.append("RSI lemah")

risk = price - support
reward = resistance - price
rr = reward / risk if risk > 0 else 0

if rr >= 1.5:
    reasons_buy.append(f"Risk/Reward layak ({rr:.2f}R)")
else:
    reasons_wait.append(f"RR kurang menarik ({rr:.2f}R)")

# ======================================================
# DECISION
# ======================================================
score = len(reasons_buy)

if score >= 4:
    decision = "BUY"
    confidence = "🟢 HIGH"
elif score >= 2:
    decision = "WAIT"
    confidence = "🟡 MEDIUM"
else:
    decision = "NO TRADE"
    confidence = "🔴 LOW"

# ======================================================
# UI OUTPUT
# ======================================================
st.subheader("📊 Market Snapshot")
st.metric("Harga", f"{price:,.0f}")
st.metric("Decision", decision)
st.metric("Confidence", confidence)
st.metric("Risk/Reward", f"{rr:.2f}R")

st.divider()

st.subheader("✅ Alasan BUY")
for r in reasons_buy:
    st.success(r)

st.subheader("⚠️ Alasan WAIT")
for r in reasons_wait:
    st.warning(r)

st.subheader("❌ Alasan SELL")
for r in reasons_sell:
    st.error(r)

st.caption("📌 Sistem ini membantu disiplin, bukan menjamin profit.")
