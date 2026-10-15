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

evaluation_df = pd.read_csv(
    DATA_DIR / "v02_independent_eval.csv"
)

combined_train = pd.concat(
    [original_train, hard_examples],
    ignore_index=True
)


# Check for exact-text leakage before evaluating.
train_texts = set(
    combined_train["text"].str.strip().str.lower()
)

eval_texts = set(
    evaluation_df["text"].str.strip().str.lower()
)

overlap = train_texts.intersection(eval_texts)

assert len(overlap) == 0, (
    f"Data leakage detected: {len(overlap)} overlapping texts"
)

assert len(evaluation_df) == 40
assert evaluation_df["label"].value_counts().to_dict() == {
    0: 20,
    1: 20,
}

print("Exact-text overlap:", len(overlap))
print("Evaluation examples:", len(evaluation_df))


def build_model():
    return Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                ngram_range=(1, 2)
            )
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                random_state=42
            )
        ),
    ])


def evaluate(name, training_df):
    model = build_model()

    model.fit(
        training_df["text"],
        training_df["label"]
    )

    predictions = model.predict(
        evaluation_df["text"]
    )

    actual = evaluation_df["label"]

    results = evaluation_df[
        ["example_id", "category", "label"]
    ].copy()

    results["predicted"] = predictions
    results["correct"] = (
        results["label"] == results["predicted"]
    )

    print(f"\n{name}")
    print("-" * 50)

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
        round(
            recall_score(actual, predictions),
            3
        )
    )

    print(
        "SENSITIVE F1:",
        round(
            f1_score(actual, predictions),
            3
        )
    )

    print("\nConfusion matrix:")
    print(
        confusion_matrix(
            actual,
            predictions,
            labels=[0, 1]
        )
    )

    category_accuracy = (
        results.groupby("category")["correct"]
        .mean()
        .mul(100)
        .round(1)
    )

    print("\nAccuracy by category (%):")
    print(category_accuracy.to_string())

    errors = results.loc[
        ~results["correct"],
        ["example_id", "category", "label", "predicted"]
    ]

    print("\nIncorrect predictions:", len(errors))

    if not errors.empty:
        print(errors.to_string(index=False))

    return {
        "model": name,
        "accuracy": accuracy_score(actual, predictions),
        "sensitive_precision": precision_score(
            actual, predictions, zero_division=0
        ),
        "sensitive_recall": recall_score(
            actual, predictions
        ),
        "sensitive_f1": f1_score(
            actual, predictions
        ),
    }


baseline_results = evaluate(
    "BASELINE: Original synthetic training",
    original_train
)

improved_results = evaluate(
    "IMPROVED: Synthetic + hard examples",
    combined_train
)

comparison = pd.DataFrame(
    [baseline_results, improved_results]
)

print("\nFINAL COMPARISON")
print("-" * 50)
print(comparison.to_string(index=False))