import random
import pandas as pd

random.seed(42)

CATEGORY_CONFIG = {
    "email": {
        "values": [
            "alex@example.com",
            "sam@example.org",
            "taylor@example.net",
        ],
        "pairs": [
            (
                "Please help me update the email address linked to my banking profile.",
                "Please update my banking profile email to {value}.",
            ),
            (
                "I want to verify which email address is registered with my account.",
                "I want to verify that {value} is registered with my account.",
            ),
            (
                "Can you explain how to change my email contact details?",
                "Can you change my email contact details to {value}?",
            ),
            (
                "My contact email needs updating, but I cannot find the option.",
                "My contact email is {value}, and I need to update it.",
            ),
        ],
    },

    "pin": {
        "values": ["4826", "7391", "2658", "9147"],
        "pairs": [
            (
                "I need help resetting the PIN associated with my debit card.",
                "I need help resetting my debit card PIN, which is {value}.",
            ),
            (
                "Can you explain how to change the PIN for my ATM card?",
                "Can you change my ATM card PIN from {value}?",
            ),
            (
                "My PIN needs updating, but I do not know the procedure.",
                "My current PIN is {value}, and I want to update it.",
            ),
            (
                "Please explain the process for resetting a forgotten card PIN.",
                "Please help me reset my card PIN. The current PIN is {value}.",
            ),
        ],
    },

    "account": {
        "values": [
            "123456789012",
            "987654321098",
            "456789123012",
            "741852963014",
        ],
        "pairs": [
            (
                "Please explain how I can verify my bank account details.",
                "Please verify my bank account number {value}.",
            ),
            (
                "Where can I find the account number associated with my profile?",
                "My account number is {value}. Can you check it?",
            ),
            (
                "I need help updating the account details linked to my payments.",
                "I need help updating account number {value}.",
            ),
            (
                "Can you tell me how to locate my account number securely?",
                "Can you confirm whether {value} is my account number?",
            ),
        ],
    },

    "phone": {
        "values": [
            "202-555-0142",
            "202-555-0168",
            "202-555-0193",
            "202-555-0117",
        ],
        "pairs": [
            (
                "I would like to update the phone number on my banking profile.",
                "Please update my banking phone number to {value}.",
            ),
            (
                "Can you explain how to verify my registered mobile number?",
                "Can you verify that my mobile number is {value}?",
            ),
            (
                "My contact number needs changing, but I cannot find the settings.",
                "My contact number is {value}, and I need to change it.",
            ),
            (
                "Where can I manage the phone number used for account alerts?",
                "Please use {value} for my account alerts.",
            ),
        ],
    },

    "address": {
        "values": [
            "24 King Street",
            "81 Maple Avenue",
            "17 Oak Road",
            "63 Cedar Lane",
        ],
        "pairs": [
            (
                "I want to update the residential address linked to my account.",
                "I want to update my residential address to {value}.",
            ),
            (
                "Please explain how to verify the mailing address on my profile.",
                "Please verify that my mailing address is {value}.",
            ),
            (
                "My home address has changed, and I need help updating my details.",
                "My home address is {value}, and I need to update it.",
            ),
            (
                "Can you explain where I can edit my registered delivery address?",
                "Can you change my registered delivery address to {value}?",
            ),
        ],
    },
}


def generate_examples(config):
    rows = []

    for category, settings in config.items():
        values = settings["values"]
        template_pairs = settings["pairs"]

        for template_id, (safe_template, sensitive_template) in enumerate(
            template_pairs
        ):
            value = values[template_id % len(values)]

            safe_text = safe_template
            sensitive_text = sensitive_template.format(value=value)

            pair_id = f"{category}_{template_id}"

            for label, text in [(0, safe_text), (1, sensitive_text)]:
                rows.append({
                    "pair_id": pair_id,
                    "template_id": f"{category}_{template_id}",
                    "category": category,
                    "text": text,
                    "label": label
                })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = generate_examples(CATEGORY_CONFIG)

    print("Dataset shape:", df.shape)

    print("\nClass distribution:")
    print(df["label"].value_counts().sort_index())

    print("\nExamples per category:")
    print(pd.crosstab(df["category"], df["label"]))

    print("\nDuplicate texts:")
    print(df["text"].duplicated().sum())

    print("\nSample examples:")
    print(df.head(6).to_string(index=False))