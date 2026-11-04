"""Development-only comparisons, calibration and selective prediction; no production writes."""
import argparse
import json
import platform
import subprocess
import time
import tracemalloc
from collections import Counter
from pathlib import Path

import httpx
import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

from src.contextual_adapter import OllamaEncoder
from src.dataset_audit import load_dataset, near_duplicates, normalize
from src.dataset_reliability import binary_metrics, digest, evaluate_rows
from src.pii_rules import detect_pii
from src.privacy_decision_engine import EXPLICIT_TYPES, analyze_message
from src.secret_detector import detect_secrets
from src.robustness import run_robustness


def probability_quality(labels, probabilities, bins=10):
    labels, p = np.asarray(labels), np.asarray(probabilities, dtype=float)
    if len(labels) == 0 or len(labels) != len(p) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("Invalid probability inputs")
    reliability, ece = [], 0.0
    for i in range(bins):
        mask = (p >= i / bins) & ((p <= 1) if i == bins - 1 else (p < (i + 1) / bins))
        n = int(mask.sum())
        mean = float(p[mask].mean()) if n else None
        rate = float(labels[mask].mean()) if n else None
        if n:
            ece += n / len(labels) * abs(mean - rate)
        reliability.append({"bin": i, "count": n, "mean_probability": mean, "observed_sensitive_rate": rate})
    return {"brier_score": float(brier_score_loss(labels, p)),
            "log_loss": float(log_loss(labels, np.clip(p, 1e-15, 1 - 1e-15), labels=[0, 1])),
            "expected_calibration_error": ece, "reliability_bins": reliability}


def logit(probabilities):
    p = np.clip(probabilities, 1e-8, 1 - 1e-8)
    return np.log(p / (1 - p)).reshape(-1, 1)


def ensure_separation(left, right):
    if {normalize(r["text"]) for r in left} & {normalize(r["text"]) for r in right}:
        raise ValueError("Calibration/evaluation text overlap")
    for field in ("template_id", "pair_id", "source_group", "group_id"):
        a = {(r["_namespace"], r[field]) for r in left if r.get(field)}
        b = {(r["_namespace"], r[field]) for r in right if r.get(field)}
        if a & b:
            raise ValueError("Calibration/evaluation group overlap")
    if near_duplicates(left, right, threshold=0.90)["candidate_text_pairs"]:
        raise ValueError("Unresolved calibration/evaluation near match")


def selective_metrics(rows, probabilities, threshold):
    allowed, reviews, blocks = [], 0, 0
    for row, score in zip(rows, probabilities):
        matches = detect_pii(row["text"])
        types = {m["type"] for m in matches}
        if detect_secrets(row["text"]) or types & EXPLICIT_TYPES:
            allowed.append(False); blocks += 1
        elif types or score >= threshold:
            allowed.append(False); reviews += 1
        else:
            allowed.append(True)
    labels = [int(r["label"]) for r in rows]
    sensitive = sum(labels); safe = len(labels) - sensitive
    accepted = sum(allowed)
    missed = sum(bool(a) and y == 1 for a, y in zip(allowed, labels))
    burden = sum(not a and y == 0 for a, y in zip(allowed, labels))
    return {"experimental_threshold": threshold, "automatic_forward_coverage": accepted / len(rows),
            "automatic_decision_coverage": (len(rows) - reviews) / len(rows),
            "accepted_request_error_rate": missed / accepted if accepted else None,
            "review_rate": reviews / len(rows), "false_safe_rate_sensitive": missed / sensitive if sensitive else None,
            "safe_withholding_burden": burden / safe if safe else None, "blocked": blocks}


def timing(call, texts):
    durations = []
    call(texts[0])  # warm-up, explicitly excluded
    tracemalloc.start()
    for text in texts:
        start = time.perf_counter()
        call(text)
        durations.append((time.perf_counter() - start) * 1000)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"warm_requests": len(texts), "median_ms": float(np.median(durations)),
            "p95_ms": float(np.percentile(durations, 95)), "python_peak_allocated_bytes": peak,
            "memory_scope": "Python tracemalloc only; excludes native allocators and Ollama process/GPU"}


