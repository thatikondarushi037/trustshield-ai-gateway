
import sys
import tempfile
import unittest
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from privacy_decision_engine import (
    train_model,
    analyze_message,
)


class TestModelPersistence(unittest.TestCase):

    def test_saved_model_matches_original(self):
        # Step 1: Train the model.
        original_model = train_model()

        examples = [
            "How can I change my PIN?",
            "My PIN is 4826.",
            "My email is alex@example.com.",
            "My phone is broken.",
        ]

        # Step 2: Save and reload in a temporary folder.
        with tempfile.TemporaryDirectory() as folder:
            model_path = Path(folder) / "test_model.joblib"

            joblib.dump(original_model, model_path)
            loaded_model = joblib.load(model_path)

            # Step 3: Compare predictions.
            for text in examples:
                original = analyze_message(
                    text, original_model
                )

                loaded = analyze_message(
                    text, loaded_model
                )

                self.assertEqual(
                    original["decision"],
                    loaded["decision"]
                )

                self.assertEqual(
                    original["action"],
                    loaded["action"]
                )

                self.assertEqual(
                    original["detected_types"],
                    loaded["detected_types"]
                )

                self.assertAlmostEqual(
                    original["ml_score"],
                    loaded["ml_score"],
                    places=6
                )


if __name__ == "__main__":
    unittest.main()
