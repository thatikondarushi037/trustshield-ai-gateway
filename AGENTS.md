# TrustShield AI Gateway — Instructions for Codex

## Project identity and current objective

TrustShield is a **privacy-aware and reliability-aware AI security gateway**. It inspects requests *before* they reach an approved local AI backend, detects personally identifiable information (PII) and credentials, applies policy, and provides explainable outcomes. The target is an interview-defensible, locally runnable end-to-end system—not a claim of production-grade protection.

**Work on this existing repository. Do not start a new repo, rewrite Git history, or merge in unrelated projects.** The user explicitly removed **n8n** from TrustShield's scope. The next milestone is **persistent privacy-safe audit logging and monitoring**, followed by ML evaluation/calibration, contextual PII improvements, experimental out-of-distribution checks, deployment, and documentation.

## Before touching files

1. Inspect `git status`, active branch, repository tree, current imports, current endpoints, existing tests, and dependency setup. The historical local branch was `feature/v0.3-fastapi-gateway`; verify the actual branch rather than assuming it.
2. Explain the implementation plan, files to create/change, design tradeoffs, and relevant risks **before editing**.
3. Make small reviewable changes in the existing working tree, preserving previous functionality and tests.
4. Do **not** commit, push, delete, reset, force-push, change remote settings, or modify unrelated files without explicit user approval.
5. Execute only commands that are appropriate to the task, respect the active sandbox, and seek confirmation before significant installs, downloads, destructive operations, or network exposure.
6. Report exactly which tests you ran and their results. Never claim tests passed merely because they passed historically.

## How to teach and collaborate

The user knows Python and wants to become an independent ML engineer. Codex should remove copying/pasting overhead **without replacing learning**:

- Explain the real-world problem, core concepts, module responsibilities, design decisions, and why an approach was chosen over alternatives.
- Explain consequential algorithms, functions, syntax, data flow, failure paths, tests, and interview implications.
- Let the user write critical logic when they request a learning exercise; provide code directly when explicitly requested.
- Review failures and limitations honestly. Be concise but technically rigorous.
- Prefer small edits over wholesale rewrites.

## Existing implementation: verify rather than assume

The following reflects the most recent browser-chat handover and user-confirmed local progress, **not an independent check of this workspace**:

- `src/privacy_decision_engine.py`: TF-IDF + Logistic Regression with regex/context rules; `analyze_message(text, model)` emits `SAFE`, `REVIEW`, or `SENSITIVE`, associated actions, detected types, reason, and an **uncalibrated** ML score.
- `src/pii_rules.py`: email, PIN, bank account, phone, address and contextual patterns; reports character spans.
- `src/redaction.py`: merges overlapping spans and replaces detected text; regex-based redaction **does not guarantee** all sensitive content is removed.
- `src/secret_detector.py`: basic credential/secret-pattern detection; known incomplete coverage.
- `src/policy_engine.py`: fail-closed routing decision: ALLOW / HOLD / BLOCK; secret matches have highest priority. Never bypass policy for human approval or demo convenience.
- `src/gateway_service.py`: analyzes input, enforces policy, and calls an injected backend only when allowed. Currently includes a deterministic demo backend; exceptions are converted into controlled error responses.
- `src/local_model_adapter.py`: Ollama HTTP adapter, historically using `llama3.2:1b` on `127.0.0.1:11434`; verify it exists, model availability, endpoint, and timeouts.
- `src/api.py`: FastAPI application; historical endpoints `/health`, `/analyze`, `/redact`, `/gateway`, `/gateway/local`, and optionally `/`. Verify actual route registration. A previous route typo (`/global/local`) caused HTTP 404 and was corrected locally.
- `dashboard.py`: Streamlit UI hitting `/gateway/local`, showing decision, detected categories, local AI output when allowed, and temporary session metrics.
- `src/review_queue.py`: SQLite review tickets for HOLD decisions, UUIDs and safe reason strings; no raw prompts; Windows-safe explicit connection closure using a `contextmanager`.
- `src/review_cli.py`: local reviewer actions to list pending, reject, or request rewrite. **No direct APPROVE** operation, and no true authenticated human-review approval workflow at this time.
- `tests/`: the user last reported **26 passing tests** after fixing Windows `PermissionError: [WinError 32]` due to unclosed SQLite file handles. The test result must be rechecked after edits.

Historical source-control information: public repo `thatikondarushi037/trustshield-ai-gateway`; last known commit `7ec06fd` (October 2026). The local tree may be ahead of remote; don't overwrite it or assume browser GitHub reflects uncommitted local files.

## Runtime and import conventions

