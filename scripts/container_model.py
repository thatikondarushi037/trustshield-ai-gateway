"""Build a synthetic DEMO artifact without copying datasets or production weights."""
import argparse
import tempfile
from pathlib import Path
from unittest.mock import patch
import joblib
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from src.build_v02_multiocategory import CATEGORY_CONFIG, generate_examples
from src.dataset_audit import literal_assignment
from src.privacy_decision_engine import train_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Refusing to replace an existing model")
    root = Path(__file__).resolve().parents[1]
    examples = generate_examples(CATEGORY_CONFIG)
    train, _ = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=42).split(examples, examples.label, groups=examples.template_id))
    hard = literal_assignment(root / "src/build_v02_hard_examples.py", "HARD_EXAMPLES")
    hard_rows = [{"text": text, "label": label} for group in hard for label, key in ((0, "safe"), (1, "sensitive")) for text in group[key]]
    with tempfile.TemporaryDirectory() as folder:
        directory = Path(folder)
        examples.iloc[train].to_csv(directory / "v02_synthetic_train.csv", index=False)
        pd.DataFrame(hard_rows).to_csv(directory / "v02_hard_examples.csv", index=False)
        with patch("src.privacy_decision_engine.DATA_DIR", directory):
            model = train_model()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, args.output)
    print("Synthetic demo artifact built; production artifact was not used or changed.")


if __name__ == "__main__":
    main()
