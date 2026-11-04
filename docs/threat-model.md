# Threat model and security boundaries

Intended deployment: one trusted developer, local machine, loopback-only ports, trusted local files and Ollama. Protect against accidental prompt disclosure through an enforced backend boundary, known PII/secret patterns, audit gaps before execution and unsafe error logging. This is not an Internet-facing multi-tenant service.

| Boundary / failure | Implemented control | Remaining risk |
|---|---|---|
| Client bypass / stale preview | Server reanalyzes every gateway submission | A false-SAFE detector result still forwards |
| Secret / explicit PII / ambiguous classification | BLOCK or HOLD prevents backend call | Pattern coverage and model generalization are incomplete |
| Audit insertion / lock / unavailable storage | Fail closed before execution | Local disk loss or tampering can destroy history |
| Audit finalization after execution | Conservative error, visible PENDING uncertainty, no implicit retry | Remote execution cannot be rolled back |
| Review insertion failure | HOLD remains closed | Metadata-only tickets cannot reconstruct original prompt |
| Malformed / oversized HTTP | Strict validation, 20k chars, 96 KiB streamed body cap | No comprehensive DoS protection or per-user quota |
| Monitoring access | Bearer plus actual-peer loopback/explicit CIDR checks | Shared token, trusted dashboard, no RBAC or TLS |
| Exception disclosure | Generic errors; no raw exception in audit/API | Third-party/native process diagnostics need independent operational review |
| SQLite / joblib files | Explicit close, ignored local files, trusted artifact load | No DB encryption, signed artifacts or automatic retention |
| Container privilege / image contents | Non-root, read-only root, dropped capabilities, allowlisted context | Host administrators/Docker daemon can read secrets and storage |

Prompt text necessarily exists in HTTP and application memory, browser/session memory, and Ollama when allowed. It is not written to audit/review storage or public reports. This is data minimization, not zero-knowledge execution. Ollama retains transient model context; no guarantee is made about third-party service configuration, OS swap, crash dumps or malicious host administrators. Raw text in query strings is not a supported interface; avoid reverse-proxy request/body logging.

Windows monitoring configuration uses DPAPI for the current user/machine. The Linux container path uses a Compose secret file mounted read-only: [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/) do not encrypt the source host file. Rotate by securely replacing the local file and restarting both services. Never copy `.env.monitoring`, plaintext tokens or private evidence into image layers. Environment secrets can be visible to process administrators; do not dump environments or `docker inspect` secrets into reports.

The dashboard has no login. Its authenticated server-side access does not authenticate the human visiting it. Loopback binding is essential; any local process/browser user may interact with it. The fixed Docker private subnet is trusted infrastructure, not a substitute for bearer checks. Do not enable public ports, broad CIDRs or a public Ollama bind for convenience.

Regex redaction, Unicode compatibility matching and credential scanning are incomplete. No guarantee covers all languages, fragmented/encoded secrets, zero-width confusables, steganography or prompt injection. The built-in secret scan is a high-confidence repository check, not a substitute for manual review or a maintained enterprise scanner. Public deployment requires identity/authz, TLS, rate limiting, retention policy, centralized durable audit, operational monitoring and a separate security review.
