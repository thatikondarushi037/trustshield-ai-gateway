import os
import secrets
from ipaddress import ip_address, ip_network

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ConfigDict, Field, field_validator
from src.settings import MAX_TEXT_CHARS, load_runtime_model, monitoring_token
from src.http_safety import HttpSafety
from src.policy_engine import enforce_policy
from src.review_queue import list_reviews
from src.audit_logger import monitoring_snapshot

from src.redaction import redact_message

from src.gateway_service import process_request, demo_backend

from src.local_model_adapter import generate_local_response

from src.privacy_decision_engine import analyze_message

from pydantic import BaseModel
# Create the FastAPI application
app = FastAPI(
    title="TrustShield AI Gateway",
    version="1.0.0-rc1",
    description="Privacy-aware AI request analysis gateway"
)
app.add_middleware(HttpSafety)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, error):
    return JSONResponse({"detail": "Invalid request. Supply nonblank text of at most 20000 characters."}, status_code=422)


@app.exception_handler(Exception)
async def unexpected_error(request, error):
    return JSONResponse({"detail": "Service unavailable"}, status_code=500)


# Define the incoming request structure
class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(strict=True, min_length=1, max_length=MAX_TEXT_CHARS)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip() or "\x00" in value:
            raise ValueError("Invalid text")
        return value


# Load a trusted saved model once; synthetic fallback is for fresh development installs.
model = load_runtime_model()


# Health-check endpoint
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "TrustShield AI Gateway"
    }


audit_bearer = HTTPBearer(auto_error=False)


def require_audit_access(request: Request,
                         credentials: HTTPAuthorizationCredentials | None = Depends(audit_bearer)):
    # Use the actual peer; forwarded headers must not grant monitoring access.
    try:
        peer = ip_address(request.client.host) if request.client else None
        trusted = [ip_network(item.strip()) for item in os.environ.get("TRUSTSHIELD_MONITORING_CIDRS", "").split(",") if item.strip()]
        local_peer = peer is not None and (peer.is_loopback or any(peer in network for network in trusted))
    except ValueError:
        local_peer = False
    if not local_peer:
        raise HTTPException(status_code=403, detail="Local monitoring access required")
    try:
        token = monitoring_token()
    except (OSError, ValueError):
        raise HTTPException(status_code=503, detail="Security monitoring is disabled") from None
    if not token:
        raise HTTPException(status_code=503, detail="Security monitoring is disabled")
    if (credentials is None or credentials.scheme.lower() != "bearer"
            or not secrets.compare_digest(credentials.credentials.encode(), token.encode())):
        raise HTTPException(status_code=401, detail="Monitoring authentication required",
                            headers={"WWW-Authenticate": "Bearer"})


@app.get("/audit", dependencies=[Depends(require_audit_access)])
def audit(limit: int = Query(default=50, ge=1, le=200)):
    try:
        return monitoring_snapshot(limit)
    except Exception:
        raise HTTPException(status_code=503, detail="Security monitoring unavailable") from None


@app.get("/reviews", dependencies=[Depends(require_audit_access)])
def reviews(status: str = Query(default="PENDING", pattern="^(PENDING|REJECTED|REWRITE_REQUESTED)$"),
            limit: int = Query(default=100, ge=1, le=200)):
    try:
        records = list_reviews(status, limit)
        # Never expose historical free-form reason strings.
        return {"records": [{key: row[key] for key in ("id", "status", "created_at", "resolved_at")} for row in records]}
    except Exception:
        raise HTTPException(status_code=503, detail="Review monitoring unavailable") from None


@app.get("/reports", dependencies=[Depends(require_audit_access)])
def reports():
    from src.report_registry import public_reports
    return public_reports()


@app.get("/operations/health", dependencies=[Depends(require_audit_access)])
def operations_health():
    import httpx
    from src.local_model_adapter import OLLAMA_URL, MODEL_NAME
    result = {"api": "UP", "audit": "UNAVAILABLE", "reviews": "UNAVAILABLE", "ollama": "UNAVAILABLE", "generation_model": "UNAVAILABLE"}
    try:
        monitoring_snapshot(1)
        result["audit"] = "UP"
    except Exception:
        pass
    try:
        list_reviews(limit=1)
        result["reviews"] = "UP"
    except Exception:
        pass
    try:
        with httpx.Client(timeout=2, trust_env=False) as client:
            response = client.get(OLLAMA_URL.removesuffix("/api/generate") + "/api/tags")
            response.raise_for_status()
            result["ollama"] = "UP"
            if any(item.get("name") == MODEL_NAME for item in response.json().get("models", [])):
                result["generation_model"] = "UP"
    except (httpx.HTTPError, ValueError, TypeError):
        pass
    return result


@app.post("/preview")
def preview(request: MessageRequest):
    # Analysis-only: never calls a backend or creates an audit/review ticket.
    analysis = analyze_message(request.text, model)
    policy = enforce_policy(request.text, analysis)
    return {"decision": policy["decision"], "reason": policy["reason"],
            "detected_types": analysis["detected_types"], "secret_types": policy["secret_types"],
            "forward_allowed": False, "preview_only": True}


# Privacy analysis endpoint
@app.post("/analyze")
def analyze(request: MessageRequest):

    result = analyze_message(
        text=request.text,
        model=model
    )

    return result



@app.post("/redact")
def redact(request: MessageRequest):
    analysis = analyze_message(
        text=request.text,
        model=model
    )

    if analysis["decision"] == "SAFE":
        return {
            **analysis,
            "redacted_text": request.text,
            "forward_allowed": True
        }

    if analysis["decision"] == "REVIEW":
        return {
            **analysis,
            "redacted_text": None,
            "forward_allowed": False
        }

    return {
        **analysis,
        "redacted_text": redact_message(request.text),
        "forward_allowed": False
    }

@app.post("/gateway")
def gateway(request: MessageRequest):
    return process_request(text=request.text, model=model, backend=demo_backend)


@app.post("/gateway/local")
def gateway_local(request: MessageRequest):
    return process_request(text=request.text, model=model, backend=generate_local_response)


@app.get("/")
def home():
    return {
        "application": "TrustShield AI Gateway",
        "version": "1.0-development",
        "status": "running",
        "documentation": "/docs"
    }
