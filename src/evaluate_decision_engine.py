
from pathlib import Path

import pandas as pd

from privacy_decision_engine import (
    train_model,
    analyze_message,
)


DATA_PATH = Path(
    "data/processed/v02_independent_eval.csv"
)


def evaluate_decisions():
    model = train_model()
    df = pd.read_csv(DATA_PATH)

    results = []

    for _, row in df.iterrows():
        prediction = analyze_message(
            str(row["text"]),
            model
        )

        results.append({
            "example_id": row["example_id"],
            "true_label": int(row["label"]),
            "decision": prediction["decision"],
            "ml_score": prediction["ml_score"],
            "detected_types": prediction["detected_types"],
        })

    results_df = pd.DataFrame(results)

    print("\nDECISION DISTRIBUTION")
    print(results_df["decision"].value_counts())

    print("\nDECISIONS BY TRUE LABEL")
    print(
        pd.crosstab(
            results_df["true_label"],
            results_df["decision"]
        )
    )

    false_safe = results_df[
        (results_df["true_label"] == 1)
        & (results_df["decision"] == "SAFE")
    ]

    print("\nSENSITIVE MESSAGES MARKED SAFE")
    print("Count:", len(false_safe))
    print("Example IDs:", false_safe["example_id"].tolist())

    safe_count = (
        results_df["decision"] == "SAFE"
    ).sum()

    review_count = (
        results_df["decision"] == "REVIEW"
    ).sum()

    total = len(results_df)

    print("\nGATEWAY METRICS")
    print(
        f"Automatic SAFE rate: "
        f"{safe_count / total:.2%}"
    )
    print(
        f"REVIEW rate: "
        f"{review_count / total:.2%}"
    )
    print(
        f"False-safe count: {len(false_safe)}"
    )


if __name__ == "__main__":
    evaluate_decisions()
