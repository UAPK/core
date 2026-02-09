"""
Billing Agent
Generates invoices, applies VAT, creates ledger entries.
"""
from typing import Dict, Any
from datetime import datetime, timedelta

from uapk.agents.base import BaseAgent
from uapk.tax import get_tax_calculator
from uapk.db.models import Invoice, InvoiceItem, LedgerEntry
from uapk.db import create_session


class BillingAgent(BaseAgent):
    """Handles invoice generation and billing operations"""

    def __init__(self, agent_id: str, manifest: Any):
        super().__init__(agent_id, manifest)
        self.finance_ops = manifest.corporateModules.financeOps

    def generate_invoice_number(self, year: int, sequence: int) -> str:
        """Generate invoice number from template"""
        template = self.finance_ops.invoiceNumberingScheme
        return template.format(year=year, seq=sequence)

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate invoice for a deliverable or subscription.

        Context should include:
        - org_id
        - customer_country
        - customer_vat_id (optional)
        - is_business
        - items: [{"description": str, "quantity": int, "unit_price": float}]
        """
        org_id = context.get("org_id")
        customer_country = context.get("customer_country", "DE")
        customer_vat_id = context.get("customer_vat_id")
        is_business = context.get("is_business", False)
        items = context.get("items", [])

        self.audit("start_invoice_generation", params=context)

        # Calculate subtotal
        subtotal = sum(item["quantity"] * item["unit_price"] for item in items)

        # Calculate VAT
        tax_calculator = get_tax_calculator()
        vat_calc = tax_calculator.calculate_vat(
            amount=subtotal,
            customer_country=customer_country,
            customer_vat_id=customer_vat_id,
            is_business=is_business
        )

        # Generate invoice number
        now = datetime.utcnow()
        year = now.year
        # In production, would query DB for next sequence number
        sequence = context.get("sequence", 1)
        invoice_number = self.generate_invoice_number(year, sequence)

        # Create invoice
        session = create_session()
        try:
            invoice = Invoice(
                invoice_number=invoice_number,
                org_id=org_id,
                status="draft",
                currency=self.manifest.saasModules.billing.currency,
                subtotal=vat_calc.subtotal,
                vat_rate=vat_calc.vat_rate,
                vat_amount=vat_calc.vat_amount,
                total=vat_calc.total,
                customer_vat_id=customer_vat_id,
                customer_country=customer_country,
                reverse_charge=vat_calc.reverse_charge,
                issued_at=now,
                due_at=now + timedelta(days=30)
            )
            session.add(invoice)
            session.flush()  # Get invoice ID

            # Create invoice items
            for item in items:
                invoice_item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item["description"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    amount=item["quantity"] * item["unit_price"]
                )
                session.add(invoice_item)

            # Create ledger entries (double-entry bookkeeping)
            # Debit: Accounts Receivable
            debit_entry = LedgerEntry(
                account_code="1000",  # Accounts Receivable
                invoice_id=invoice.id,
                description=f"Invoice {invoice_number}",
                debit=vat_calc.total,
                credit=0.0
            )
            session.add(debit_entry)

            # Credit: Revenue
            credit_entry = LedgerEntry(
                account_code="4000",  # Revenue - Services
                invoice_id=invoice.id,
                description=f"Invoice {invoice_number} - Revenue",
                debit=0.0,
                credit=vat_calc.subtotal
            )
            session.add(credit_entry)

            # Credit: VAT Payable (if VAT charged)
            if vat_calc.vat_amount > 0:
                vat_entry = LedgerEntry(
                    account_code="2000",  # VAT Payable
                    invoice_id=invoice.id,
                    description=f"Invoice {invoice_number} - VAT",
                    debit=0.0,
                    credit=vat_calc.vat_amount
                )
                session.add(vat_entry)

            session.commit()

            result = {
                "invoice_id": invoice.id,
                "invoice_number": invoice_number,
                "subtotal": vat_calc.subtotal,
                "vat_rate": vat_calc.vat_rate,
                "vat_amount": vat_calc.vat_amount,
                "total": vat_calc.total,
                "reverse_charge": vat_calc.reverse_charge,
                "vat_reason": vat_calc.reason
            }

            self.audit("invoice_generated", params=context, result=result)

            return result

        except Exception as e:
            session.rollback()
            self.audit("invoice_generation_failed", params=context, result={"error": str(e)})
            raise
        finally:
            session.close()
