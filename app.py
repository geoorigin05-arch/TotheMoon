import streamlit as st
import pandas as pd
from data_engine import fetch_price
from scoring import rank_stocks
from ai_model import ai_confidence

st.set_page_config(
    page_title="IDX Professional Trading System v2.4 Update",
    layout="wide"
)

st.title("📊 IDX Professional Trading System v2.4 Update")
st.caption("Top-10 IDX Scan + Manual Input Stabil + AI Confidence + Level Guidance")

# ===============================
# LOAD IDX UNIVERSE
# ===============================
@st.cache_data
def load_idx_universe():
    df = pd.read_csv("idx_universe.csv")
    return df["code"].apply(lambda x: f"{x}.JK").tolist()

IDX = load_idx_universe()

# ===============================
# FETCH PRICE CACHED (per symbol) - Stabil
# ===============================
@st.cache_data(show_spinner=False)
def fetch_price_cached(symbol):
    df = fetch_price(symbol)
    if df is None or df.empty:
        return None
    # Pastikan pakai Adjusted Close jika ada
    if "Adj Close" in df.columns:
        df["Close"] = df["Adj Close"]
    # Hitung indikator jika belum ada
    if "MA50" not in df.columns:
        df["MA50"] = df["Close"].rolling(50).mean()
    if "MA200" not in df.columns:
        df["MA200"] = df["Close"].rolling(200).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["Support"] = df["Low"].rolling(20).min()
    df["Resistance"] = df["High"].rolling(20).max()
    return df.dropna()

# ===============================
# MODE SELECTION
# ===============================
mode = st.radio(
    "🧭 Mode Analisa",
    ["🔥 Auto IDX Scan (Top 10 Trending)", "🎯 Analisa Saham Manual"]
)

# ===============================
# AUTO IDX SCAN - TOP 10
# ===============================
if mode == "🔥 Auto IDX Scan (Top 10 Trending)":
    st.subheader("🔥 IDX Market Scan — Top 10 Trending + Grade A/B/C")

    @st.cache_data(show_spinner=False)
    def get_top10_scan(idx_list):
        dfs = []
        for s in idx_list:
            df = fetch_price_cached(s)
            if df is None or df.empty:
                continue
            last = df.iloc[-1].copy()
            last["Symbol"] = s
            # TrendScore sederhana: RSI + MA50/MA200 ratio
            last["TrendScore"] = (last["Close"]/last["MA50"] + last["Close"]/last["MA200"] + last["RSI"]/100)
            dfs.append(last)
        if not dfs:
            return pd.DataFrame()
        scan_df = pd.DataFrame(dfs)
        scan_df.sort_values(by="TrendScore", ascending=False, inplace=True)
        return scan_df.head(10)

    scan_df = get_top10_scan(IDX)
    if scan_df.empty:
        st.warning("Tidak ada saham memenuhi kriteria")
        st.stop()

    ranked = rank_stocks(scan_df)

    st.dataframe(
        ranked[["Symbol", "Close", "RSI", "TrendScore", "Momentum", "Score", "Grade"]],
        use_container_width=True
    )

    # Pilih untuk analisa manual detail
    symbol = st.selectbox(
        "🎯 Analisa Detail Saham",
        ranked["Symbol"]
    )
    modal_rp = st.number_input(
        "💰 Modal Investasi (Rp)",
        min_value=10_000,
        value=100_000_000,
        step=10_000,
        key="modal_input_scan"
    )

# ===============================
# MANUAL INPUT
# ===============================
else:
    st.subheader("🎯 Analisa Saham Manual")
    symbol_input = st.text_input(
        "Masukkan Kode Saham (contoh: BBCA.JK)",
        value="BBCA.JK",
        key="manual_symbol_input"
    ).upper().strip()

    if symbol_input == "":
        st.stop()
    symbol = symbol_input

    modal_rp = st.number_input(
        "💰 Modal Investasi (Rp)",
        min_value=10_000,
        value=100_000_000,
        step=10_000,
        key="modal_input_manual"
    )

# ===============================
# FETCH DATA STABIL
# ===============================
df = fetch_price_cached(symbol)
if df is None or df.empty:
    st.warning(f"❌ Data untuk {symbol} tidak tersedia / terlalu sedikit. Cek simbol atau pilih saham lain.")
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
# DECISION + LEVELS + RISK MANAGEMENT
# ===============================
decision = "WAIT"
buy_area = (0, 0)
sell_area = (0, 0)
tp_price = None
stop_loss = support * 0.97
lot_size = 100  # 1 lot = 100 saham

if trend == "BULLISH" and rsi < 70 and price <= support * 1.08:
    decision = "BUY"
    buy_area = (support, support * 1.08)
    tp_price = resistance * 0.97
elif rsi > 70 or price >= resistance * 0.97:
    decision = "SELL"
    sell_area = (resistance * 0.97, resistance)
else:
    buy_area = (support, support * 1.08)  # WAIT → target entry

max_lot = int(modal_rp / price / lot_size)

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
# LEVEL / ZONES
# ===============================
st.divider()
st.subheader("📉 Level / Zone Guidance & Risk Management")
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

st.metric("💹 Max Lot (Realistic)", max_lot)
