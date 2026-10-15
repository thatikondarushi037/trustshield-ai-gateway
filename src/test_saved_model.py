
from pathlib import Path

import joblib

from privacy_decision_engine import analyze_message


MODEL_PATH = Path("models/privacy_model_v02.joblib")


def main():
    model = joblib.load(MODEL_PATH)

    examples = [
        "How can I change my PIN?",
        "My PIN is 4826.",
        "My email is alex@example.com.",
    ]

    for example_id, text in enumerate(examples, start=1):
        result = analyze_message(text, model)

        print(f"\nExample ID: {example_id}")
        print("Decision:", result["decision"])
        print("Action:", result["action"])
        print("Detected types:", result["detected_types"])
        print("ML score:", result["ml_score"])


if __name__ == "__main__":
    main()
