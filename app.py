import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="IDX Professional Trading System", layout="wide")
st.title("📊 IDX Professional Trading System")
st.caption("Market Insight (Auto IDX) + Decision Support (Input Saham)")

# ======================================================
# 🔥 AUTO IDX UNIVERSE (INFO ONLY)
# ======================================================
@st.cache_data
def load_idx_universe():
    df = pd.read_csv("idx_universe.csv")
    df["listingDate"] = pd.to_datetime(df["listingDate"], errors="coerce")
    df["listing_years"] = (pd.Timestamp.today() - df["listingDate"]).dt.days / 365

    df = df[
        (df["listingBoard"] == "Utama") &
        (df["listing_years"] >= 3) &
        (df["shares"] > 500_000_000)
    ]

    return [f"{c}.JK" for c in df["code"].unique()]

@st.cache_data
def scan_market(ticker):
    df = yf.download(ticker, period="1y", auto_adjust=True, progress=False)
    if df.empty or len(df) < 220:
        return None

    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df.dropna(inplace=True)
    if df.empty:
        return None

    last = df.iloc[-1]
    close = float(last["Close"])
    ma50 = float(last["MA50"])
    ma200 = float(last["MA200"])

    if close > ma50 > ma200:
        return {"ticker": ticker, "price": close}

    return None


st.subheader("🔥 Saham Potensial IDX (Auto – Market Insight)")

candidates = []
for t in load_idx_universe():
    r = scan_market(t)
    if r:
        candidates.append(r)

if candidates:
    for r in candidates[:3]:
        st.success(
            f"**{r['ticker']}**\n"
            f"Harga: {int(r['price']):,}\n"
            f"Alasan: Trend naik MA50 > MA200"
        )
else:
    st.info("Belum ada saham IDX dengan trend kuat saat ini")

st.divider()

# ======================================================
# 🎯 MAIN ANALYSIS (INPUT SAHAM)
# ======================================================
st.sidebar.header("⚙️ Analisa Saham")
symbol = st.sidebar.text_input("Kode Saham (.JK)", "BBCA.JK")
modal = st.sidebar.number_input("Modal (Rp)", value=10_000_000, step=1_000_000)
risk_pct = st.sidebar.slider("Risk per Trade (%)", 1, 10, 2)

df = yf.download(symbol, period="1y", auto_adjust=True, progress=False)

if df.empty or len(df) < 220:
    st.error("❌ Data tidak cukup untuk analisa")
    st.stop()

# ======================================================
# INDICATORS
# ======================================================
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()
df["MA200"] = df["Close"].rolling(200).mean()

delta = df["Close"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
rs = gain.rolling(14).mean() / loss.rolling(14).mean()
df["RSI"] = 100 - (100 / (1 + rs))

df.dropna(inplace=True)
last = df.iloc[-1]

price = float(last["Close"])
ma50 = float(last["MA50"])
ma200 = float(last["MA200"])
rsi = float(last["RSI"])

support = float(df["Low"].rolling(20).min().iloc[-1])
resistance = float(df["High"].rolling(20).max().iloc[-1])

# ======================================================
# DECISION LOGIC
# ======================================================
buy, sell, wait = [], [], []

if price > ma50 > ma200:
    buy.append("Trend naik (MA50 > MA200)")
else:
    wait.append("Trend belum konfirmasi")

if rsi < 70:
    buy.append("RSI sehat")
elif rsi > 70:
    sell.append("RSI overbought (potensi koreksi)")

if price <= support * 1.02:
    buy.append("Harga dekat support")

if price >= resistance * 0.98:
    sell.append("Harga dekat resistance")

# ======================================================
# FINAL DECISION
# ======================================================
if len(buy) >= 3:
    decision = "BUY"
elif len(sell) >= 2:
    decision = "SELL"
else:
    decision = "WAIT"

# ======================================================
# OUTPUT SNAPSHOT
# ======================================================
st.subheader(f"📌 Decision: **{decision}**")

c1, c2, c3 = st.columns(3)
c1.metric("Harga", f"{int(price):,}")
c2.metric("RSI", f"{rsi:.1f}")
c3.metric("Trend", "BULLISH" if price > ma200 else "BEARISH")

# ======================================================
# ALASAN KEPUTUSAN (LENGKAP)
# ======================================================
st.divider()
st.subheader("🧠 Alasan Keputusan")

if decision == "BUY":
    for r in buy:
        st.success("✅ " + r)

elif decision == "SELL":
    for r in sell:
        st.error("❌ " + r)

else:  # WAIT
    if buy:
        st.info("🟡 Sinyal positif:")
        for r in buy:
            st.info("• " + r)

    if sell:
        st.warning("⚠️ Risiko / penahan entry:")
        for r in sell:
            st.warning("• " + r)

    if wait:
        st.info("⏳ Pertimbangan tambahan:")
        for r in wait:
            st.info("• " + r)

# ======================================================
# ACTION PLAN (BUY / SELL / WAIT JELAS)
# ======================================================
buy_area_low = support * 1.01
buy_area_high = support * 1.03
sell_area_low = resistance * 0.99
sell_area_high = resistance * 1.03

st.divider()
st.subheader("📍 Rencana Aksi (Action Plan)")

if decision == "BUY":
    st.success(f"🟢 BUY di area: {int(buy_area_low):,} – {int(buy_area_high):,}")
    st.info(f"🎯 SELL / TP di area: {int(sell_area_low):,} – {int(sell_area_high):,}")

elif decision == "SELL":
    st.error(f"🔴 SELL di area: {int(sell_area_low):,} – {int(sell_area_high):,}")
    st.info("⏳ BUY ulang hanya jika harga kembali ke support")

else:  # WAIT
    st.warning("⏳ WAIT – menunggu harga ideal")
    st.info(f"🟢 BUY jika pullback ke: {int(buy_area_low):,} – {int(buy_area_high):,}")
    st.info(f"🔴 SELL / TAKE PROFIT di: {int(sell_area_low):,} – {int(sell_area_high):,}")

# ======================================================
# RISK MANAGEMENT
# ======================================================
risk_amount = modal * (risk_pct / 100)
risk_per_share = max(price - support, 1)
max_lot = int(risk_amount / (risk_per_share * 100))

st.divider()
st.subheader("📉 Risk Management")
st.metric("Stop Loss", f"{int(support):,}")
st.metric("Max Lot", f"{max_lot:,}")

st.caption("Decision support system — bukan rekomendasi mutlak.")
