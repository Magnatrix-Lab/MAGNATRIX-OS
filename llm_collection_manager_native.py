"""Collection Manager — accession, provenance, loan, deaccession, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class CollectionItem:
    accession_number: str
    title: str
    date_acquired: str
    donor: str = ""
    on_loan: bool = False
    loan_to: str = ""
    deaccession_date: Optional[str] = None

class CollectionManager:
    def __init__(self):
        self.items: Dict[str, CollectionItem] = {}

    def add_item(self, item: CollectionItem):
        self.items[item.accession_number] = item

    def provenance(self, accession: str) -> List[str]:
        item = self.items.get(accession)
        if not item:
            return []
        chain = [f"Acquired {item.date_acquired}"]
        if item.donor:
            chain.append(f"Donor: {item.donor}")
        if item.on_loan:
            chain.append(f"On loan to: {item.loan_to}")
        return chain

    def loan_status(self) -> List[str]:
        return [i.accession_number for i in self.items.values() if i.on_loan]

    def deaccession_list(self) -> List[str]:
        return [i.accession_number for i in self.items.values() if i.deaccession_date]

    def acquisition_value(self, values: Dict[str, float]) -> float:
        return sum(values.get(acc, 0) for acc in self.items)

    def stats(self) -> Dict:
        return {"total": len(self.items), "on_loan": len(self.loan_status()), "deaccessioned": len(self.deaccession_list())}

def run():
    cm = CollectionManager()
    cm.add_item(CollectionItem("2024.001", "Vase", "2024-01-15", "Smith", False, ""))
    cm.add_item(CollectionItem("2024.002", "Painting", "2024-02-01", "", True, "Museum B"))
    print(cm.stats())
    print("Provenance 2024.001:", cm.provenance("2024.001"))

if __name__ == "__main__":
    run()
