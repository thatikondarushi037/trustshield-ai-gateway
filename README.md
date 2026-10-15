## TrustShield V0.2 — Hybrid Privacy Detection

TrustShield AI Gateway is a privacy-focused ML engineering project designed to identify potentially sensitive information before prompts are forwarded to AI models.

### Current capabilities

- TF-IDF + Logistic Regression text classification.
- Regex-based detection for email addresses, PINs, account numbers, phone numbers, and street addresses.
- Hybrid decision engine with three outcomes:
  - **SAFE:** Eligible for forwarding.
  - **SENSITIVE:** Explicit sensitive information detected; block or redact according to policy.
  - **REVIEW:** Potential sensitive information detected; hold for further review.
- Saved ML pipeline using `joblib`.
- Automated regression and model-persistence tests.
- Evaluation reports without raw message text.

### V0.2 evaluation

A frozen-model evaluation was performed using 20 synthetic examples: 10 SAFE and 10 SENSITIVE.

| Actual label | SAFE decision | REVIEW decision | SENSITIVE decision |
|---|---:|---:|---:|
| SAFE | 9 | 1 | 0 |
| SENSITIVE | 0 | 8 | 2 |

**Observed results:**
- Sensitive messages incorrectly marked SAFE: 0/10.
- Safe messages automatically allowed: 9/10 (90%).
- Sensitive messages explicitly classified SENSITIVE: 2/10.
- Automated tests: 8 passed.

These results are preliminary. The dataset is small and synthetic, and it does not establish real-world privacy guarantees. The ML scores have not been calibrated. REVIEW decisions are held rather than forwarded automatically.

### Planned features

- FastAPI endpoints for privacy analysis and policy enforcement.
- Redaction and blocking of sensitive information.
- Live privacy warnings while users type prompts.
- Integrations with supported cloud and local AI models.
- Docker, CI/CD, monitoring, and broader independent evaluation.