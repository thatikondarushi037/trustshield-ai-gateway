
from pathlib import Path

import joblib

from privacy_decision_engine import train_model


MODEL_DIR = Path("models")
MODEL_PATH = MODEL_DIR / "privacy_model_v02.joblib"


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    model = train_model()

    joblib.dump(model, MODEL_PATH)

    print(f"Model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()
