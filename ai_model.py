import joblib
import os
from sklearn.linear_model import LogisticRegression

MODEL_FILE = "ai_model.pkl"

def train_ai(df):
    X, y = [], []

    for i in range(60, len(df)-5):
        X.append([
            df["RSI"].iloc[i],
            df["Close"].iloc[i] / df["MA50"].iloc[i],
            df["Close"].iloc[i] / df["MA200"].iloc[i],
        ])
        y.append(int(df["Close"].iloc[i+5] > df["Close"].iloc[i]))

    model = LogisticRegression()
    model.fit(X, y)
    joblib.dump(model, MODEL_FILE)
    return model

def load_ai_model(df):
    if os.path.exists(MODEL_FILE):
        return joblib.load(MODEL_FILE)
    return train_ai(df)

def ai_confidence(df):
    model = load_ai_model(df)
    last = df.iloc[-1]

    prob = model.predict_proba([[
        last["RSI"],
        last["Close"] / last["MA50"],
        last["Close"] / last["MA200"]
    ]])[0][1]

    return float(prob)
