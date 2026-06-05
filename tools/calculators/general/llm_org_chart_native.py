"""Org Chart — hierarchy, reporting, span, depth, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

@dataclass
class Employee:
    id: str
    name: str
    manager_id: Optional[str] = None
    title: str = ""

class OrgChart:
    def __init__(self):
        self.employees: Dict[str, Employee] = {}

    def add_employee(self, e: Employee):
        self.employees[e.id] = e

    def reports(self, manager_id: str) -> List[Employee]:
        return [e for e in self.employees.values() if e.manager_id == manager_id]

    def span_of_control(self, manager_id: str) -> int:
        return len(self.reports(manager_id))

    def depth(self, employee_id: str) -> int:
        depth = 0
        current = employee_id
        while current and self.employees.get(current) and self.employees[current].manager_id:
            depth += 1
            current = self.employees[current].manager_id
        return depth

    def max_depth(self) -> int:
        return max(self.depth(e.id) for e in self.employees.values()) if self.employees else 0

    def chain_of_command(self, employee_id: str) -> List[str]:
        chain = [employee_id]
        current = employee_id
        while current and self.employees.get(current) and self.employees[current].manager_id:
            current = self.employees[current].manager_id
            chain.append(current)
        return chain

    def find_root(self) -> Optional[str]:
        for e in self.employees.values():
            if e.manager_id is None:
                return e.id
        return None

    def stats(self) -> Dict:
        return {
            "employees": len(self.employees),
            "max_depth": self.max_depth(),
            "avg_span": sum(self.span_of_control(e.id) for e in self.employees.values()) / len(self.employees) if self.employees else 0
        }

def run():
    oc = OrgChart()
    oc.add_employee(Employee("CEO", "Alice", None, "CEO"))
    oc.add_employee(Employee("VP1", "Bob", "CEO", "VP Engineering"))
    oc.add_employee(Employee("VP2", "Carol", "CEO", "VP Sales"))
    oc.add_employee(Employee("M1", "Dave", "VP1", "Manager"))
    oc.add_employee(Employee("E1", "Eve", "M1", "Engineer"))
    print(oc.stats())
    print("Chain E1:", oc.chain_of_command("E1"))
    print("Span CEO:", oc.span_of_control("CEO"))

if __name__ == "__main__":
    run()
