from datasets import load_dataset
import pandas as pd
import re


RANDOM_STATE = 42
N_PER_CLASS = 3000


# --------------------------------------------------
# 1. Load SENSITIVE examples
# --------------------------------------------------

pii_dataset = load_dataset(
    "ai4privacy/pii-masking-micro-100k",
    split="train"
)

# Keep only English examples
pii_english = pii_dataset.filter(
    lambda row: row["language"] == "en"
)

sensitive_df = pd.DataFrame({
    "text": pii_english["source_text"],
    "label": 1
})

print("English sensitive examples:", len(sensitive_df))


# --------------------------------------------------
# 2. Load candidate SAFE examples
# --------------------------------------------------

safe_dataset = load_dataset(
    "mteb/banking77",
    split="train"
)

safe_df = safe_dataset.to_pandas()[["text"]].copy()


# --------------------------------------------------
# 3. Remove obvious PII-looking examples
# --------------------------------------------------

def contains_obvious_pii(text):
    text = str(text)

    patterns = [
        r"\b[\w\.-]+@[\w\.-]+\.\w+\b",       # email
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b", # IBAN-like
        r"\b\d{12,19}\b",                     # long card/account-like number
        r"\+?\d[\d\s\-\(\)]{8,}\d",           # phone-like
    ]

    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


safe_df = safe_df[
    ~safe_df["text"].apply(contains_obvious_pii)
].copy()


# Remove missing values and duplicates
safe_df = safe_df.dropna()
safe_df = safe_df.drop_duplicates(subset=["text"])


# Sample exactly 3000
safe_df = safe_df.sample(
    n=N_PER_CLASS,
    random_state=RANDOM_STATE
)

safe_df["label"] = 0


# --------------------------------------------------
# 4. Prepare sensitive data
# --------------------------------------------------

sensitive_df = sensitive_df.dropna()
sensitive_df = sensitive_df.drop_duplicates(subset=["text"])

sensitive_df = sensitive_df.sample(
    n=N_PER_CLASS,
    random_state=RANDOM_STATE
)


# --------------------------------------------------
# 5. Combine both classes
# --------------------------------------------------

df = pd.concat(
    [safe_df, sensitive_df],
    ignore_index=True
)


# Shuffle rows
df = df.sample(
    frac=1,
    random_state=RANDOM_STATE
).reset_index(drop=True)


# --------------------------------------------------
# 6. Inspect
# --------------------------------------------------

print("\nFINAL DATASET")
print("Shape:", df.shape)

print("\nCLASS DISTRIBUTION")
print(df["label"].value_counts())

print("\nFIRST 10 ROWS")
print(df.head(10))


# --------------------------------------------------
# 7. Save
# --------------------------------------------------

output_path = "data/processed/privacy_classification.csv"

df.to_csv(
    output_path,
    index=False
)

print("\nSaved to:", output_path)