import streamlit as st
import pandas as pd
from data_engine import scan_universe, fetch_price
from scoring import rank_stocks
from ai_model import ai_confidence

st.set_page_config(
    page_title="IDX Professional Trading System",
    layout="wide"
)

st.title("📊 IDX Professional Trading System")
st.caption("Auto Market Scan + Manual Analysis (Production Grade)")

# ===============================
# LOAD IDX UNIVERSE
# ===============================
@st.cache_data
def load_idx_universe():
    df = pd.read_csv("idx_universe.csv")
    return df["code"].apply(lambda x: f"{x}.JK").tolist()

IDX = load_idx_universe()

# ===============================
# MODE SELECTION
# ===============================
mode = st.radio(
    "🧭 Mode Analisa",
    ["🔥 Auto IDX Scan (Ranking)", "🎯 Analisa Saham Manual"]
)

# ===============================
# MODE 1 — AUTO IDX SCAN
# ===============================
if mode == "🔥 Auto IDX Scan (Ranking)":
    st.subheader("🔥 IDX Market Scan — Top Ranked")

    scan_df = scan_universe(IDX, limit=20)
    if scan_df.empty:
        st.warning("Tidak ada saham memenuhi kriteria")
        st.stop()

    ranked = rank_stocks(scan_df)

    st.dataframe(
        ranked[["Symbol", "Close", "RSI", "Score"]],
        use_container_width=True
    )

    symbol = st.selectbox(
        "🎯 Analisa Detail Saham",
        ranked["Symbol"]
    )

# ===============================
# MODE 2 — MANUAL INPUT
# ===============================
else:
    st.subheader("🎯 Analisa Saham Manual")
    symbol = st.text_input(
        "Masukkan Kode Saham (contoh: BBCA.JK)",
        "BBCA.JK"
    )

# ===============================
# COMMON ANALYSIS (BOTH MODES)
# ===============================
df = fetch_price(symbol)
if df is None or df.empty:
    st.error("❌ Data tidak cukup / saham tidak valid")
    st.stop()

last = df.iloc[-1]

price = float(last["Close"])
ma200 = float(last["MA200"])
rsi = float(last["RSI"])
support = float(last["Support"])
resistance = float(last["Resistance"])

trend = "BULLISH" if price > ma200 else "BEARISH"

# ===============================
# METRICS
# ===============================
st.divider()
st.subheader(f"📌 {symbol} — {trend}")

c1, c2, c3 = st.columns(3)
c1.metric("Harga", int(price))
c2.metric("RSI", round(rsi, 1))
c3.metric("Trend", trend)

# ===============================
# DECISION ENGINE
# ===============================
decision = "WAIT"

if trend == "BULLISH" and rsi < 65 and price <= support * 1.05:
    decision = "BUY"
elif rsi > 75 or price >= resistance * 0.98:
    decision = "SELL"

st.subheader(f"🧠 Decision: {decision}")

# ===============================
# AI CONFIDENCE
# ===============================
st.divider()
st.subheader("🤖 AI Confidence")

conf = ai_confidence(df)
st.progress(conf)
st.caption("AI confidence only — decision tetap rule-based")

# ===============================
# RISK MANAGEMENT
# ===============================
st.divider()
st.subheader("📉 Risk Management")

stop_loss = support * 0.97
max_lot = int(100_000_000 / price)

c4, c5 = st.columns(2)
c4.metric("Stop Loss", int(stop_loss))
c5.metric("Max Lot", max_lot)

st.caption("Decision support system — bukan rekomendasi mutlak.")
