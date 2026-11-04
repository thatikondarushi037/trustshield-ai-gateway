
from time import perf_counter

from src.privacy_decision_engine import analyze_message
from src.policy_engine import enforce_policy
from src.review_queue import create_review
from src.audit_logger import record_decision, record_outcome


def process_request(text: str, model, backend) -> dict:
    started_at = perf_counter()

    def finish(audit_id, status):
        record_outcome(audit_id, status, latency_ms=(perf_counter() - started_at) * 1000)

    # Analyze the incoming request locally.
    try:
        analysis = analyze_message(text, model)
        policy = enforce_policy(text, analysis)
    except Exception:
        return {"decision": "ERROR", "forward_allowed": False, "reason": "Security analysis unavailable",
                "detected_types": [], "secret_types": [], "backend_called": False, "response": None}

    # Enforce the security policy.
    if (policy.get("decision") not in {"ALLOW", "BLOCK", "HOLD"}
            or policy.get("forward_allowed") is not (policy.get("decision") == "ALLOW")):
        return {"decision": "ERROR", "forward_allowed": False, "reason": "Security policy unavailable",
                "detected_types": [], "secret_types": [], "backend_called": False, "response": None}

    response = {
        "decision": policy["decision"],
        "forward_allowed": policy["forward_allowed"],
        "reason": policy["reason"],
        "detected_types": analysis["detected_types"],
        "secret_types": policy["secret_types"],
        "backend_called": False,
        "response": None,
    }

    def storage_error():
        response.update(decision="ERROR", forward_allowed=False,
                        reason="Security storage unavailable", response=None)
        return response

    try:
        audit_id = record_decision(policy["decision"], analysis["detected_types"],
                                   policy["secret_types"])
    except Exception:
        return storage_error()
    response["audit_id"] = audit_id

    # Never invoke the backend for blocked or held requests.
    if not policy["forward_allowed"]:
        if policy["decision"] == "HOLD":
            try:
                review_id = create_review(reason="Uncertain privacy classification")
            except Exception:
                try:
                    finish(audit_id, "REVIEW_FAILED")
                except Exception:
                    pass
                return storage_error()
            response["review_id"] = review_id
            response["review_status"] = "PENDING"
        try:
            finish(audit_id, "NOT_ALLOWED")
        except Exception:
            return storage_error()
        return response

    try:
        backend_response = backend(text)
    except Exception:
        try:
            finish(audit_id, "FAILED")
        except Exception:
            return storage_error()
        response["decision"] = "ERROR"
        response["forward_allowed"] = False
        response["reason"] = "Downstream service unavailable"
        return response

    response["backend_called"] = True
    try:
        finish(audit_id, "SUCCEEDED")
    except Exception:
        return storage_error()
    response["response"] = backend_response
    return response


def demo_backend(text: str) -> str:
    # A deterministic local demonstration backend.
    # No external AI service is contacted.
    return "Demo backend received the approved request."
