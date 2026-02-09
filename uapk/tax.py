"""
Tax/VAT Calculation Module
Implements VAT rules for EU and other jurisdictions.
Handles reverse charge, VAT rates, and compliance.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass

from uapk.manifest_schema import TaxOpsModule


@dataclass
class VATCalculation:
    """Result of VAT calculation"""
    subtotal: float
    vat_rate: float
    vat_amount: float
    total: float
    reverse_charge: bool
    reason: str


class TaxCalculator:
    """
    Calculate VAT based on simplified EU rules.

    Rules implemented:
    1. EU B2B with valid VAT ID: reverse charge (0% VAT, customer pays)
    2. EU B2C: apply VAT rate of customer country
    3. Non-EU: no VAT (0%)
    """

    def __init__(self, tax_config: TaxOpsModule):
        self.config = tax_config
        self.vat_rates = tax_config.vatRules.get("vat_rates", {})
        self.reverse_charge_countries = tax_config.vatRules.get("reverse_charge_countries", [])
        self.eu_b2b_reverse_charge = tax_config.vatRules.get("EU_B2B_reverse_charge", True)
        self.eu_b2c_apply_vat = tax_config.vatRules.get("EU_B2C_apply_vat", True)
        self.default_vat_rate = tax_config.vatRules.get("default_vat_rate", 0.19)

    def is_eu_country(self, country_code: str) -> bool:
        """Check if country is in EU (simplified)"""
        return country_code in self.reverse_charge_countries

    def calculate_vat(
        self,
        amount: float,
        customer_country: str,
        customer_vat_id: Optional[str] = None,
        is_business: bool = False
    ) -> VATCalculation:
        """
        Calculate VAT for an invoice.

        Args:
            amount: Subtotal (before VAT)
            customer_country: 2-letter country code (e.g., "DE", "US")
            customer_vat_id: Customer VAT ID (if business)
            is_business: Whether customer is a business

        Returns:
            VATCalculation with all tax details
        """
        # Non-EU: no VAT
        if not self.is_eu_country(customer_country):
            return VATCalculation(
                subtotal=amount,
                vat_rate=0.0,
                vat_amount=0.0,
                total=amount,
                reverse_charge=False,
                reason=f"Non-EU country ({customer_country}): no VAT"
            )

        # EU B2B with valid VAT ID: reverse charge
        if is_business and customer_vat_id and self.eu_b2b_reverse_charge:
            # In real implementation, would validate VAT ID via VIES
            # For now, simple check: VAT ID must exist and start with country code
            if customer_vat_id.startswith(customer_country):
                return VATCalculation(
                    subtotal=amount,
                    vat_rate=0.0,
                    vat_amount=0.0,
                    total=amount,
                    reverse_charge=True,
                    reason=f"EU B2B reverse charge ({customer_country})"
                )

        # EU B2C or B2B without valid VAT ID: apply VAT
        if self.eu_b2c_apply_vat:
            vat_rate = self.vat_rates.get(customer_country, self.default_vat_rate)
            vat_amount = round(amount * vat_rate, 2)
            total = amount + vat_amount

            return VATCalculation(
                subtotal=amount,
                vat_rate=vat_rate,
                vat_amount=vat_amount,
                total=total,
                reverse_charge=False,
                reason=f"EU B2C VAT applied ({customer_country}): {vat_rate * 100}%"
            )

        # Fallback: no VAT
        return VATCalculation(
            subtotal=amount,
            vat_rate=0.0,
            vat_amount=0.0,
            total=amount,
            reverse_charge=False,
            reason="No VAT applied (fallback)"
        )

    def validate_vat_id(self, vat_id: str, country_code: str) -> bool:
        """
        Validate VAT ID format (simplified).
        In production, would call VIES API.
        """
        if not vat_id:
            return False

        # Simple validation: VAT ID should start with country code
        # Real validation would use VIES API
        if not vat_id.startswith(country_code):
            return False

        # Additional format checks (very simplified)
        # Real implementation would have country-specific patterns
        if len(vat_id) < 5:
            return False

        return True


class VATReportGenerator:
    """Generate VAT reports for a period"""

    def __init__(self, tax_calculator: TaxCalculator):
        self.calculator = tax_calculator

    def generate_report(
        self,
        invoices: list,
        period_start: str,
        period_end: str
    ) -> Dict[str, Any]:
        """
        Generate VAT report from invoices.

        Returns summary with:
        - Total sales (by country)
        - Total VAT collected (by rate)
        - Reverse charge transactions
        - Export for tax authorities
        """
        # Group by country and rate
        sales_by_country: Dict[str, float] = {}
        vat_by_rate: Dict[float, float] = {}
        reverse_charge_total = 0.0
        total_sales = 0.0
        total_vat = 0.0

        for invoice in invoices:
            country = invoice.customer_country or "UNKNOWN"
            sales_by_country[country] = sales_by_country.get(country, 0.0) + invoice.subtotal
            total_sales += invoice.subtotal

            if invoice.reverse_charge:
                reverse_charge_total += invoice.subtotal
            else:
                rate = invoice.vat_rate
                vat_by_rate[rate] = vat_by_rate.get(rate, 0.0) + invoice.vat_amount
                total_vat += invoice.vat_amount

        # Generate report
        report = {
            "period": {
                "start": period_start,
                "end": period_end
            },
            "summary": {
                "totalSales": round(total_sales, 2),
                "totalVATCollected": round(total_vat, 2),
                "reverseChargeTransactions": round(reverse_charge_total, 2)
            },
            "salesByCountry": {
                country: round(amount, 2)
                for country, amount in sales_by_country.items()
            },
            "vatByRate": {
                f"{int(rate * 100)}%": round(amount, 2)
                for rate, amount in vat_by_rate.items()
            },
            "invoiceCount": len(invoices)
        }

        return report

    def export_datev_csv(
        self,
        invoices: list,
        output_path: str
    ) -> str:
        """
        Export invoices to DATEV-like CSV format.
        Simplified version for demonstration.
        """
        import csv
        from pathlib import Path

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=';')

            # Header
            writer.writerow([
                "Invoice Number",
                "Date",
                "Customer Country",
                "Subtotal",
                "VAT Rate",
                "VAT Amount",
                "Total",
                "Reverse Charge",
                "Status"
            ])

            # Rows
            for invoice in invoices:
                writer.writerow([
                    invoice.invoice_number,
                    invoice.issued_at.strftime("%Y-%m-%d") if invoice.issued_at else "",
                    invoice.customer_country or "",
                    f"{invoice.subtotal:.2f}",
                    f"{invoice.vat_rate * 100:.0f}%" if invoice.vat_rate else "0%",
                    f"{invoice.vat_amount:.2f}",
                    f"{invoice.total:.2f}",
                    "Yes" if invoice.reverse_charge else "No",
                    invoice.status
                ])

        return output_path


# Global tax calculator
_tax_calculator: Optional[TaxCalculator] = None


def init_tax_calculator(tax_config: TaxOpsModule):
    """Initialize global tax calculator"""
    global _tax_calculator
    _tax_calculator = TaxCalculator(tax_config)


def get_tax_calculator() -> TaxCalculator:
    """Get global tax calculator"""
    if _tax_calculator is None:
        raise RuntimeError("Tax calculator not initialized")
    return _tax_calculator


def calculate_vat(
    amount: float,
    customer_country: str,
    customer_vat_id: Optional[str] = None,
    is_business: bool = False
) -> VATCalculation:
    """Convenience function to calculate VAT"""
    return get_tax_calculator().calculate_vat(
        amount=amount,
        customer_country=customer_country,
        customer_vat_id=customer_vat_id,
        is_business=is_business
    )
