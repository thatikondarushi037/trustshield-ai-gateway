"""Offline release/CI privacy and high-confidence secret checks, no service needed."""
import json
import re
import subprocess
from pathlib import Path
from src.settings import ROOT


def inspect(root=ROOT):
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    candidates = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=root).decode().split("\0")
    paths = sorted(set(filter(None, tracked + candidates)))
    prohibited = {".db", ".sqlite", ".sqlite3", ".log", ".joblib", ".pkl", ".pickle", ".pem", ".key", ".safetensors", ".pt", ".pth"}
    patterns = [rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", rb"\b(?:gh[pousr]_[A-Za-z0-9_]{20,255}|github_pat_[A-Za-z0-9_]{40,})\b",
                rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", rb"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"]
    problems = []
    for name in paths:
        p = Path(name)
        if (p.name.startswith(".env") or p.suffix.lower() in prohibited or
                set(p.parts) & {".secrets", "models", "raw", "processed", "holdout", "local-dev", ".venv", ".tools-venv"}):
            problems.append({"file": name, "kind": "prohibited_artifact"})
        contents = (root / name).read_bytes()
        if any(re.search(pattern, contents) for pattern in patterns):
            problems.append({"file": name, "kind": "possible_secret"})
    # Validate reports against available datasets without needing private corpora in CI.
    from src.dataset_audit import load_dataset
    configuration = json.loads((root / "config/dataset_audit.json").read_text())
    loaded, checked = {}, 0
    for spec in configuration["datasets"]:
        try:
            loaded[spec["id"]] = load_dataset(root, spec, loaded)[0]
        except (OSError, KeyError, ValueError):
            continue
    reports = list((root / "reports").glob("*.json")) + list((root / "reports").glob("*.md"))
    payloads = [p.read_text(encoding="utf-8") for p in reports]
    for rows in loaded.values():
        for row in rows:
            if row.get("text"):
                checked += 1
                if any(row["text"] in payload for payload in payloads):
                    problems.append({"kind": "raw_report_text", "row": row["_ref"]})
    return {"files_scanned": len(paths), "dataset_records_checked": checked,
            "problems": problems, "scope": "High-confidence patterns and available full-text matches; not a universal secret detector"}


def main():
    result = inspect()
    print(json.dumps(result))
    return int(bool(result["problems"]))


if __name__ == "__main__":
    raise SystemExit(main())
