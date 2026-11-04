# Dataset reliability and generalization

Frozen local artifact; no retraining. See JSON for input/model/tool checksums and complete metrics.
No dataset here is a newly independently sourced holdout. Do not pool their results.

## Legacy pair review

- legacy_train:451 / legacy_validation:87 (prior audit cosine 0.915323): **INCONCLUSIVE**. High lexical overlap includes negation or content changes; similarity cannot establish semantic equivalence or common origin.
- legacy_train:138 / legacy_test:70 (prior audit cosine 0.976999): **LIKELY_DUPLICATE**. Identical normalized text or near-identical wording with only function-word/punctuation edits; shared origin not proven.

## Source confounding

The legacy builder assigns labels by collection, perfectly confounding declared source with assigned label by construction. This is not verified row-level provenance or proof that this model relies on source.
Missing lineage prevents verifying upstream source assignments or causally attributing errors to source style.

## Per-dataset hybrid non-SAFE metrics

Positive = REVIEW or SENSITIVE, so false positives include safe requests held for review.
Matrices are [[TN, FP], [FN, TP]]. Undefined rates are null in JSON, shown as n/a here.

| Dataset | N | Matrix | Precision | Recall | F1 | FPR | FNR |
|---|---:|---|---:|---:|---:|---:|---:|
| legacy_validation | 117 | [[25, 33], [19, 40]] | 0.5479 | 0.6780 | 0.6061 | 0.5690 | 0.3220 |
| legacy_test | 117 | [[26, 33], [14, 44]] | 0.5714 | 0.7586 | 0.6519 | 0.5593 | 0.2414 |
| synthetic_validation | 10 | [[5, 0], [0, 5]] | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| independent_eval | 40 | [[17, 3], [0, 20]] | 0.8696 | 1.0000 | 0.9302 | 0.1500 | 0.0000 |
| challenge_csv | 20 | [[10, 0], [0, 10]] | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| challenge_model | 20 | [[7, 3], [0, 10]] | 0.7692 | 1.0000 | 0.8696 | 0.3000 | 0.0000 |
| frozen_eval | 20 | [[9, 1], [0, 10]] | 0.9091 | 1.0000 | 0.9524 | 0.1000 | 0.0000 |

## ML-only metrics

| Dataset | Matrix | Precision | Recall | F1 | FPR | FNR |
|---|---|---:|---:|---:|---:|---:|
| legacy_validation | [[25, 33], [20, 39]] | 0.5417 | 0.6610 | 0.5954 | 0.5690 | 0.3390 |
| legacy_test | [[26, 33], [18, 40]] | 0.5479 | 0.6897 | 0.6107 | 0.5593 | 0.3103 |
| synthetic_validation | [[5, 0], [0, 5]] | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| independent_eval | [[17, 3], [3, 17]] | 0.8500 | 0.8500 | 0.8500 | 0.1500 | 0.1500 |
| challenge_csv | [[10, 0], [0, 10]] | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| challenge_model | [[7, 3], [0, 10]] | 0.7692 | 1.0000 | 0.8696 | 0.3000 | 0.0000 |
| frozen_eval | [[9, 1], [1, 9]] | 0.9000 | 0.9000 | 0.9000 | 0.1000 | 0.1000 |

## Live production consistency

{"checked": 344, "endpoint": "http://127.0.0.1:8000/analyze", "mismatch_references": [], "mismatches": 0, "scope": "Agreement on checked rows and rounded scores only; not model identity or independence proof. No backend, gateway, or audit-write call was made.", "status": "COMPLETE"}

## Limitations and next steps

- Artifact training lineage is unverified. API now loads the saved artifact when present; bounded live agreement does not establish independent generalization.
- REVIEW is not a true positive disclosure classification. Inspect the separate 2x3 decision matrices and review counts in JSON.
- Small, development-exposed sets and source-confounded legacy data do not establish generalization or calibrated probabilities.
- Review likely duplicate clusters before new splitting; do not alter existing evidence or quote it as independent performance.
- Execute the independent provenance/annotation/freeze protocol in docs/independent-holdout.md before future model selection.
- No new holdout was collected or generated in this milestone.
