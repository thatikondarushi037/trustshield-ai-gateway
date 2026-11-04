# Working-tree release inventory

Includes preserved uncommitted dataset/reliability/holdout milestones as well as this release work. These files are not staged or committed. Secrets, local datasets, databases, logs, environments and model artifacts remain ignored.

## Modified tracked files

- `.gitignore`
- `README.md`
- `dashboard.py`
- `scripts/start-local.ps1`
- `src/api.py`
- `src/audit_logger.py`
- `src/gateway_service.py`
- `src/local_model_adapter.py`
- `src/pii_rules.py`
- `src/review_queue.py`
- `src/secret_detector.py`

## Untracked review candidates

- `.dockerignore`
- `.github/workflows/ci.yml`
- `.streamlit/config.toml`
- `Dockerfile`
- `compose.yaml`
- `config/dataset_audit.json`
- `config/holdout_rules.json`
- `config/holdout_schema.json`
- `docs/architecture.md`
- `docs/dataset-audit.md`
- `docs/dataset-reliability.md`
- `docs/holdout-annotation.md`
- `docs/independent-holdout.md`
- `docs/interview-guide.md`
- `docs/ml-experiments.md`
- `docs/release-files.md`
- `docs/release-verification.md`
- `docs/reproducibility.md`
- `docs/threat-model.md`
- `reports/calibration.png`
- `reports/dataset_reliability.json`
- `reports/dataset_reliability.md`
- `reports/holdout_preparation.json`
- `reports/ml1_dataset_audit.json`
- `reports/ml1_dataset_audit.md`
- `reports/ml_experiments.json`
- `reports/robustness_before_hardening.json`
- `reports/screenshots/console-1.png`
- `reports/screenshots/console-2.png`
- `reports/screenshots/console-3.png`
- `reports/screenshots/console-4.png`
- `reports/screenshots/console-5.png`
- `reports/screenshots/console-mobile.png`
- `reports/verified_manifest.json`
- `requirements-experiments.txt`
- `requirements.lock`
- `scripts/ci_verify.py`
- `scripts/container_model.py`
- `scripts/verify_console.py`
- `scripts/verify_deployment.py`
- `scripts/verify_image.py`
- `src/console_client.py`
- `src/contextual_adapter.py`
- `src/dataset_audit.py`
- `src/dataset_reliability.py`
- `src/demo.py`
- `src/devtools.py`
- `src/holdout_schema.py`
- `src/holdout_workflow.py`
- `src/http_safety.py`
- `src/ml_experiments.py`
- `src/release_checks.py`
- `src/report_registry.py`
- `src/robustness.py`
- `src/settings.py`
- `src/text_normalization.py`
- `tests/test_dashboard.py`
- `tests/test_dataset_audit.py`
- `tests/test_dataset_reliability.py`
- `tests/test_holdout_workflow.py`
- `tests/test_ml_experiments.py`
- `tests/test_release_security.py`
- `tests/test_report_registry.py`
- `tests/test_text_normalization.py`
