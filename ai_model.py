import os
import joblib
from sklearn.linear_model import LogisticRegression

MODEL_FILE = "ai_model.pkl"

def train_ai(df):
    # Pastikan kolom MA50 selalu ada
    if "MA50" not in df.columns:
        df["MA50"] = df["MA200"]

    X, y = [], []

    for i in range(60, len(df)-5):
        X.append([
            df["RSI"].iloc[i],
            df["Close"].iloc[i] / df["MA50"].iloc[i],
            df["Close"].iloc[i] / df["MA200"].iloc[i],
        ])
        y.append(int(df["Close"].iloc[i+5] > df["Close"].iloc[i]))

    if len(X) == 0:
        return None

    model = LogisticRegression()
    model.fit(X, y)
    joblib.dump(model, MODEL_FILE)
    return model

def ai_confidence(df):
    model = load_ai_model(df)
    if model is None:
        return 0.5

    last = df.iloc[-1]

    ma50 = last["MA50"] if "MA50" in last else last["MA200"]

    prob = model.predict_proba([[
        last["RSI"],
        last["Close"] / ma50,
        last["Close"] / last["MA200"]
    ]])[0][1]

    return float(prob)

