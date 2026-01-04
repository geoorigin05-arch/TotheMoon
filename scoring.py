import pandas as pd

def score_stock(row):
    # Ambil nilai RSI, TrendScore, Momentum → aman
    rsi = row.get("RSI", 50)
    trend_score = row.get("TrendScore", 0)
    momentum = row.get("Momentum", 0)

    # Pastikan scalar, jika Series atau NaN → ganti default
    if isinstance(rsi, pd.Series):
        rsi = rsi.iloc[-1] if not rsi.empty else 50
    elif pd.isna(rsi):
        rsi = 50

    if isinstance(trend_score, pd.Series):
        trend_score = trend_score.iloc[-1] if not trend_score.empty else 0
    elif pd.isna(trend_score):
        trend_score = 0

    if isinstance(momentum, pd.Series):
        momentum = momentum.iloc[-1] if not momentum.empty else 0
    elif pd.isna(momentum):
        momentum = 0

    score = 0
    if rsi < 65:
        score += 1
    if trend_score > 1:
        score += 1
    if momentum > 0:
        score += 1

    return score

def rank_stocks(df):
    # Pastikan semua kolom numeric dan NaN diganti
    for col in ["RSI","TrendScore","Momentum"]:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df["Score"] = df.apply(score_stock, axis=1)
    df["Grade"] = df["Score"].apply(lambda x: "A" if x >=3 else ("B" if x==2 else "C"))
    return df.sort_values("Score", ascending=False).reset_index(drop=True)
