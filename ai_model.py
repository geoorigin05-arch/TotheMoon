import joblib
import os
from sklearn.linear_model import LogisticRegression

MODEL_FILE = "ai_model.pkl"

def train_ai(df):
    """Train AI model only if data cukup"""
    X, y = [], []

    for i in range(60, len(df)-5):
        X.append([
            df["RSI"].iloc[i],
            df["Close"].iloc[i] / df["MA50"].iloc[i],
            df["Close"].iloc[i] / df["MA200"].iloc[i],
        ])
        y.append(int(df["Close"].iloc[i+5] > df["Close"].iloc[i]))

    if len(X) == 0:
        return None  # data tidak cukup untuk train

    model = LogisticRegression()
    model.fit(X, y)
    joblib.dump(model, MODEL_FILE)
    return model

def load_ai_model(df):
    if os.path.exists(MODEL_FILE):
        return joblib.load(MODEL_FILE)

    model = train_ai(df)
    return model  # bisa None jika data pendek

def ai_confidence(df):
    model = load_ai_model(df)
    if model is None:
        return 0.5  # default confidence jika data pendek

    last = df.iloc[-1]
    prob = model.predict_proba([[
        last["RSI"],
        last["Close"] / last["MA50"],
        last["Close"] / last["MA200"]
    ]])[0][1]

    return float(prob)
