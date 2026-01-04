import streamlit as st
import pandas as pd
from data_engine import scan_universe, fetch_price_latest
from scoring import rank_stocks
from ai_model import ai_confidence  # pastikan ada ai_model.py

st.set_page_config(
    page_title="IDX Professional Trading System v2.9 Ultimate",
    layout="wide"
)

st.title("📊 IDX Professional Trading System v2.9 Ultimate")
st.caption("Top-Ranked + Trending + Grade A/B/C + Manual Default + Buy/Sell/Wait + Fallback Data")

# ===============================
# Load IDX Universe
# ===============================
@st.cache_data
def load_idx_universe():
    df = pd.read_csv("idx_universe.csv")
    return df["code"].apply(lambda x: f"{x}.JK").tolist()

IDX = load_idx_universe()

# ===============================
# Mode selection
# ===============================
mode = st.radio(
    "🧭 Mode Analisa",
    ["🎯 Analisa Saham Manual", "🔥 Auto IDX Scan (Top 10 Ranked)"],
    index=0  # Manual default
)

# ===============================
# Manual input
# ===============================
if mode=="🎯 Analisa Saham Manual":
    st.subheader("🎯 Analisa Saham Manual (Default Display)")
    symbol_input = st.text_input("Masukkan Kode Saham (contoh: BBCA.JK)").upper().strip()
    modal_rp = st.number_input("💰 Modal Investasi (Rp)", value=100_000_000, step=10_000)
    refresh = st.button("🔄 Refresh Harga")

    if not symbol_input:
        st.info("Masukkan kode saham untuk mulai analisa.")
        st.stop()
    symbol = symbol_input
    if refresh or "last_symbol" not in st.session_state or st.session_state.last_symbol != symbol:
        df = fetch_price_latest(symbol)
        st.session_state.last_symbol = symbol
        st.session_state.last_df = df
    else:
        df = st.session_state.get("last_df", None)

# ===============================
# Auto Top10 scan
# ===============================
else:
    st.subheader("🔥 IDX Market Scan — Top 10 Realistic")
    @st.cache_data
    def get_top10_scan():
        return scan_universe(IDX, limit=10)
    scan_df = get_top10_scan()
    if scan_df.empty:
        st.warning("Tidak ada saham memenuhi kriteria")
        st.stop()
    ranked = rank_stocks(scan_df)
    st.dataframe(
        ranked[["Symbol","Close","RSI","TrendScore","Momentum","Score","Grade"]],
        use_container_width=True
    )
    symbol = st.selectbox("🎯 Analisa Detail Saham", ranked["Symbol"])
    df = fetch_price_latest(symbol)

# ===============================
# Safety check
# ===============================
if df is None or df.empty:
    st.error("Data tidak tersedia")
    st.stop()

# ===============================
# Extract latest
# ===============================
last = df.iloc[-1]
price = float(last["Close"])
ma200 = float(last.get("MA200", price))
rsi = float(last.get("RSI",50))
support = float(last.get("Support", price*0.95))
resistance = float(last.get("Resistance", price*1.05))
trend = "BULLISH" if price > ma200 else "BEARISH"

# ===============================
# Metrics
# ===============================
st.divider()
st.subheader(f"📌 {symbol} — {trend}")
c1,c2,c3 = st.columns(3)
c1.metric("Harga", int(price))
c2.metric("RSI", round(rsi,1))
c3.metric("Trend", trend)

# ===============================
# Decision + Levels
# ===============================
decision = "WAIT"
buy_area = (0,0)
sell_area = (0,0)
tp_price = None
stop_loss = support*0.97
max_lot = int(modal_rp/price)

if trend=="BULLISH" and rsi<70 and price<=support*1.08:
    decision="BUY"
    buy_area = (support, support*1.08)
    tp_price = resistance*0.97
elif rsi>70 or price>=resistance*0.97:
    decision="SELL"
    sell_area = (resistance*0.97, resistance)
else:
    buy_area = (support, support*1.08)

st.subheader(f"🧠 Decision: {decision}")
cols=st.columns(3)
if decision=="BUY":
    cols[0].metric("Buy Area", f"{buy_area[0]:.0f}-{buy_area[1]:.0f}")
    cols[1].metric("TP", f"{tp_price:.0f}")
    cols[2].metric("Stop Loss", f"{stop_loss:.0f}")
elif decision=="SELL":
    cols[0].metric("Sell Area", f"{sell_area[0]:.0f}-{sell_area[1]:.0f}")
    cols[1].metric("Stop Loss", f"{stop_loss:.0f}")
    cols[2].metric("—","-")
else:
    cols[0].metric("Buy Area (Target Entry)", f"{buy_area[0]:.0f}-{buy_area[1]:.0f}")
    cols[1].metric("Stop Loss", f"{stop_loss:.0f}")
    cols[2].metric("—","-")

# ===============================
# AI Confidence
# ===============================
st.divider()
st.subheader("🤖 AI Confidence")
conf = ai_confidence(df)
st.progress(conf)
st.caption("AI confidence only — decision tetap rule-based")

# ===============================
# Max lot
# ===============================
st.divider()
st.subheader("💹 Max Lot (Realistic)")
st.metric("Berdasarkan Modal", max_lot)
