# ======================================================
# PROFESSIONAL STOCK MONITORING SYSTEM
# IDX • TECHNICAL • AI • RISK-FIRST
# ======================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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
st.caption("Decision Support System • Not Signal Generator")

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
# LOAD DATA
# ======================================================
df = yf.download(symbol, period=period, interval="1d")
df.dropna(inplace=True)

if len(df) < 60:
    st.error("❌ Data tidak cukup")
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

df.dropna(inplace=True)

# ======================================================
# MARKET ELIGIBILITY FILTER (PRO)
# ======================================================
price = float(df["Close"].iloc[-1])
avg_volume = df["Volume"].rolling(20).mean().iloc[-1]
atr = (df["High"] - df["Low"]).rolling(14).mean().iloc[-1]

eligible = True
block_reason = []

if avg_volume < 5_000_000:
    eligible = False
    block_reason.append("Likuiditas rendah")

if atr / price < 0.01:
    eligible = False
    block_reason.append("Volatilitas terlalu kecil")

if not eligible:
    st.error("❌ SAHAM TIDAK LAYAK DIPERDAGANGKAN")
    for r in block_reason:
        st.write(f"- {r}")
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
sell_zone_high = resistance * 1.05

# ======================================================
# AI MODEL
# ======================================================
ai_prob = 0.5
if len(df) >= 100:
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

# ======================================================
# SCORING (CONFLUENCE)
# ======================================================
score = 0
if trend_bias == "BULLISH": score += 1
if price > df["MA_fast"].iloc[-1]: score += 1
if df["MACD"].iloc[-1] > df["Signal"].iloc[-1]: score += 1
if 30 < df["RSI"].iloc[-1] < 65: score += 1
if buy_zone_low <= price <= buy_zone_high: score += 1
if ai_prob > 0.6: score += 1
if ai_prob < 0.4: score -= 1

confidence = "🟢 HIGH" if score >= 5 else "🟡 MEDIUM" if score >= 3 else "🔴 LOW"

decision = (
    "NO TRADE" if confidence == "🔴 LOW"
    else "BUY" if score >= 5
    else "WAIT"
)

# ======================================================
# RISK MANAGEMENT (STRUCTURE BASED)
# ======================================================
stop_loss = min(support, df["Low"].iloc[-3:].min())
risk_amount = modal * (risk_pct / 100)
risk_per_share = abs(price - stop_loss)
max_lot = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0

rr_ratio = (sell_zone_low - price) / (price - stop_loss) if price > stop_loss else 0

# ======================================================
# TELEGRAM ALERT (PRO ONLY)
# ======================================================
alert_file = f".alert_{symbol.replace('.', '_')}.txt"
today = now.strftime("%Y-%m-%d")

def can_alert():
    if not os.path.exists(alert_file):
        return True
    with open(alert_file) as f:
        return f.read().strip() != today

def mark_alerted():
    with open(alert_file, "w") as f:
        f.write(today)

if (
    bot and is_market_hour and can_alert()
    and confidence == "🟢 HIGH"
    and rr_ratio >= 1.5
    and decision == "BUY"
):
    bot.send_message(
        chat_id=CHAT_ID,
        text=f"""
📊 {symbol}
Decision: BUY (PRO SETUP)

Harga : {price:,.0f}
BUY   : {int(buy_zone_low):,} – {int(buy_zone_high):,}
SELL  : {int(sell_zone_low):,}
SL    : {int(stop_loss):,}

Risk/Reward: {rr_ratio:.2f}R
AI Prob: {ai_prob:.2f}
"""
    )
    mark_alerted()

# ======================================================
# UI OUTPUT
# ======================================================
st.divider()
st.subheader("📊 Market Snapshot")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Harga", f"{price:,.0f}")
c2.metric("Trend Bias", trend_bias)
c3.metric("AI Prob", f"{ai_prob:.2f}")
c4.metric("Score", score)

st.markdown(f"""
## 📌 Trading Decision
**{decision}**  
Confidence: **{confidence}**  
Risk/Reward: **{rr_ratio:.2f}R**
""")

# ======================================================
# ZONE
# ======================================================
st.divider()
z1, z2 = st.columns(2)
z1.success(f"🟢 BUY ZONE\n{int(buy_zone_low):,} – {int(buy_zone_high):,}")
z2.error(f"🔴 SELL ZONE\n{int(sell_zone_low):,} – {int(sell_zone_high):,}")

# ======================================================
# RISK PANEL
# ======================================================
st.divider()
r1, r2, r3 = st.columns(3)
r1.metric("Risk Amount", f"Rp {risk_amount:,.0f}")
r2.metric("Stop Loss", f"{stop_loss:,.0f}")
r3.metric("Max Lot", f"{max_lot:,}")

st.caption("⚠️ Sistem ini adalah decision support. Disiplin tetap di trader.")
