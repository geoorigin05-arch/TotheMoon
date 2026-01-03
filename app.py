import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="AI Stock Trading System FINAL++",
    layout="centered"
)

st.title("📊 AI Stock Trading System (FINAL++)")

# ======================================================
# SIDEBAR INPUT
# ======================================================
st.sidebar.header("⚙️ Parameter")

symbol = st.sidebar.text_input("Kode Saham IDX (.JK)", "GOTO.JK")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y"], index=1)
mode = st.sidebar.selectbox("Mode Trading", ["Swing", "Scalping"])

modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=500_000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 1, 20, 2)

# ======================================================
# LOAD DATA
# ======================================================
df = yf.download(symbol, period=period, interval="1d")
df.dropna(inplace=True)

if len(df) < 30:
    st.error("❌ Data terlalu sedikit untuk analisis")
    st.stop()

# ======================================================
# INDICATORS
# ======================================================
fast = 9 if mode == "Scalping" else 20
slow = 20 if mode == "Scalping" else 50

df["MA_fast"] = df["Close"].rolling(fast).mean()
df["MA_slow"] = df["Close"].rolling(slow).mean()

# RSI
delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
rs = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

# MACD
ema12 = df["Close"].ewm(span=12).mean()
ema26 = df["Close"].ewm(span=26).mean()
df["MACD"] = ema12 - ema26
df["Signal"] = df["MACD"].ewm(span=9).mean()

df.dropna(inplace=True)

# ======================================================
# LATEST VALUES (SAFE FLOAT)
# ======================================================
price = float(df["Close"].iloc[-1])
rsi = float(df["RSI"].iloc[-1])
macd = float(df["MACD"].iloc[-1])
signal = float(df["Signal"].iloc[-1])
ma_fast = float(df["MA_fast"].iloc[-1])

# ======================================================
# SUPPORT / RESISTANCE
# ======================================================
support = float(df["Low"].rolling(20).min().iloc[-1])
resistance = float(df["High"].rolling(20).max().iloc[-1])

# ENTRY ZONE
buy_zone_low = float(support * 1.02)
buy_zone_high = float(ma_fast)

sell_zone_low = float(resistance * 0.98)
sell_zone_high = float(resistance * 1.05)

# ======================================================
# SCORING SYSTEM
# ======================================================
score = 0
if price > ma_fast:
    score += 1
if macd > signal:
    score += 1
if rsi < 70:
    score += 1
if rsi < 30:
    score += 1

# ======================================================
# AI MODEL (ADAPTIVE)
# ======================================================
ai_enabled = len(df) >= 50
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

    latest = scaler.transform([X.iloc[-1]])
    ai_prob = float(model.predict_proba(latest)[0][1])

    if ai_prob > 0.6:
        score += 1
    elif ai_prob < 0.4:
        score -= 1

# ======================================================
# DECISION & CONFIDENCE
# ======================================================
if score >= 3:
    decision = "BUY"
elif score <= -2:
    decision = "SELL"
else:
    decision = "HOLD"

if score >= 4:
    confidence = "🟢 HIGH"
elif score >= 2:
    confidence = "🟡 MEDIUM"
else:
    confidence = "🔴 LOW"

# ======================================================
# STOP LOSS & RISK MANAGEMENT
# ======================================================
stop_loss = float(support)

risk_amount = float(modal * (risk_pct / 100))
risk_per_share = abs(price - stop_loss)

if risk_per_share <= 0:
    max_lot = 0
else:
    max_lot = int(risk_amount / risk_per_share)

# ======================================================
# DISPLAY SUMMARY
# ======================================================
st.subheader("📊 Ringkasan")

c1, c2, c3 = st.columns(3)
c1.metric("Harga", f"{price:,.2f}")
c2.metric("RSI", f"{rsi:.2f}")
c3.metric("AI Prob", f"{ai_prob:.2f}")

st.metric("Score", score)
st.metric("Decision", decision)
st.metric("Confidence", confidence)

# ======================================================
# ENTRY ZONE DISPLAY
# ======================================================
st.subheader("📍 Entry Zone")
st.write(f"🟢 BUY ZONE : {int(buy_zone_low):,} – {int(buy_zone_high):,}")
st.write(f"🔴 SELL ZONE : {int(sell_zone_low):,} – {int(sell_zone_high):,}")

# ======================================================
# BACKTEST EQUITY CURVE (SAFE)
# ======================================================
st.subheader("📈 Backtest – Equity Curve")

equity = [float(modal)]
position = 0.0

for i in range(1, len(df)):
    close_i = float(df["Close"].iloc[i])
    ma_i = float(df["MA_fast"].iloc[i])

    if close_i > ma_i and position == 0:
        position = equity[-1] / close_i
    elif close_i < ma_i and position > 0:
        equity.append(position * close_i)
        position = 0.0
    else:
        equity.append(equity[-1])

equity = equity[:len(df)]

fig, ax = plt.subplots()
ax.plot(df.index[:len(equity)], equity)
ax.set_ylabel("Equity (Rp)")
ax.set_xlabel("Tanggal")
st.pyplot(fig)

# ======================================================
# RISK INFO
# ======================================================
st.subheader("📌 Risk Management")
st.write(f"Modal: Rp {modal:,.0f}")
st.write(f"Risk per Trade: {risk_pct}%")
st.write(f"Risk Amount: Rp {risk_amount:,.0f}")
st.write(f"Stop Loss: {stop_loss:,.2f}")
st.write(f"Max Lot (estimasi): {max_lot:,}")

# ======================================================
# NOTE / BASKET
# ======================================================
with st.expander("🧠 Cara Membaca Hasil (PENTING)", expanded=False):
    st.markdown("""
### 📍 ENTRY ZONE
- 🟢 BUY ZONE → tempat **AMAN masuk**
- 🔴 SELL ZONE → target / distribusi

### 📈 EQUITY CURVE
- Naik stabil → strategi sehat
- Banyak drawdown → jangan agresif

### 🎯 CONFIDENCE
- 🟢 HIGH → size normal
- 🟡 MEDIUM → kecilkan size
- 🔴 LOW → tunggu

📌 *Gunakan sistem sebagai alat bantu, bukan emosi.*
""")

st.caption("AI Aktif" if ai_enabled else "AI Nonaktif (data terbatas)")
