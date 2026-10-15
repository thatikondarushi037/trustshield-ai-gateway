import pandas as pd

df = pd.read_csv("data/processed/privacy_classification.csv")

print("Dataset shape: ", df.shape)
print("\nCloumns: ", df.columns.tolist())
print("\nClass Distribution: ")
print(df["label"].value_counts())


#chekcing duplicates and missing values


print("\nMissing values:")
print(df[["text", "label"]].isna().sum())

print("\nDuplicate texts:")
print(df["text"].duplicated().sum())

print("\nConflicting labels:")
conflicts = df.groupby("text")["label"].nunique()
print((conflicts > 1).sum())

# inspectiong length differnce 

df["text_length"] = df["text"].str.len()

print("\nText length by label:")
print(
    df.groupby("label")["text_length"]
    .agg(["count", "mean", "median", "min", "max"])
)

