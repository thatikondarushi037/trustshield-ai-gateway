import pandas as pd
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42

df = pd.read_csv(
    "data/processed/privacy_classification_matched.csv"
)

assert df["text"].notna().all(), "Missing text found"
assert df["label"].notna().all(), "Missing labels found"
assert df["text"].is_unique, "Duplicate texts found"
assert set(df["label"].unique()) == {0, 1}, "Unexpected labels"

print("Total samples:", len(df))

train_df, temp_df = train_test_split(
    df,
    test_size=0.30,
    random_state=RANDOM_STATE,
    stratify=df["label"]
)

val_df, test_df = train_test_split(
    temp_df,
    test_size=0.50,
    random_state=RANDOM_STATE,
    stratify=temp_df["label"]
)

train_df.to_csv("data/processed/train.csv", index=False)
val_df.to_csv("data/processed/validation.csv", index=False)
test_df.to_csv("data/processed/test.csv", index=False)

for name, split in [
    ("TRAIN", train_df),
    ("VALIDATION", val_df),
    ("TEST", test_df)
]:
    print(f"\n{name}: {len(split)} samples")
    print(split["label"].value_counts())