- Development environment: Windows, VS Code, PowerShell, Python virtual environment (`.venv`), FastAPI/Uvicorn, Streamlit, SQLite and Ollama.
- Prefer consistent imports from the project root such as `from src.pii_rules import detect_pii` and run commands from the repository root (`python -m ...`). Mixed top-level `from pii_rules ...` vs `from src.pii_rules ...` previously caused repeated `ModuleNotFoundError` errors.
- Inspect current structure before changing imports across all files. Avoid ad hoc `sys.path` mutation where a coherent package structure works.
- Run the main test suite from repository root: `python -m unittest discover -s tests -v`.
- FastAPI development server was started using `python -m uvicorn src.api:app --reload`; Swagger: `http://127.0.0.1:8000/docs`.
- Streamlit was started using `python -m streamlit run dashboard.py`; UI: `http://localhost:8501`.
- Ollama is a separate local process; do not assume it is running just because FastAPI starts.

## Mandatory security and privacy rules

- Never store or log raw prompts, passwords, API keys, tokens, PII values, or generated AI responses in the audit database. Use only controlled enumerated outcome/category strings and non-sensitive metadata. Be aware that HTTP/web-server logs and debugging can also leak inputs.
- No real credentials or private data in demos/tests. Use fictional values.
- **Only the server-side gateway policy decides forwarding**; dashboard display logic is not enforcement.
- BLOCK and HOLD must never reach a downstream AI adapter. A reviewer cannot override hard blocks. Revised inputs must pass the entire security check again.
- Fail closed if required pre-forward audit recording fails, or if policy output is unknown. Never allow a missing service, exception, or unrecognized decision to create an alternate unchecked path.
- Avoid exposing reviewer/admin operations or audit records through unauthenticated HTTP endpoints. A local demo is **not** authentication.
- Minimize storage; ignore local DB and journal artifacts in Git; protect file access and eventually implement retention/deletion policy.
- Never claim the classifier's raw `predict_proba` is calibrated, or that a 26-test synthetic suite demonstrates real-world security.

## Current task: SQLite security audit and dashboard monitoring

**First inspect whether `src/audit_logger.py` or its tests already exist.** They were proposed in a prior chat, but the user has not confirmed implementing them. Do not duplicate or overwrite working local changes.

Implement, iteratively:

1. `src/audit_logger.py` — SQLite audit schema and functions with explicit Windows-safe connection closure, deterministic enum validation, UUID/UTC timestamp, policy decision, safe outcome, `latency_ms`, and backend-attempt/success indicators. Do not store raw user text or model responses.
2. `tests/test_audit_logger.py` — isolated temporary DB; create/finish, counts, invalid decisions, double finalization, transaction cleanup, no raw prompt persistence; use stable test cases.
3. Integrate at the **single gateway enforcement boundary** in `src/gateway_service.py`: create a PENDING audit record before any permitted backend call; never forward when required audit creation fails; finalize on BLOCK/HOLD, success, and exception. Handle finalization failure explicitly and conservatively; do not misleadingly report a successful audited operation when it wasn't recorded. The audit mechanism should not change the policy that HOLD/BLOCK never reach the backend.
4. Add aggregation for counts and latency/failures. Do not expose unauthenticated audit administration endpoints. If the dashboard needs aggregate metrics, implement an appropriately constrained local-only read path and document its access limitations.
5. Add integration tests that assert backend invocation/non-invocation for ALLOW/HOLD/BLOCK and audit failures, including no raw prompt storage. Ensure failures don't silently bypass security or crash the entire service without controlled error behavior.
6. Update `.gitignore` for DB and SQLite sidecar files (`.db`, `.db-wal`, `.db-shm`, `.db-journal`, etc.) as appropriate; update README with startup/test commands, limitations, and audit architecture.
7. Run all tests and summarize results and unverified properties. **Do not commit or push** until the user approves.

Important design detail: audit creation before a backend call is straightforward, but audit finalization after execution can fail, so discuss this tradeoff before claiming an 'audited' success. `backend_called` in historical code may actually mean 'backend returned successfully'; distinguish attempted vs succeeded fields where practical. Avoid altering public API semantics casually.

## Longer-term roadmap (after audit)

1. Rigorous ML evaluation: data provenance, leakage-resistant splits, genuine held-out examples, per-class precision/recall/F1, false-positive/false-negative analysis, span-level evaluation for redaction.
2. Calibration and reliability: held-out calibration methods, risk/coverage and abstention curves; do not confuse privacy-detector confidence with the downstream LLM's reliability.
3. More robust contextual PII detection: compare regex, classical ML, and NER/span models with measured latency and error rates.
4. Experimental OOD/drift detection with explicit limitations and shift tests.
5. Reproducible local deployment, Docker if justified, robust tests, privacy and security hardening, documentation, architecture diagram and interview-ready demonstration.

## Definition of done for each milestone

- Existing behavior preserved unless an intentional, documented change is approved.
- Code is explainable, modular, and consistent with repository structure.
- Relevant tests added, existing suite re-run, actual pass/fail counts reported.
- Privacy and policy bypass paths tested; known limitations made explicit.
- User understands and approves before any Git commit/push.
