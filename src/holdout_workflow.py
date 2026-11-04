"""Offline holdout preparation. No collection, scoring, model fitting, or API calls."""

import argparse
import ast
import csv
import hashlib
import itertools
import json
import platform
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sklearn.feature_extraction.text import TfidfVectorizer

from src.dataset_audit import GROUP_FIELDS, literal_assignment, load_dataset, normalize
from src.holdout_schema import Bundle, Collection, TABLES

EVALUATION_FILES = ("src/privacy_decision_engine.py", "src/pii_rules.py", "src/secret_detector.py",
                    "src/text_normalization.py", "src/settings.py",
                    "src/policy_engine.py", "src/api.py", "src/holdout_schema.py", "src/holdout_workflow.py",
                    "docs/holdout-annotation.md", "config/holdout_schema.json", "config/holdout_rules.json",
                    "config/dataset_audit.json", "models/privacy_model_v02.joblib")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def initialize(directory, format="csv", root=None):
    """Empty forms only. Never overwrite an existing collection."""
    directory.mkdir(parents=True, exist_ok=False)
    for name, schema in TABLES.items():
        if name == "sources" or format == "json":
            (directory / f"{name}.json").write_text("[]\n", encoding="utf-8")
        else:
            with (directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerow(schema.model_fields)
    (directory / "collection.json").write_text(json.dumps({
        "version": "draft-1", "state": "PREPARATION", "custodian_id": None,
        "independence_attested": False}, indent=2) + "\n", encoding="utf-8")
    (directory / "evidence").mkdir()
    if root is not None:
        (directory / "planning.json").write_text(json.dumps(
            {"evaluation_sha256": {name: sha(root / name) for name in EVALUATION_FILES}},
            indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_bundle(directory):
    data, issues, hashes = {}, Counter(), {}
    for name, schema in TABLES.items():
        paths = [p for ext in ("csv", "json") if (p := directory / f"{name}.{ext}").is_file()]
        data[name] = []
        if len(paths) != 1:
            issues["MISSING_OR_AMBIGUOUS_" + name.upper()] += 1
            continue
        path = paths[0]
        hashes[path.name] = sha(path)
        try:
            if path.suffix == ".json":
                items = json.loads(path.read_text(encoding="utf-8-sig"))
            else:
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    fields = reader.fieldnames or []
                    if len(set(fields)) != len(fields) or set(fields) != set(schema.model_fields):
                        issues["INVALID_HEADER_" + name.upper()] += 1
                    items = list(reader)
                for item in items:
                    for field in ("independent_blind", "license_or_consent_verified", "independence_attested"):
                        if item.get(field) in ("true", "false"):
                            item[field] = item[field] == "true"
                    if item.get("derivation_parent_id") == "":
                        item["derivation_parent_id"] = None
            if not isinstance(items, list):
                raise ValueError("Expected a list")
            for item in items:
                try:
                    data[name].append(schema.model_validate(item).model_dump(mode="json"))
                except (ValidationError, TypeError, ValueError):
                    issues["INVALID_ROW_" + name.upper()] += 1
        except (OSError, ValueError, TypeError):
            issues["UNREADABLE_" + name.upper()] += 1
    path = directory / "collection.json"
    try:
        hashes[path.name] = sha(path)
        data["collection"] = Collection.model_validate_json(path.read_text()).model_dump(mode="json")
    except (OSError, ValueError):
        data["collection"] = {}
        issues["INVALID_COLLECTION_METADATA"] += 1
    return data, issues, hashes


def load_known(root):
    """Manifest inventory plus literal strings in source/tests, never execution."""
    path = root / "config/dataset_audit.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    loaded, known, hashes, missing = {}, [], {"config/dataset_audit.json": sha(path)}, 0
    registered = set()
    for spec in manifest["datasets"]:
        if "path" in spec:
            registered.add(spec["path"])
        try:
            rows, _, checksum = load_dataset(root, spec, loaded)
            loaded[spec["id"]] = rows
            if "members" not in spec:
                known.extend(rows)
                hashes[spec["path"]] = checksum
        except (OSError, KeyError, ValueError):
            missing += 1
    for pattern in ("data/raw/*.csv", "data/processed/*.csv"):
        missing += sum(p.relative_to(root).as_posix() not in registered for p in root.glob(pattern))
    for folder in ("src", "tests"):
        for file in sorted((root / folder).glob("*.py")):
            relative = file.relative_to(root).as_posix()
            hashes[relative] = sha(file)
            try:
                tree = ast.parse(file.read_text(encoding="utf-8-sig"))
            except (ValueError, SyntaxError):
                missing += 1
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value.strip()) >= 20:
                    known.append({"text": node.value, "label": None, "_ref": f"code:{relative}:{node.lineno}",
                                  "_namespace": relative})
    return known, hashes, missing


def resolve_annotations(bundle, rules, issues):
    records = {r["record_id"]: r for r in bundle["records"]}
    annotations, adjudications = defaultdict(list), defaultdict(list)
    for row in bundle["annotations"]:
        annotations[row["record_id"]].append(row)
    for row in bundle["adjudications"]:
        adjudications[row["record_id"]].append(row)
    issues["ORPHAN_ANNOTATION"] += sum(key not in records for key in annotations)
    issues["ORPHAN_ADJUDICATION"] += sum(key not in records for key in adjudications)
    final, paired, disagreements, excluded = {}, 0, 0, 0
    reason = {"SAFE": "CONCEPT_ONLY", "SENSITIVE": "OBSERVED_DISCLOSURE",
              "UNCERTAIN": "AMBIGUOUS", "OUT_OF_SCOPE": "OUT_OF_SCOPE"}
    label_pairs = []
    for key, record in records.items():
        rows = annotations[key]
        if len(rows) != 2 or len({r["annotator_id"] for r in rows}) != 2:
            issues["TWO_DISTINCT_ANNOTATORS_REQUIRED"] += 1
            continue
        rows = sorted(rows, key=lambda r: r["annotator_id"])
        paired += 1
        labels = [r["label"] for r in rows]
        label_pairs.append(labels)
        disagreements += int(labels[0] != labels[1])
        if any(r["guideline_version"] != rules["guideline_version"] or r["reason_code"] != reason[r["label"]]
               or datetime.fromisoformat(r["annotated_at"]) < datetime.fromisoformat(record["collected_at"]) for r in rows):
            issues["INVALID_ANNOTATION_CONTEXT"] += 1
        if any(r["annotator_id"] == record["author_group_id"] for r in rows):
            issues["AUTHOR_ANNOTATOR_COLLISION"] += 1
        decisions = adjudications[key]
        if labels[0] == labels[1] and labels[0] in ("SAFE", "SENSITIVE") and not decisions:
            final[key] = labels[0]
            continue
        if len(decisions) != 1:
            issues["ADJUDICATION_REQUIRED_OR_DUPLICATED"] += 1
            continue
        decision = decisions[0]
        if (decision["adjudicator_id"] in {r["annotator_id"] for r in rows}
                or decision["adjudicator_id"] == record["author_group_id"]
                or decision["guideline_version"] != rules["guideline_version"]
                or datetime.fromisoformat(decision["adjudicated_at"]) < max(datetime.fromisoformat(r["annotated_at"]) for r in rows)
                or (decision["final_label"] == "EXCLUDE") != (decision["reason_code"] != "LABEL_RESOLVED")):
            issues["INVALID_ADJUDICATION_CONTEXT"] += 1
            continue
        final[key] = decision["final_label"]
        excluded += int(decision["final_label"] == "EXCLUDE")
    agreement = (paired - disagreements) / paired if paired else None
    # Fixed annotator identities are needed for interpretable Cohen's kappa.
    identities = {tuple(sorted(r["annotator_id"] for r in group)) for group in annotations.values() if len(group) == 2}
    kappa = None
    if paired and len(identities) == 1:
        a, b = Counter(x[0] for x in label_pairs), Counter(x[1] for x in label_pairs)
        expected = sum(a[label] * b[label] for label in reason) / paired ** 2
        kappa = (agreement - expected) / (1 - expected) if expected < 1 else None
    return final, {"paired_records": paired, "disagreements": disagreements,
                   "disagreement_rate": disagreements / paired if paired else None,
                   "agreement_rate": agreement, "cohen_kappa_fixed_rater_pair": kappa,
                   "excluded_records": excluded, "resolved_records": len(final)}


def components(records):
    parent = {r["record_id"]: r["record_id"] for r in records}
    def find(key):
        while key != parent[key]:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key
    owners = {}
    for row in records:
        key = row["record_id"]
        for field in ("author_group_id", "document_group_id", "person_group_id", "template_family_id"):
            token = (row["group_namespace"] if field == "template_family_id" else "GLOBAL", field, row[field])
            if token in owners:
                parent[find(key)] = find(owners[token])
            else:
                owners[token] = key
        ancestor = row.get("derivation_parent_id")
        if ancestor in parent:
            parent[find(key)] = find(ancestor)
    return {key: find(key) for key in parent}


def near_candidates(records, known, threshold):
    """Yield all suspicious pairs; sparse bounded products, not a truncated top-k."""
    a, b = defaultdict(list), defaultdict(list)
    for row in records:
        a[normalize(row["text"])].append(row)
    for row in known:
        if row.get("text", "").strip():
            b[normalize(row["text"])].append(row)
    if not a or not b:
        return
    corpus = sorted(a.keys() | b.keys())
    positions = {text: i for i, text in enumerate(corpus)}
    matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=False).fit_transform(corpus)
    keys_a, keys_b = sorted(a), sorted(b)
    reference = matrix[[positions[text] for text in keys_b]].T.tocsc()
    for start in range(0, len(keys_a), 32):
        scores = (matrix[[positions[text] for text in keys_a[start:start + 32]]] @ reference).tocoo()
        for i, j, score in zip(scores.row, scores.col, scores.data):
            text_a, text_b = keys_a[start + int(i)], keys_b[int(j)]
            if score + 1e-12 < threshold or text_a == text_b:
                continue
            match = min(b[text_b], key=lambda r: r["_ref"])
            for record in a[text_a]:
                yield record, match


def inspect_collection(root, directory):
    rules_path = root / "config/holdout_rules.json"
    rules = json.loads(rules_path.read_text())
    if (not 0 < rules["near_threshold"] <= 1 or any(
        not isinstance(rules[key], int) or isinstance(rules[key], bool) or rules[key] < 1
        for key in ("minimum_rows_per_class", "minimum_components_per_class", "minimum_sources"))
            or not rules["required_categories"]):
        raise ValueError("Invalid readiness rules")
    bundle, issues, input_hashes = read_bundle(directory)
    plan_path = directory / "planning.json"
    try:
        plan = json.loads(plan_path.read_text())
        if plan["evaluation_sha256"] != {name: sha(root / name) for name in EVALUATION_FILES}:
            issues["PRECOLLECTION_EVALUATION_PLAN_CHANGED"] += 1
        input_hashes["planning.json"] = sha(plan_path)
    except (OSError, ValueError, KeyError):
        issues["MISSING_PRECOLLECTION_EVALUATION_PLAN"] += 1
    known, reference_hashes, missing = load_known(root)
    issues["MISSING_OR_UNREGISTERED_REFERENCE"] += missing
    if not known:
        issues["NO_KNOWN_REFERENCE_ROWS"] += 1
    records = bundle["records"]
    if not records:
        issues["NO_INDEPENDENT_MATERIAL_COLLECTED"] += 1
    collection = bundle["collection"]
    if collection.get("state") != "COLLECTED_REVIEWED" or not collection.get("independence_attested") or not collection.get("custodian_id"):
        issues["CUSTODIAN_PROVENANCE_ATTESTATION_REQUIRED"] += 1
    if len({r["record_id"] for r in records}) != len(records):
        issues["DUPLICATE_RECORD_ID"] += 1
    sources = {r["source_id"]: r for r in bundle["sources"]}
    if len(sources) != len(bundle["sources"]):
        issues["DUPLICATE_SOURCE_ID"] += 1
    for source in sources.values():
        path = directory / source["evidence_file"]
        if not path.resolve().is_relative_to(directory.resolve()) or not path.is_file() or sha(path) != source["evidence_sha256"]:
            issues["MISSING_OR_CHANGED_PROVENANCE_EVIDENCE"] += 1
        else:
            input_hashes[source["evidence_file"]] = sha(path)
    known_groups = {(r.get("_namespace"), r[field]) for r in known for field in GROUP_FIELDS if r.get(field)}
    identity_fields = ("author_group_id", "document_group_id", "person_group_id")
    known_identities = {(field, r[field]) for r in known for field in identity_fields if r.get(field)}
    texts, exact, normalized = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in known:
        exact[row["text"]].append(row)
        normalized[normalize(row["text"])].append(row)
    final, annotation_summary = resolve_annotations(bundle, rules, issues)
    ancestors = {r["record_id"]: r.get("derivation_parent_id") for r in records}
    completed = set()
    for start in ancestors:
        trail, key = set(), start
        while key in ancestors and key not in completed:
            if key in trail:
                issues["CYCLIC_DERIVATION_LINEAGE"] += 1
                break
            trail.add(key)
            key = ancestors[key]
        completed.update(trail)
    component = components(records)
    partitions = defaultdict(set)
    for row in records:
        key = row["record_id"]
        partitions[component[key]].add(row["partition"])
        source = sources.get(row["source_id"])
        if not source or source["revision"] != row["source_revision"]:
            issues["MISSING_OR_MISMATCHED_SOURCE"] += 1
        if any((row["group_namespace"], row[field]) in known_groups
               for field in ("template_family_id",) + identity_fields):
            issues["KNOWN_TEMPLATE_OR_SOURCE_GROUP_OVERLAP"] += 1
        if any((field, row[field]) in known_identities for field in identity_fields):
            issues["KNOWN_AUTHOR_DOCUMENT_PERSON_OVERLAP"] += 1
        if row.get("derivation_parent_id") and row["derivation_parent_id"] not in component:
            issues["UNKNOWN_DERIVATION_PARENT"] += 1
        texts[normalize(row["text"])].append(row)
        matches = normalized.get(normalize(row["text"]), [])
        if matches:
            issues["EXACT_KNOWN_REUSE" if row["text"] in exact else "NORMALIZED_KNOWN_REUSE"] += 1
            if any(r.get("label") in {"0", "1"} and final.get(key) in {"SAFE", "SENSITIVE"}
                   and int(r["label"]) != int(final[key] == "SENSITIVE") for r in matches):
                issues["KNOWN_LABEL_CONFLICT"] += 1
    issues["CROSS_PARTITION_CONNECTED_GROUP"] += sum(len(values) > 1 for values in partitions.values())
    for group in texts.values():
        if len(group) > 1:
            issues["DUPLICATE_COLLECTION_TEXT"] += 1
            if len({final[r["record_id"]] for r in group if r["record_id"] in final}) > 1:
                issues["COLLECTION_LABEL_CONFLICT"] += 1
    reviews = defaultdict(list)
    for review in bundle["leakage_reviews"]:
        reviews[(review["record_id"], review["known_ref"])].append(review)
    internal = [dict(r, _ref=f"collection:{i}", _internal_id=r["record_id"])
                for i, r in enumerate(records, 1)]
    def internal_pairs():
        for record, match in near_candidates(records, internal, rules["near_threshold"]):
            if (record["record_id"] < match["_internal_id"] and
                    (component[record["record_id"]] != component[match["_internal_id"]]
                     or record["partition"] != match["partition"])):
                yield record, match
    candidates, internal_count, unreviewed, near_jobs = 0, 0, 0, []
    for record, match in itertools.chain(near_candidates(records, known, rules["near_threshold"]), internal_pairs()):
        candidates += 1
        internal_count += int("_internal_id" in match)
        near_jobs.append({"record_id": record["record_id"], "known_ref": match["_ref"],
                          "candidate_sha256": fingerprint(record), "known_text_sha256": fingerprint(match["text"])})
        entries = reviews[(record["record_id"], match["_ref"])]
        valid = len(entries) == 1
        if valid:
            review = entries[0]
            valid = (review["candidate_sha256"] == fingerprint(record)
                     and review["known_text_sha256"] == fingerprint(match["text"])
                     and review["disposition"] == "BENIGN"
                     and review["reason_code"] in ("DISTINCT_INTENT", "GENERIC_WORDING")
                     and review["reviewer_id"] == collection.get("custodian_id")
                     and review["reviewer_id"] not in {record["author_group_id"]} | {
                         r["annotator_id"] for r in bundle["annotations"] if r["record_id"] == record["record_id"]})
        if not valid:
            unreviewed += 1
    issues["UNRESOLVED_NEAR_DUPLICATE"] += unreviewed
    held = [r for r in records if r["partition"] == "HOLDOUT" and final.get(r["record_id"]) in ("SAFE", "SENSITIVE")]
    classes = Counter(final[r["record_id"]] for r in held)
    by_source, by_category = defaultdict(set), defaultdict(set)
    for row in held:
        by_source[row["source_id"]].add(final[row["record_id"]])
        by_category[row["category"]].add(final[row["record_id"]])
    group_counts = {label: len({component[r["record_id"]] for r in held if final[r["record_id"]] == label})
                    for label in ("SAFE", "SENSITIVE")}
    if any(classes[label] < rules["minimum_rows_per_class"] for label in ("SAFE", "SENSITIVE")):
        issues["CLASS_SAMPLE_FLOOR_NOT_MET"] += 1
    if any(count < rules["minimum_components_per_class"] for count in group_counts.values()):
        issues["GROUP_SAMPLE_FLOOR_NOT_MET"] += 1
    if len(by_source) < rules["minimum_sources"] or any(len(labels) < 2 for labels in by_source.values()):
        issues["SOURCE_COVERAGE_OR_LABEL_BALANCE_NOT_MET"] += 1
    if any(len(by_category[category]) < 2 for category in rules["required_categories"]):
        issues["CATEGORY_COVERAGE_NOT_MET"] += 1
    codes = {key: count for key, count in sorted(issues.items()) if count}
    report = {"status": "NOT_READY" if codes else "READY_FOR_CUSTODIAN_REVIEW",
              "independence": "Attested provenance plus mechanical checks; never proof of independence",
              "records": len(records), "eligible_holdout_rows": len(held), "class_counts": dict(classes),
              "independent_component_counts": group_counts, "source_tracks": len(by_source),
              "annotation_summary": annotation_summary, "blocking_findings": codes,
              "near_candidate_pairs": candidates, "unresolved_near_pairs": unreviewed,
              "within_collection_near_pairs": internal_count,
              "known_reference_rows": len(known), "rules_version": rules["version"],
              "known_rows_with_identity_metadata": sum(any(r.get(field) for field in identity_fields) for r in known),
              "raw_text_exported": False,
              "limitations": ["Missing historical document/person IDs prevent complete historical group proof",
                              "Lexical similarity does not detect every semantic derivation",
                              "Blinding, fictional content and provenance truth require custodian evidence"]}
    return report, {"bundle": bundle, "final": final, "held": held, "rules": rules,
                    "inputs": input_hashes, "references": reference_hashes,
                    "rules_sha256": sha(rules_path), "near_jobs": near_jobs}


def annotation_package(directory, annotator_id):
    annotator_id = str(UUID(annotator_id))
    bundle, issues, _ = read_bundle(directory)
    if any(issues.values()):
        raise ValueError("Collection schema must validate before packaging")
    target = directory / "annotation_jobs" / f"{annotator_id}.json"
    target.parent.mkdir(exist_ok=True)
    jobs = [{"record_id": r["record_id"], "text": r["text"]} for r in bundle["records"]]
    with target.open("x", encoding="utf-8") as handle:
        json.dump(jobs, handle, indent=2)
    return len(jobs)


def submit_annotations(directory, submission):
    if not submission.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Submission must remain in the private collection directory")
    items = json.loads(submission.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise ValueError("Expected nonempty annotation submission")
    schema = TABLES["annotations"]
    parsed = [schema.model_validate(item).model_dump(mode="json") for item in items]
    identities = {row["annotator_id"] for row in parsed}
    if len(identities) != 1:
        raise ValueError("Submit one annotator at a time")
    annotator = next(iter(identities))
    assigned = {r["record_id"] for r in json.loads((directory / "annotation_jobs" / f"{annotator}.json").read_text())}
    bundle, issues, _ = read_bundle(directory)
    if any(issues.values()):
        raise ValueError("Collection schema must validate")
    keys = {(r["record_id"], r["annotator_id"]) for r in bundle["annotations"]}
    for row in parsed:
        key = (row["record_id"], row["annotator_id"])
        if row["record_id"] not in assigned or key in keys:
            raise ValueError("Duplicate or unassigned annotation")
        keys.add(key)
    target = next(p for ext in ("csv", "json") if (p := directory / f"annotations.{ext}").is_file())
    rows = bundle["annotations"] + parsed
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=directory,
                                     prefix="pending-", delete=False) as handle:
        temporary = Path(handle.name)
        if target.suffix == ".json":
            json.dump(rows, handle, indent=2)
        else:
            writer = csv.DictWriter(handle, fieldnames=schema.model_fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row, independent_blind="true"))
    try:
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return len(parsed)


