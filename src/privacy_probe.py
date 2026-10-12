import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

train_df = pd.read_csv("data/processed/train.csv")

model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
    ("classifier", LogisticRegression(
        max_iter=1000,
        random_state=42
    ))
])

model.fit(train_df["text"], train_df["label"])

probes = [
    ("How can I change my PIN?", 0),
    ("My PIN is 4826.", 1),

    ("How do I update my address?", 0),
    ("My address is 24 King Street.", 1),

    ("Can I change my email?", 0),
    ("My email is alex@example.com.", 1),

    ("How do I verify my identity?", 0),
    ("My passport number is X1234567.", 1),

    ("Can I update my account details?", 0),
    ("My account number is 123456789012.", 1),
]

for text, expected in probes:

    predicted = int(model.predict([text])[0])
    probability = model.predict_proba([text])[0][1]

    print("\nText:", text)
    print("Expected:", expected)
    print("Predicted:", predicted)
    print(f"Sensitive probability: {probability:.2%}")
    print("Correct:", predicted == expected)