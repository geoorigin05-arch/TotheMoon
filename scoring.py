def score_stock(row):
    score = 0

    # RSI contribution
    if row["RSI"] < 65:
        score += 30
    elif row["RSI"] < 70:
        score += 20
    else:
        score += 10

    # Trend strength
    score += min((row["TrendScore"] - 1) * 100, 30)

    # Momentum contribution
    score += row["Momentum"] * 20  # bobot kecil tapi cukup untuk trending

    return round(score, 1)

def rank_stocks(df):
    df["Score"] = df.apply(score_stock, axis=1)

    # Grade A/B/C
    df["Grade"] = pd.cut(df["Score"],
                         bins=[0, 25, 45, 100],
                         labels=["C", "B", "A"])
    
    return df.sort_values("Score", ascending=False)
