import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

df = pd.read_csv(
    "data/processed/privacy_classification_matched.csv"
)

df["text_length"] = df["text"].str.len()

X = df[["text_length"]]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)

model = LogisticRegression()

model.fit(X_train, y_train)

predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print(
    f"Length-only accuracy: {accuracy:.2%}"
)

print("\nClassification report:")
print(
    classification_report(
        y_test,
        predictions
    )
)