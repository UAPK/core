"""Ledger entry model for double-entry bookkeeping."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LedgerEntry(Base):
    """Ledger entry for double-entry bookkeeping."""

    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    account_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # e.g., "1000" (Accounts Receivable), "4000" (Revenue), "2000" (VAT Payable)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    debit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    credit: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    invoice: Mapped["Invoice | None"] = relationship(  # noqa: F821
        "Invoice",
        back_populates="ledger_entries",
    )

    def __repr__(self) -> str:
        return f"<LedgerEntry(id={self.id}, account={self.account_code}, debit={self.debit}, credit={self.credit})>"
