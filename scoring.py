import pandas as pd

# ===============================
# Score per saham
# ===============================
def score_stock(row):
    rsi = row.get("RSI", 50)
    try:
        rsi = float(rsi) if pd.notna(rsi) else 50
    except:
        rsi = 50
    score = 0
    if rsi < 65:
        score += 1
    trendscore = row.get("TrendScore", 0)
    if trendscore > 1:
        score += 1
    momentum = row.get("Momentum", 0)
    if momentum > 0:
        score += 1
    return score

# ===============================
# Rank + Grade
# ===============================
def rank_stocks(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["Score"] = df.apply(score_stock, axis=1)
    # Grade A/B/C
    df["Grade"] = df["Score"].apply(lambda x: "A" if x>=3 else "B" if x==2 else "C")
    return df.sort_values(by="Score", ascending=False)
