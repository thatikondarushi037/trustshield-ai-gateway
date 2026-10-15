from pathlib import Path

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from build_v02_multiocategory import CATEGORY_CONFIG, generate_examples


OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

df = generate_examples(CATEGORY_CONFIG)

# Each template family contains related SAFE and SENSITIVE examples.
groups = df["template_id"]

splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.25,
    random_state=42,
)

train_idx, val_idx = next(
    splitter.split(df, df["label"], groups=groups)
)

train_df = df.iloc[train_idx].copy()
val_df = df.iloc[val_idx].copy()

print("Training shape:", train_df.shape)
print("Validation shape:", val_df.shape)

print("\nTraining labels:")
print(train_df["label"].value_counts().sort_index())

print("\nValidation labels:")
print(val_df["label"].value_counts().sort_index())

train_groups = set(train_df["template_id"])
val_groups = set(val_df["template_id"])

overlap = train_groups.intersection(val_groups)

print("\nOverlapping template families:", len(overlap))

assert len(overlap) == 0, "Template leakage detected!"

train_df.to_csv(
    OUTPUT_DIR / "v02_synthetic_train.csv",
    index=False,
)

val_df.to_csv(
    OUTPUT_DIR / "v02_synthetic_validation.csv",
    index=False,
)

print("\nLeakage-safe synthetic splits saved.")