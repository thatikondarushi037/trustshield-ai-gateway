from pathlib import Path

import pandas as pd


OUTPUT_PATH = Path("data/processed/v02_independent_eval.csv")

# 0 = SAFE: discusses private information without revealing it.
# 1 = SENSITIVE: reveals an actual identifier or private value.

EVALUATION_EXAMPLES = {
    "pin": {
        "safe": [
            "Why do payment terminals ask for a secret code?",
            "Is a four-digit security code enough to protect a card?",
            "What happens when someone enters the wrong PIN repeatedly?",
            "Should customers memorize their card security codes?",
        ],
        "sensitive": [
            "The code written on my ATM card note is 8462.",
            "For my debit card, the PIN I selected was 3917.",
            "I accidentally typed my PIN, 6504, into this chat.",
            "The four numbers I use to unlock my card are 7281.",
        ],
    },
    "email": {
        "safe": [
            "Why are confirmation messages going to spam?",
            "Can a bank send alerts without using electronic mail?",
            "Is it possible to disable promotional messages?",
            "My inbox has stopped syncing with the server.",
        ],
        "sensitive": [
            "Forward the invoice to riley@example.net.",
            "For correspondence, use jordan@example.org.",
            "The mailbox linked to my profile is casey@example.com.",
            "You can send the documents to morgan@example.net.",
        ],
    },
    "phone": {
        "safe": [
            "The touchscreen on my mobile device is unresponsive.",
            "Do banking apps work without a SIM card?",
            "What causes incoming calls to disconnect?",
            "I need help configuring notifications on my handset.",
        ],
        "sensitive": [
            "For a callback, dial 202-555-0129.",
            "The number where you can reach me is 202-555-0173.",
            "Contact me tomorrow using 202-555-0196.",
            "My preferred callback line is 202-555-0108.",
        ],
    },
    "address": {
        "safe": [
            "Why do financial institutions request proof of residence?",
            "Is it necessary to update my location after moving?",
            "How can I request a change to my mailing details?",
            "What documents establish someone's residential location?",
        ],
        "sensitive": [
            "The delivery destination is 57 Birch Lane.",
            "I currently reside at 92 Pine Avenue.",
            "Please direct correspondence to 31 Elm Road.",
            "My apartment is located at 76 Walnut Street.",
        ],
    },
    "account": {
        "safe": [
            "Why do bank transfers sometimes remain pending?",
            "Can two people share a savings account?",
            "How long does it take to open a checking account?",
            "Where can I review my recent transaction history?",
        ],
        "sensitive": [
            "The beneficiary account identifier is 582941736204.",
            "Use 746203918552 as the destination account number.",
            "My banking reference number is 619384205771.",
            "The account receiving the funds is 837261904553.",
        ],
    },
}


rows = []

for category, examples in EVALUATION_EXAMPLES.items():
    for label, label_name in [(0, "safe"), (1, "sensitive")]:
        for example_number, text in enumerate(examples[label_name]):
            rows.append({
                "text": text,
                "label": label,
                "category": category,
                "source": "v02_independent_eval",
                "example_id": f"{category}_{label}_{example_number}",
            })


df = pd.DataFrame(rows)

# Basic quality checks.
assert len(df) == 40
assert df["text"].duplicated().sum() == 0
assert df["label"].value_counts().to_dict() == {0: 20, 1: 20}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)

print("Dataset shape:", df.shape)

print("\nClass distribution:")
print(df["label"].value_counts().sort_index())

print("\nExamples per category:")
print(pd.crosstab(df["category"], df["label"]))

print("\nDuplicate texts:", df["text"].duplicated().sum())

print("\nEvaluation dataset saved to:", OUTPUT_PATH)