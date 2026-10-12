import pandas as pd
import matplotlib.pyplot as plt

# --------------------------------------------------
# 1. Load real processed dataset
# --------------------------------------------------

df = pd.read_csv(
    "data/processed/privacy_classification.csv"
)


# --------------------------------------------------
# 2. Basic structure
# --------------------------------------------------

print("\n--- SHAPE ---")
print(df.shape)

print("\n--- COLUMNS ---")
print(df.columns)

print("\n--- DATA TYPES ---")
print(df.dtypes)


# --------------------------------------------------
# 3. Missing values
# --------------------------------------------------

print("\n--- MISSING VALUES ---")
print(df.isnull().sum())


# --------------------------------------------------
# 4. Duplicate rows
# --------------------------------------------------

print("\n--- DUPLICATES ---")
print(df.duplicated().sum())


# --------------------------------------------------
# 5. Class distribution
# --------------------------------------------------

print("\n--- CLASS DISTRIBUTION ---")
print(df["label"].value_counts())

print("\n--- CLASS PERCENTAGES ---")
print(
    df["label"].value_counts(normalize=True) * 100
)


# --------------------------------------------------
# 6. Text length
# --------------------------------------------------

df["text_length"] = df["text"].str.len()

print("\n--- TEXT LENGTH STATISTICS ---")
print(
    df.groupby("label")["text_length"].describe()
)


# --------------------------------------------------
# 7. Random SAFE examples
# --------------------------------------------------

print("\n--- RANDOM SAFE EXAMPLES ---")

safe_examples = df[
    df["label"] == 0
].sample(
    n=5,
    random_state=42
)

for text in safe_examples["text"]:
    print("-", text)


# --------------------------------------------------
# 8. Random SENSITIVE examples
# --------------------------------------------------

print("\n--- RANDOM SENSITIVE EXAMPLES ---")

sensitive_examples = df[
    df["label"] == 1
].sample(
    n=5,
    random_state=42
)

for text in sensitive_examples["text"]:
    print("-", text)
    
    
    
    
df.boxplot(
    column="text_length",
    by="label"
)

plt.title("text length by privacy class")
plt.suptitle("")
plt.xlabel("Label")
plt.ylabel("number of character")

plt.show()