import pandas as pd

from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

train_df = pd.read_csv("data/processed/train.csv")
val_df = pd.read_csv("data/processed/validation.csv")

X_train = train_df["text"]
y_train = train_df["label"]

X_val = val_df["text"]
y_val = val_df["label"]

dummy = DummyClassifier(
    strategy="most_frequent"   #most frequent 
)

text_model = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 2)                   #indcidal words and pair of consective words
    )),
    ("classifier", LogisticRegression(
        max_iter=1000,
        random_state=42
    ))
])

models = {
    "Dummy baseline": dummy,
    "TF-IDF + Logistic Regression": text_model
}

for name, model in models.items():

    model.fit(X_train, y_train)

    predictions = model.predict(X_val)

    print(f"\n--- {name} ---")

    print("Accuracy:", round(
        accuracy_score(y_val, predictions), 4
    ))

    print("Precision:", round(
        precision_score(y_val, predictions, zero_division=0), 4
    ))

    print("Recall:", round(
        recall_score(y_val, predictions, zero_division=0), 4
    ))

    print("F1:", round(
        f1_score(y_val, predictions, zero_division=0), 4
    ))

    print("Confusion matrix:")
    print(confusion_matrix(y_val, predictions))
    
    
    
# --------------------------------------------------
# 5. Inspect validation mistakes
# --------------------------------------------------

predictions = text_model.predict(X_val)

errors = val_df[
    predictions != y_val.to_numpy()
].copy()

errors["predicted_label"] = predictions[
    predictions != y_val.to_numpy()
]

print("\n--- MODEL ERRORS ---")

for _, row in errors.iterrows():
    print("Text:", row["text"])
    print("Actual label:", row["label"])
    print("Predicted label:", row["predicted_label"])
    print("---")

# --------------------------------------------------
# 6. Inspect learned feature importance
# --------------------------------------------------

vectorizer = text_model.named_steps["tfidf"]
classifier = text_model.named_steps["classifier"]

feature_names = vectorizer.get_feature_names_out()
weights = classifier.coef_[0]

important_features = pd.DataFrame({
    "feature": feature_names,
    "weight": weights
})

print("\n--- TOP SENSITIVE FEATURES ---")
print(
    important_features
    .sort_values("weight", ascending=False)
    .head(15)
)

print("\n--- TOP SAFE FEATURES ---")
print(
    important_features
    .sort_values("weight", ascending=True)
    .head(15)
)