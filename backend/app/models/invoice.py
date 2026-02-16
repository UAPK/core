"""Invoice model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Invoice(Base):
    """Invoice for organization billing."""

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        index=True,
    )  # draft, sent, paid, void, overdue

    # Amounts
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    subtotal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vat_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vat_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # VAT/Tax details
    customer_vat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    customer_country: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    reverse_charge: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Dates
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="invoices",
    )
    subscription: Mapped["Subscription | None"] = relationship(  # noqa: F821
        "Subscription",
    )
    items: Mapped[list["InvoiceItem"]] = relationship(  # noqa: F821
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(  # noqa: F821
        "LedgerEntry",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, number={self.invoice_number}, status={self.status})>"
