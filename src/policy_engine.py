from src.secret_detector import detect_secrets



def enforce_policy(text: str, analysis: dict) -> dict:
    secrets = detect_secrets(text)

    # Rule 1: Known secret patterns have highest priority.
    if secrets:
        return {
            "decision": "BLOCK",
            "forward_allowed": False,
            "reason": "Credential or secret pattern detected",
            "secret_types": sorted({
                item["type"] for item in secrets
            }),
        }

    # Rule 2: Explicit sensitive information is blocked.
    if analysis["decision"] == "SENSITIVE":
        return {
            "decision": "BLOCK",
            "forward_allowed": False,
            "reason": "Sensitive personal information detected",
            "secret_types": [],
        }

    # Rule 3: Uncertain requests must not be forwarded.
    if analysis["decision"] == "REVIEW":
        return {
            "decision": "HOLD",
            "forward_allowed": False,
            "reason": "Manual review required",
            "secret_types": [],
        }

    # Rule 4: Only explicitly SAFE requests may proceed.
    if analysis["decision"] == "SAFE":
        return {
            "decision": "ALLOW",
            "forward_allowed": True,
            "reason": "Passed configured privacy checks",
            "secret_types": [],
        }

    # Unknown decisions must never allow forwarding.
    return {
        "decision": "BLOCK",
        "forward_allowed": False,
        "reason": "Unknown privacy classification",
        "secret_types": [],
    }
