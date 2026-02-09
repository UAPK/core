"""Projects endpoints"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlmodel import Session, select
from uapk.db import get_session
from uapk.db.models import User, Project, KBDocument
from uapk.api.auth import get_current_user
from uapk.cas import ContentAddressedStore

router = APIRouter()
cas = ContentAddressedStore()

class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None
    org_id: int

@router.post("")
def create_project(request: CreateProjectRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    project = Project(name=request.name, description=request.description, org_id=request.org_id, created_by=current_user.id)
    session.add(project)
    session.commit()
    session.refresh(project)
    return {"id": project.id, "name": project.name, "org_id": project.org_id}

@router.get("")
def list_projects(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    statement = select(Project)
    projects = session.exec(statement).all()
    return [{"id": p.id, "name": p.name, "org_id": p.org_id} for p in projects]

@router.post("/{project_id}/kb/upload")
async def upload_kb_document(project_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Upload knowledge base document"""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = await file.read()
    content_hash = cas.put(content)
    content_text = content.decode('utf-8')

    kb_doc = KBDocument(project_id=project_id, filename=file.filename, content_hash=content_hash, content=content_text)
    session.add(kb_doc)
    session.commit()

    return {"id": kb_doc.id, "filename": kb_doc.filename, "content_hash": content_hash}
