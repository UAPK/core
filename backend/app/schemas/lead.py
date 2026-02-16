"""Lead management schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LeadCreate(BaseModel):
    """Schema for creating a new lead (public form submission)."""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    company: str = Field(..., min_length=1, max_length=255)
    role: str | None = Field(None, max_length=100)
    use_case: str = Field(..., min_length=10, description="Describe your use case")
    timeline: str | None = None
    budget: str | None = None
    interest_type: str = Field("pilot", pattern="^(pilot|blueprint|support|other)$")
    source: str | None = Field(None, max_length=100)


class LeadUpdate(BaseModel):
    """Schema for updating a lead (admin only)."""

    status: str | None = Field(None, pattern="^(new|contacted|qualified|won|lost)$")
    notes: str | None = None
    contacted_at: datetime | None = None


class LeadResponse(BaseModel):
    """Schema for lead responses."""

    id: UUID
    name: str
    email: str
    company: str
    role: str | None
    use_case: str
    timeline: str | None
    budget: str | None
    interest_type: str
    status: str
    source: str | None
    notes: str | None
    contacted_at: datetime | None
    converted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    """Schema for paginated lead list."""

    leads: list[LeadResponse]
    total: int
    page: int
    page_size: int


class LeadStats(BaseModel):
    """Lead pipeline statistics."""

    total_leads: int
    new_leads: int
    contacted_leads: int
    qualified_leads: int
    won_leads: int
    lost_leads: int
    conversion_rate: float  # Won / Total
