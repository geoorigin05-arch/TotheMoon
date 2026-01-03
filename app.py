import os
import pytz
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from telegram import Bot
from telegram.error import InvalidToken

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(
    page_title="AI Stock Trading System FINAL++",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 AI Stock Trading System (FINAL++)")

# =====================================================
# AUTO REFRESH (ANTI SLEEP)
# =====================================================
st_autorefresh(interval=60_000, key="refresh")

# =====================================================
# TELEGRAM (SAFE INIT)
# =====================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = None
if BOT_TOKEN:
    try:
        bot = Bot(token=BOT_TOKEN)
    except InvalidToken:
        st.warning("⚠️ BOT_TOKEN tidak valid")

def send_alert(message):
    if bot is None or CHAT_ID is None:
        return
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception:
        pass

# =====================================================
# JAM BURSA IDX
# =====================================================
tz = pytz.timezone("Asia/Jakarta")
now = datetime.now(tz)

market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
market_close = now.replace(hour=15, minute=0, second=0, microsecond=0)
is_market_open = market_open <= now <= market_close

# =====================================================
# INPUT USER
# =====================================================
ticker = st.text_input("Kode Saham IDX (.JK)", "GOTO.JK")
period = st.selectbox("Periode Data", ["6mo", "1y", "2y"])

modal = st.number_input("Modal (Rp)", value=10_000_000, step=1_000_000)
risk_pct = st.slider("Risk per Trade (%)", 1, 5, 2)

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data(ttl=300)
def load_data(ticker, period):
    return yf.download(ticker, period=period, progress=False)

df = load_data(ticker, period)

if df.empty or len(df) < 20:
    st.error("❌ Data terlalu sedikit (<20 candle). Tidak bisa dianalisis.")
    st.stop()

data_len = len(df)

# =====================================================
# ADAPTIVE MODE
# =====================================================
if data_len < 50:
    ai_enabled = False
    st.warning("⚠️ Data terbatas — AI & MA50 nonaktif (Mode IPO / Saham Baru)")
else:
    ai_enabled = True

# =====================================================
# INDIKATOR
# =====================================================
df["MA20"] = df["Close"].rolling(20).mean()

if ai_enabled:
    df["MA50"] = df["Close"].rolling(50).mean()
else:
    df["MA50"] = df["MA20"]  # fallback aman

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
# SAFE SCALAR VALUES
# =====================================================
price = float(df["Close"].iloc[-1])
ma20 = float(df["MA20"].iloc[-1])
ma50 = float(df["MA50"].iloc[-1])
rsi_val = float(df["RSI"].iloc[-1])

macd_now = float(df["MACD"].iloc[-1])
signal_now = float(df["Signal"].iloc[-1])
macd_prev = float(df["MACD"].iloc[-2])
signal_prev = float(df["Signal"].iloc[-2])

support = float(df["Low"].rolling(20).min().iloc[-1])

# =====================================================
# AI MODEL (OPTIONAL)
# =====================================================
if ai_enabled:
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

    features = ["RSI", "MACD", "MA20", "MA50"]
    X = df[features]
    y = df["Target"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LogisticRegression(max_iter=200)
    model.fit(X_scaled[:-1], y[:-1])

    latest_features = scaler.transform([df[features].iloc[-1]])
    ai_prob = float(model.predict_proba(latest_features)[0][1])
else:
    ai_prob = 0.5  # netral

# =====================================================
# SCORING SYSTEM (ADAPTIVE)
# =====================================================
score = 0

# Trend
if price > ma20:
    score += 1
if ma20 > ma50:
    score += 1

# Momentum
if rsi_val < 30:
    score += 1
elif rsi_val > 70:
    score -= 1

# MACD
if macd_prev < signal_prev and macd_now > signal_now:
    score += 1
elif macd_prev > signal_prev and macd_now < signal_now:
    score -= 1

# AI influence (only if enabled)
if ai_enabled:
    if ai_prob > 0.6:
        score += 1
    elif ai_prob < 0.4:
        score -= 1

# Final decision
if score >= 3:
    decision = "BUY"
elif score <= -2:
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
# TELEGRAM ALERT (ANTI-SPAM)
# =====================================================
if "last_signal" not in st.session_state:
    st.session_state.last_signal = ""

if is_market_open and decision != "HOLD" and decision != st.session_state.last_signal:
    send_alert(
        f"📊 AI SIGNAL\n"
        f"Saham: {ticker}\n"
        f"Signal: {decision}\n"
        f"Harga: {price:,.2f}\n"
        f"AI Prob: {ai_prob:.2f}\n"
        f"Mode: {'AI' if ai_enabled else 'Rule-Based'}"
    )
    st.session_state.last_signal = decision

# =====================================================
# DASHBOARD
# =====================================================
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Harga", f"{price:,.2f}")
c2.metric("RSI", f"{rsi_val:.2f}")
c3.metric("AI Prob", f"{ai_prob:.2f}")
c4.metric("Score", score)
c5.metric("Decision", decision)

st.subheader("📌 Risk Management")
st.write(f"""
- Modal: Rp {modal:,.0f}  
- Risk per Trade: {risk_pct}%  
- Risk Amount: Rp {risk_amount:,.0f}  
- Stop Loss: Rp {stop_loss:,.2f}  
- Max Lot (estimasi): {lot_size:,}
""")

st.caption(
    f"Mode: {'AI Aktif' if ai_enabled else 'Rule-Based (Data Terbatas)'} | "
    f"Data Candle: {data_len} | "
    "FINAL++ Streamlit Cloud Ready"
)
