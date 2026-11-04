"""Server-side console transport. Never log prompts, responses, or headers."""
import os
import httpx
from src.settings import monitoring_token


def api_request(method, path, payload=None, protected=False):
    headers = {}
    if protected:
        token = monitoring_token()
        if not token:
            raise ValueError("Monitoring unavailable")
        headers["Authorization"] = "Bearer " + token
    url = os.environ.get("TRUSTSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
    with httpx.Client(base_url=url, timeout=90 if method == "POST" and path.startswith("/gateway") else 8,
                      trust_env=False, follow_redirects=False) as client:
        response = client.request(method, path, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def safe_get(path, protected=False):
    try:
        return api_request("GET", path, protected=protected)
    except (httpx.HTTPError, ValueError, OSError):
        return None
