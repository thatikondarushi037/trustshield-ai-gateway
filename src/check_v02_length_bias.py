from pathlib import Path

import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.model_selection import train_test_split


DATA_PATH = Path("data/processed/privacy_v02_combined.csv")

df = pd.read_csv(DATA_PATH)

print("Total examples:", len(df))

print("\nLength shortcut test by source")
print("-" * 45)

for source, group in df.groupby("source"):

    X = group["text"].str.len().to_frame(name="text_length")
    y = group["label"]

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y,
    )

    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_val)

    accuracy = accuracy_score(y_val, predictions)

    balanced_accuracy = balanced_accuracy_score(
        y_val,
        predictions,
    )

    print(f"\nSource: {source}")
    print(f"Training examples: {len(X_train)}")
    print(f"Validation examples: {len(X_val)}")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Balanced accuracy: {balanced_accuracy:.2%}")