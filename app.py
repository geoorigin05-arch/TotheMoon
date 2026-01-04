import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.linear_model import LogisticRegression

st.set_page_config(
    page_title="IDX Professional Trading System",
    layout="wide"
)

st.title("📊 IDX Professional Trading System")
st.caption("Market Insight (Auto IDX) + Decision Support (Fund Manager Grade)")

# ===============================
# LOAD IDX UNIVERSE
# ===============================
@st.cache_data
def load_idx_universe():
    df = pd.read_csv("idx_universe.csv")
    df = df[df["listingBoard"] == "Utama"]
    return df["code"].apply(lambda x: f"{x}.JK").tolist()

IDX_UNIVERSE = load_idx_universe()

# ===============================
# DATA FETCH
# ===============================
@st.cache_data
def get_price(symbol):
    df = yf.download(symbol, period="1y", auto_adjust=True, progress=False)
    if df.empty or len(df) < 200:
        return None

    df["MA50"] = df["Close"].rolling(50).mean()
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
# FUNDAMENTAL
# ===============================
@st.cache_data
def get_fundamental(symbol):
    try:
        info = yf.Ticker(symbol).info
        return {
            "ROE": info.get("returnOnEquity"),
            "EPS": info.get("trailingEps"),
            "PER": info.get("trailingPE"),
            "PBV": info.get("priceToBook"),
            "MarketCap": info.get("marketCap")
        }
    except:
        return {}

# ===============================
# AI CONFIDENCE (NON-DESTRUCTIVE)
# ===============================
def ai_confidence_score(df):
    X = []
    y = []

    for i in range(60, len(df)-5):
        X.append([
            df["RSI"].iloc[i],
            df["Close"].iloc[i] / df["MA50"].iloc[i],
            df["Close"].iloc[i] / df["MA200"].iloc[i],
        ])
        y.append(int(df["Close"].iloc[i+5] > df["Close"].iloc[i]))

    if len(X) < 50:
        return 0.5

    model = LogisticRegression()
    model.fit(X, y)

    last = df.iloc[-1]
    prob = model.predict_proba([[
        last["RSI"],
        last["Close"] / last["MA50"],
        last["Close"] / last["MA200"],
    ]])[0][1]

    return float(prob)

# ===============================
# MARKET INSIGHT AUTO IDX
# ===============================
st.subheader("🔥 Saham Potensial IDX (Auto – Market Insight)")

potentials = []

for s in IDX_UNIVERSE:
    df = get_price(s)
    if df is None:
        continue

    last = df.iloc[-1]

    if last["Close"] > last["MA50"] > last["MA200"]:
        potentials.append({
            "Symbol": s,
            "Harga": int(last["Close"]),
            "Alasan": "Trend naik (MA50 > MA200)"
        })

    if len(potentials) == 3:
        break

for p in potentials:
    st.markdown(f"**{p['Symbol']}** Harga: `{p['Harga']}`  \nAlasan: {p['Alasan']}")

# ===============================
# INPUT SAHAM
# ===============================
st.divider()
symbol = st.text_input("🎯 Analisa Saham (contoh: BBCA.JK)", "BBCA.JK")

df = get_price(symbol)

if df is None:
    st.error("❌ Data tidak cukup / tidak stabil")
    st.stop()

last = df.iloc[-1]
price = last["Close"]
rsi = last["RSI"]
support = last["Support"]
resistance = last["Resistance"]

trend = "BULLISH" if price > last["MA200"] else "BEARISH"

# ===============================
# DECISION (LOGIKA TIDAK DIUBAH)
# ===============================
decision = "WAIT"

if trend == "BULLISH" and rsi < 65 and price <= support * 1.05:
    decision = "BUY"
elif rsi > 75 or price >= resistance * 0.98:
    decision = "SELL"

st.subheader(f"📌 Decision: {decision}")

# ===============================
# METRICS
# ===============================
c1, c2, c3 = st.columns(3)
c1.metric("Harga", int(price))
c2.metric("RSI", round(rsi, 1))
c3.metric("Trend", trend)

# ===============================
# ALASAN KEPUTUSAN
# ===============================
st.subheader("🧠 Alasan Keputusan")

if decision == "WAIT":
    st.markdown("""
🟡 **Sinyal positif:**
- Trend naik (MA50 > MA200)
- Struktur harga sehat

⚠️ **Penahan entry:**
- Harga belum dekat support ideal
- Risk/Reward belum optimal
""")

elif decision == "BUY":
    st.markdown("""
🟢 **Alasan BUY:**
- Harga dekat support
- Trend kuat
- RSI sehat

🎯 **Buy Area:** dekat support
📈 **Target:** area resistance
""")

else:
    st.markdown("""
🔴 **Alasan SELL:**
- Harga dekat resistance
- RSI overbought

📉 **Aksi:** Ambil profit / kurangi posisi
""")

# ===============================
# RISK MANAGEMENT
# ===============================
st.subheader("📉 Risk Management")

stop_loss = support * 0.97
max_lot = int(100_000_000 / price)

c4, c5 = st.columns(2)
c4.metric("Stop Loss", int(stop_loss))
c5.metric("Max Lot", max_lot)

# ===============================
# FUND MANAGER PANEL
# ===============================
st.divider()
st.subheader("🏦 Fundamental & Valuasi (Fund Manager View)")

f = get_fundamental(symbol)

c6, c7, c8, c9, c10 = st.columns(5)
c6.metric("ROE", "-" if not f.get("ROE") else f"{f['ROE']*100:.1f}%")
c7.metric("EPS", "-" if not f.get("EPS") else f"{f['EPS']:.2f}")
c8.metric("PER", "-" if not f.get("PER") else f"{f['PER']:.1f}")
c9.metric("PBV", "-" if not f.get("PBV") else f"{f['PBV']:.2f}")
c10.metric("Market Cap", "-" if not f.get("MarketCap") else f"{f['MarketCap']/1e12:.1f}T")

# ===============================
# AI CONFIDENCE
# ===============================
st.divider()
st.subheader("🤖 AI Confidence")

conf = ai_confidence_score(df)
st.progress(conf)
st.caption("AI hanya confidence, decision tetap rule-based")

st.caption("Decision support system — bukan rekomendasi mutlak.")
