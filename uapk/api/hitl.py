"""Human-in-the-loop (HITL) endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from uapk.db import get_session
from uapk.db.models import User, HITLRequest
from uapk.api.auth import get_current_user
from datetime import datetime

# M1.1: Override token support
from uapk.core.ed25519_token import create_override_token, hash_override_token

# M1.4: RBAC enforcement
from uapk.api.rbac import require_role

router = APIRouter()

class CreateHITLRequest(BaseModel):
    org_id: int
    action: str
    agent_id: str | None = None
    reason: str
    params: dict = {}

@router.post("/requests")
def create_hitl_request(request: CreateHITLRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Create HITL approval request"""
    hitl = HITLRequest(
        org_id=request.org_id,
        action=request.action,
        agent_id=request.agent_id,
        reason=request.reason,
        params=request.params,
        status="pending"
    )
    session.add(hitl)
    session.commit()
    session.refresh(hitl)

    return {"id": hitl.id, "action": hitl.action, "status": hitl.status}

@router.get("/requests")
def list_hitl_requests(status: str | None = None, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """List HITL requests"""
    statement = select(HITLRequest)
    if status:
        statement = statement.where(HITLRequest.status == status)

    requests = session.exec(statement).all()
    return [{"id": r.id, "action": r.action, "status": r.status, "reason": r.reason} for r in requests]

@router.post("/requests/{request_id}/approve")
@require_role("Owner", "Admin")  # M1.4: Only Owner/Admin can approve
def approve_hitl_request(request_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Approve HITL request and generate Ed25519-signed override token"""
    hitl = session.get(HITLRequest, request_id)
    if not hitl:
        raise HTTPException(status_code=404, detail="Request not found")

    if hitl.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")

    hitl.status = "approved"
    hitl.approved_by = current_user.id
    hitl.approved_at = datetime.utcnow()

    # M1.1: Generate override token (Ed25519-signed, 5-minute expiry, bound to action)
    override_token = create_override_token(
        approval_id=hitl.id,
        action=hitl.action,
        params=hitl.params,
        expiry_minutes=5
    )

    # Store token hash (not plaintext) for consumption tracking
    hitl.override_token_hash = hash_override_token(override_token)

    session.add(hitl)
    session.commit()

    return {
        "id": hitl.id,
        "status": hitl.status,
        "approved_by": hitl.approved_by,
        "override_token": override_token  # M1.1: Return override token for retry
    }

@router.post("/requests/{request_id}/reject")
@require_role("Owner", "Admin")  # M1.4: Only Owner/Admin can reject
def reject_hitl_request(request_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Reject HITL request"""
    hitl = session.get(HITLRequest, request_id)
    if not hitl:
        raise HTTPException(status_code=404, detail="Request not found")

    if hitl.status != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")

    hitl.status = "rejected"
    hitl.approved_by = current_user.id
    hitl.approved_at = datetime.utcnow()
    session.add(hitl)
    session.commit()

    return {"id": hitl.id, "status": hitl.status}
