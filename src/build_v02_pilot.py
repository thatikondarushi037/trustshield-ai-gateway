import pandas as pd


# we deliberately included both classes  fro each privacy class
patterns = [
    {
        "category": "email",
        "safe": [
            "How can I update my email address?",
            "Where do I change my contact email?",
            "Can I remove an old email from my profile?"
        ],
        "sensitive": [
            "My email address is alex@example.com.",
            "Please contact me at sam@example.org.",
            "You can send the confirmation to taylor@example.net."
        ]
    },
    {
        "category": "account",
        "safe": [
            "Where can I find my account number?",
            "How do I update my account details?",
            "Can I hide my account number in the app?"
        ],
        "sensitive": [
            "My account number is 123456789012.",
            "Please check account 987654321098.",
            "The account number I entered was 456789123012."
        ]
    },
    {
        "category": "pin",
        "safe": [
            "How can I reset my PIN?",
            "Can I change my PIN at an ATM?",
            "What should I do if I forget my PIN?"
        ],
        "sensitive": [
            "My PIN is 4826.",
            "The ATM PIN is 7391.",
            "I entered PIN 2658."
        ]
    }
]

rows = []

for group_id, group in enumerate(patterns):
    for label_name, label_value in [("safe", 0), ("sensitive", 1)]:
        for text in group[label_name]:
            rows.append({
                "group_id": group_id,
                "category": group["category"],
                "text": text,
                "label": label_value
            })

df = pd.DataFrame(rows)

from pathlib import Path

output_path = Path("data/processed/privacy_v02_pilot.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)

print("Dataset shape:", df.shape)
print("\nClass distribution:")
print(df["label"].value_counts().sort_index())

print("\nExamples per category:")
print(pd.crosstab(df["category"], df["label"]))

df.to_csv(output_path, index=False)