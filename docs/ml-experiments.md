# ML experiments and limitations

All measurements in `reports/ml_experiments.json` are development evidence. The original 16,164-byte artifact SHA256 is `214ac08759da67bedf87a2ddd93de6a970a3f68edca35e2e2aa6b56c8d299fda`. It was loaded without retraining or overwrite. Seven datasets were evaluated; every report records input hashes. The legacy sets contain 117 rows each. Small synthetic validation has 10 rows; the historically named independent evaluation has 40, challenge CSV and embedded challenge have 20 each, and frozen evaluation has 20. Names do not prove independence. Prior development exposure and absent lineage prevent final model selection.

## Baselines and abstention

Binary matrices are `[[TN, FP], [FN, TP]]`. Legacy-test ML-only matrix is `[[26,33],[18,40]]`; hybrid withholding matrix is `[[26,33],[14,44]]`. Hybrid precision .5714, recall .7586, F1 .6519, FPR .5593 and FNR .2414 reproduce the historical concern. Legacy-validation hybrid matrix `[[25,33],[19,40]]` yields FNR .3220 and FPR .5690.

Legacy-test three-way matrix (columns SAFE, REVIEW, SENSITIVE) is `[[26,33,0],[14,20,24]]`. There are 53 reviews, not 53 confirmed positive predictions. If REVIEW is abstention, decision coverage is 64/117 = 54.7%; the 64 decided examples include 14 missed sensitive requests. Among the 40 SAFE examples, 14 are sensitive: accepted-request error rate 35%. Reviewing more requests reduces exposure but burdens users; it does not magically improve the underlying detector.

All seven dataset matrices, per-category ground-truth-supported summaries and gateway non-forwarding metrics are in JSON. Missing category metadata is named UNRECORDED, not inferred. Privacy labels are not credential-policy labels: a credential can properly be blocked despite a privacy-only SAFE label.

## Contextual comparison

The installed Ollama `nomic-embed-text:latest` is a nomic-bert encoder (136,727,040 parameters), 768-dimensional embeddings, 274,302,450 bytes of model storage. The report pins its installed digest. The adapter uses the local [Ollama embedding API](https://docs.ollama.com/api/embed), `classification: ` prefix, bounded batches and no silent truncation. The public [Nomic model page](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) documents the model family/license; the installed Ollama tag alone is not proof of that exact revision or training corpus independence.

A logistic head and a fresh TF-IDF/logistic control were fit in memory on the same 60 active development rows. The encoder was frozen. Neither was persisted or promoted. The matched control reproduces the saved baseline on the measured evaluation sets, but missing artifact training lineage prevents proof of identical training history.

| Dataset | Contextual matrix | Precision | Recall | F1 | FPR | FNR |
|---|---|---:|---:|---:|---:|---:|
| Legacy validation | [[54,4],[1,58]] | .9355 | .9831 | .9587 | .0690 | .0169 |
| Legacy test | [[57,2],[3,55]] | .9649 | .9483 | .9565 | .0339 | .0517 |
| Synthetic validation | [[5,0],[1,4]] | 1.0000 | .8000 | .8889 | .0000 | .2000 |

The encoder's improvement on legacy sets and regression on tiny synthetic validation are both retained. No winner is selected. Pretraining overlap, source confounding and development reuse remain unresolved.

Ten identical warm single-request inputs: saved baseline median **1.123 ms**, p95 **1.730 ms**; contextual HTTP + encoder + head median **262.802 ms**, p95 **274.691 ms**. Python tracemalloc peaks were 6,802 and 262,525 bytes respectively, excluding native allocation and Ollama/GPU memory. Encoder allocated VRAM snapshot was 335,743,549 bytes, not measured peak or total system memory. These are low-sample warm observations on this RTX 4060 laptop, not throughput/cold-start guarantees. Contextual operation also needs a separate Ollama service and model lifecycle; the baseline is an in-process small artifact.

## Calibration and selective prediction

Regularized sigmoid calibration (logit input, C=1) fits legacy validation and evaluates legacy test. Exact/normalized text, available scoped groups and cosine >= .90 overlap gates separate these two sets. Historical person/document lineage and original training membership remain unknown; this is leakage-checked development calibration, not a certified independent trial.

| Metric | Original | Sigmoid |
|---|---:|---:|
| Brier score | .242975 | .243190 |
| Log loss | .678890 | .679331 |
| 10-bin ECE | .026537 | .020922 |

Proper scores worsened slightly despite lower ECE. Scores cluster near .5 and ECE is sensitive to bins/sample size. [Reliability plot](../reports/calibration.png) is descriptive; no calibration is deployed.

| Experimental review threshold | Forward coverage | Accepted error | Review rate | False-SAFE / sensitive | Safe withholding burden |
|---|---:|---:|---:|---:|---:|
| .30 | .0000 | undefined | .7949 | .0000 | 1.0000 |
| .40 | .0342 | .0000 | .7607 | .0000 | .9322 |
| .50 | .3419 | .3500 | .4530 | .2414 | .5593 |
| .60 | .7778 | .3516 | .0171 | .5517 | .0000 |
| .70 | .7863 | .3587 | .0085 | .5690 | .0000 |

Rules and secret blocks remain active in this simulation. Automatic decision coverage excludes review; forward coverage additionally excludes blocks. No accepted samples means undefined risk, not evidence of perfect protection. Thresholds remain unchanged in production.

## Robustness and OOD development probes

80 reproducible fictional probes span whitespace/punctuation, contextual discussion/disclosure, negation, masked identifiers, mixed categories, unfamiliar phrasing, Unicode width and long/boundary inputs. Eight ambiguous masked variants are unscored. Correlated variants from ten seed families are **not an independent holdout** or statistical proof of OOD detection.

Before hardening, gateway-withholding FNR was 8/56 (14.3%); after offset-preserving compatibility matching and newline context fixes it is 1/56 (1.8%). Safe withholding remains 13/16 (81.3%). ML-only privacy FNR remains 20/48 (41.7%). The remaining gateway miss is identified only by `unfamiliar:fullwidth`; raw probes are not exported. These development findings motivated a narrow rule fix, not training or threshold selection. Before/after rule fingerprints are preserved in reports. No dedicated calibrated OOD rejection model is implemented.

## Holdout and provenance

No independently collected records, sources, annotations or frozen snapshots exist. Strict original sample/group/source floors remain. Validation also detects the changed evaluation implementation against the earlier precollection plan; a human custodian must review and re-register the intended plan before collection. Do not lower floors or silently rewrite that evidence. Legacy builder source/label confounding and missing document/person IDs remain unresolved; see the prior reliability report. Generalization cannot be conclusively established until legitimate independent collection, two independent annotations, adjudication and custodian-reviewed freezing are completed.
