"""Lead management API endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.models import Lead, Organization
from app.schemas.lead import (
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    LeadStats,
    LeadUpdate,
)
from app.services.email import get_email_service

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    db: DbSession,
) -> Lead:
    """Create a new lead (public endpoint - no authentication required)."""
    # Create lead
    lead = Lead(
        name=lead_data.name,
        email=lead_data.email,
        company=lead_data.company,
        role=lead_data.role,
        use_case=lead_data.use_case,
        timeline=lead_data.timeline,
        budget=lead_data.budget,
        interest_type=lead_data.interest_type,
        source=lead_data.source or "website",
        status="new",
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Send auto-response email to lead
    email_service = get_email_service()
    email_service.send_lead_auto_response(lead)

    # Send notification email to admin
    email_service.send_admin_notification(lead)

    return lead


@router.get("", response_model=LeadListResponse)
async def list_leads(
    db: DbSession,
    status_filter: str | None = Query(None, alias="status"),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> LeadListResponse:
    """List all leads with optional status filtering."""
    # Build query
    query = select(Lead)
    if status_filter:
        query = query.where(Lead.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Lead.created_at.desc())
    result = await db.execute(query)
    leads = list(result.scalars().all())

    return LeadListResponse(
        leads=leads,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=LeadStats)
async def get_lead_stats(
    db: DbSession,
) -> LeadStats:
    """Get lead pipeline statistics."""
    # Count by status
    stats_query = select(
        func.count(Lead.id).label("total"),
        func.count(Lead.id).filter(Lead.status == "new").label("new"),
        func.count(Lead.id).filter(Lead.status == "contacted").label("contacted"),
        func.count(Lead.id).filter(Lead.status == "qualified").label("qualified"),
        func.count(Lead.id).filter(Lead.status == "won").label("won"),
        func.count(Lead.id).filter(Lead.status == "lost").label("lost"),
    )
    result = await db.execute(stats_query)
    stats = result.one()

    # Calculate conversion rate
    conversion_rate = (stats.won / stats.total * 100) if stats.total > 0 else 0.0

    return LeadStats(
        total_leads=stats.total,
        new_leads=stats.new,
        contacted_leads=stats.contacted,
        qualified_leads=stats.qualified,
        won_leads=stats.won,
        lost_leads=stats.lost,
        conversion_rate=conversion_rate,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: DbSession,
) -> Lead:
    """Get a specific lead by ID."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )

    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    db: DbSession,
) -> Lead:
    """Update a lead's status and notes."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )

    # Update fields
    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    # Auto-set contacted_at if status changed to contacted
    if lead_data.status == "contacted" and not lead.contacted_at:
        lead.contacted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(lead)
    return lead


@router.post("/{lead_id}/convert", response_model=dict)
async def convert_lead_to_client(
    lead_id: UUID,
    db: DbSession,
) -> dict:
    """Convert a lead to a client (organization)."""
    # Get lead
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead {lead_id} not found",
        )

    # Check if lead already converted
    if lead.status == "won" and lead.converted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lead already converted to client",
        )

    # Generate slug from company name
    slug = lead.company.lower().replace(" ", "-").replace(".", "")[:100]

    # Check if organization with this slug exists
    existing = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if existing.scalar_one_or_none():
        # Add number suffix if slug exists
        count = 1
        while True:
            new_slug = f"{slug}-{count}"
            existing = await db.execute(
                select(Organization).where(Organization.slug == new_slug)
            )
            if not existing.scalar_one_or_none():
                slug = new_slug
                break
            count += 1

    # Create organization from lead
    organization = Organization(
        name=lead.company,
        slug=slug,
        billing_email=lead.email,
        contact_name=lead.name,
        contact_email=lead.email,
    )
    db.add(organization)

    # Update lead status
    lead.status = "won"
    lead.converted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(organization)

    return {
        "lead_id": str(lead.id),
        "client_id": str(organization.id),
        "message": f"Lead converted to client: {organization.name}",
    }