def freeze(root, directory, version, confirmed=False):
    """Future action only; fixture tests use temporary directories."""
    if not confirmed or not version or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in version) or version in (".", ".."):
        raise ValueError("Explicit confirmation and a safe version identifier are required")
    report, state = inspect_collection(root, directory)
    if report["status"] != "READY_FOR_CUSTODIAN_REVIEW":
        raise ValueError("Holdout is NOT READY")
    threshold = literal_assignment(root / "src/privacy_decision_engine.py", "SAFE_THRESHOLD")
    if threshold != state["rules"]["evaluation"]["decision_threshold"]:
        raise ValueError("Evaluation rules no longer match production threshold")
    protected = {name: sha(root / name) for name in EVALUATION_FILES}
    parent = directory / "frozen"
    parent.mkdir(exist_ok=True)
    target = parent / version
    if target.exists():
        raise ValueError("Freeze versions cannot be overwritten")
    with tempfile.TemporaryDirectory(prefix="pending-", dir=parent) as folder:
        stage = Path(folder) / "snapshot"
        stage.mkdir()
        for name in state["inputs"]:
            destination = stage / "inputs" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(directory / name, destination)
        with (stage / "dataset.csv").open("w", encoding="utf-8", newline="") as handle:
            fields = list(TABLES["records"].model_fields) + ["label"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in state["held"]:
                writer.writerow(dict(row, label=int(state["final"][row["record_id"]] == "SENSITIVE")))
        inputs = {f"inputs/{name}": checksum for name, checksum in state["inputs"].items()}
        inputs["dataset.csv"] = sha(stage / "dataset.csv")
        if any(sha(stage / name) != checksum for name, checksum in inputs.items()) or any(
            sha(directory / name) != checksum for name, checksum in state["inputs"].items()):
            raise ValueError("Inputs changed while freezing")
        if any(sha(root / name) != checksum for name, checksum in {**state["references"], **protected}.items()):
            raise ValueError("Reference data or evaluation implementation changed")
        manifest = {"version": version, "collection_version": state["bundle"]["collection"]["version"],
                    "status": "FROZEN_ATTESTED_NOT_PROVEN_INDEPENDENT", "files": inputs,
                    "references": state["references"], "implementation": protected,
                    "evaluation_rules": state["rules"], "validation": report,
                    "model_identity_scope": "Saved artifact hash only; runtime can select a different explicit trusted artifact and is not verified by this snapshot",
                    "python": platform.python_version()}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stage.rename(target)
    return target


def verify_snapshot(snapshot):
    manifest = json.loads((snapshot / "manifest.json").read_text())
    actual = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"manifest.json"}:
        return False
    for name, checksum in manifest["files"].items():
        path = (snapshot / name).resolve()
        if not path.is_relative_to(snapshot.resolve()) or not path.is_file() or sha(path) != checksum:
            return False
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "validate", "package", "submit", "freeze", "verify"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--directory", type=Path, default=Path("data/holdout/candidate"))
    parser.add_argument("--format", choices=("csv", "json"), default="csv")
    parser.add_argument("--annotator-id")
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--version")
    parser.add_argument("--confirm-freeze", action="store_true")
    args = parser.parse_args()
    directory = (args.root / args.directory).resolve()
    # All material, including future snapshots and annotation packages, stays private/ignored.
    if not directory.is_relative_to((args.root / "data/holdout").resolve()):
        parser.error("Collection directory must be inside data/holdout")
    try:
        if args.action == "init":
            initialize(directory, args.format, args.root)
            print(json.dumps({"status": "NOT_READY", "records_created": 0}))
        elif args.action == "validate":
            report, state = inspect_collection(args.root, directory)
            if directory.is_dir():
                (directory / "leakage_jobs.json").write_text(json.dumps(state["near_jobs"], indent=2) + "\n", encoding="utf-8")
            destination = args.root / "reports/holdout_preparation.json"
            destination.parent.mkdir(exist_ok=True)
            destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(report, sort_keys=True))
            return 0 if report["status"] == "READY_FOR_CUSTODIAN_REVIEW" else 2
        elif args.action == "package":
            count = annotation_package(directory, args.annotator_id)
            print(json.dumps({"private_annotation_records": count}))
        elif args.action == "submit":
            count = submit_annotations(directory, directory / (args.submission or ""))
            print(json.dumps({"annotations_accepted": count}))
        elif args.action == "freeze":
            freeze(args.root, directory, args.version, args.confirm_freeze)
            print(json.dumps({"status": "FROZEN_ATTESTED_NOT_PROVEN_INDEPENDENT"}))
        else:
            if not args.version or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in args.version) or args.version in (".", ".."):
                raise ValueError("Safe snapshot version required")
            valid = verify_snapshot(directory / "frozen" / (args.version or ""))
            print(json.dumps({"snapshot_hashes_valid": valid}))
            return 0 if valid else 2
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"status": "NOT_READY", "error": "Input or workflow validation failed; private values withheld"}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
