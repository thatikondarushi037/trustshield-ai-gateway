"""Local runtime configuration. Never log configuration or secret values."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_TEXT_CHARS = 20000
MAX_BODY_BYTES = 96 * 1024


def data_directory():
    return Path(os.environ.get("TRUSTSHIELD_DATA_DIR", str(ROOT / "data")))


def monitoring_token():
    direct = os.environ.get("TRUSTSHIELD_AUDIT_TOKEN", "")
    filename = os.environ.get("TRUSTSHIELD_AUDIT_TOKEN_FILE", "")
    if direct and filename:
        raise ValueError("Ambiguous monitoring configuration")
    if filename:
        direct = Path(filename).read_text(encoding="utf-8").strip()
    return direct


def load_runtime_model():
    # An explicitly configured artifact must never silently fall back to training.
    import joblib
    from src.privacy_decision_engine import train_model
    explicit = os.environ.get("TRUSTSHIELD_MODEL_PATH")
    artifact = Path(explicit) if explicit else ROOT / "models/privacy_model_v02.joblib"
    if explicit or artifact.is_file():
        return joblib.load(artifact)  # trusted local artifact only
    return train_model()  # documented synthetic development/CI fallback
