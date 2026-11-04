# ML-1 dataset audit

No raw text or per-text hashes are exported.

| Dataset | Rows | SAFE | SENSITIVE | Missing source | Exact excess | Conflicts | Near pairs |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw_sample | 12 | 6 | 6 | 12 | 0 | 0 | 0 |
| legacy_corpus | 6000 | 3000 | 3000 | 6000 | 0 | 0 | 302 |
| legacy_matched | 780 | 390 | 390 | 780 | 0 | 0 | 3 |
| legacy_train | 546 | 273 | 273 | 546 | 0 | 0 | 1 |
| legacy_validation | 117 | 58 | 59 | 117 | 0 | 0 | 0 |
| legacy_test | 117 | 59 | 58 | 117 | 0 | 0 | 0 |
| combined | 820 | 410 | 410 | 0 | 0 | 0 | 3 |
| pilot | 18 | 9 | 9 | 18 | 0 | 0 | 0 |
| synthetic_train | 30 | 15 | 15 | 30 | 0 | 0 | 0 |
| synthetic_validation | 10 | 5 | 5 | 10 | 0 | 0 | 0 |
| hard | 30 | 15 | 15 | 0 | 0 | 0 | 0 |
| independent_eval | 40 | 20 | 20 | 0 | 0 | 0 | 0 |
| challenge_csv | 20 | 10 | 10 | 20 | 0 | 0 | 0 |
| challenge_model | 20 | 10 | 10 | 20 | 0 | 0 | 0 |
| challenge_comparison | 20 | 10 | 10 | 20 | 0 | 0 | 0 |
| frozen_eval | 20 | 10 | 10 | 20 | 0 | 0 | 0 |
| active_train | 60 | 30 | 30 | 30 | 0 | 0 | 0 |

## Recorded sources

These are observed collection labels, not verified upstream document IDs. Missing source rows are in the inventory above.

| Dataset | Recorded source | SAFE | SENSITIVE |
|---|---|---:|---:|
| combined | v01_length_matched | 390 | 390 |
| combined | v02_synthetic | 20 | 20 |
| hard | v02_hard_examples | 15 | 15 |
| independent_eval | v02_independent_eval | 20 | 20 |
| active_train | v02_hard_examples | 15 | 15 |

## Evaluation boundaries

| Left | Right | Exact shared texts | Normalized shared | Near candidates |
|---|---|---:|---:|---:|
| legacy_train | legacy_validation | 0 | 0 | 1 |
| legacy_train | legacy_test | 0 | 0 | 1 |
| legacy_validation | legacy_test | 0 | 0 | 0 |
| synthetic_train | synthetic_validation | 0 | 0 | 0 |
| synthetic_validation | active_train | 0 | 0 | 0 |
| independent_eval | active_train | 0 | 0 | 0 |
| challenge_csv | active_train | 0 | 0 | 0 |
| challenge_model | active_train | 0 | 0 | 0 |
| frozen_eval | active_train | 0 | 0 | 0 |

## Group separation at evaluation boundaries

Unknown means no comparable recorded namespace/metadata, not zero leakage.

| Left | Right | Shared templates | Shared pairs | Shared source groups |
|---|---|---:|---:|---:|
| legacy_train | legacy_validation | unknown | unknown | unknown |
| legacy_train | legacy_test | unknown | unknown | unknown |
| legacy_validation | legacy_test | unknown | unknown | unknown |
| synthetic_train | synthetic_validation | 0 | 0 | unknown |
| synthetic_validation | active_train | 0 | 0 | unknown |
| independent_eval | active_train | unknown | unknown | unknown |
| challenge_csv | active_train | unknown | unknown | unknown |
| challenge_model | active_train | unknown | unknown | unknown |
| frozen_eval | active_train | unknown | unknown | unknown |

## Boundary near-match references

- legacy_train:451 / legacy_validation:87: cosine 0.915323; review candidate, not proven leakage.
- legacy_train:138 / legacy_test:70: cosine 0.976999; review candidate, not proven leakage.

## Hard-example provenance

CSV matches current builder literal text/labels: True.
Builder contains literals, no challenge/evaluation input read. Comparison script reuses previous challenge examples to measure improvement.
No programmatic derivation established. Exact/near overlap is reported separately; manual paraphrasing or feedback-driven selection cannot be ruled out.

## Actions and interpretation

- Quarantine exact training/evaluation reuse before quoting held-out metrics.
- Review normalized reuse and near candidates locally via dataset:row references; similarity alone is not proof of leakage.
- Preserve template groups, and collect document/person/source-group IDs before future splitting.
- Source collection overlap is not document-level leakage; missing group metadata is unknown, not a clean result.
- Parent/derived and duplicated challenge-file overlap is expected inventory reuse.
- Recover upstream revisions/licenses, row IDs, collection dates, and hard-example derivation notes.
- Treat previously inspected challenge/evaluation sets as development data; create a new untouched evaluation set.
- See docs/dataset-audit.md for code provenance evidence, scope, and limitations.

Missing inputs: none.
Full schemas, source/label distributions, checksums, groups and sampled row references are in the JSON report.
