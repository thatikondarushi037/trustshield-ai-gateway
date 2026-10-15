import pandas as pd
from pathlib import Path

examples = [
    ("How can I change my PIN?", "My PIN is 4826."),
    ("How do I update my email?", "My email is alex@example.com."),
    ("Can I change my home address?", "My home address is 24 King Street."),
    ("How do I verify my passport?", "My passport number is X1234567."),
    ("Where can I find my account number?", "My account number is 123456789012."),
    ("Can I update my phone number?", "My phone number is 555-234-7890."),
    ("How can I change my date of birth?", "My date of birth is 14 March 1998."),
    ("Can I update my driver's license?", "My driver's license number is D1234567."),
    ("How do I change my username?", "My username is alex_1998."),
    ("How do I update my contact details?", "You can contact me at alex@example.com."),
]

rows = []

for pair_id, (safe_text, sensitive_text) in enumerate(examples):
    rows.append({
        "pair_id": pair_id,
        "text": safe_text,
        "label": 0
    })

    rows.append({
        "pair_id": pair_id,
        "text": sensitive_text,
        "label": 1
    })

df = pd.DataFrame(rows)

output_path = Path("data/processed/privacy_challenge.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)

df.to_csv(output_path, index=False)

print("Dataset shape:", df.shape)
print("\nLabel distribution:")
print(df["label"].value_counts().sort_index())

print("\nFirst six rows:")
print(df.head(6))