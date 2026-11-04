"""Read-only frozen-model evaluation and privacy-safe reliability analysis."""

import argparse
import difflib
import hashlib
import json
import platform
import re
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path

import httpx
import joblib

from src.dataset_audit import load_dataset, normalize
from src.privacy_decision_engine import SAFE_THRESHOLD, analyze_message

EVALUATION_IDS = ("legacy_validation", "legacy_test", "synthetic_validation",
                  "independent_eval", "challenge_csv", "challenge_model", "frozen_eval")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binary_metrics(labels, predictions):
    if len(labels) != len(predictions) or any(x not in (0, 1) for x in labels + predictions):
        raise ValueError("Expected aligned binary labels and predictions")
    tn = sum(y == 0 and p == 0 for y, p in zip(labels, predictions))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))
    tp = sum(y == 1 and p == 1 for y, p in zip(labels, predictions))
    def ratio(a, b):
        return a / b if b else None
    return {"confusion_matrix": [[tn, fp], [fn, tp]], "rows": len(labels),
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
            "f1": ratio(2 * tp, 2 * tp + fp + fn),
            "false_positive_rate": ratio(fp, fp + tn),
            "false_negative_rate": ratio(fn, fn + tp)}


def review_pair(left, right):
    """Inspect raw strings in memory; export structural evidence only."""
    a, b = normalize(left["text"]), normalize(right["text"])
    edits = [(a[i:j], b[k:l]) for tag, i, j, k, l in
             difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if tag != "equal"]
    negation_changed = any(re.search(r"\b(?:not|never|no)\b|n't", x)
                           for pair in edits for x in pair)
    function_words = {"a", "an", "the", "and", "but", "or", "so", "to", "of", "in", "on",
                      "at", "is", "it", "my", "i", "me", "all", "any", "just", "still",
                      "also", "now", "can", "do", "does", "have", "has", "with", "for",
                      "that", "this", "there", "was", "were", "been", "be", "am", "are",
                      "please", "really", "very", "yet"}
    function_edits = all(all(token in function_words for token in re.findall(r"\w+", x))
                         for pair in edits for x in pair)
    ratio = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    if a == b or (ratio >= 0.97 and function_edits and not negation_changed):
        classification = "LIKELY_DUPLICATE"
        rationale = "Identical normalized text or near-identical wording with only function-word/punctuation edits; shared origin not proven."
    else:
        classification = "INCONCLUSIVE"
        rationale = ("High lexical overlap includes negation or content changes; similarity cannot establish semantic equivalence or common origin."
                     if ratio >= 0.9 else "Lexical evidence alone does not establish whether the examples share an origin.")
    return {"left": left["_ref"], "right": right["_ref"], "classification": classification,
            "rationale": rationale, "normalized_character_ratio": ratio,
            "negation_edit": negation_changed, "function_word_or_punctuation_edits_only": function_edits,
            "same_label": left.get("label") == right.get("label"),
            "review_method": "Deterministic local lexical inspection; not a semantic or provenance oracle"}


def source_analysis(loaded):
    result = {"observed": {},
              "builder_declared_label_origin": {"0": "mteb/banking77", "1": "ai4privacy/pii-masking-micro-100k English source_text"},
              "interpretation": "The legacy builder assigns labels by collection, perfectly confounding declared source with assigned label by construction. This is not verified row-level provenance or proof that this model relies on source.",
              "unknowns": ["Upstream revisions and row/document/person identifiers", "License and acquisition evidence",
                           "Whether every positive record actually contains in-scope PII", "Manual lineage and authorship",
                           "Causal contribution of source style versus privacy content to model errors"]}
    for name, rows in loaded.items():
        if name == "active_train":
            continue
        table = defaultdict(Counter)
        for row in rows:
            label = row.get("label") if row.get("label") in {"0", "1"} else "INVALID"
            table[row.get("source") or "NOT_RECORDED"][label] += 1
        result["observed"][name] = {source: dict(sorted(labels.items()))
                                     for source, labels in sorted(table.items())}
    return result


