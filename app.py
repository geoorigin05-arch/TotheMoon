import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import os

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
# TIMEZONE & MARKET HOURS
# ======================================================
tz = pytz.timezone("Asia/Jakarta")
now = datetime.now(tz)
is_weekday = now.weekday() < 5
is_market_hour = is_weekday and (9 <= now.hour < 15)

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Professional Stock System", layout="centered")
st.title("📊 Professional Stock Decision System")
st.caption("IDX • Multi-Factor • Risk Managed")

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.header("⚙️ Trading Parameters")
symbol = st.sidebar.text_input("Kode Saham IDX (.JK)", "BBCA.JK")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y"], index=1)
mode = st.sidebar.selectbox("Mode Trading", ["Swing", "Scalping"])
modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=500_000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 1, 10, 2)

# ======================================================
# LOAD DATA
# ======================================================
df = yf.download(symbol, period=period, interval="1d", auto_adjust=True)

if df.empty or len(df) < 30:
    st.error("❌ Data tidak cukup / gagal diambil dari Yahoo Finance")
    st.stop()

# ======================================================
# INDICATORS
# ======================================================
fast = 9 if mode == "Scalping" else 20
slow = 20 if mode == "Scalping" else 50

df["MA_fast"] = df["Close"].rolling(fast).mean()
df["MA_slow"] = df["Close"].rolling(slow).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
rs = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

ema12 = df["Close"].ewm(span=12).mean()
ema26 = df["Close"].ewm(span=26).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9).mean()

# ======================================================
# ADAPTIVE TREND MA (ANTI ERROR)
# ======================================================
if len(df) >= 200:
    trend_len = 200
elif len(df) >= 100:
    trend_len = 100
else:
    trend_len = 50

df["MA_trend"] = df["Close"].rolling(trend_len).mean()

df.dropna(inplace=True)

if df.empty:
    st.error("❌ Data habis setelah perhitungan indikator")
    st.stop()

# ======================================================
# LATEST VALUES
# ======================================================
price = float(df["Close"].iloc[-1])
rsi = float(df["RSI"].iloc[-1])
macd = float(df["MACD"].iloc[-1])
signal = float(df["Signal"].iloc[-1])
ma_fast = float(df["MA_fast"].iloc[-1])
trend_ma = float(df["MA_trend"].iloc[-1])

trend_bias = "BULLISH" if price > trend_ma else "BEARISH"

# ======================================================
# SUPPORT & RESISTANCE
# ======================================================
support = df["Low"].rolling(20).min().iloc[-1]
resistance = df["High"].rolling(20).max().iloc[-1]

# ======================================================
# ENTRY ZONES
# ======================================================
buy_zone_low = support * 1.02 if support > 0 else np.nan
buy_zone_high = ma_fast if ma_fast > 0 else np.nan
sell_zone = resistance * 0.98 if resistance > 0 else np.nan

# ======================================================
# SCORING SYSTEM
# ======================================================
score = 0
score += 1 if price > ma_fast else 0
score += 1 if macd > signal else 0
score += 1 if rsi < 70 else 0
score += 1 if trend_bias == "BULLISH" else 0

# ======================================================
# AI MODEL (AUTO DISABLE JIKA DATA KURANG)
# ======================================================
ai_prob = "-"
if len(df) >= 60:
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    features = ["RSI", "MACD", "MA_fast", "MA_slow"]

    X = df[features]
    y = df["Target"]

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=300)
    model.fit(Xs[:-1], y[:-1])

    ai_prob = float(model.predict_proba(
        scaler.transform([X.iloc[-1]])
    )[0][1])

    if ai_prob > 0.6:
        score += 1
    elif ai_prob < 0.4:
        score -= 1

# ======================================================
# DECISION
# ======================================================
confidence = "🟢 HIGH" if score >= 4 else "🟡 MEDIUM" if score >= 2 else "🔴 LOW"
decision = "NO TRADE" if confidence == "🔴 LOW" else "BUY" if score >= 4 else "WAIT"

# ======================================================
# RISK MANAGEMENT
# ======================================================
risk_amount = modal * (risk_pct / 100)
stop_loss = support
risk_per_share = price - stop_loss

max_lot = int(risk_amount / (risk_per_share * 100)) if risk_per_share > 0 else 0

reward = sell_zone - price if sell_zone > price else 0
rr_ratio = reward / risk_per_share if risk_per_share > 0 and reward > 0 else 0

# ======================================================
# SAFE FORMATTER (ANTI ERROR UI)
# ======================================================
def safe_price(x):
    return "-" if pd.isna(x) or np.isinf(x) else f"{int(x):,}"

# ======================================================
# UI OUTPUT
# ======================================================
st.divider()
st.subheader("📊 Market Snapshot")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Harga", safe_price(price))
c2.metric("RSI", f"{rsi:.1f}")
c3.metric("Trend", trend_bias)
c4.metric("Score", score)

st.markdown(f"### 📌 Decision: **{decision}**")
st.markdown(f"Confidence: **{confidence}**")
st.markdown(f"Risk/Reward: **{rr_ratio:.2f}R**")

# ======================================================
# ENTRY ZONE
# ======================================================
st.divider()
st.subheader("📍 Entry Zone")

z1, z2 = st.columns(2)
z1.success(f"🟢 BUY ZONE\n{safe_price(buy_zone_low)} – {safe_price(buy_zone_high)}")
z2.error(f"🔴 SELL ZONE\n{safe_price(sell_zone)}")

# ======================================================
# RISK MANAGEMENT
# ======================================================
st.divider()
st.subheader("📌 Risk Management")

r1, r2, r3 = st.columns(3)
r1.metric("Risk Amount", f"Rp {risk_amount:,.0f}")
r2.metric("Stop Loss", safe_price(stop_loss))
r3.metric("Max Lot", f"{max_lot:,}")

st.caption("📌 Sistem ini adalah decision support — disiplin risk management tetap nomor satu.")
