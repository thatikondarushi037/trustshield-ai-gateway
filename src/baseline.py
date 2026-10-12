import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score

#load data

df = pd.read_csv("data/raw/privacy_sample.csv")

X = df["text"]
y = df["label"]

# split train and test 

X_train, X_test, y_train, y_test = train_test_split(
    
    X,
    y,
    test_size=0.25,
    random_state=42,
    stratify=y
)



# created a dummy model 

model = DummyClassifier(strategy="most_frequent")

#train 

model.fit(X_train, y_train)

# predict 

predictions = model.predict(X_test)

#evalute

accuracy = accuracy_score(y_test, predictions)

print("REAL LABELS")
print(y_test.to_list())

print("\nMODEL PREDICTIONS")
print(predictions)

print("\nBASELINE ACCURACY:")
print(f"{accuracy:.2%}")