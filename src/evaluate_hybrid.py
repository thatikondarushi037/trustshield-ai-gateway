
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

from pii_rules import contains_pii


DATA_DIR = Path("data/processed")

original_train = pd.read_csv(
    DATA_DIR / "v02_synthetic_train.csv"
)

hard_examples = pd.read_csv(
    DATA_DIR / "v02_hard_examples.csv"
)

evaluation_df = pd.read_csv(
    DATA_DIR / "v02_independent_eval.csv"
)

combined_train = pd.concat(
    [original_train, hard_examples],
    ignore_index=True
)


# 1. Train the improved ML model.
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

model.fit(
    combined_train["text"],
    combined_train["label"],
)


# 2. Generate predictions from each detector.
actual = evaluation_df["label"]

ml_predictions = model.predict(
    evaluation_df["text"]
)

rule_predictions = evaluation_df["text"].apply(
    lambda text: int(contains_pii(text))
).to_numpy()

hybrid_predictions = (
    (ml_predictions == 1) | (rule_predictions == 1)
).astype(int)


# 3. Evaluate all three systems.
def evaluate(name, predictions):
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
                actual, predictions, zero_division=0
            ),
            3
        )
    )

    print(
        "SENSITIVE recall:",
        round(
            recall_score(
                actual, predictions, zero_division=0
            ),
            3
        )
    )

    print(
        "SENSITIVE F1:",
        round(
            f1_score(
                actual, predictions, zero_division=0
            ),
            3
        )
    )

    print("Confusion matrix:")
    print(
        confusion_matrix(
            actual,
            predictions,
            labels=[0, 1]
        )
    )


evaluate("ML ONLY", ml_predictions)
evaluate("RULES ONLY", rule_predictions)
evaluate("HYBRID", hybrid_predictions)


# 4. Compare ML and hybrid errors without printing raw PII.
results = evaluation_df[
    ["example_id", "category", "label"]
].copy()

results["ml_predicted"] = ml_predictions
results["rule_predicted"] = rule_predictions
results["hybrid_predicted"] = hybrid_predictions

print("\nCases where rules changed the ML prediction:")
changed = results[
    results["ml_predicted"] != results["hybrid_predicted"]
]

print(changed.to_string(index=False))

print("\nHybrid mistakes:")
mistakes = results[
    results["label"] != results["hybrid_predicted"]
]

print(mistakes.to_string(index=False))