def check_report_privacy(report, rows):
    """Fail conservatively if an input's full text occurs in any report string."""
    def strings(value):
        if isinstance(value, dict):
            return [s for child in value.values() for s in strings(child)]
        if isinstance(value, list):
            return [s for child in value for s in strings(child)]
        return [value] if isinstance(value, str) else []
    outputs = strings(report) + [markdown_report(report)]
    texts = {r["text"] for r in rows if r.get("text")}
    if any(text in output for text in texts for output in outputs):
        raise ValueError("Report privacy check failed; raw content is not displayed")
    return {"input_records_checked": len(rows), "raw_text_matches": 0}


def evaluate_rows(rows, model):
    labels, ml, hybrid, decisions = [], [], [], []
    errors = {"ml_false_positive": [], "ml_false_negative": [],
              "hybrid_false_positive": [], "hybrid_false_negative": []}
    consistency_rows = []
    valid_rows = [r for r in rows if r.get("label") in {"0", "1"} and r.get("text", "").strip()]
    if valid_rows:
        ml = [int(x) for x in model.predict([r["text"] for r in valid_rows])]
    for row, predicted in zip(valid_rows, ml):
        analysis = analyze_message(row["text"], model)
        if analysis["decision"] not in {"SAFE", "REVIEW", "SENSITIVE"}:
            raise ValueError("Unexpected hybrid decision")
        label = int(row["label"])
        detected = int(analysis["decision"] != "SAFE")
        labels.append(label); hybrid.append(detected); decisions.append(analysis["decision"])
        consistency_rows.append((row, analysis))
        for prefix, p in (("ml", predicted), ("hybrid", detected)):
            if p != label:
                key = prefix + ("_false_negative" if label else "_false_positive")
                if len(errors[key]) < 5:
                    errors[key].append(row["_ref"])
    ternary = [[sum(y == label and d == decision for y, d in zip(labels, decisions))
                for decision in ("SAFE", "REVIEW", "SENSITIVE")] for label in (0, 1)]
    return {"rows": len(rows), "valid_rows": len(valid_rows), "excluded_rows": len(rows) - len(valid_rows),
            "ml_only": binary_metrics(labels, ml), "hybrid_non_safe": binary_metrics(labels, hybrid),
            "hybrid_decision_matrix": ternary, "review_count": decisions.count("REVIEW"),
            "error_references": errors}, consistency_rows


def live_consistency(items, base_url):
    """Use only the already running /analyze endpoint; never import src.api."""
    url = httpx.URL(base_url)
    if url.host not in {"127.0.0.1", "localhost", "::1"} or url.scheme != "http":
        raise ValueError("Live comparison requires a loopback HTTP service")
    result = {"endpoint": str(url).rstrip("/") + "/analyze", "checked": 0, "mismatches": 0,
              "mismatch_references": [], "status": "COMPLETE"}
    try:
        with httpx.Client(base_url=base_url, timeout=15, trust_env=False) as client:
            client.get("/health").raise_for_status()
            for row, analysis in items:
                response = client.post("/analyze", json={"text": row["text"]})
                response.raise_for_status()
                live = response.json()
                same = (live.get("decision") == analysis["decision"]
                        and live.get("ml_score") == analysis["ml_score"]
                        and live.get("detected_types") == analysis["detected_types"])
                result["checked"] += 1
                if not same:
                    result["mismatches"] += 1
                    if len(result["mismatch_references"]) < 5:
                        result["mismatch_references"].append(row["_ref"])
    except (httpx.HTTPError, ValueError, KeyError):
        result["status"] = "INCOMPLETE_SERVICE_OR_RESPONSE_ERROR"
    result["scope"] = "Agreement on checked rows and rounded scores only; not model identity or independence proof. No backend, gateway, or audit-write call was made."
    return result


