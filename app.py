import os
import time
import pytz
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

from datetime import datetime
from telegram import Bot
from streamlit_autorefresh import st_autorefresh
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# =====================================================
# STREAMLIT CONFIG (FAST BOOT)
# =====================================================
st.set_page_config(
    page_title="Stock AI Trading System",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 Stock AI Trading System (Always-On Optimized)")

# =====================================================
# AUTO REFRESH INTERNAL (ANTI SLEEP)
# =====================================================
st_autorefresh(interval=60000, key="auto_refresh")  # 1 menit

# =====================================================
# ENV (STREAMLIT SECRETS COMPATIBLE)
# =====================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN)

# =====================================================
# HEARTBEAT (SESSION KEEP-ALIVE)
# =====================================================
if "heartbeat" not in st.session_state:
    st.session_state.heartbeat = time.time()

st.session_state.heartbeat = time.time()

# =====================================================
# JAM BURSA IDX
# =====================================================
tz = pytz.timezone("Asia/Jakarta")
now = datetime.now(tz)

market_open = now.replace(hour=9, minute=0, second=0)
market_close = now.replace(hour=15, minute=0, second=0)
is_market_open = market_open <= now <= market_close

# =====================================================
# INPUT
# =====================================================
ticker = st.text_input("Kode Saham (.JK)", "GOTO.JK")
period = st.selectbox("Periode Data", ["6mo", "1y", "2y"])

modal = st.number_input("Modal (Rp)", value=10_000_000, step=1_000_000)
risk_pct = st.slider("Risk per Trade (%)", 1, 5, 2)

# =====================================================
# LOAD DATA (CACHE OPTIMAL)
# =====================================================
@st.cache_data(ttl=300)  # refresh data tiap 5 menit
def load_data(ticker, period):
    return yf.download(ticker, period=period, progress=False)

df = load_data(ticker, period)

if df.empty:
    st.error("❌ Data tidak tersedia")
    st.stop()

# =====================================================
# INDIKATOR
# =====================================================
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()

# RSI
delta = df["Close"].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# MACD
ema12 = df["Close"].ewm(span=12, adjust=False).mean()
ema26 = df["Close"].ewm(span=26, adjust=False).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

df.dropna(inplace=True)

# =====================================================
# AI-BASED SCORING (LIGHTWEIGHT)
# =====================================================
df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

features = ["RSI", "MACD", "MA20", "MA50"]
X = df[features]
y = df["Target"]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = LogisticRegression(max_iter=200)
model.fit(X_scaled[:-1], y[:-1])

latest_features = scaler.transform([df[features].iloc[-1]])
ai_prob = model.predict_proba(latest_features)[0][1]

# =====================================================
# RULE SCORING
# =====================================================
price = float(df["Close"].iloc[-1])
ma20 = float(df["MA20"].iloc[-1])
ma50 = float(df["MA50"].iloc[-1])
rsi_val = float(df["RSI"].iloc[-1])
macd_now = float(df["MACD"].iloc[-1])
signal_now = float(df["Signal"].iloc[-1])
macd_prev = float(df["MACD"].iloc[-2])
signal_prev = float(df["Signal"].iloc[-2])

support = df["Low"].rolling(20).min().iloc[-1]
resistance = df["High"].rolling(20).max().iloc[-1]

score = 0
if price > df["MA20"].iloc[-1]: score += 1
if df["MA20"].iloc[-1] > df["MA50"].iloc[-1]: score += 1
if df["RSI"].iloc[-1] < 30: score += 1
if df["RSI"].iloc[-1] > 70: score -= 1
if df["MACD"].iloc[-2] < df["Signal"].iloc[-2] and df["MACD"].iloc[-1] > df["Signal"].iloc[-1]: score += 1
if df["MACD"].iloc[-2] > df["Signal"].iloc[-2] and df["MACD"].iloc[-1] < df["Signal"].iloc[-1]: score -= 1

final_score = score + (1 if ai_prob > 0.6 else -1 if ai_prob < 0.4 else 0)

if final_score >= 3:
    decision = "BUY"
elif final_score <= -2:
    decision = "SELL"
else:
    decision = "HOLD"

# =====================================================
# RISK MANAGEMENT
# =====================================================
risk_amount = modal * (risk_pct / 100)
stop_loss = support * 0.98
risk_per_share = max(price - stop_loss, 1)
lot_size = int(risk_amount / risk_per_share)

# =====================================================
# TELEGRAM ALERT (ANTI SPAM)
# =====================================================
def send_alert(msg):
    if is_market_open:
        try:
            bot.send_message(chat_id=CHAT_ID, text=msg)
        except:
            pass

if "last_signal" not in st.session_state:
    st.session_state.last_signal = ""

if decision != "HOLD" and decision != st.session_state.last_signal:
    send_alert(
        f"📊 AI SIGNAL\n"
        f"{ticker}\n"
        f"Decision: {decision}\n"
        f"AI Prob UP: {ai_prob:.2f}"
    )
    st.session_state.last_signal = decision

# =====================================================
# DASHBOARD
# =====================================================
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Harga", f"{price:,.2f}")
c2.metric("RSI", f"{df['RSI'].iloc[-1]:.2f}")
c3.metric("AI Prob", f"{ai_prob:.2f}")
c4.metric("Decision", decision)
c5.metric("Max Lot", f"{lot_size:,}")

st.subheader("📌 Risk Management")
st.write(f"""
- Modal: Rp {modal:,.0f}  
- Risk/Trade: {risk_pct}%  
- Risk Amount: Rp {risk_amount:,.0f}  
- Stop Loss: {stop_loss:,.2f}  
- Max Lot: {lot_size:,}
""")

st.caption("Optimized for Streamlit Cloud | Internal auto-refresh + heartbeat")
