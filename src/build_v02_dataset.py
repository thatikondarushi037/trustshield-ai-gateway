from pathlib import Path

import pandas as pd

from build_v02_multiocategory import CATEGORY_CONFIG, generate_examples


OLD_DATA_PATH = Path(
    "data/processed/privacy_classification_matched.csv"
)

OUTPUT_PATH = Path(
    "data/processed/privacy_v02_combined.csv"
)


# preparing the  original dataset 

old_df = pd.read_csv(OLD_DATA_PATH)

old_df = old_df[["text", "label"]].copy()

old_df["source"] = "v01_length_matched"
old_df["category"] = "unknown"
old_df["template_id"] = None
old_df["pair_id"] = None


#generating new examples 


new_df = generate_examples(CATEGORY_CONFIG)

new_df["source"] = "v02_synthetic"

print("Original examples:", len(old_df))
print("New examples:", len(new_df))


combined_df = pd.concat(
    [old_df, new_df],
    ignore_index=True
)

print("\nCombined shape:", combined_df.shape)

print("\nClass distribution:")
print(combined_df["label"].value_counts().sort_index())

print("\nSource distribution:")
print(pd.crosstab(combined_df["source"], combined_df["label"]))

OUTPUT_PATH = Path("data/processed/privacy_v02_combined.csv")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

combined_df.to_csv(OUTPUT_PATH, index=False)

print("Dataset saved to:", OUTPUT_PATH)