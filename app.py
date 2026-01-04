import streamlit as st
from data_engine import scan_universe, fetch_price
from scoring import rank_stocks
from ai_model import ai_confidence
import pandas as pd

st.set_page_config(
    page_title="IDX Professional Trading System v2.0",
    layout="wide"
)

st.title("📊 IDX Professional Trading System v2.0")
st.caption("Top-Ranked Realistic + Trending + Grade A/B/C")

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
    ["🔥 Auto IDX Scan (Top Ranked)", "🎯 Analisa Saham Manual"]
)

# ===============================
# AUTO IDX SCAN
# ===============================
if mode == "🔥 Auto IDX Scan (Top Ranked)":
    st.subheader("🔥 IDX Market Scan — Top Ranked Realistic")

    scan_df = scan_universe(IDX, limit=50)
    if scan_df.empty:
        st.warning("Tidak ada saham memenuhi kriteria")
        st.stop()

    ranked = rank_stocks(scan_df)

    st.dataframe(
        ranked[["Symbol", "Close", "RSI", "TrendScore", "Momentum", "Score", "Grade"]],
        use_container_width=True
    )

    symbol = st.selectbox(
        "🎯 Analisa Detail Saham",
        ranked["Symbol"]
    )

# ===============================
# MANUAL INPUT
# ===============================
else:
    st.subheader("🎯 Analisa Saham Manual")
    symbol = st.text_input(
        "Masukkan Kode Saham (contoh: BBCA.JK)",
        "BBCA.JK"
    )

# ===============================
# COMMON ANALYSIS
# ===============================
df = fetch_price(symbol)
if df is None or df.empty:
    st.error(f"❌ Data tidak cukup / saham {symbol} tidak valid")
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
# DECISION ENGINE + LEVELS
# ===============================
decision = "WAIT"
buy_area = (0, 0)
sell_area = (0, 0)
tp_price = None
stop_loss = support * 0.97

if trend == "BULLISH" and rsi < 70 and price <= support * 1.08:
    decision = "BUY"
    # Buy area
    buy_area = (support, support * 1.08)
    # Take profit target
    tp_price = resistance * 0.97
elif rsi > 70 or price >= resistance * 0.97:
    decision = "SELL"
    # Sell zone
    sell_area = (resistance * 0.97, resistance)
else:
    # WAIT → tunjukkan Buy Area untuk entry nanti
    buy_area = (support, support * 1.08)

st.subheader(f"🧠 Decision: {decision}")

# ===============================
# DISPLAY LEVELS
# ===============================
st.markdown("**Level / Zone Guidance:**")

cols = st.columns(3)

if decision == "BUY":
    cols[0].metric("Buy Area", f"{buy_area[0]:.0f} - {buy_area[1]:.0f}")
    cols[1].metric("Take Profit (TP)", f"{tp_price:.0f}")
    cols[2].metric("Stop Loss", f"{stop_loss:.0f}")

elif decision == "SELL":
    cols[0].metric("Sell Area", f"{sell_area[0]:.0f} - {sell_area[1]:.0f}")
    cols[1].metric("Stop Loss", f"{stop_loss:.0f}")
    cols[2].metric("—", "-")

else:  # WAIT
    cols[0].metric("Buy Area (Target Entry)", f"{buy_area[0]:.0f} - {buy_area[1]:.0f}")
    cols[1].metric("Stop Loss", f"{stop_loss:.0f}")
    cols[2].metric("—", "-")
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
