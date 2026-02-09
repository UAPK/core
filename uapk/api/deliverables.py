"""Deliverables endpoints"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session
from uapk.db import get_session
from uapk.db.models import User, Project, Deliverable
from uapk.api.auth import get_current_user
from uapk.agents.fulfillment import FulfillmentAgent
from uapk.api.main import get_manifest

router = APIRouter()

class CreateDeliverableRequest(BaseModel):
    project_id: int
    title: str
    description: str | None = None
    request_details: dict = {}

@router.post("")
async def create_deliverable(request: CreateDeliverableRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Create deliverable request"""
    project = session.get(Project, request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    deliverable = Deliverable(
        project_id=request.project_id,
        title=request.title,
        description=request.description,
        status="requested",
        request_params=request.request_details,
        created_by=current_user.id
    )
    session.add(deliverable)
    session.commit()
    session.refresh(deliverable)

    # Trigger fulfillment agent (in background)
    async def fulfill():
        manifest = get_manifest()
        agent = FulfillmentAgent("fulfillment-agent", manifest)
        context = {
            "deliverable_id": deliverable.id,
            "project_id": project.id,
            "project_name": project.name,
            "title": deliverable.title,
            "request_details": deliverable.description or ""
        }
        result = await agent.execute(context)

        # Update deliverable
        with Session(session.bind) as update_session:
            db_deliverable = update_session.get(Deliverable, deliverable.id)
            db_deliverable.status = "completed"
            db_deliverable.content_md_hash = result.get("markdown_hash")
            db_deliverable.content_pdf_hash = result.get("pdf_hash")
            update_session.add(db_deliverable)
            update_session.commit()

    background_tasks.add_task(fulfill)

    return {"id": deliverable.id, "title": deliverable.title, "status": deliverable.status}

@router.get("/{deliverable_id}")
def get_deliverable(deliverable_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    deliverable = session.get(Deliverable, deliverable_id)
    if not deliverable:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    return {
        "id": deliverable.id,
        "title": deliverable.title,
        "status": deliverable.status,
        "content_md_hash": deliverable.content_md_hash,
        "content_pdf_hash": deliverable.content_pdf_hash
    }