def run(root, contextual=True):
    manifest = json.loads((root / "config/dataset_audit.json").read_text())
    loaded, hashes, missing = {}, {}, []
    for spec in manifest["datasets"]:
        try:
            rows, _, checksum = load_dataset(root, spec, loaded)
            loaded[spec["id"]] = rows
            if checksum:
                hashes[spec["path"]] = checksum
        except (OSError, KeyError, ValueError):
            missing.append(spec["id"])
    artifact = root / "models/privacy_model_v02.joblib"
    artifact_hash = digest(artifact)
    model = joblib.load(artifact)
    report = {"status": "COMPLETE", "development_only": True, "artifact_sha256": artifact_hash,
              "tool_sha256": digest(Path(__file__)), "inputs_sha256": hashes,
              "python": platform.python_version(), "missing_datasets": missing,
              "limitations": "All data is development-exposed or has uncertain source independence. No holdout read. Artifact training manifest is absent; the control model provides a matched experimental training recipe, not proof of artifact lineage.",
              "datasets": {}, "contextual": {"status": "NOT_REQUESTED"}}
    eval_ids = [name for name in ("legacy_validation", "legacy_test", "synthetic_validation", "independent_eval", "challenge_csv", "challenge_model", "frozen_eval") if name in loaded]
    for name in eval_ids:
        rows = loaded[name]
        metrics, _ = evaluate_rows(rows, model)
        categories = sorted({r.get("category", "UNRECORDED") for r in rows})
        metrics["per_category"] = {}
        for category in categories:
            subset = [r for r in rows if r.get("category", "UNRECORDED") == category]
            values, _ = evaluate_rows(subset, model)
            metrics["per_category"][category] = {k: values[k] for k in ("ml_only", "hybrid_non_safe", "hybrid_decision_matrix", "review_count")}
        policy_predictions = []
        from src.policy_engine import enforce_policy
        for row in rows:
            policy_predictions.append(int(not enforce_policy(row["text"], analyze_message(row["text"], model))["forward_allowed"]))
        metrics["gateway_non_forwarding"] = binary_metrics([int(r["label"]) for r in rows], policy_predictions)
        report["datasets"][name] = metrics
    if "legacy_validation" in loaded and "legacy_test" in loaded:
        calibration, evaluation = loaded["legacy_validation"], loaded["legacy_test"]
        ensure_separation(calibration, evaluation)
        p_cal = model.predict_proba([r["text"] for r in calibration])[:, list(model.classes_).index(1)]
        p_eval = model.predict_proba([r["text"] for r in evaluation])[:, list(model.classes_).index(1)]
        calibrator = LogisticRegression(C=1.0, random_state=42).fit(logit(p_cal), [int(r["label"]) for r in calibration])
        calibrated = calibrator.predict_proba(logit(p_eval))[:, list(calibrator.classes_).index(1)]
        y = [int(r["label"]) for r in evaluation]
        report["calibration"] = {"method": "Regularized sigmoid (Platt-style), C=1.0, logit input",
            "fit_dataset": "legacy_validation", "fit_rows": len(calibration),
            "evaluation_dataset": "legacy_test", "evaluation_rows": len(evaluation),
            "separation": "No exact/normalized, available scoped group, or cosine>=0.90 overlap. Historical document/person lineage is missing; semantic independence is not proven.",
            "before": probability_quality(y, p_eval), "after": probability_quality(y, calibrated),
            "selective_original": [selective_metrics(evaluation, p_eval, t) for t in (.3, .4, .5, .6, .7)],
            "selective_calibrated": [selective_metrics(evaluation, calibrated, t) for t in (.3, .4, .5, .6, .7)],
            "deployed": False}
    else:
        report["calibration"] = {"status": "UNAVAILABLE_MISSING_LEGACY_SPLITS", "deployed": False}
    if contextual:
        try:
            train = loaded["active_train"]
            encoder = OllamaEncoder()
            metadata = encoder.metadata()
            features = encoder.encode([r["text"] for r in train])
            head = LogisticRegression(max_iter=1000, random_state=42).fit(features, [int(r["label"]) for r in train])
            control = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), LogisticRegression(max_iter=1000, random_state=42))
            control.fit([r["text"] for r in train], [int(r["label"]) for r in train])
            comparison = {"status": "COMPLETE", "encoder": metadata, "dimensions": int(features.shape[1]),
                          "training_rows": len(train), "head_parameter_bytes": head.coef_.nbytes + head.intercept_.nbytes,
                          "deployed": False, "datasets": {},
                          "comparability": "Frozen artifact lineage unverified. Matched TF-IDF control and contextual head use the same 60-row development recipe and same evaluation texts. Development exposure prevents independent winner selection."}
            for name in eval_ids:
                rows = loaded[name]; texts = [r["text"] for r in rows]; y = [int(r["label"]) for r in rows]
                comparison["datasets"][name] = {"contextual": binary_metrics(y, head.predict(encoder.encode(texts)).tolist()),
                                               "tfidf_control": binary_metrics(y, control.predict(texts).tolist()),
                                               "frozen_baseline": report["datasets"][name]["ml_only"]}
            texts = [r["text"] for r in loaded.get("independent_eval", train)[:10]]
            comparison["benchmark"] = {"scope": "Ten identical single-request inputs, warm services; includes contextual HTTP/encoder/head overhead. Not cold-start or concurrent throughput.",
                "frozen_baseline": timing(lambda text: model.predict([text]), texts),
                "contextual": timing(lambda text: head.predict(encoder.encode([text])), texts),
                "baseline_artifact_bytes": artifact.stat().st_size}
            try:
                with httpx.Client(timeout=5, trust_env=False) as client:
                    response = client.get(encoder.url + "/api/ps"); response.raise_for_status()
                    memory = next(item for item in response.json()["models"] if item.get("name") == encoder.model)
                    comparison["benchmark"]["encoder_allocated_vram_bytes_snapshot"] = memory.get("size_vram")
            except (httpx.HTTPError, ValueError, KeyError, StopIteration):
                comparison["benchmark"]["encoder_allocated_vram_bytes_snapshot"] = None
            report["contextual"] = comparison
        except (httpx.HTTPError, ValueError, KeyError):
            report["contextual"] = {"status": "BLOCKED_ENCODER_OR_DATA_UNAVAILABLE", "deployed": False,
                                     "detail": "Check installed nomic-embed-text and local Ollama. Private errors withheld."}
    report["robustness"] = run_robustness(model, root)
    protected = dict(hashes, **{"models/privacy_model_v02.joblib": artifact_hash})
    if any(digest(root / name) != checksum for name, checksum in protected.items()):
        raise ValueError("Protected input changed")
    serialized = json.dumps(report)
    if any(r["text"] in serialized for rows in loaded.values() for r in rows if r.get("text")):
        raise ValueError("Report privacy check failed")
    return report


