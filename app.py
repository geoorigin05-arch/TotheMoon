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
    page_title="Stock Monitoring System",
    layout="centered"
)

st.title("📊 Stock Monitoring System")
st.caption("Decision Support System • IDX • AI + Technical Analysis")

# ======================================================
# SIDEBAR — INPUT
# ======================================================
st.sidebar.header("⚙️ Trading Parameters")

symbol = st.sidebar.text_input("Kode Saham IDX (.JK)", "GOTO.JK")
period = st.sidebar.selectbox("Periode Data", ["3mo", "6mo", "1y"], index=1)
mode = st.sidebar.selectbox("Mode Trading", ["Swing", "Scalping"])

modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=500_000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 1, 20, 2)

# =======================
# 🧠 CARA MEMBACA (SIDEBAR)
# =======================
with st.sidebar.expander("🧠 Cara Membaca Hasil", expanded=False):
    st.markdown("""
**📍 ENTRY ZONE**
- 🟢 BUY ZONE → Area aman masuk
- 🔴 SELL ZONE → Area target / distribusi

**📈 EQUITY CURVE**
- Naik stabil → strategi sehat
- Banyak drawdown → kurangi agresivitas

**🎯 CONFIDENCE**
- 🟢 HIGH → size normal
- 🟡 MEDIUM → kecilkan size
- 🔴 LOW → tunggu (no trade)
""")

# ======================================================
# LOAD DATA
# ======================================================
df = yf.download(symbol, period=period, interval="1d")
df.dropna(inplace=True)

if len(df) < 20:
    st.error("❌ Data terlalu sedikit untuk dianalisis")
    st.stop()

# ======================================================
# DATA STATUS (SAFE LOGIC)
# ======================================================
data_limited = (period == "3mo") or (len(df) < 50)
quick_view = data_limited  # otomatis quick view

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
# LATEST VALUES (SAFE FLOAT)
# ======================================================
price = float(df["Close"].iloc[-1])
rsi = float(df["RSI"].iloc[-1])
macd = float(df["MACD"].iloc[-1])
signal = float(df["Signal"].iloc[-1])
ma_fast = float(df["MA_fast"].iloc[-1])

# ======================================================
# SUPPORT / RESISTANCE (SAFE 3mo)
# ======================================================
low_roll = df["Low"].rolling(20).min()
high_roll = df["High"].rolling(20).max()

support = float(low_roll.iloc[-1]) if not np.isnan(low_roll.iloc[-1]) else float(df["Low"].iloc[-5:].min())
resistance = float(high_roll.iloc[-1]) if not np.isnan(high_roll.iloc[-1]) else float(df["High"].iloc[-5:].max())

# ======================================================
# ENTRY ZONE
# ======================================================
buy_zone_low = float(support * 1.02)
buy_zone_high = float(ma_fast)

sell_zone_low = float(resistance * 0.98)
sell_zone_high = float(resistance * 1.05)

# ======================================================
# SCORING SYSTEM
# ======================================================
score = 0
if price > ma_fast: score += 1
if macd > signal: score += 1
if rsi < 70: score += 1
if rsi < 30: score += 1

# ======================================================
# AI MODEL (AUTO OFF WHEN DATA LIMITED)
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
decision = "BUY" if score >= 3 else "SELL" if score <= -2 else "HOLD"

confidence = (
    "🟢 HIGH" if score >= 4 else
    "🟡 MEDIUM" if score >= 2 else
    "🔴 LOW"
)

# ======================================================
# RISK MANAGEMENT
# ======================================================
stop_loss = support
risk_amount = modal * (risk_pct / 100)
risk_per_share = abs(price - stop_loss)
max_lot = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0

# ======================================================
# ================= UI OUTPUT ===========================
# ======================================================
st.divider()

if data_limited:
    st.warning("⚠️ **Data Terbatas** — AI & Backtest dinonaktifkan (Quick View Mode)")

st.subheader("📊 Market Snapshot")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Harga", f"{price:,.0f}")
c2.metric("RSI", f"{rsi:.1f}")
c3.metric("AI Prob", "-" if not ai_enabled else f"{ai_prob:.2f}")
c4.metric("Score", score)

st.markdown(
    f"### 📌 Decision: **{decision}** &nbsp;&nbsp;|&nbsp;&nbsp; Confidence: **{confidence}**"
)

# ======================================================
# ENTRY ZONE DISPLAY (SAFE)
# ======================================================
st.divider()
st.subheader("📍 Entry Zone")

z1, z2 = st.columns(2)

z1.success(
    f"🟢 BUY ZONE\n\n"
    f"{int(buy_zone_low) if np.isfinite(buy_zone_low) else '-'} – "
    f"{int(buy_zone_high) if np.isfinite(buy_zone_high) else '-'}"
)

z2.error(
    f"🔴 SELL ZONE\n\n"
    f"{int(sell_zone_low) if np.isfinite(sell_zone_low) else '-'} – "
    f"{int(sell_zone_high) if np.isfinite(sell_zone_high) else '-'}"
)

# ======================================================
# BACKTEST (AUTO OFF IN QUICK VIEW)
# ======================================================
if not quick_view:
    st.divider()
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
st.divider()
st.subheader("📌 Risk Management")

r1, r2, r3 = st.columns(3)
r1.metric("Risk Amount", f"Rp {risk_amount:,.0f}")
r2.metric("Stop Loss", f"{stop_loss:,.0f}")
r3.metric("Max Lot", f"{max_lot:,}")

st.caption("AI Aktif" if ai_enabled else "AI Nonaktif")
