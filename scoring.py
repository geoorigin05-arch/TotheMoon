def score_stock(row):
    score = 0

    if row["RSI"] < 65:
        score += 30
    elif row["RSI"] < 70:
        score += 15

    score += min((row["TrendScore"] - 1) * 100, 30)

    return round(score, 1)

def rank_stocks(df):
    df["Score"] = df.apply(score_stock, axis=1)
    return df.sort_values("Score", ascending=False)
