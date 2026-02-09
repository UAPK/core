"""Billing endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from datetime import datetime
from uapk.db import get_session
from uapk.db.models import User, Invoice, VATReport, LedgerEntry
from uapk.api.auth import get_current_user
from uapk.agents.billing import BillingAgent
from uapk.api.main import get_manifest
from uapk.tax import VATReportGenerator, get_tax_calculator

router = APIRouter()

class GenerateInvoiceRequest(BaseModel):
    org_id: int
    customer_country: str = "DE"
    customer_vat_id: str | None = None
    is_business: bool = False
    items: list[dict]

@router.post("/invoices/generate")
async def generate_invoice(request: GenerateInvoiceRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Generate invoice"""
    manifest = get_manifest()
    agent = BillingAgent("billing-agent", manifest)

    # Get next sequence number
    statement = select(Invoice).where(Invoice.org_id == request.org_id)
    invoices = session.exec(statement).all()
    sequence = len(invoices) + 1

    context = {
        "org_id": request.org_id,
        "customer_country": request.customer_country,
        "customer_vat_id": request.customer_vat_id,
        "is_business": request.is_business,
        "items": request.items,
        "sequence": sequence
    }

    result = await agent.execute(context)
    return result

@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "subtotal": invoice.subtotal,
        "vat_rate": invoice.vat_rate,
        "vat_amount": invoice.vat_amount,
        "total": invoice.total,
        "reverse_charge": invoice.reverse_charge,
        "status": invoice.status
    }

@router.get("/reports/vat")
def get_vat_report(org_id: int, period_start: str, period_end: str, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Get VAT report for period"""
    statement = select(Invoice).where(Invoice.org_id == org_id)
    invoices = session.exec(statement).all()

    calculator = get_tax_calculator()
    generator = VATReportGenerator(calculator)
    report = generator.generate_report(invoices, period_start, period_end)

    return report

@router.get("/exports/ledger")
def export_ledger(org_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Export ledger in CSV format"""
    from uapk.tax import VATReportGenerator, get_tax_calculator

    statement = select(Invoice).where(Invoice.org_id == org_id)
    invoices = session.exec(statement).all()

    calculator = get_tax_calculator()
    generator = VATReportGenerator(calculator)

    output_path = f"artifacts/exports/ledger_org_{org_id}.csv"
    generator.export_datev_csv(invoices, output_path)

    return {"path": output_path, "invoice_count": len(invoices)}
