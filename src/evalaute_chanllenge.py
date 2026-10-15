from pathlib import Path

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix

train_df = pd.read_csv("data/processed/train.csv")
challenge_df = pd.read_csv("data/processed/privacy_challenge.csv")

print("Training examples:", len(train_df))
print("Challenge examples:", len(challenge_df))

model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
    ("classifier", LogisticRegression(
        max_iter=1000,
        random_state=42
    ))
])

model.fit(train_df["text"], train_df["label"])

predictions = model.predict(challenge_df["text"])

print("\nClassification report:")
print(classification_report(
    challenge_df["label"],
    predictions,
    labels=[0, 1],
    target_names=["SAFE", "SENSITIVE"],
    zero_division=0
))

print("Confusion matrix:")
print(confusion_matrix(
    challenge_df["label"],
    predictions,
    labels=[0, 1]
))

results = challenge_df.copy()
results["predicted"] = predictions

mistakes = results[results["label"] != results["predicted"]]

print("\nIncorrect predictions:", len(mistakes))

for _, row in mistakes.iterrows():
    print("\nText:", row["text"])
    print("Expected:", row["label"])
    print("Predicted:", row["predicted"])