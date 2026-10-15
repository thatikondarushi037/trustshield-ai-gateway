from pathlib import Path

import pandas as pd


OUTPUT_PATH = Path("data/processed/v02_hard_examples.csv")

# Each group contains related SAFE and SENSITIVE messages.
# All identifiers below are fictional.
HARD_EXAMPLES = [
    {
        "category": "pin",
        "safe": [
            "Why does a debit card require a PIN?",
            "What should I do if I forget my security PIN?",
            "Does changing my PIN affect online payments?",
        ],
        "sensitive": [
            "The security code for my card is 5832.",
            "I wrote down my PIN as 6149.",
            "Use 2758 as the PIN for my card.",
        ],
    },
    {
        "category": "email",
        "safe": [
            "My email application keeps crashing.",
            "Why am I not receiving verification emails?",
            "Can an email address be changed later?",
        ],
        "sensitive": [
            "Send the receipt to nina@example.net.",
            "You can reach me at dev@example.org.",
            "Use billing@example.com for notifications.",
        ],
    },
    {
        "category": "phone",
        "safe": [
            "My smartphone battery drains quickly.",
            "Why does the banking app request phone access?",
            "Can I receive alerts without a phone?",
        ],
        "sensitive": [
            "Reach me on 202-555-0137.",
            "My contact number is 202-555-0184.",
            "Please call 202-555-0116 tomorrow.",
        ],
    },
    {
        "category": "address",
        "safe": [
            "Why does a bank need proof of address?",
            "Can I update my residential address online?",
            "Is sharing a home address risky?",
        ],
        "sensitive": [
            "Deliver the document to 63 Cedar Avenue.",
            "My residence is 42 Willow Road.",
            "Please send the letter to 18 Oak Street.",
        ],
    },
    {
        "category": "account",
        "safe": [
            "Why was my savings account frozen?",
            "How can I find the account details section?",
            "Is an account number required for transfers?",
        ],
        "sensitive": [
            "The destination account is 734829105632.",
            "Transfer it to account 618204937155.",
            "Use account number 903746182501.",
        ],
    },
]


rows = []

for group_id, group in enumerate(HARD_EXAMPLES):
    for label, key in [(0, "safe"), (1, "sensitive")]:
        for text in group[key]:
            rows.append({
                "text": text,
                "label": label,
                "category": group["category"],
                "source": "v02_hard_examples",
                "group_id": f"hard_{group_id}",
            })


df = pd.DataFrame(rows)

assert df["text"].duplicated().sum() == 0
assert df["label"].value_counts().to_dict() == {0: 15, 1: 15}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)

print("Dataset shape:", df.shape)

print("\nClass distribution:")
print(df["label"].value_counts().sort_index())

print("\nExamples per category:")
print(pd.crosstab(df["category"], df["label"]))

print("\nDuplicate texts:", df["text"].duplicated().sum())