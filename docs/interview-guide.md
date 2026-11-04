# Explaining TrustShield in an interview

**What did you build?** A local privacy gateway whose enforcement, metadata persistence, reviewer workflow, monitoring console and ML evaluation tools are independently testable. The result is an engineering portfolio release candidate with explicit detector limitations, not a claim that all sensitive prompts are caught.

**Why a hybrid detector?** TF-IDF/logistic regression is cheap and interpretable but misses unfamiliar phrasing. Explicit rules handle known identifiers; contextual rules hold ambiguous disclosures. Secret detection takes priority. Rules also overblock benign discussion, which is measured rather than hidden.

**What is fail closed?** BLOCK/HOLD never invoke the injected backend. An audit insertion error prevents ALLOW execution. It does not mean the detector has zero false negatives. A saved ML false-SAFE can pass policy. The legacy-test hybrid missed 14/58 sensitive cases and withheld 33/59 safe cases.

**Why audit before execution?** A post-execution-only log can lose all evidence of a disclosure during disk failure. PENDING is committed first. Finalization can still fail after execution; the system cannot honestly promise rollback/exactly-once behavior. It returns a conservative failure, retains uncertainty and avoids silent retries.

**Why no approve button?** An approval bypass undermines the same enforcement boundary. Metadata-only review cannot recover the original prompt. The reviewer rejects or requests rewrite; the submitter supplies a new request that receives every check again.

**How did you test generalization?** Reproduced seven development dataset evaluations, investigated leakage/confounding, reported model-only and withholding metrics, compared a frozen contextual encoder with a matched lightweight control, and kept the true holdout empty. Random splits of templated synthetic data can share scaffolding; family separation and provenance checks reduce but cannot prove independence. Missing historical lineage remains a limitation.

**Why not deploy the better contextual score?** It improves legacy-test F1 from .611 ML-only to .957, but misses one of five sensitive synthetic validation cases, adds about 263 ms warm latency, needs a separate model service, and has no trustworthy independent winner-selection dataset. Promotion would be premature.

**What did calibration teach you?** Lower ECE alone was misleading: sigmoid calibration slightly worsened Brier and log loss. Scores near .5 and small samples make apparent certainty fragile. No calibration or threshold was promoted. At the existing threshold, 35% of accepted legacy-test requests are sensitive; abstention burden must be reported alongside recall.

**What real defect did experiments uncover?** Fullwidth forms and newline context evaded some rules. Matching through a compatibility view while mapping spans back to original offsets fixed measured variants without changing the saved classifier. Remaining misses and high false-positive burden remain documented. Development-generated probes are not an independent benchmark.

**Why SQLite and Docker?** SQLite fits a single local service and enables deterministic Windows-safe tests. Docker separates API and console, keeps persistent audit storage outside the image and proves Linux compatibility. It intentionally packages a public synthetic demo artifact; private original weights/data are not distributable release evidence. Shared filesystem/Compose secrets are not an enterprise key manager.

**What would you do next?** Have independent contributors author genuinely new fictional material, register evidence and template families, obtain two blinded labels and adjudication, satisfy the unchanged freeze floors, then evaluate once under a reviewed protocol. Before public deployment add real identity, authorization, TLS, rate limits, retention and durable operational controls. These are distinct from optional model research.
