import os
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import pytz
from datetime import datetime

from telegram import Bot
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

# ==============================
# LOAD ENV
# ==============================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
bot = Bot(token=BOT_TOKEN)

# ==============================
# STREAMLIT CONFIG
# ==============================
st.set_page_config(
    page_title="Stock Monitor Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 Stock Monitor Pro (IDX)")

# ==============================
# AUTO REFRESH (60 detik)
# ==============================
st_autorefresh(interval=60000, key="refresh")

# ==============================
# CEK JAM BURSA IDX (WIB)
# ==============================
tz = pytz.timezone("Asia/Jakarta")
now = datetime.now(tz)
market_open = now.replace(hour=9, minute=0, second=0)
market_close = now.replace(hour=15, minute=0, second=0)

is_market_open = market_open <= now <= market_close

# ==============================
# INPUT
# ==============================
ticker = st.text_input("Kode Saham (.JK)", "GOTO.JK")
period = st.selectbox("Periode Data", ["1mo", "3mo", "6mo", "1y"])

# ==============================
# LOAD DATA
# ==============================
@st.cache_data
def load_data(ticker, period):
    return yf.download(ticker, period=period)

data = load_data(ticker, period)

if data.empty:
    st.error("❌ Data tidak ditemukan")
    st.stop()

# ==============================
# INDIKATOR TEKNIKAL
# ==============================
data["MA20"] = data["Close"].rolling(20).mean()
data["MA50"] = data["Close"].rolling(50).mean()

support = data["Low"].rolling(20).min().iloc[-1]
resistance = data["High"].rolling(20).max().iloc[-1]
last_price = data["Close"].iloc[-1]

# ==============================
# RSI
# ==============================
delta = data["Close"].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = -delta.where(delta < 0, 0).rolling(14).mean()
rs = gain / loss
data["RSI"] = 100 - (100 / (1 + rs))
rsi = data["RSI"].iloc[-1]

# ==============================
# MACD
# ==============================
ema12 = data["Close"].ewm(span=12, adjust=False).mean()
ema26 = data["Close"].ewm(span=26, adjust=False).mean()
data["MACD"] = ema12 - ema26
data["Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()

macd = data["MACD"].iloc[-1]
signal = data["Signal"].iloc[-1]
macd_prev = data["MACD"].iloc[-2]
signal_prev = data["Signal"].iloc[-2]

# ==============================
# SCORING SYSTEM
# ==============================
score = 0

if last_price > data["MA20"].iloc[-1]:
    score += 1
if data["MA20"].iloc[-1] > data["MA50"].iloc[-1]:
    score += 1
if rsi < 30:
    score += 1
if rsi > 70:
    score -= 1
if macd_prev < signal_prev and macd > signal:
    score += 1
if macd_prev > signal_prev and macd < signal:
    score -= 1
if last_price < support:
    score -= 1

if score >= 3:
    decision = "BUY"
elif score <= -2:
    decision = "SELL"
else:
    decision = "HOLD"

# ==============================
# TELEGRAM ALERT
# ==============================
def send_alert(msg):
    if is_market_open:
        try:
            bot.send_message(chat_id=CHAT_ID, text=msg)
        except:
            pass

if "alert_state" not in st.session_state:
    st.session_state.alert_state = ""

# RSI Alert
if is_market_open:
    if rsi < 30 and st.session_state.alert_state != "rsi_os":
        send_alert(f"📉 RSI OVERSOLD\n{ticker}\nRSI: {rsi:.2f}")
        st.session_state.alert_state = "rsi_os"

    elif rsi > 70 and st.session_state.alert_state != "rsi_ob":
        send_alert(f"📈 RSI OVERBOUGHT\n{ticker}\nRSI: {rsi:.2f}")
        st.session_state.alert_state = "rsi_ob"

# MACD Alert
if is_market_open:
    if macd_prev < signal_prev and macd > signal and st.session_state.alert_state != "macd_buy":
        send_alert(f"🚀 MACD BULLISH CROSS\n{ticker}\nSinyal BUY")
        st.session_state.alert_state = "macd_buy"

    elif macd_prev > signal_prev and macd < signal and st.session_state.alert_state != "macd_sell":
        send_alert(f"⚠️ MACD BEARISH CROSS\n{ticker}\nSinyal SELL")
        st.session_state.alert_state = "macd_sell"

# ==============================
# DASHBOARD
# ==============================
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Harga", f"{last_price:,.2f}")
c2.metric("Support", f"{support:,.2f}")
c3.metric("Resistance", f"{resistance:,.2f}")
c4.metric("RSI", f"{rsi:.2f}")
c5.metric("MACD", f"{macd:.4f}")

st.subheader("📌 Keputusan Sistem")
if decision == "BUY":
    st.success("🟢 BUY")
elif decision == "SELL":
    st.error("🔴 SELL")
else:
    st.warning("🟡 HOLD")

# ==============================
# GRAFIK
# ==============================
st.subheader("📈 Grafik Harga")
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(data["Close"], label="Close", linewidth=2)
ax.plot(data["MA20"], label="MA20")
ax.plot(data["MA50"], label="MA50")
ax.axhline(support, linestyle="--", label="Support")
ax.axhline(resistance, linestyle="--", label="Resistance")
ax.legend()
ax.grid()
st.pyplot(fig)

# ==============================
# FOOTER
# ==============================
st.caption("Alert aktif hanya jam bursa IDX (09.00–15.00 WIB). Data Yahoo Finance (delay ±15 menit).")