def run_reliability(root, live_api=None):
    manifest_path = root / "config/dataset_audit.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    loaded, checksums, missing = {}, {}, []
    for spec in manifest["datasets"]:
        if ("members" in spec and any(m not in loaded for m in spec["members"])) or (
            "path" in spec and not (root / spec["path"]).is_file()
        ):
            missing.append(spec["id"])
            continue
        rows, _, checksum = load_dataset(root, spec, loaded)
        loaded[spec["id"]] = rows
        if checksum:
            checksums[spec["path"]] = checksum
    model_path = root / "models/privacy_model_v02.joblib"
    model_hash = digest(model_path)
    # Only load this trusted local artifact. joblib/pickle files are executable.
    model = joblib.load(model_path)
    report = {"version": 1, "tool_sha256": digest(Path(__file__)),
              "manifest_sha256": digest(manifest_path), "input_sha256": checksums,
              "source_sha256": {name: digest(root / name) for name in (
                  "src/dataset_audit.py", "src/privacy_decision_engine.py", "src/pii_rules.py",
                  "src/api.py", "src/build_dataset.py") if (root / name).is_file()},
              "environment": {"python": platform.python_version(), "scikit_learn": version("scikit-learn")},
              "model": {"path": "models/privacy_model_v02.joblib", "sha256": model_hash,
                        "type": type(model).__name__, "classes": [int(x) for x in model.classes_],
                        "training_lineage": "Unverified: artifact lacks a signed training/input manifest",
                        "scope": "Existing artifact with current production analyze_message logic; no fit or dump"},
              "semantics": {"positive_label": 1, "matrix_order": "[[TN, FP], [FN, TP]]",
                            "hybrid_positive": "REVIEW or SENSITIVE (not automatic SAFE); REVIEW is abstention, not confirmed disclosure",
                            "hybrid_decision_columns": ["SAFE", "REVIEW", "SENSITIVE"],
                            "decision_threshold_unchanged": SAFE_THRESHOLD,
                            "undefined_metrics": "null when denominator is zero",
                            "pooling": "None; sources, development sets and reused examples are not independent trials"},
              "source_analysis": source_analysis(loaded), "pair_reviews": [], "datasets": {},
              "missing_inputs": missing}
    for a, ai, b, bi in (("legacy_train", 451, "legacy_validation", 87),
                         ("legacy_train", 138, "legacy_test", 70)):
        if a in loaded and b in loaded and len(loaded[a]) >= ai and len(loaded[b]) >= bi:
            report["pair_reviews"].append(review_pair(loaded[a][ai - 1], loaded[b][bi - 1]))
    audit_path = root / "reports/ml1_dataset_audit.json"
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        report["prior_audit_sha256"] = digest(audit_path)
        for pair in report["pair_reviews"]:
            names = [pair[key].split(":")[0] for key in ("left", "right")]
            current_inputs = all(
                audit.get("datasets", {}).get(name, {}).get("sha256") == next(
                    (checksums.get(s.get("path")) for s in manifest["datasets"] if s["id"] == name), None
                ) for name in names)
            pair["audit_inputs_match"] = current_inputs
            if current_inputs:
                for comparison in audit.get("comparisons", []):
                    for example in comparison.get("near", {}).get("examples", []):
                        if (example["left"], example["right"]) == (pair["left"], pair["right"]):
                            pair["prior_audit_cosine"] = example["cosine"]
    all_items = []
    for name in EVALUATION_IDS:
        if name not in loaded:
            continue
        metrics, items = evaluate_rows(loaded[name], model)
        metrics["independence"] = (
            "UNCERTAIN_LEGACY_SOURCE_LINEAGE_AND_NEAR_DUPLICATES" if name.startswith("legacy")
            else "TEMPLATE_SEPARATED_BUT_DEVELOPMENT_EXPOSED" if name == "synthetic_validation"
            else "DEVELOPMENT_EXPOSED_OR_UNVERIFIED_AUTHORSHIP_NOT_NEW_HOLDOUT")
        # Known component overlap is contextual evidence, not artifact training proof.
        active = {normalize(r["text"]) for r in loaded.get("active_train", [])}
        metrics["normalized_overlap_with_current_training_inputs"] = sum(
            normalize(r["text"]) in active for r in loaded[name])
        report["datasets"][name] = metrics
        all_items.extend(items)
    report["live_consistency"] = live_consistency(all_items, live_api) if live_api else {"status": "NOT_REQUESTED"}
    protected = dict(checksums)
    protected["models/privacy_model_v02.joblib"] = model_hash
    if any(digest(root / name) != checksum for name, checksum in protected.items()):
        raise RuntimeError("Protected input changed during evaluation")
    report["protected_inputs_unchanged"] = True
    unique_rows = {row["_ref"]: row for rows in loaded.values() for row in rows}
    report["privacy_check"] = check_report_privacy(report, list(unique_rows.values()))
    return report


