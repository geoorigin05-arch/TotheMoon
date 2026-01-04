# ======================================================
# PROFESSIONAL STOCK MONITORING SYSTEM (HARDENED)
# ======================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime
import pytz

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from telegram import Bot
from dotenv import load_dotenv

# ======================================================
# ENV & TELEGRAM
# ======================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None

# ======================================================
# MARKET TIME (IDX)
# ======================================================
tz = pytz.timezone("Asia/Jakarta")
now = datetime.now(tz)
is_weekday = now.weekday() < 5
is_market_hour = is_weekday and (9 <= now.hour < 15)

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config("Professional Stock System", layout="centered")
st.title("📊 Professional Stock Monitoring System")
st.caption("Decision Support • Risk First • Anti Overtrade")

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.header("⚙️ Trading Parameters")
symbol = st.sidebar.text_input("Kode Saham IDX (.JK)", "BBCA.JK")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y"], index=1)
mode = st.sidebar.selectbox("Trading Mode", ["Swing", "Scalping"])
modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=500_000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 1, 10, 2)

# ======================================================
# LOAD DATA (ROBUST & IDX SAFE)
# ======================================================
try:
    df = yf.download(
        symbol,
        period=period,
        interval="1d",
        progress=False
    )
except Exception:
    st.error("❌ Gagal mengambil data dari Yahoo Finance")
    st.stop()

# ======================================================
# NORMALIZE DATAFRAME (CRITICAL FIX)
# ======================================================
if df is None or df.empty:
    st.error("❌ Data kosong. Ticker tidak valid / market libur.")
    st.stop()

# Jika kolom MultiIndex (sering terjadi di IDX)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

# Standarisasi nama kolom
df.columns = [c.strip().title() for c in df.columns]

required_cols = {"Open", "High", "Low", "Close", "Volume"}
missing = required_cols - set(df.columns)

if missing:
    st.error(f"❌ Kolom tidak lengkap dari Yahoo Finance: {missing}")
    st.stop()

df = df[["Open", "High", "Low", "Close", "Volume"]]
df = df.dropna()

if len(df) < 60:
    st.error("❌ Data terlalu sedikit untuk analisis profesional")
    st.stop()

# ======================================================
# INDICATORS
# ======================================================
fast = 9 if mode == "Scalping" else 20
slow = 20 if mode == "Scalping" else 50

df["MA_fast"] = df["Close"].rolling(fast).mean()
df["MA_slow"] = df["Close"].rolling(slow).mean()
df["MA_200"] = df["Close"].rolling(200).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
rs = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

ema12 = df["Close"].ewm(span=12).mean()
ema26 = df["Close"].ewm(span=26).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9).mean()

df = df.dropna()

if len(df) == 0:
    st.error("❌ Data habis setelah perhitungan indikator")
    st.stop()

# ======================================================
# SAFE LAST VALUES
# ======================================================
last = df.iloc[-1]
price = float(last["Close"])
rsi = float(last["RSI"])

# ======================================================
# MARKET ELIGIBILITY FILTER
# ======================================================
avg_volume = df["Volume"].rolling(20).mean().iloc[-1]
atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]

if avg_volume < 5_000_000:
    st.error("❌ Saham tidak likuid (volume rendah)")
    st.stop()

if atr / price < 0.01:
    st.error("❌ Volatilitas terlalu kecil (tidak layak trading)")
    st.stop()

# ======================================================
# TREND HIERARCHY
# ======================================================
trend_bias = "BULLISH" if price > df["MA_200"].iloc[-1] else "BEARISH"

# ======================================================
# SUPPORT & RESISTANCE
# ======================================================
support = df["Low"].rolling(20).min().iloc[-1]
resistance = df["High"].rolling(20).max().iloc[-1]

# ======================================================
# ENTRY ZONE
# ======================================================
buy_zone_low = support * 1.02
buy_zone_high = df["MA_fast"].iloc[-1]
sell_zone_low = resistance * 0.98

# ======================================================
# AI MODEL (SAFE)
# ======================================================
ai_prob = 0.5
if len(df) >= 120:
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    features = ["RSI", "MACD", "MA_fast", "MA_slow"]
    X = df[features].iloc[:-1]
    y = df["Target"].iloc[:-1]

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=300)
    model.fit(Xs, y)

    ai_prob = float(
        model.predict_proba(
            scaler.transform([df[features].iloc[-1]])
        )[0][1]
    )

# ======================================================
# SCORING
# ======================================================
score = 0
if trend_bias == "BULLISH": score += 1
if price > df["MA_fast"].iloc[-1]: score += 1
if df["MACD"].iloc[-1] > df["Signal"].iloc[-1]: score += 1
if 30 < rsi < 65: score += 1
if buy_zone_low <= price <= buy_zone_high: score += 1
if ai_prob > 0.6: score += 1
if ai_prob < 0.4: score -= 1

confidence = "🟢 HIGH" if score >= 5 else "🟡 MEDIUM" if score >= 3 else "🔴 LOW"
decision = "BUY" if confidence == "🟢 HIGH" else "NO TRADE"

# ======================================================
# RISK MANAGEMENT
# ======================================================
stop_loss = min(support, df["Low"].iloc[-3:].min())
risk_amount = modal * (risk_pct / 100)
risk_per_share = price - stop_loss
max_lot = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
rr_ratio = (sell_zone_low - price) / risk_per_share if risk_per_share > 0 else 0

# ======================================================
# UI OUTPUT
# ======================================================
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Harga", f"{price:,.0f}")
c2.metric("Trend", trend_bias)
c3.metric("AI Prob", f"{ai_prob:.2f}")
c4.metric("Score", score)

st.markdown(f"""
## 📌 Trading Decision
**{decision}**  
Confidence: **{confidence}**  
Risk/Reward: **{rr_ratio:.2f}R**
""")

st.caption("⚠️ Sistem ini tahan error & memprioritaskan NO TRADE daripada entry buruk.")
