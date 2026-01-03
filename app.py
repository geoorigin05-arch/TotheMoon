import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="AI Stock Trading System",
    layout="centered"
)

st.title("📊 AI Stock Trading System")
st.caption("IDX • Technical + AI • Decision Support")

# ======================================================
# SIDEBAR INPUT
# ======================================================
st.sidebar.header("⚙️ Trading Parameters")

symbol = st.sidebar.text_input("Kode Saham IDX (.JK)", "GOTO.JK")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y"], index=1)
mode = st.sidebar.selectbox("Mode Trading", ["Swing", "Scalping"])

modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=500_000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 1, 20, 2)

with st.sidebar.expander("🧠 Cara Membaca Hasil", expanded=True):
    st.markdown("""
**📍 ENTRY ZONE**
- 🟢 BUY ZONE → area aman masuk
- 🔴 SELL ZONE → target distribusi

**📈 EQUITY CURVE**
- Naik stabil → strategi sehat
- Banyak drawdown → jangan agresif

**🎯 CONFIDENCE**
- 🟢 HIGH → size normal
- 🟡 MEDIUM → kecilkan size
- 🔴 LOW → tunggu
""")

# ======================================================
# LOAD DATA
# ======================================================
df = yf.download(symbol, period=period, interval="1d")
df.dropna(inplace=True)

if len(df) < 15:
    st.error("❌ Data terlalu sedikit")
    st.stop()

# ======================================================
# MODE & DATA STATUS
# ======================================================
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
# LATEST VALUE (SAFE FLOAT)
# ======================================================
price = float(df["Close"].iloc[-1])
rsi = float(df["RSI"].iloc[-1])
macd = float(df["MACD"].iloc[-1])
signal = float(df["Signal"].iloc[-1])
ma_fast = float(df["MA_fast"].iloc[-1])

# ======================================================
# SUPPORT & RESISTANCE (FIX ERROR)
# ======================================================
low_roll = df["Low"].rolling(20).min()
high_roll = df["High"].rolling(20).max()

last_low = low_roll.iloc[-1]
last_high = high_roll.iloc[-1]

support = float(last_low) if not pd.isna(last_low) else float(df["Low"].iloc[-5:].min())
resistance = float(last_high) if not pd.isna(last_high) else float(df["High"].iloc[-5:].max())

# ======================================================
# ENTRY ZONE
# ======================================================
buy_zone_low = float(support * 1.02)
buy_zone_high = float(ma_fast)

sell_zone_low = float(resistance * 0.98)
sell_zone_high = float(resistance * 1.05)

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
# DECISION
# ======================================================
decision = "BUY" if score >= 3 else "SELL" if score <= -2 else "HOLD"
confidence = "🟢 HIGH" if score >= 4 else "🟡 MEDIUM" if score >= 2 else "🔴 LOW"

# ======================================================
# RISK MANAGEMENT
# ======================================================
stop_loss = support
risk_amount = modal * (risk_pct / 100)
risk_per_share = abs(price - stop_loss)
max_lot = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0

# ======================================================
# TELEGRAM ALERT (BUY ZONE)
# ======================================================
if bot and (buy_zone_low <= price <= buy_zone_high):
    try:
        bot.send_message(
            chat_id=CHAT_ID,
            text=f"""
📢 BUY ZONE ALERT

📊 {symbol}
💰 Harga: {price:,.0f}

🟢 BUY ZONE:
{int(buy_zone_low):,} – {int(buy_zone_high):,}

🎯 Decision: {decision}
{confidence}
"""
        )
    except:
        pass

# ======================================================
# ================= UI ================================
# ======================================================
st.divider()

if data_limited:
    st.warning("⚠️ Data Terbatas — AI & Backtest dinonaktifkan (Quick View Mode)")

st.subheader("📊 Market Snapshot")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Harga", f"{price:,.0f}")
c2.metric("RSI", f"{rsi:.1f}")
c3.metric("AI Prob", "-" if not ai_enabled else f"{ai_prob:.2f}")
c4.metric("Score", score)

st.markdown(f"### 📌 Decision: **{decision}** | Confidence: **{confidence}**")

st.divider()
st.subheader("📍 Entry Zone")

z1, z2 = st.columns(2)
z1.success(f"🟢 BUY ZONE\n\n{int(buy_zone_low):,} – {int(buy_zone_high):,}")
z2.error(f"🔴 SELL ZONE\n\n{int(sell_zone_low):,} – {int(sell_zone_high):,}")

# ======================================================
# BACKTEST (AUTO OFF)
# ======================================================
if not quick_view:
    st.divider()
    st.subheader("📈 Backtest Equity Curve")

    equity = [modal]
    position = 0

    for i in range(1, len(df)):
        close_i = float(df["Close"].iloc[i])
        ma_i = float(df["MA_fast"].iloc[i])

        if close_i > ma_i and position == 0:
            position = equity[-1] / close_i
        elif close_i < ma_i and position > 0:
            equity.append(position * close_i)
            position = 0
        else:
            equity.append(equity[-1])

    fig, ax = plt.subplots()
    ax.plot(df.index[:len(equity)], equity)
    ax.set_ylabel("Equity (Rp)")
    ax.set_xlabel("Tanggal")
    st.pyplot(fig)

# ======================================================
# RISK INFO
# ======================================================
st.divider()
st.subheader("📌 Risk Management")

r1, r2, r3 = st.columns(3)
r1.metric("Risk Amount", f"Rp {risk_amount:,.0f}")
r2.metric("Stop Loss", f"{stop_loss:,.0f}")
r3.metric("Max Lot", f"{max_lot:,}")
