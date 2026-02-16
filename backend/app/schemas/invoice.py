"""Invoice management schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceItemCreate(BaseModel):
    """Schema for creating an invoice item."""

    description: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., ge=0)


class InvoiceItemResponse(BaseModel):
    """Schema for invoice item response."""

    id: UUID
    description: str
    quantity: int
    unit_price: float
    amount: float
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    """Schema for creating an invoice."""

    organization_id: UUID = Field(..., description="Client organization ID")
    subscription_id: UUID | None = Field(None, description="Optional subscription ID")
    items: list[InvoiceItemCreate] = Field(..., min_length=1, description="Invoice line items")

    # Optional metadata
    customer_vat_id: str | None = Field(None, max_length=50)
    customer_country: str | None = Field(None, min_length=2, max_length=2)
    due_days: int = Field(30, ge=0, le=365, description="Days until payment is due")


class InvoiceUpdateStatus(BaseModel):
    """Schema for updating invoice status."""

    status: str = Field(..., pattern="^(draft|sent|paid|void|overdue)$")


class InvoiceResponse(BaseModel):
    """Schema for invoice response."""

    id: UUID
    invoice_number: str
    organization_id: UUID
    subscription_id: UUID | None
    status: str
    currency: str
    subtotal: float
    vat_rate: float
    vat_amount: float
    total: float
    customer_vat_id: str | None
    customer_country: str | None
    reverse_charge: bool
    issued_at: datetime | None
    due_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Computed/related fields
    items: list[InvoiceItemResponse] = []
    organization_name: str | None = None

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    """Schema for paginated invoice list."""

    invoices: list[InvoiceResponse]
    total: int
    page: int
    page_size: int


class InvoiceSummary(BaseModel):
    """Summary statistics for invoices."""

    total_invoices: int
    total_revenue: float
    total_outstanding: float
    total_paid: float
    total_overdue: float
    currency: str = "EUR"
