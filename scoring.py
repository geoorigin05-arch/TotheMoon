import pandas as pd

# ===============================
# Scoring saham untuk Grade + Score
# ===============================
def score_stock(row):
    try:
        rsi = float(row.get("RSI",50))
        trendscore = float(row.get("TrendScore",0))
        momentum = float(row.get("Momentum",0))
    except:
        rsi, trendscore, momentum = 50, 0, 0

    score = 0
    if 50 < rsi < 70:
        score += 2
    if trendscore > 1:
        score += 3
    if momentum > 0:
        score += 1
    return score

def grade_stock(score):
    if score >=5:
        return "A"
    elif score >=3:
        return "B"
    else:
        return "C"

# ===============================
# Rank stocks
# ===============================
def rank_stocks(df: pd.DataFrame):
    df = df.copy()
    df["Score"] = df.apply(score_stock, axis=1)
    df["Grade"] = df["Score"].apply(grade_stock)
    # Decision default
    df["Decision"] = df.apply(lambda x: "BUY" if x["Score"]>=5 else ("SELL" if x["Score"]<=2 else "WAIT"), axis=1)
    return df
