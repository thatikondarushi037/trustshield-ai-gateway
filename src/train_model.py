import pandas as pd

from sklearn.metrics import(
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score


# Load dataset
df = pd.read_csv("data/raw/privacy_sample.csv")

X = df["text"]
y = df["label"]


# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)


# Convert text into numbers
vectorizer = TfidfVectorizer()

X_train_tfidf = vectorizer.fit_transform(X_train)

X_test_tfidf = vectorizer.transform(X_test)


# Create model
model = LogisticRegression()


print("number  of features:", X_train_tfidf.shape[1])

print("\n Vocabulary")
print(vectorizer.get_feature_names_out())

# Train model
model.fit(X_train_tfidf, y_train)


# Predict
predictions = model.predict(X_test_tfidf)
probabilities = model.predict_proba(X_test_tfidf)


# Evaluate
accuracy = accuracy_score(y_test, predictions)


print("REAL LABELS:")
print(y_test.to_list())

print("\nPREDICTIONS:")
print(predictions)

print("\nACCURACY:")
print(f"{accuracy:.2%}")


print("\nPREDICTION DETAILS")

for text, true_label, prediction, probability in zip(
    X_test,
    y_test,
    predictions,
    probabilities
):
    print("\nText:", text)
    print("True label:", true_label)
    print("Prediction:", prediction)
    print("Probability SAFE:", round(probability[0], 3))
    print("Probability SENSITIVE:", round(probability[1], 3))
    
    
accuracy = accuracy_score(y_test, predictions)
precision = precision_score(y_test, predictions)
recall = recall_score(y_test, predictions)
f1 = f1_score(y_test, predictions)

print("\n METRICS")
print(f"Accuracy: {accuracy:.2%}")
print(f"Precision: {precision:.2%}")
print(f"Recall: {recall:.2%}")
print(f"F1 Score: {f1:.2%}")

print("\n Confusion Matrix")
print(confusion_matrix(y_test, predictions))