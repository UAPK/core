"""Client management schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ClientBase(BaseModel):
    """Base client schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Client/organization name")
    slug: str = Field(..., min_length=1, max_length=100, description="URL-friendly identifier")


class ClientCreate(ClientBase):
    """Schema for creating a new client."""

    # Contact information
    billing_email: EmailStr | None = Field(None, description="Billing contact email")
    contact_name: str | None = Field(None, max_length=255, description="Primary contact name")
    contact_email: EmailStr | None = Field(None, description="Primary contact email")

    # Business details
    company_address: str | None = Field(None, max_length=500, description="Company address")
    vat_id: str | None = Field(None, max_length=50, description="VAT/Tax ID")
    country_code: str | None = Field(None, min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")

    # Payment terms
    payment_terms_days: int = Field(30, ge=0, le=365, description="Payment terms in days")
    currency: str = Field("EUR", min_length=3, max_length=3, description="Preferred currency (ISO 4217)")


class ClientUpdate(BaseModel):
    """Schema for updating a client."""

    name: str | None = Field(None, min_length=1, max_length=255)
    billing_email: EmailStr | None = None
    contact_name: str | None = Field(None, max_length=255)
    contact_email: EmailStr | None = None
    company_address: str | None = Field(None, max_length=500)
    vat_id: str | None = Field(None, max_length=50)
    country_code: str | None = Field(None, min_length=2, max_length=2)
    payment_terms_days: int | None = Field(None, ge=0, le=365)
    currency: str | None = Field(None, min_length=3, max_length=3)


class ClientResponse(ClientBase):
    """Schema for client responses."""

    id: UUID
    created_at: datetime

    # Extended business fields
    billing_email: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    company_address: str | None = None
    vat_id: str | None = None
    country_code: str | None = None
    payment_terms_days: int = 30
    currency: str = "EUR"

    # Statistics (computed)
    total_invoices: int = 0
    total_revenue: float = 0.0
    outstanding_balance: float = 0.0
    active_subscription: bool = False

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    """Schema for paginated client list."""

    clients: list[ClientResponse]
    total: int
    page: int
    page_size: int
