import pandas as pd

# ===============================
# Scoring untuk satu saham
# ===============================
def score_stock(row):
    rsi = row.get("RSI", 50)
    trend = row.get("TrendScore", 1)
    momentum = row.get("Momentum", 0)

    # Pastikan numeric
    rsi = float(rsi) if pd.notna(rsi) else 50
    trend = float(trend) if pd.notna(trend) else 1
    momentum = float(momentum) if pd.notna(momentum) else 0

    score = 0
    if rsi < 65:
        score += 1
    if trend > 1:
        score += 1
    if momentum > 0:
        score += 1
    return score

# ===============================
# Rank & Grade Top10
# ===============================
def rank_stocks(df):
    if df.empty:
        return df
    df["Score"] = df.apply(score_stock, axis=1)
    def grade(x):
        if x==3:
            return "A"
        elif x==2:
            return "B"
        else:
            return "C"
    df["Grade"] = df["Score"].apply(grade)
    return df.sort_values("Score", ascending=False)
