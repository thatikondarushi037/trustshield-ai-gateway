import pandas as pd 
from pathlib import Path


DATA_PATH = Path("data/processed/privacy_v02_combined.csv")


df = pd.read_csv(DATA_PATH)

print("Data shape:", df.shape)
print("Columns:", df.columns.tolist())


print("\nDuplicate texts:")
print(df["text"].duplicated().sum())

conflicting_labels = (
    df.groupby("text")["label"]
    .nunique()
    .gt(1)
    .sum()
)

print("\nTexts with conflicting labels:")
print(conflicting_labels)

df["text_length"] = df["text"].str.len()

summary = df.groupby(
    ["source", "label"]
)["text_length"].agg(
    ["count", "mean", "median", "min", "max"]
)

print("\nText length by source and label:")
print(summary.round(2))