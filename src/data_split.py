import pandas as pd
from sklearn.model_selection import train_test_split

# Load dataset
df = pd.read_csv("data/raw/privacy_sample.csv")

# X = inputs
# y = correct answers
X = df["text"]
y = df["label"]

# First: separate test data
X_train_val, X_test, y_train_val, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)

# Second: split remaining data into training and validation
X_train, X_val, y_train, y_val = train_test_split(
    X_train_val,
    y_train_val,
    test_size=1/3,
    random_state=42,
    stratify=y_train_val
)

print("Training samples:", len(X_train))
print("Validation samples:", len(X_val))
print("Test samples:", len(X_test))

print("\nTRAIN LABELS")
print(y_train.value_counts())

print("\nVALIDATION LABELS")
print(y_val.value_counts())

print("\nTEST LABELS")
print(y_test.value_counts())