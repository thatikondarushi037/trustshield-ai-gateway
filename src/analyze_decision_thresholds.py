
from pathlib import Path

import pandas as pd

from privacy_decision_engine import train_model
from pii_rules import detect_pii


DATA_PATH = Path(
    "data/processed/v02_independent_eval.csv"
)

EXPLICIT_TYPES = {
    "EMAIL", "PIN", "ACCOUNT", "PHONE", "ADDRESS"
}


def main():
    model = train_model()
    df = pd.read_csv(DATA_PATH)

    records = []

    for _, row in df.iterrows():
        text = str(row["text"])
        matches = detect_pii(text)

        types = {m["type"] for m in matches}

        has_explicit = bool(types & EXPLICIT_TYPES)
        has_context = any(
            t.endswith("_CONTEXT") for t in types
        )

        sensitive_index = list(
            model.classes_
        ).index(1)

        score = float(
            model.predict_proba([text])[0][sensitive_index]
        )

        records.append({
            "example_id": row["example_id"],
            "label": int(row["label"]),
            "score": score,
            "has_rule": has_explicit or has_context,
        })

    results = pd.DataFrame(records)

    print("\nTHRESHOLD EXPERIMENT")
    print("-" * 65)

    for threshold in [
        0.30, 0.35, 0.40, 0.45,
        0.50, 0.55, 0.60
    ]:
        # A message is automatically SAFE only when:
        # 1. No PII rule matched.
        # 2. ML score is below the threshold.

        allowed = (
            (~results["has_rule"])
            & (results["score"] < threshold)
        )

        safe_allowed = (
            allowed & (results["label"] == 0)
        ).sum()

        sensitive_allowed = (
            allowed & (results["label"] == 1)
        ).sum()

        total_allowed = allowed.sum()

        print(
            f"Threshold: {threshold:.2f} | "
            f"Allowed: {total_allowed:2d}/40 | "
            f"Safe allowed: {safe_allowed:2d}/20 | "
            f"Sensitive allowed: {sensitive_allowed:2d}/20"
        )

    print("\nSCORE RANGES WITHOUT RULE MATCHES")

    no_rule = results[~results["has_rule"]]

    print(
        no_rule.groupby("label")["score"]
        .agg(["count", "min", "median", "max"])
    )


if __name__ == "__main__":
    main()
