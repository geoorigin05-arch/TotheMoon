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
# IDX MARKET HOURS
# ======================================================
tz = pytz.timezone("Asia/Jakarta")
now = datetime.now(tz)
is_weekday = now.weekday() < 5
is_market_hour = is_weekday and (9 <= now.hour < 15)

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Stock Monitoring System", layout="centered")
st.title("📊 Stock Monitoring System")
st.caption("IDX • Technical + AI • Decision Support")

# ======================================================
# SIDEBAR INPUT
# ======================================================
st.sidebar.header("⚙️ Trading Parameters")
symbol = st.sidebar.text_input("Kode Saham IDX (.JK)", "BUMI.JK")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y"], index=1)
mode = st.sidebar.selectbox("Mode Trading", ["Swing", "Scalping"])
modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=500_000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 1, 20, 2)

with st.sidebar.expander("🧠 Cara Membaca Hasil", expanded=False):
    st.markdown("""
**📍 ENTRY ZONE**
- 🟢 BUY ZONE → area aman masuk
- 🔴 SELL ZONE → target distribusi

**🎯 CONFIDENCE**
- 🟢 HIGH → boleh entry
- 🟡 MEDIUM → kecilkan size
- 🔴 LOW → NO TRADE
""")

# ======================================================
# LOAD DATA
# ======================================================
df = yf.download(symbol, period=period, interval="1d")
df.dropna(inplace=True)

if len(df) < 15:
    st.error("❌ Data terlalu sedikit")
    st.stop()

data_limited = (period == "3mo") or (len(df) < 50)
quick_view = data_limited

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

df.dropna(inplace=True)

# ======================================================
# LATEST VALUES
# ======================================================
price = float(df["Close"].iloc[-1])
rsi = float(df["RSI"].iloc[-1])
macd = float(df["MACD"].iloc[-1])
signal = float(df["Signal"].iloc[-1])
ma_fast = float(df["MA_fast"].iloc[-1])

# ======================================================
# SUPPORT & RESISTANCE (ULTRA SAFE)
# ======================================================
low_roll = df["Low"].rolling(20).min()
high_roll = df["High"].rolling(20).max()

last_low = low_roll.iloc[-1]
last_high = high_roll.iloc[-1]

support = float(last_low) if isinstance(last_low, (float, int)) and not np.isnan(last_low) else float(df["Low"].iloc[-5:].min())
resistance = float(last_high) if isinstance(last_high, (float, int)) and not np.isnan(last_high) else float(df["High"].iloc[-5:].max())

# ======================================================
# ENTRY ZONE
# ======================================================
buy_zone_low = support * 1.02
buy_zone_high = ma_fast
sell_zone_low = resistance * 0.98
sell_zone_high = resistance * 1.05

# ======================================================
# SCORING
# ======================================================
score = 0
if price > ma_fast: score += 1
if macd > signal: score += 1
if rsi < 70: score += 1
if rsi < 30: score += 1

# ======================================================
# AI MODEL (AUTO OFF)
# ======================================================
ai_enabled = not data_limited
ai_prob = 0.5

if ai_enabled:
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

    if ai_prob > 0.6: score += 1
    elif ai_prob < 0.4: score -= 1

# ======================================================
# DECISION & CONFIDENCE
# ======================================================
confidence = "🟢 HIGH" if score >= 4 else "🟡 MEDIUM" if score >= 2 else "🔴 LOW"
decision = "NO TRADE" if confidence == "🔴 LOW" else ("BUY" if score >= 3 else "SELL" if score <= -2 else "HOLD")

# ======================================================
# RISK MANAGEMENT
# ======================================================
stop_loss = support
risk_amount = modal * (risk_pct / 100)
risk_per_share = abs(price - stop_loss)
max_lot = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0

# ======================================================
# TELEGRAM ALERT (ANTI-SPAM 1x/HARI)
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

if bot and is_market_hour and can_alert():
    alert_type = None

    if buy_zone_low <= price <= buy_zone_high:
        alert_type = "🟢 BUY ZONE"
    elif price >= sell_zone_low:
        alert_type = "🔴 SELL ZONE"
    elif price <= stop_loss:
        alert_type = "⛔ STOP LOSS"

    if alert_type:
        try:
            bot.send_message(
                chat_id=CHAT_ID,
                text=f"""
📢 {alert_type}

📊 {symbol}
💰 Harga: {price:,.0f}

BUY : {int(buy_zone_low):,} – {int(buy_zone_high):,}
SELL: {int(sell_zone_low):,} – {int(sell_zone_high):,}
SL  : {int(stop_loss):,}

🎯 Decision: {decision}
{confidence}
"""
            )
            mark_alerted()
        except:
            pass

# ======================================================
# UI OUTPUT
# ======================================================
st.divider()

if data_limited:
    st.warning("⚠️ Data Terbatas — AI & Backtest dinonaktifkan (Quick View)")

st.subheader("📊 Market Snapshot")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Harga", f"{price:,.0f}")
c2.metric("RSI", f"{rsi:.1f}")
c3.metric("AI Prob", "-" if not ai_enabled else f"{ai_prob:.2f}")
c4.metric("Score", score)

st.markdown(f"### 📌 Decision: **{decision}** | Confidence: **{confidence}**")

# ======================================================
# ENTRY ZONE
# ======================================================
st.divider()
st.subheader("📍 Entry Zone")
z1, z2 = st.columns(2)
z1.success(f"🟢 BUY ZONE\n\n{int(buy_zone_low):,} – {int(buy_zone_high):,}")
z2.error(f"🔴 SELL ZONE\n\n{int(sell_zone_low):,} – {int(sell_zone_high):,}")

# ======================================================
# RISK MANAGEMENT
# ======================================================
st.divider()
st.subheader("📌 Risk Management")
r1, r2, r3 = st.columns(3)
r1.metric("Risk Amount", f"Rp {risk_amount:,.0f}")
r2.metric("Stop Loss", f"{stop_loss:,.0f}")
r3.metric("Max Lot", f"{max_lot:,}")

# ======================================================
# PROFIT CALCULATOR (NEW)
# ======================================================
st.divider()
st.subheader("💰 Profit Calculator")

target_price = st.number_input(
    "Target Jual (Rp)",
    min_value=0.0,
    value=float(sell_zone_low),
    step=10.0
)

lot = max_lot
shares = lot * 100

profit_per_share = target_price - price
total_profit = profit_per_share * shares
profit_pct = (total_profit / modal) * 100 if modal > 0 else 0

p1, p2, p3 = st.columns(3)
p1.metric("Lot Digunakan", f"{lot:,}")
p2.metric("Profit (Rp)", f"{total_profit:,.0f}")
p3.metric("Profit (%)", f"{profit_pct:.2f}%")

if target_price <= price:
    st.warning("⚠️ Target jual harus di atas harga beli")
elif confidence == "🔴 LOW":
    st.info("ℹ️ Confidence LOW → sistem menyarankan NO TRADE")

st.caption("📌 Profit adalah estimasi berdasarkan target harga & risk management (belum termasuk fee & pajak).")
