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
    ["🔥 Auto IDX Scan (Top 10 Ranked)", "🎯 Analisa Saham Manual"]
)

if mode == "🔥 Auto IDX Scan (Top 10 Ranked)":
    st.subheader("🔥 IDX Market Scan — Top 10 Realistic")
    
    scan_df = scan_universe(IDX, limit=10)  # Top 10 saja
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

else:  # Manual Input Mode
    st.subheader("🎯 Analisa Saham Manual")
    
    symbol = st.text_input("Masukkan Kode Saham (contoh: BBCA.JK)", "BBCA.JK").upper().strip()
    modal_rp = st.number_input("💰 Modal Investasi (Rp)", value=100_000_000, step=10_000)
    refresh = st.button("🔄 Refresh Harga")
    
    # Fetch fresh data manual
    if refresh or "last_symbol" not in st.session_state or st.session_state.last_symbol != symbol:
        df = fetch_price(symbol)
        st.session_state.last_symbol = symbol
        st.session_state.last_df = df
    else:
        df = st.session_state.get("last_df", None)

    if df is None or df.empty:
        st.warning(f"❌ Data untuk {symbol} tidak tersedia / terlalu sedikit.")
        st.stop()


last = df.iloc[-1]
price = float(last["Close"])
support = float(last["Support"])
resistance = float(last["Resistance"])
rsi = float(last["RSI"])
ma200 = float(last["MA200"])
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
# DECISION ENGINE + LEVELS + RISK
# ===============================
# Default
decision = "WAIT"
buy_area = (0, 0)
sell_area = (0, 0)
tp_price = None
stop_loss = support * 0.97

# Rules
if trend == "BULLISH" and rsi < 70 and price <= support * 1.08:
    decision = "BUY"
    buy_area = (support, support * 1.08)
    tp_price = resistance * 0.97
elif rsi > 70 or price >= resistance * 0.97:
    decision = "SELL"
    sell_area = (resistance * 0.97, resistance)
else:
    # WAIT → tunjukkan Buy Area
    buy_area = (support, support * 1.08)

# Display Decision
st.subheader(f"🧠 Decision: {decision}")

# Display Levels / Zones
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
