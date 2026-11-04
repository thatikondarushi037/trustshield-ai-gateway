"""Allowlisted fingerprint-checked local aggregate reports for the console."""
import hashlib
import json
import os
from src.settings import ROOT

REPORTS = ("dataset_reliability.json", "ml_experiments.json", "holdout_preparation.json")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_manifest(root=ROOT):
    from src.dataset_audit import load_dataset
    configuration = json.loads((root / "config/dataset_audit.json").read_text())
    loaded = {}
    for spec in configuration["datasets"]:
        try:
            loaded[spec["id"]] = load_dataset(root, spec, loaded)[0]
        except (OSError, KeyError, ValueError):
            continue
    files = {}
    for name in REPORTS:
        path = root / "reports" / name
        if path.is_file():
            data = json.loads(path.read_text())
            text = json.dumps(data, ensure_ascii=False)
            if any(r["text"] in text for rows in loaded.values() for r in rows if r.get("text")):
                raise ValueError("Report includes dataset text")
            files[name] = file_hash(path)
    manifest = {"kind": "local_verified_aggregate_index_v1", "reports": files,
                "scope": "Local integrity/privacy checks, not a signature or independent validation"}
    (root / "reports/verified_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def public_reports(root=ROOT):
    try:
        index = json.loads((root / "reports/verified_manifest.json").read_text())
    except (OSError, ValueError):
        return {"status": "NO_VERIFIED_REPORTS", "reports": {}}
    results = {}
    archival_display = False
    for name in REPORTS:
        path = root / "reports" / name
        try:
            if name not in index["reports"] or file_hash(path) != index["reports"][name]:
                continue
            data = json.loads(path.read_text())
            artifact = data.get("artifact_sha256", data.get("model", {}).get("sha256"))
            model_matches = not artifact or ((root / "models/privacy_model_v02.joblib").is_file()
                              and artifact == file_hash(root / "models/privacy_model_v02.joblib"))
            inputs = data.get("inputs_sha256", data.get("input_sha256", {}))
            inputs_match = all((root / file).is_file() and file_hash(root / file) == checksum for file, checksum in inputs.items())
            aligned = model_matches and inputs_match
            if not aligned and os.environ.get("TRUSTSHIELD_ARCHIVE_REPORTS") != "true":
                continue
            archival_display |= not aligned
            if name == "holdout_preparation.json":
                results[name] = {k: data[k] for k in ("status", "records", "eligible_holdout_rows", "blocking_findings")}
            elif name == "dataset_reliability.json":
                results[name] = {"datasets": data["datasets"], "limitations": "Development exposed or uncertain source independence; REVIEW is abstention.",
                                 "model_sha256": artifact, "live_consistency": data.get("live_consistency", {})}
            else:
                results[name] = {k: data[k] for k in ("datasets", "contextual", "calibration", "robustness", "limitations")}
            results[name]["runtime_alignment"] = "MATCHED_LOCAL_INPUTS" if aligned else "ARCHIVED_DIFFERENT_OR_UNAVAILABLE_RUNTIME_INPUTS"
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return {"status": "VERIFIED_LOCAL_AGGREGATES" if results else "NO_VERIFIED_REPORTS", "reports": results,
            "archival_display": archival_display}