def plot_calibration(report, root):
    if "before" not in report["calibration"]:
        return False
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    figure, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Ideal")
    for method, label in (("before", "Original"), ("after", "Sigmoid (development only)")):
        bins = [b for b in report["calibration"][method]["reliability_bins"] if b["count"]]
        ax.plot([b["mean_probability"] for b in bins], [b["observed_sensitive_rate"] for b in bins], "o-", label=label)
    ax.set(xlabel="Mean predicted sensitive probability", ylabel="Observed sensitive fraction", xlim=(0, 1), ylim=(0, 1),
           title="Legacy test reliability • development evidence")
    ax.legend(); figure.tight_layout()
    figure.savefig(root / "reports/calibration.png", dpi=160)
    plt.close(figure)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--skip-contextual", action="store_true")
    args = parser.parse_args()
    report = run(args.root, not args.skip_contextual)
    (args.root / "reports").mkdir(exist_ok=True)
    report["calibration_plot_created"] = plot_calibration(report, args.root)
    (args.root / "reports/ml_experiments.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"datasets": len(report["datasets"]), "contextual": report["contextual"]["status"],
                      "calibration": report["calibration"].get("method", "UNAVAILABLE"),
                      "robustness_probes": report["robustness"]["overall"]["cases"], "production_updated": False}))


if __name__ == "__main__":
    main()
