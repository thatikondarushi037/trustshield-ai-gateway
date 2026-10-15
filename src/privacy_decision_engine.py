
from pathlib import Path

import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from pii_rules import detect_pii


DATA_DIR = Path("data/processed")

# Candidate threshold from exploratory development analysis.
# Must be validated on new, unseen examples.
SAFE_THRESHOLD = 0.50

# Explicit patterns are more specific.
EXPLICIT_TYPES = {
    "EMAIL",
    "PIN",
    "ACCOUNT",
    "PHONE",
    "ADDRESS",
}


def train_model():
    synthetic_df = pd.read_csv(
        DATA_DIR / "v02_synthetic_train.csv"
    )

    hard_df = pd.read_csv(
        DATA_DIR / "v02_hard_examples.csv"
    )

    training_df = pd.concat(
        [synthetic_df, hard_df],
        ignore_index=True
    )

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
        ),
    ])

    model.fit(
        training_df["text"],
        training_df["label"]
    )

    return model


def analyze_message(text, model):
    matches = detect_pii(text)

    detected_types = sorted({
        match["type"] for match in matches
    })

    sensitive_index = list(
        model.classes_
    ).index(1)

    ml_score = float(
        model.predict_proba([text])[0][sensitive_index]
    )

    explicit_matches = [
        match for match in matches
        if match["type"] in EXPLICIT_TYPES
    ]

    context_matches = [
        match for match in matches
        if match["type"].endswith("_CONTEXT")
    ]

    if explicit_matches:
        decision = "SENSITIVE"
        action = "BLOCK_OR_REDACT"
        reason = "Explicit PII pattern detected"

    elif context_matches:
        decision = "REVIEW"
        action = "HOLD"
        reason = "Potential PII detected by context rule"

    elif ml_score >= SAFE_THRESHOLD:
        decision = "REVIEW"
        action = "HOLD"
        reason = "ML score above the safe threshold"

    else:
        decision = "SAFE"
        action = "ALLOW"
        reason = "No rule match and ML score below threshold"

    return {
        "decision": decision,
        "action": action,
        "reason": reason,
        "ml_score": round(ml_score, 4),
        "detected_types": detected_types,
    }


if __name__ == "__main__":
    model = train_model()

    examples = [
        "How can I change my PIN?",
        "My PIN is 4826.",
        "My email is alex@example.com.",
        "What is a PIN used for?",
        "For my debit card, the PIN I selected was 3917.",
        "My phone is broken.",
        "The account receiving the funds is 837261904553.",
    ]

    for text in examples:
        result = analyze_message(text, model)

        print("\nMessage:", text)
        print("Decision:", result["decision"])
        print("Action:", result["action"])
        print("ML score:", result["ml_score"])
        print("Detected types:", result["detected_types"])
        print("Reason:", result["reason"])
        print("-" * 50)
