def score_stock(row):
    # Ambil RSI, TrendScore, Momentum → pastikan scalar
    rsi = row.get("RSI", 50)
    trend_score = row.get("TrendScore", 0)
    momentum = row.get("Momentum", 0)

    # Jika masih NaN / Series → ganti default
    rsi = float(rsi) if pd.notna(rsi) else 50
    trend_score = float(trend_score) if pd.notna(trend_score) else 0
    momentum = float(momentum) if pd.notna(momentum) else 0

    score = 0
    if rsi < 65:
        score += 1
    if trend_score > 1:
        score += 1
    if momentum > 0:
        score += 1

    return score

def rank_stocks(df):
    df["Score"] = df.apply(score_stock, axis=1)

    # Assign Grade
    df["Grade"] = df["Score"].apply(lambda x: "A" if x >= 3 else ("B" if x==2 else "C"))
    return df.sort_values("Score", ascending=False).reset_index(drop=True)
