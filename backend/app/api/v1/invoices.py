"""Invoice management API endpoints."""

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.models import Invoice, InvoiceItem, LedgerEntry, Organization
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceSummary,
    InvoiceUpdateStatus,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def generate_invoice_number(year: int, sequence: int) -> str:
    """Generate invoice number in format INV-YYYY-NNNN."""
    return f"INV-{year}-{sequence:04d}"


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    db: DbSession,
) -> InvoiceResponse:
    """Create a new invoice with line items."""
    # Verify organization exists
    org_result = await db.execute(
        select(Organization).where(Organization.id == invoice_data.organization_id)
    )
    organization = org_result.scalar_one_or_none()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {invoice_data.organization_id} not found",
        )

    # Get next invoice number
    year = datetime.utcnow().year
    count_result = await db.execute(
        select(func.count(Invoice.id)).where(
            func.extract("year", Invoice.created_at) == year
        )
    )
    sequence = count_result.scalar_one() + 1
    invoice_number = generate_invoice_number(year, sequence)

    # Calculate subtotal
    subtotal = sum(item.quantity * item.unit_price for item in invoice_data.items)

    # Calculate VAT (simplified - 19% for Germany, 0% for reverse charge)
    vat_rate = 0.0
    reverse_charge = False

    if invoice_data.customer_country:
        # EU reverse charge logic
        if invoice_data.customer_country != "DE" and invoice_data.customer_vat_id:
            reverse_charge = True
            vat_rate = 0.0
        elif invoice_data.customer_country == "DE":
            vat_rate = 0.19
    else:
        # Default German VAT
        vat_rate = 0.19

    vat_amount = subtotal * vat_rate
    total = subtotal + vat_amount

    # Create invoice
    now = datetime.utcnow()
    invoice = Invoice(
        invoice_number=invoice_number,
        organization_id=invoice_data.organization_id,
        subscription_id=invoice_data.subscription_id,
        status="draft",
        currency=organization.currency,
        subtotal=subtotal,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        total=total,
        customer_vat_id=invoice_data.customer_vat_id,
        customer_country=invoice_data.customer_country,
        reverse_charge=reverse_charge,
        issued_at=now,
        due_at=now + timedelta(days=invoice_data.due_days),
    )
    db.add(invoice)
    await db.flush()  # Get invoice ID

    # Create invoice items
    for item_data in invoice_data.items:
        item = InvoiceItem(
            invoice_id=invoice.id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            amount=item_data.quantity * item_data.unit_price,
        )
        db.add(item)

    # Create ledger entries (double-entry bookkeeping)
    # Debit: Accounts Receivable
    debit_entry = LedgerEntry(
        account_code="1000",
        invoice_id=invoice.id,
        description=f"Invoice {invoice_number}",
        debit=total,
        credit=0.0,
    )
    db.add(debit_entry)

    # Credit: Revenue
    credit_revenue = LedgerEntry(
        account_code="4000",
        invoice_id=invoice.id,
        description=f"Invoice {invoice_number} - Revenue",
        debit=0.0,
        credit=subtotal,
    )
    db.add(credit_revenue)

    # Credit: VAT Payable (if VAT charged)
    if vat_amount > 0:
        credit_vat = LedgerEntry(
            account_code="2000",
            invoice_id=invoice.id,
            description=f"Invoice {invoice_number} - VAT",
            debit=0.0,
            credit=vat_amount,
        )
        db.add(credit_vat)

    await db.commit()
    await db.refresh(invoice)

    # Load items for response
    items_result = await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    )
    items = list(items_result.scalars().all())

    return InvoiceResponse(
        **invoice.__dict__,
        items=items,
        organization_name=organization.name,
    )


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    db: DbSession,
    organization_id: UUID | None = None,
    status: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> InvoiceListResponse:
    """List invoices with optional filtering."""
    # Build query
    query = select(Invoice)
    if organization_id:
        query = query.where(Invoice.organization_id == organization_id)
    if status:
        query = query.where(Invoice.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Invoice.created_at.desc())
    result = await db.execute(query)
    invoices = list(result.scalars().all())

    # Load related data
    invoice_responses = []
    for invoice in invoices:
        # Load items
        items_result = await db.execute(
            select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
        )
        items = list(items_result.scalars().all())

        # Load organization name
        org_result = await db.execute(
            select(Organization.name).where(Organization.id == invoice.organization_id)
        )
        org_name = org_result.scalar_one()

        invoice_responses.append(
            InvoiceResponse(
                **invoice.__dict__,
                items=items,
                organization_name=org_name,
            )
        )

    return InvoiceListResponse(
        invoices=invoice_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=InvoiceSummary)
async def get_invoice_summary(
    db: DbSession,
    organization_id: UUID | None = None,
) -> InvoiceSummary:
    """Get invoice summary statistics."""
    query = select(
        func.count(Invoice.id).label("total_invoices"),
        func.coalesce(func.sum(Invoice.total), 0).label("total_revenue"),
        func.coalesce(
            func.sum(case((Invoice.status.in_(["sent", "overdue"]), Invoice.total), else_=0)),
            0,
        ).label("total_outstanding"),
        func.coalesce(
            func.sum(case((Invoice.status == "paid", Invoice.total), else_=0)),
            0,
        ).label("total_paid"),
        func.coalesce(
            func.sum(case((Invoice.status == "overdue", Invoice.total), else_=0)),
            0,
        ).label("total_overdue"),
    )

    if organization_id:
        query = query.where(Invoice.organization_id == organization_id)

    result = await db.execute(query)
    stats = result.one()

    return InvoiceSummary(
        total_invoices=stats.total_invoices,
        total_revenue=float(stats.total_revenue),
        total_outstanding=float(stats.total_outstanding),
        total_paid=float(stats.total_paid),
        total_overdue=float(stats.total_overdue),
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    db: DbSession,
) -> InvoiceResponse:
    """Get a specific invoice by ID."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    # Load items
    items_result = await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    )
    items = list(items_result.scalars().all())

    # Load organization name
    org_result = await db.execute(
        select(Organization.name).where(Organization.id == invoice.organization_id)
    )
    org_name = org_result.scalar_one()

    return InvoiceResponse(
        **invoice.__dict__,
        items=items,
        organization_name=org_name,
    )


@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
async def update_invoice_status(
    invoice_id: UUID,
    status_data: InvoiceUpdateStatus,
    db: DbSession,
) -> InvoiceResponse:
    """Update invoice status."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    # Update status
    invoice.status = status_data.status

    # If marking as paid, set paid_at timestamp
    if status_data.status == "paid" and not invoice.paid_at:
        invoice.paid_at = datetime.utcnow()

    await db.commit()
    await db.refresh(invoice)

    # Load items
    items_result = await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    )
    items = list(items_result.scalars().all())

    # Load organization name
    org_result = await db.execute(
        select(Organization.name).where(Organization.id == invoice.organization_id)
    )
    org_name = org_result.scalar_one()

    return InvoiceResponse(
        **invoice.__dict__,
        items=items,
        organization_name=org_name,
    )


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: UUID,
    db: DbSession,
) -> InvoiceResponse:
    """Mark an invoice as paid."""
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    invoice.status = "paid"
    invoice.paid_at = datetime.utcnow()

    await db.commit()
    await db.refresh(invoice)

    # Load items
    items_result = await db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    )
    items = list(items_result.scalars().all())

    # Load organization name
    org_result = await db.execute(
        select(Organization.name).where(Organization.id == invoice.organization_id)
    )
    org_name = org_result.scalar_one()

    return InvoiceResponse(
        **invoice.__dict__,
        items=items,
        organization_name=org_name,
    )
