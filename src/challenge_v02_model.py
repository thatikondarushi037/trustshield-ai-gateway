from pathlib import Path

import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix


DATA_DIR = Path("data/processed")

train_df = pd.read_csv(DATA_DIR / "v02_synthetic_train.csv")

model = Pipeline([
    (
        "tfidf",
        TfidfVectorizer(ngram_range=(1, 2))
    ),
    (
        "classifier",
        LogisticRegression(
            max_iter=1000,
            random_state=42
        )
    )
])

model.fit(train_df["text"], train_df["label"])


# Manually designed challenge examples.
# All identifiers are fictional.
challenge_examples = [
    ("My PIN is 4826.", 1),
    ("What is a PIN used for?", 0),

    ("My account number is 123456789012.", 1),
    ("Where can I find my account number?", 0),

    ("alex@example.com", 1),
    ("What does an email address look like?", 0),

    ("Call me at 202-555-0142.", 1),
    ("How do I change my phone number?", 0),

    ("I live at 24 King Street.", 1),
    ("How can I update my home address?", 0),

    ("My email is not working.", 0),
    ("My email is sam@example.org.", 1),

    ("Can I reset my PIN without visiting a bank?", 0),
    ("Please don't share my PIN: 7391.", 1),

    ("My account has been locked.", 0),
    ("Account number: 987654321098.", 1),

    ("My new address is 81 Maple Avenue.", 1),
    ("Is it safe to share my address online?", 0),

    ("My phone is broken.", 0),
    ("My mobile number is 202-555-0168.", 1),
]

challenge_df = pd.DataFrame(
    challenge_examples,
    columns=["text", "label"]
)

predictions = model.predict(challenge_df["text"])

challenge_df["predicted"] = predictions
challenge_df["correct"] = (
    challenge_df["label"] == challenge_df["predicted"]
)

print("Challenge examples:", len(challenge_df))

print("\nClassification report:")
print(
    classification_report(
        challenge_df["label"],
        predictions,
        labels=[0, 1],
        target_names=["SAFE", "SENSITIVE"],
        zero_division=0
    )
)

print("\nConfusion matrix:")
print(
    confusion_matrix(
        challenge_df["label"],
        predictions,
        labels=[0, 1]
    )
)

print("\nIncorrect predictions:")
errors = challenge_df[~challenge_df["correct"]]

if errors.empty:
    print("No errors on this challenge set.")
else:
    print(
        errors[
            ["text", "label", "predicted"]
        ].to_string(index=False)
    )
    
# Categorize each challenge example.
categories = [
    "pin", "pin",
    "account", "account",
    "email", "email",
    "phone", "phone",
    "address", "address",
    "email", "email",
    "pin", "pin",
    "account", "account",
    "address", "address",
    "phone", "phone",
]

challenge_df["category"] = categories

# Calculate accuracy for each privacy category.
category_results = (
    challenge_df
    .groupby("category")["correct"]
    .agg(["count", "sum", "mean"])
)

category_results["accuracy_percent"] = (
    category_results["mean"] * 100
)

print("\nAccuracy by privacy category:")
print(
    category_results[
        ["count", "sum", "accuracy_percent"]
    ].to_string()
)