import pandas as pd

def score_stock(row):
    # Safety: pastikan scalar
    rsi = row.get("RSI", 50)
    if rsi is None or pd.isna(rsi):
        rsi = 50

    trend_score = row.get("TrendScore", 0)
    if trend_score is None or pd.isna(trend_score):
        trend_score = 0

    momentum = row.get("Momentum", 0)
    if momentum is None or pd.isna(momentum):
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
    df["Score"] = df.apply(score_stock, axis=1)

    # Assign Grade
    df["Grade"] = df["Score"].apply(lambda x: "A" if x >= 3 else ("B" if x==2 else "C"))
    return df.sort_values("Score", ascending=False).reset_index(drop=True)
