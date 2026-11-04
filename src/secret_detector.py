import re
from src.text_normalization import matching_view, original_span



SECRET_PATTERNS = {
    "GITHUB_TOKEN": re.compile(
        r"\bgh[pousr]_[A-Za-z0-9_]{20,255}\b"
    ),
    "AWS_ACCESS_KEY_ID": re.compile(
        r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    ),
    "API_KEY": re.compile(
        r"\b(?:api[_ -]?key|secret[_ -]?key)"
        r"\s*(?:is|:|=)\s*"
        r"[\"']?([A-Za-z0-9_\-]{12,})",
        re.IGNORECASE,
    ),
    "PASSWORD": re.compile(
        r"\bpassword\s*(?:is|:|=)\s*"
        r"[\"']?([^\s\"']{8,})",
        re.IGNORECASE,
    ),
}


def detect_secrets(text: str) -> list[dict]:
    matches = []
    view, positions = matching_view(text)

    for secret_type, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(view):
            start, end = original_span(match.start(), match.end(), positions)
            matches.append({
                "type": secret_type,
                "start": start,
                "end": end,
            })

    return sorted(matches, key=lambda item: item["start"])
