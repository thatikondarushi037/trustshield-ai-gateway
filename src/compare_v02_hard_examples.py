from pathlib import Path

import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)


DATA_DIR = Path("data/processed")

original_train = pd.read_csv(
    DATA_DIR / "v02_synthetic_train.csv"
)

hard_examples = pd.read_csv(
    DATA_DIR / "v02_hard_examples.csv"
)

# Same 20 challenge examples used in our previous experiment.
# These examples are for evaluation only.
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

# Ensure challenge examples are not present in training.
combined_train = pd.concat(
    [original_train, hard_examples],
    ignore_index=True
)

assert not set(challenge_df["text"]).intersection(
    set(combined_train["text"])
), "Exact-text leakage detected!"


def build_model():
    return Pipeline([
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
        ),
    ])


def evaluate_model(name, training_data):
    model = build_model()

    model.fit(
        training_data["text"],
        training_data["label"]
    )

    predictions = model.predict(
        challenge_df["text"]
    )

    actual = challenge_df["label"]

    print(f"\n{name}")
    print("-" * 45)

    print(
        "Accuracy:",
        round(accuracy_score(actual, predictions), 3)
    )

    print(
        "SENSITIVE precision:",
        round(
            precision_score(
                actual,
                predictions,
                zero_division=0
            ),
            3
        )
    )

    print(
        "SENSITIVE recall:",
        round(recall_score(actual, predictions), 3)
    )

    print(
        "SENSITIVE F1:",
        round(f1_score(actual, predictions), 3)
    )

    print("\nConfusion matrix:")
    print(
        confusion_matrix(
            actual,
            predictions,
            labels=[0, 1]
        )
    )

    errors = challenge_df.loc[
        predictions != actual.to_numpy()
    ].copy()

    errors["predicted"] = predictions[
        predictions != actual.to_numpy()
    ]

    print("\nIncorrect predictions:", len(errors))

    if not errors.empty:
        print(
            errors[
                ["text", "label", "predicted"]
            ].to_string(index=False)
        )


print("Original training examples:", len(original_train))
print("Hard examples:", len(hard_examples))
print("Combined training examples:", len(combined_train))

evaluate_model(
    "BASELINE: Original synthetic training",
    original_train
)

evaluate_model(
    "IMPROVED: Synthetic + hard examples",
    combined_train
)