def markdown_report(report):
    lines = ["# Dataset reliability and generalization", "",
             "Frozen local artifact; no retraining. See JSON for input/model/tool checksums and complete metrics.",
             "No dataset here is a newly independently sourced holdout. Do not pool their results.", "",
             "## Legacy pair review", ""]
    for pair in report["pair_reviews"]:
        cosine = pair.get("prior_audit_cosine", "unverified")
        lines.append(f"- {pair['left']} / {pair['right']} (prior audit cosine {cosine}): **{pair['classification']}**. {pair['rationale']}")
    lines += ["", "## Source confounding", "", report["source_analysis"]["interpretation"],
              "Missing lineage prevents verifying upstream source assignments or causally attributing errors to source style.",
              "", "## Per-dataset hybrid non-SAFE metrics", "",
              "Positive = REVIEW or SENSITIVE, so false positives include safe requests held for review.",
              "Matrices are [[TN, FP], [FN, TP]]. Undefined rates are null in JSON, shown as n/a here.", "",
              "| Dataset | N | Matrix | Precision | Recall | F1 | FPR | FNR |",
              "|---|---:|---|---:|---:|---:|---:|---:|"]
    def show(value):
        return "n/a" if value is None else f"{value:.4f}"
    for name, data in report["datasets"].items():
        m = data["hybrid_non_safe"]
        values = " | ".join(show(m[k]) for k in ("precision", "recall", "f1", "false_positive_rate", "false_negative_rate"))
        lines.append(f"| {name} | {data['valid_rows']} | {m['confusion_matrix']} | {values} |")
    lines += ["", "## ML-only metrics", "",
              "| Dataset | Matrix | Precision | Recall | F1 | FPR | FNR |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for name, data in report["datasets"].items():
        m = data["ml_only"]
        values = " | ".join(show(m[k]) for k in ("precision", "recall", "f1", "false_positive_rate", "false_negative_rate"))
        lines.append(f"| {name} | {m['confusion_matrix']} | {values} |")
    lines += ["", "## Live production consistency", "", json.dumps(report["live_consistency"], sort_keys=True),
              "", "## Limitations and next steps", "",
              "- Artifact training lineage is unverified. API now loads the saved artifact when present; bounded live agreement does not establish independent generalization.",
              "- REVIEW is not a true positive disclosure classification. Inspect the separate 2x3 decision matrices and review counts in JSON.",
              "- Small, development-exposed sets and source-confounded legacy data do not establish generalization or calibrated probabilities.",
              "- Review likely duplicate clusters before new splitting; do not alter existing evidence or quote it as independent performance.",
              "- Execute the independent provenance/annotation/freeze protocol in docs/independent-holdout.md before future model selection.",
              "- No new holdout was collected or generated in this milestone.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--live-api", help="Existing loopback API; no startup or training is performed")
    args = parser.parse_args()
    report = run_reliability(args.root, args.live_api)
    output = args.root / "reports/dataset_reliability"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({"datasets_evaluated": len(report["datasets"]),
                      "live_consistency": report["live_consistency"],
                      "privacy_check": report["privacy_check"],
                      "protected_inputs_unchanged": report["protected_inputs_unchanged"]}))
    return 2 if report["missing_inputs"] or (args.live_api and
        (report["live_consistency"]["status"] != "COMPLETE" or report["live_consistency"]["mismatches"])) else 0


if __name__ == "__main__":
    raise SystemExit(main())
