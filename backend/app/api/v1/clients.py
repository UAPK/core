"""Client management API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.models import Invoice, Organization, Subscription
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    db: DbSession,
) -> Organization:
    """Create a new client (organization)."""
    # Check if slug already exists
    existing = await db.execute(
        select(Organization).where(Organization.slug == client_data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Client with slug '{client_data.slug}' already exists",
        )

    # Create organization with client fields
    client = Organization(
        name=client_data.name,
        slug=client_data.slug,
        billing_email=client_data.billing_email,
        contact_name=client_data.contact_name,
        contact_email=client_data.contact_email,
        company_address=client_data.company_address,
        vat_id=client_data.vat_id,
        country_code=client_data.country_code,
        payment_terms_days=client_data.payment_terms_days,
        currency=client_data.currency,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


@router.get("", response_model=ClientListResponse)
async def list_clients(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ClientListResponse:
    """List all clients with pagination."""
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(Organization))
    total = count_result.scalar_one()

    # Get paginated clients
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Organization).offset(offset).limit(page_size).order_by(Organization.created_at.desc())
    )
    clients = list(result.scalars().all())

    # For each client, compute statistics
    client_responses = []
    for client in clients:
        # Get invoice stats
        invoice_stats = await db.execute(
            select(
                func.count(Invoice.id).label("total_invoices"),
                func.coalesce(func.sum(Invoice.total), 0).label("total_revenue"),
                func.coalesce(
                    func.sum(
                        case(
                            (Invoice.status.in_(["sent", "overdue"]), Invoice.total),
                            else_=0,
                        )
                    ),
                    0,
                ).label("outstanding_balance"),
            ).where(Invoice.organization_id == client.id)
        )
        stats = invoice_stats.one()

        # Check for active subscription
        active_sub = await db.execute(
            select(Subscription)
            .where(Subscription.organization_id == client.id)
            .where(Subscription.status == "active")
        )
        has_active_subscription = active_sub.scalar_one_or_none() is not None

        client_responses.append(
            ClientResponse(
                id=client.id,
                name=client.name,
                slug=client.slug,
                created_at=client.created_at,
                billing_email=client.billing_email,
                contact_name=client.contact_name,
                contact_email=client.contact_email,
                company_address=client.company_address,
                vat_id=client.vat_id,
                country_code=client.country_code,
                payment_terms_days=client.payment_terms_days,
                currency=client.currency,
                total_invoices=stats.total_invoices,
                total_revenue=float(stats.total_revenue),
                outstanding_balance=float(stats.outstanding_balance),
                active_subscription=has_active_subscription,
            )
        )

    return ClientListResponse(
        clients=client_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: DbSession,
) -> ClientResponse:
    """Get a specific client by ID."""
    result = await db.execute(select(Organization).where(Organization.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    # Get invoice stats
    invoice_stats = await db.execute(
        select(
            func.count(Invoice.id).label("total_invoices"),
            func.coalesce(func.sum(Invoice.total), 0).label("total_revenue"),
            func.coalesce(
                func.sum(
                    func.case(
                        (Invoice.status.in_(["sent", "overdue"]), Invoice.total),
                        else_=0,
                    )
                ),
                0,
            ).label("outstanding_balance"),
        ).where(Invoice.organization_id == client.id)
    )
    stats = invoice_stats.one()

    # Check for active subscription
    active_sub = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == client.id)
        .where(Subscription.status == "active")
    )
    has_active_subscription = active_sub.scalar_one_or_none() is not None

    return ClientResponse(
        id=client.id,
        name=client.name,
        slug=client.slug,
        created_at=client.created_at,
        billing_email=client.billing_email,
        contact_name=client.contact_name,
        contact_email=client.contact_email,
        company_address=client.company_address,
        vat_id=client.vat_id,
        country_code=client.country_code,
        payment_terms_days=client.payment_terms_days,
        currency=client.currency,
        total_invoices=stats.total_invoices,
        total_revenue=float(stats.total_revenue),
        outstanding_balance=float(stats.outstanding_balance),
        active_subscription=has_active_subscription,
    )


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    client_data: ClientUpdate,
    db: DbSession,
) -> ClientResponse:
    """Update a client's information."""
    result = await db.execute(select(Organization).where(Organization.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    # Update only provided fields
    update_data = client_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.commit()
    await db.refresh(client)

    # Get stats for response
    invoice_stats = await db.execute(
        select(
            func.count(Invoice.id).label("total_invoices"),
            func.coalesce(func.sum(Invoice.total), 0).label("total_revenue"),
            func.coalesce(
                func.sum(
                    func.case(
                        (Invoice.status.in_(["sent", "overdue"]), Invoice.total),
                        else_=0,
                    )
                ),
                0,
            ).label("outstanding_balance"),
        ).where(Invoice.organization_id == client.id)
    )
    stats = invoice_stats.one()

    active_sub = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == client.id)
        .where(Subscription.status == "active")
    )
    has_active_subscription = active_sub.scalar_one_or_none() is not None

    return ClientResponse(
        id=client.id,
        name=client.name,
        slug=client.slug,
        created_at=client.created_at,
        billing_email=client.billing_email,
        contact_name=client.contact_name,
        contact_email=client.contact_email,
        company_address=client.company_address,
        vat_id=client.vat_id,
        country_code=client.country_code,
        payment_terms_days=client.payment_terms_days,
        currency=client.currency,
        total_invoices=stats.total_invoices,
        total_revenue=float(stats.total_revenue),
        outstanding_balance=float(stats.outstanding_balance),
        active_subscription=has_active_subscription,
    )


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: DbSession,
) -> None:
    """Delete a client (and all related data)."""
    result = await db.execute(select(Organization).where(Organization.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found",
        )

    await db.delete(client)
    await db.commit()
