
from pathlib import Path

import pandas as pd

from pii_rules import detect_pii


DATA_PATH = Path("data/processed/v02_independent_eval.csv")

df = pd.read_csv(DATA_PATH)

required_columns = {"example_id", "category", "text", "label"}

assert required_columns.issubset(df.columns), (
    "Evaluation dataset is missing required columns."
)


# 1. Apply our PII rules to every message.
df["matches"] = df["text"].apply(detect_pii)

df["rule_predicted"] = df["matches"].apply(
    lambda matches: int(len(matches) > 0)
)

df["detected_types"] = df["matches"].apply(
    lambda matches: sorted(
        {match["type"] for match in matches}
    )
)

df["correct"] = df["rule_predicted"] == df["label"]


# 2. Measure rule coverage for each category.
summary = (
    df.groupby("category")
    .agg(
        total=("label", "size"),
        sensitive_examples=("label", "sum"),
        rule_detections=("rule_predicted", "sum"),
        correct=("correct", "sum"),
    )
)

summary["accuracy_percent"] = (
    summary["correct"] / summary["total"] * 100
).round(1)

print("\nRULE COVERAGE BY CATEGORY")
print("-" * 55)
print(summary.to_string())


# 3. Find sensitive messages missed by our rules.
false_negatives = df[
    (df["label"] == 1) &
    (df["rule_predicted"] == 0)
].copy()

print("\nMISSED SENSITIVE EXAMPLES")
print("-" * 55)

print(
    false_negatives[
        ["example_id", "category", "detected_types"]
    ].to_string(index=False)
)

print("\nTotal missed:", len(false_negatives))


# 4. Inspect selected examples locally.
# Do not print the entire dataset or save raw PII to logs.
inspect_ids = [
    "pin_1_1",
    "pin_1_2",
    "account_1_3",
]

selected = df[df["example_id"].isin(inspect_ids)]

print("\nSELECTED EXAMPLES FOR LOCAL INSPECTION")
print("-" * 55)

for _, row in selected.iterrows():
    print("ID:", row["example_id"])
    print("Category:", row["category"])
    print("Expected:", row["label"])
    print("Rule prediction:", row["rule_predicted"])
    print("Text:", row["text"])
    print("-" * 30)
