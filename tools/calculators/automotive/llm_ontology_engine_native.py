"""Ontology Engine — classes, subclasses, properties, reasoning, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

@dataclass
class OntologyClass:
    name: str
    parent: Optional[str] = None
    properties: List[str] = field(default_factory=list)

class OntologyEngine:
    def __init__(self):
        self.classes: Dict[str, OntologyClass] = {}
        self.instances: Dict[str, str] = {}
        self.property_values: Dict[Tuple[str, str], str] = {}

    def add_class(self, name: str, parent: Optional[str] = None, properties: List[str] = None):
        self.classes[name] = OntologyClass(name, parent, properties or [])

    def add_instance(self, name: str, cls: str):
        self.instances[name] = cls

    def set_property(self, instance: str, prop: str, value: str):
        self.property_values[(instance, prop)] = value

    def is_a(self, instance: str, cls: str) -> bool:
        if instance not in self.instances:
            return False
        current = self.instances[instance]
        while current:
            if current == cls:
                return True
            parent = self.classes.get(current, OntologyClass(current)).parent
            current = parent
        return False

    def get_properties(self, cls: str) -> List[str]:
        props = []
        current = cls
        while current:
            c = self.classes.get(current)
            if c:
                props.extend(c.properties)
                current = c.parent
            else:
                break
        return props

    def stats(self) -> Dict:
        return {"classes": len(self.classes), "instances": len(self.instances), "properties": len(self.property_values)}

def run():
    ont = OntologyEngine()
    ont.add_class("Animal", properties=["has_legs"])
    ont.add_class("Dog", parent="Animal", properties=["barks"])
    ont.add_instance("Rex", "Dog")
    ont.set_property("Rex", "barks", "true")
    print("Rex is Animal:", ont.is_a("Rex", "Animal"))
    print("Props:", ont.get_properties("Dog"))
    print(ont.stats())

if __name__ == "__main__":
    run()
