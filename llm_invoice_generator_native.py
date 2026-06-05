"""Native stdlib module: Invoice Generator
Generates line-item invoices with subtotals, tax, and totals.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class LineItem:
    description: str
    quantity: float
    unit_price: float
    tax_rate_pct: float = 0.0

    def subtotal(self) -> float:
        return self.quantity * self.unit_price

    def tax_amount(self) -> float:
        return self.subtotal() * (self.tax_rate_pct / 100)

    def total(self) -> float:
        return self.subtotal() + self.tax_amount()

@dataclass
class InvoiceGenerator:
    invoice_number: str
    client_name: str
    issue_date: str
    due_date: str
    items: List[LineItem] = field(default_factory=list)

    def subtotal(self) -> float:
        return sum(i.subtotal() for i in self.items)

    def total_tax(self) -> float:
        return sum(i.tax_amount() for i in self.items)

    def total(self) -> float:
        return self.subtotal() + self.total_tax()

    def stats(self) -> Dict[str, float]:
        return {
            "invoice": self.invoice_number,
            "subtotal": round(self.subtotal(), 2),
            "total_tax": round(self.total_tax(), 2),
            "total_due": round(self.total(), 2),
            "line_items": len(self.items),
        }

def run():
    ig = InvoiceGenerator(
        invoice_number="INV-2024-001",
        client_name="Acme Corp",
        issue_date="2024-06-01",
        due_date="2024-06-30",
        items=[
            LineItem("Consulting", 40, 150, tax_rate_pct=10),
            LineItem("Software License", 2, 500, tax_rate_pct=10),
            LineItem("Support", 10, 100, tax_rate_pct=0),
        ]
    )
    print(ig.stats())

if __name__ == "__main__":
    run()
