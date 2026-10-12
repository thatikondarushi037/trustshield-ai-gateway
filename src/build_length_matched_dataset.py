import pandas as pd


RANDOM_STATE = 42


# --------------------------------------------------
# 1. Load current dataset
# --------------------------------------------------

df = pd.read_csv(
    "data/processed/privacy_classification.csv"
)

df = df.dropna(subset=["text", "label"]).copy()

df["text_length"] = df["text"].str.len()


# --------------------------------------------------
# 2. Keep only an overlapping length range
# --------------------------------------------------

df = df[
    (df["text_length"] >= 50)
    & (df["text_length"] <= 250)
].copy()

print("\nAFTER LENGTH FILTER")
print(df["label"].value_counts())

print("\nLENGTH STATISTICS")
print(
    df.groupby("label")["text_length"].describe()
)


# --------------------------------------------------
# 3. Put texts into length bins
# --------------------------------------------------

bins = [
    49,
    74,
    99,
    124,
    149,
    174,
    199,
    224,
    250
]

df["length_bin"] = pd.cut(
    df["text_length"],
    bins=bins,
    include_lowest=True
)


# --------------------------------------------------
# 4. Match SAFE and SENSITIVE counts inside each bin
# --------------------------------------------------

matched_parts = []

for length_bin, group in df.groupby(
    "length_bin",
    observed=True
):

    safe = group[group["label"] == 0]
    sensitive = group[group["label"] == 1]

    n = min(
        len(safe),
        len(sensitive)
    )

    if n == 0:
        continue

    safe_sample = safe.sample(
        n=n,
        random_state=RANDOM_STATE
    )

    sensitive_sample = sensitive.sample(
        n=n,
        random_state=RANDOM_STATE
    )

    matched_parts.append(safe_sample)
    matched_parts.append(sensitive_sample)


# --------------------------------------------------
# 5. Combine matched samples
# --------------------------------------------------

matched_df = pd.concat(
    matched_parts,
    ignore_index=True
)

matched_df = matched_df.sample(
    frac=1,
    random_state=RANDOM_STATE
).reset_index(drop=True)


# --------------------------------------------------
# 6. Inspect result
# --------------------------------------------------

print("\n--- MATCHED DATASET ---")

print("\nShape:")
print(matched_df.shape)

print("\nClass distribution:")
print(matched_df["label"].value_counts())

print("\nText length statistics:")
print(
    matched_df
    .groupby("label")["text_length"]
    .describe()
)

print("\nExamples per length bin:")
print(
    matched_df.groupby(
        ["length_bin", "label"],
        observed=True
    ).size()
)


# --------------------------------------------------
# 7. Save only model columns
# --------------------------------------------------

output = matched_df[
    ["text", "label"]
]

output.to_csv(
    "data/processed/privacy_classification_matched.csv",
    index=False
)

print(
    "\nSaved to:",
    "data/processed/privacy_classification_matched.csv"
)