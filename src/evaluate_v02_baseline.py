from pathlib import Path

import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)


DATA_DIR = Path("data/processed")

train_df = pd.read_csv(DATA_DIR / "v02_synthetic_train.csv")
val_df = pd.read_csv(DATA_DIR / "v02_synthetic_validation.csv")

# Verify that no template family appears in both splits.
train_groups = set(train_df["template_id"])
val_groups = set(val_df["template_id"])

assert train_groups.isdisjoint(val_groups), (
    "Template leakage detected!"
)

# Train our existing ML baseline.
model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(ngram_range=(1, 2)),
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000,
            random_state=42,
        ),
    ),
])

model.fit(train_df["text"], train_df["label"])

# Evaluate on unseen template families.
predictions = model.predict(val_df["text"])

print("Validation accuracy:", accuracy_score(
    val_df["label"],
    predictions,
))

print("\nClassification report:")
print(classification_report(
    val_df["label"],
    predictions,
    labels=[0, 1],
    target_names=["SAFE", "SENSITIVE"],
    zero_division=0,
))

print("\nConfusion matrix:")
print(confusion_matrix(
    val_df["label"],
    predictions,
    labels=[0, 1],
))

# Inspect errors without printing the full message contents.
errors = val_df.loc[
    predictions != val_df["label"].to_numpy()
].copy()

errors["predicted_label"] = predictions[
    predictions != val_df["label"].to_numpy()
]

print("\nIncorrect predictions:", len(errors))

if not errors.empty:
    print(
        errors[
            ["category", "template_id", "label", "predicted_label"]
        ].to_string(index=False)
    )