
from pathlib import Path

import joblib
import pandas as pd

from privacy_decision_engine import analyze_message


MODEL_PATH = Path("models/privacy_model_v02.joblib")

# New synthetic examples, not used in our earlier training
# or threshold experiments.
# Label: 0 = SAFE, 1 = SENSITIVE

EXAMPLES = [
    # EMAIL
    ("email_safe_1", "How do I update the email linked to my profile?", 0),
    ("email_safe_2", "Is it safe to share an email address with an AI?", 0),
    ("email_sensitive_1", "You can reach me at jordan.wells@example.org.", 1),
    ("email_sensitive_2", "Please send the report to mira77@sample.net.", 1),

    # PIN
    ("pin_safe_1", "Why should a debit card PIN be kept private?", 0),
    ("pin_safe_2", "Can I reset a forgotten PIN online?", 0),
    ("pin_sensitive_1", "The secret code for my card is 7392.", 1),
    ("pin_sensitive_2", "I chose 28461 as my banking PIN.", 1),

    # ACCOUNT
    ("account_safe_1", "How do I open a new savings account?", 0),
    ("account_safe_2", "Can banks change account numbers?", 0),
    ("account_sensitive_1", "Deposit the money into account 472819305661.", 1),
    ("account_sensitive_2", "Use bank account 9382716045 for the transfer.", 1),

    # PHONE
    ("phone_safe_1", "Why does my phone battery drain so quickly?", 0),
    ("phone_safe_2", "How can I change my mobile network provider?", 0),
    ("phone_sensitive_1", "Call me on +1 415 555 0198.", 1),
    ("phone_sensitive_2", "You can contact me at 202-555-0174.", 1),

    # ADDRESS
    ("address_safe_1", "How do I change my delivery address?", 0),
    ("address_safe_2", "Can I use a post office box for shipping?", 0),
    ("address_sensitive_1", "Please deliver it to 72 Willow Road.", 1),
    ("address_sensitive_2", "I currently live at 418 Maple Avenue.", 1),
]


def main():
    model = joblib.load(MODEL_PATH)

    records = []

    for example_id, text, label in EXAMPLES:
        result = analyze_message(text, model)

        records.append({
            "example_id": example_id,
            "true_label": label,
            "decision": result["decision"],
            "ml_score": result["ml_score"],
            "detected_types": result["detected_types"],
        })

    df = pd.DataFrame(records)
    REPORT_DIR = Path("reports")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    REPORT_PATH = REPORT_DIR / "frozen_v02_evaluation.csv"

    df.to_csv(REPORT_PATH, index=False)

    print(f"Evaluation saved to: {REPORT_PATH}")
    
   

    print("\nFROZEN V0.2 EVALUATION")
    print("=" * 50)

    print("\nDECISIONS BY TRUE LABEL")
    print(
        pd.crosstab(
            df["true_label"],
            df["decision"]
        )
    )

    sensitive = df[df["true_label"] == 1]
    safe = df[df["true_label"] == 0]

    false_safe = sensitive[
        sensitive["decision"] == "SAFE"
    ]

    safe_allowed = safe[
        safe["decision"] == "SAFE"
    ]

    print("\nPRIVACY METRICS")
    print("Total examples:", len(df))
    print("Sensitive marked SAFE:", len(false_safe))
    print(
        "Sensitive false-safe rate:",
        f"{len(false_safe) / len(sensitive):.2%}"
    )
    print(
        "Safe messages allowed:",
        f"{len(safe_allowed) / len(safe):.2%}"
    )

    print("\nSENSITIVE EXAMPLES MARKED SAFE")
    print(false_safe["example_id"].tolist())

    print("\nSAFE EXAMPLES HELD OR FLAGGED")
    print(
        safe[safe["decision"] != "SAFE"][
            "example_id"
        ].tolist()
    )

    print("\nALL RESULTS (NO RAW MESSAGES)")
    print(
        df[
            ["example_id", "true_label",
             "decision", "ml_score"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()


