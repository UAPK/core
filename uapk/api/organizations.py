"""Organizations endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from uapk.db import get_session
from uapk.db.models import User, Organization, Membership
from uapk.api.auth import get_current_user

router = APIRouter()

class CreateOrgRequest(BaseModel):
    name: str

@router.post("")
def create_org(request: CreateOrgRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Create organization"""
    org = Organization(name=request.name, owner_id=current_user.id)
    session.add(org)
    session.flush()

    membership = Membership(user_id=current_user.id, org_id=org.id, role="Owner")
    session.add(membership)
    session.commit()
    session.refresh(org)

    return {"id": org.id, "name": org.name, "owner_id": org.owner_id}

@router.get("/{org_id}")
def get_org(org_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Get organization"""
    org = session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"id": org.id, "name": org.name, "owner_id": org.owner_id}
