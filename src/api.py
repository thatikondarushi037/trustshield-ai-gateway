import os
import secrets
from ipaddress import ip_address

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.audit_logger import monitoring_snapshot

from src.redaction import redact_message

from src.gateway_service import process_request, demo_backend

from src.local_model_adapter import generate_local_response

from src.privacy_decision_engine import train_model, analyze_message

from pydantic import BaseModel
# Create the FastAPI application
app = FastAPI(
    title="TrustShield AI Gateway",
    version="0.3.0",
    description="Privacy-aware AI request analysis gateway"
)


# Define the incoming request structure
class MessageRequest(BaseModel):
    text: str


# Train the model once when the application loads
model = train_model()


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
        local_peer = request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        local_peer = False
    if not local_peer:
        raise HTTPException(status_code=403, detail="Local monitoring access required")
    token = os.environ.get("TRUSTSHIELD_AUDIT_TOKEN", "")
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
