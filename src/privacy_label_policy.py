SAFE = 0
SENSITIVE = 1

LABEL_NAMES ={
    SAFE: "SAFE",
    SENSITIVE: "SENSITIVE"
}

LABEL_POLICY = {
    "SAFE": [
        "Questions about personal information without revealing a value",
        "General explanations of privacy or account procedures",
        "Messages mentioning identifiers without disclosing them"
    ],
    "SENSITIVE": [
        "Explicit PINs or passwords",
        "Email addresses or phone numbers disclosed as contact details",
        "Personal addresses",
        "Passport, license, or account numbers",
        "Other personal identifiers covered by the project policy"
    ]
}

if __name__ == "__main__":
    for label, rules in LABEL_POLICY.items():
        print(f"\n{label}")

        for rule in rules:
            print(f"- {rule}")