"""Offline, read-only ML-1 audit. Never imports training or generation scripts."""

import argparse
import ast
import csv
import hashlib
import itertools
import json
import math
import platform
import unicodedata
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

GROUP_FIELDS = ("template_id", "pair_id", "group_id", "source_group")


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def literal_assignment(path, variable):
    """Read a literal without executing module-level imports, writes, or model.fit."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == variable for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError("Required literal assignment was not found")


def counts(values):
    return dict(sorted(Counter(values).items()))


def duplicate_stats(rows, canonical=False, sample_limit=10):
    groups = defaultdict(list)
    for row in rows:
        if row.get("text", "").strip():
            key = normalize(row["text"]) if canonical else row["text"]
            groups[key].append(row)
    duplicates = [group for group in groups.values() if len(group) > 1]
    conflicts = [group for group in groups.values()
                 if len({r.get("label") for r in group if r.get("label") in {"0", "1"}}) > 1]
    return {
        "duplicate_groups": len(duplicates),
        "excess_rows": sum(len(group) - 1 for group in duplicates),
        "conflicting_label_groups": len(conflicts),
        "conflict_examples": [[r["_ref"] for r in group[:sample_limit]]
                              for group in conflicts[:sample_limit]],
    }


def inventory(rows, columns):
    valid = [row for row in rows if row.get("text", "").strip()]
    recorded_sources = [r["source"] for r in rows if r.get("source")]
    source_labels = defaultdict(Counter)
    for row in rows:
        source_labels[row.get("source") or "NOT_RECORDED"][
            row.get("label") if row.get("label") in {"0", "1"} else "INVALID_OR_MISSING"
        ] += 1
    return {
        "rows": len(rows), "columns": columns,
        "missing_required_columns": sorted({"text", "label"} - set(columns)),
        "class_counts": counts(r["label"] if r.get("label") in {"0", "1"}
                               else "INVALID_OR_MISSING" for r in rows),
        "missing_or_blank_text": len(rows) - len(valid),
        "invalid_or_missing_labels": sum(r.get("label") not in {"0", "1"} for r in rows),
        "source_counts": counts(recorded_sources),
        "source_missing_rows": len(rows) - len(recorded_sources),
        "source_by_label": {s: dict(sorted(c.items())) for s, c in sorted(source_labels.items())},
        "groups": {key: {"unique": len({r[key] for r in rows if r.get(key)}),
                         "missing_rows": sum(not r.get(key) for r in rows)}
                   for key in GROUP_FIELDS if key in columns},
        "exact": duplicate_stats(rows), "normalized": duplicate_stats(rows, canonical=True),
    }


def overlap(left, right):
    """Row references only; source collections are not treated as document groups."""
    result = {}
    for name, canonical in (("exact", False), ("normalized", True)):
        a, b = defaultdict(list), defaultdict(list)
        for rows, index in ((left, a), (right, b)):
            for row in rows:
                if row.get("text", "").strip():
                    key = normalize(row["text"]) if canonical else row["text"]
                    index[key].append(row)
        shared = sorted(a.keys() & b.keys())
        conflicting = [key for key in shared if len(
            {r["label"] for r in a[key] + b[key] if r.get("label") in {"0", "1"}}
        ) > 1]
        result[name] = {
            "shared_texts": len(shared),
            "left_rows": sum(len(a[key]) for key in shared),
            "right_rows": sum(len(b[key]) for key in shared),
            "conflicting_label_texts": len(conflicting),
            "examples": [{"left": a[key][0]["_ref"], "right": b[key][0]["_ref"]}
                         for key in sorted(shared, key=lambda k: (a[k][0]["_ref"], b[k][0]["_ref"]))[:10]],
        }
    result["groups"] = {}
    for field in GROUP_FIELDS:
        def scoped(rows):
            return {(r["_namespace"], r[field]) for r in rows if r.get(field)}
        a, b = scoped(left), scoped(right)
        comparable = bool({n for n, _ in a} & {n for n, _ in b})
        result["groups"][field] = {
            "comparable_namespace": comparable,
            "shared_groups": len(a & b) if comparable else None,
            "left_missing_rows": sum(not r.get(field) for r in left),
            "right_missing_rows": sum(not r.get(field) for r in right),
        }
    a = {r["source"] for r in left if r.get("source")}
    b = {r["source"] for r in right if r.get("source")}
    result["shared_source_collections"] = len(a & b) if a and b else None
    return result


def near_duplicates(left, right=None, threshold=0.9, batch_size=64, sample_limit=10):
    """Exhaustive sparse cosine search, unique normalized texts, bounded query blocks."""
    if not math.isfinite(threshold) or not 0 < threshold <= 1 or batch_size < 1:
        raise ValueError("Invalid similarity configuration")
    within = right is None
    right = left if within else right
    def index(rows):
        groups = defaultdict(list)
        for row in rows:
            if row.get("text", "").strip():
                groups[normalize(row["text"])].append(row)
        return groups
    a, b = index(left), index(right)
    corpus = sorted(a.keys() | b.keys())
    result = {"candidate_text_pairs": 0, "candidate_row_pairs": 0,
              "opposite_label_text_pairs": 0, "examples": [],
              "unique_left_texts": len(a), "unique_right_texts": len(b)}
    if not corpus:
        return result
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=False,
                                 norm="l2")
    # Empty vocabularies (e.g. one-character inputs) have no usable lexical evidence.
    try:
        matrix = vectorizer.fit_transform(corpus)
    except ValueError as error:
        if "empty vocabulary" not in str(error):
            raise
        result["unscorable_texts"] = len(corpus)
        return result
    positions = {text: i for i, text in enumerate(corpus)}
    keys_a, keys_b = sorted(a), sorted(b)
    matrix_a = matrix[[positions[text] for text in keys_a]]
    matrix_b = matrix[[positions[text] for text in keys_b]].T.tocsc()
    best = []
    for start in range(0, len(keys_a), batch_size):
        scores = (matrix_a[start:start + batch_size] @ matrix_b).tocoo()
        for i, j, score in zip(scores.row, scores.col, scores.data):
            if score + 1e-12 < threshold:
                continue
            i = int(i) + start
            j = int(j)
            if within and i >= j:
                continue
            text_a, text_b = keys_a[i], keys_b[j]
            if text_a == text_b:
                continue  # Already covered by normalized/exact overlap, not a near match.
            result["candidate_text_pairs"] += 1
            result["candidate_row_pairs"] += len(a[text_a]) * len(b[text_b])
            labels_a = {r.get("label") for r in a[text_a]} & {"0", "1"}
            labels_b = {r.get("label") for r in b[text_b]} & {"0", "1"}
            result["opposite_label_text_pairs"] += int(any(x != y for x in labels_a for y in labels_b))
            best.append({"left": a[text_a][0]["_ref"], "right": b[text_b][0]["_ref"],
                         "cosine": round(float(min(score, 1.0)), 6)})
            if len(best) >= max(1, 2 * sample_limit):
                best = sorted(best, key=lambda x: (-x["cosine"], x["left"], x["right"]))[:sample_limit]
    result["examples"] = sorted(best, key=lambda x: (-x["cosine"], x["left"], x["right"]))[:sample_limit]
    return result


def load_dataset(root, spec, loaded):
    if "members" in spec:
        rows = [row.copy() for member in spec["members"] for row in loaded[member]]
        return rows, sorted({key for row in rows for key in row if not key.startswith("_")}), None
    path = root / spec["path"]
    if "variable" in spec:
        literals = literal_assignment(path, spec["variable"])
        rows = [{"text": item[0], "label": str(item[1])} if spec["format"] == "text_label"
                else {"example_id": item[0], "text": item[1], "label": str(item[2])}
                for item in literals]
        columns = list(rows[0]) if rows else ["text", "label"]
    else:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            rows = list(reader)
        if any(None in row for row in rows):
            raise ValueError("CSV contains extra fields")
    for i, row in enumerate(rows, 1):
        row.update(_ref=f"{spec['id']}:{i}", _namespace=spec["group_namespace"])
        row["text"] = row.get("text") or ""
    return rows, columns, hashlib.sha256(path.read_bytes()).hexdigest()


def run_audit(root, manifest_path, threshold=0.9, batch_size=64):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {"audit_version": 1,
              "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "environment": {"python": platform.python_version(),
                              "scikit_learn": version("scikit-learn"), "scipy": version("scipy")},
              "method": {"normalization": "NFKC, casefold, collapse whitespace",
                         "near_metric": "char_wb TF-IDF 3-5 grams, L2 cosine; IDF fit per comparison",
                         "near_threshold": threshold, "batch_size": batch_size,
                         "near_scope": "within each input and explicit near_comparisons only",
                         "sample_limit": 10, "raw_text_exported": False},
              "datasets": {}, "comparisons": [], "missing_inputs": []}
    loaded = {}
    for spec in manifest["datasets"]:
        if "members" in spec and any(member not in loaded for member in spec["members"]):
            report["missing_inputs"].append(spec["id"])
            continue
        if "path" in spec and not (root / spec["path"]).is_file():
            report["missing_inputs"].append(spec["id"])
            continue
        rows, columns, checksum = load_dataset(root, spec, loaded)
        loaded[spec["id"]] = rows
        report["datasets"][spec["id"]] = {
            "spec": spec, "sha256": checksum, **inventory(rows, columns),
            "near_within": near_duplicates(rows, threshold=threshold, batch_size=batch_size),
        }
    boundaries = {tuple(sorted(pair)) for pair in manifest["boundaries"]}
    near_pairs = {tuple(sorted(pair)) for pair in manifest["near_comparisons"]}
    for left, right in itertools.combinations(loaded, 2):
        pair = tuple(sorted((left, right)))
        result = {"left": left, "right": right, "evaluation_boundary": pair in boundaries,
                  **overlap(loaded[left], loaded[right])}
        result["interpretation"] = (
            "DEFINITE_TEXT_CONTAMINATION" if pair in boundaries and result["exact"]["shared_texts"]
            else "NORMALIZED_TEXT_REUSE_REVIEW" if pair in boundaries and result["normalized"]["shared_texts"]
            else "GROUP_BOUNDARY_VIOLATION" if pair in boundaries and any(
                group["shared_groups"] for group in result["groups"].values())
            else "NO_EXACT_TEXT_CONTAMINATION_FOUND" if pair in boundaries
            else "INVENTORY_REUSE_NOT_AUTOMATIC_LEAKAGE"
        )
        if pair in near_pairs:
            result["near"] = near_duplicates(loaded[left], loaded[right], threshold, batch_size)
        report["comparisons"].append(result)
    # Deduplicate physical rows, not texts: detect label disagreements across files too.
    unique_rows = {row["_ref"]: row for rows in loaded.values() for row in rows}
    report["global_text_quality"] = {
        "note": "Parent/derived copies inflate duplicate counts; these are not independent samples.",
        "exact": duplicate_stats(list(unique_rows.values())),
        "normalized": duplicate_stats(list(unique_rows.values()), canonical=True),
    }
    report["provenance_file_sha256"] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in manifest.get("provenance_files", []) if (root / name).is_file()
    }
    if "hard" in loaded and (root / "src/build_v02_hard_examples.py").is_file():
        groups = literal_assignment(root / "src/build_v02_hard_examples.py", "HARD_EXAMPLES")
        literal_rows = Counter((text, str(label)) for group in groups
                               for label, key in ((0, "safe"), (1, "sensitive")) for text in group[key])
        report["hard_example_provenance"] = {
            "csv_matches_current_builder_literals": literal_rows == Counter(
                (r["text"], r.get("label")) for r in loaded["hard"]),
            "evidence": "Builder contains literals, no challenge/evaluation input read. Comparison script reuses previous challenge examples to measure improvement.",
            "conclusion": "No programmatic derivation established. Exact/near overlap is reported separately; manual paraphrasing or feedback-driven selection cannot be ruled out.",
            "lineage_status": "UNKNOWN_BEYOND_CURRENT_BUILDER",
        }
    return report


def markdown_report(report):
    lines = ["# ML-1 dataset audit", "", "No raw text or per-text hashes are exported.", "",
             "| Dataset | Rows | SAFE | SENSITIVE | Missing source | Exact excess | Conflicts | Near pairs |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, data in report["datasets"].items():
        lines.append(f"| {name} | {data['rows']} | {data['class_counts'].get('0', 0)} | "
                     f"{data['class_counts'].get('1', 0)} | {data['source_missing_rows']} | "
                     f"{data['exact']['excess_rows']} | {data['exact']['conflicting_label_groups']} | "
                     f"{data['near_within']['candidate_text_pairs']} |")
    lines += ["", "## Recorded sources", "",
              "These are observed collection labels, not verified upstream document IDs. Missing source rows are in the inventory above.",
              "", "| Dataset | Recorded source | SAFE | SENSITIVE |", "|---|---|---:|---:|"]
    for name, data in report["datasets"].items():
        for source, labels in data["source_by_label"].items():
            if source != "NOT_RECORDED":
                lines.append(f"| {name} | {source} | {labels.get('0', 0)} | {labels.get('1', 0)} |")
    lines += ["", "## Evaluation boundaries", "",
              "| Left | Right | Exact shared texts | Normalized shared | Near candidates |",
              "|---|---|---:|---:|---:|"]
    for pair in report["comparisons"]:
        if pair["evaluation_boundary"]:
            lines.append(f"| {pair['left']} | {pair['right']} | {pair['exact']['shared_texts']} | "
                         f"{pair['normalized']['shared_texts']} | "
                         f"{pair.get('near', {}).get('candidate_text_pairs', 'not run')} |")
    lines += ["", "## Group separation at evaluation boundaries", "",
              "Unknown means no comparable recorded namespace/metadata, not zero leakage.", "",
              "| Left | Right | Shared templates | Shared pairs | Shared source groups |",
              "|---|---|---:|---:|---:|"]
    for pair in report["comparisons"]:
        if pair["evaluation_boundary"]:
            shared = [pair["groups"][key]["shared_groups"] for key in
                      ("template_id", "pair_id", "source_group")]
            cells = " | ".join("unknown" if value is None else str(value) for value in shared)
            lines.append(f"| {pair['left']} | {pair['right']} | {cells} |")
    lines += ["", "## Boundary near-match references", ""]
    for pair in report["comparisons"]:
        if pair["evaluation_boundary"]:
            for example in pair.get("near", {}).get("examples", []):
                lines.append(f"- {example['left']} / {example['right']}: cosine {example['cosine']}; review candidate, not proven leakage.")
    if "hard_example_provenance" in report:
        evidence = report["hard_example_provenance"]
        lines += ["", "## Hard-example provenance", "",
                  f"CSV matches current builder literal text/labels: {evidence['csv_matches_current_builder_literals']}.",
                  evidence["evidence"], evidence["conclusion"]]
    lines += ["", "## Actions and interpretation", "",
              "- Quarantine exact training/evaluation reuse before quoting held-out metrics.",
              "- Review normalized reuse and near candidates locally via dataset:row references; similarity alone is not proof of leakage.",
              "- Preserve template groups, and collect document/person/source-group IDs before future splitting.",
              "- Source collection overlap is not document-level leakage; missing group metadata is unknown, not a clean result.",
              "- Parent/derived and duplicated challenge-file overlap is expected inventory reuse.",
              "- Recover upstream revisions/licenses, row IDs, collection dates, and hard-example derivation notes.",
              "- Treat previously inspected challenge/evaluation sets as development data; create a new untouched evaluation set.",
              "- See docs/dataset-audit.md for code provenance evidence, scope, and limitations.", "",
              f"Missing inputs: {', '.join(report['missing_inputs']) or 'none'}.",
              "Full schemas, source/label distributions, checksums, groups and sampled row references are in the JSON report.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", default="config/dataset_audit.json")
    parser.add_argument("--output", default="reports/ml1_dataset_audit")
    parser.add_argument("--near-threshold", type=float, default=0.9)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    if not math.isfinite(args.near_threshold) or not 0 < args.near_threshold <= 1 or args.batch_size < 1:
        parser.error("Threshold must be in (0, 1] and batch size must be positive")
    report = run_audit(args.root, args.root / args.manifest, args.near_threshold, args.batch_size)
    output = args.root / args.output
    input_paths = {(args.root / spec["path"]).resolve() for spec in
                   json.loads((args.root / args.manifest).read_text())["datasets"] if "path" in spec}
    for suffix in (".json", ".md"):
        if output.with_suffix(suffix).resolve() in input_paths:
            parser.error("Report output must not overwrite an input")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix(".json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.with_suffix(".md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({"datasets_audited": len(report["datasets"]), "missing_inputs": report["missing_inputs"],
                      "report": args.output, "raw_text_exported": False}))
    return 2 if report["missing_inputs"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
