"""Ontology Manager - Class hierarchy for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto
from collections import defaultdict

class RelationType(Enum):
    SUBCLASS = auto(); INSTANCE = auto(); PROPERTY = auto()

@dataclass
class OntologyManager:
    classes: Dict[str, Dict] = field(default_factory=dict)
    relations: List[Tuple[str, str, str, RelationType]] = field(default_factory=list)

    def add_class(self, class_name: str, parent: Optional[str] = None) -> None:
        self.classes[class_name] = {"parent": parent, "instances": set(), "properties": set()}

    def add_instance(self, instance: str, class_name: str) -> None:
        if class_name in self.classes:
            self.classes[class_name]["instances"].add(instance)

    def add_relation(self, a: str, relation: str, b: str, rtype: RelationType) -> None:
        self.relations.append((a, relation, b, rtype))

    def is_subclass(self, child: str, parent: str) -> bool:
        if child == parent: return True
        if child not in self.classes: return False
        p = self.classes[child]["parent"]
        return self.is_subclass(p, parent) if p else False

    def get_instances(self, class_name: str) -> Set[str]:
        instances = set(self.classes.get(class_name, {}).get("instances", set()))
        for c, info in self.classes.items():
            if self.is_subclass(c, class_name):
                instances.update(info["instances"])
        return instances

    def stats(self) -> dict:
        return {"classes": len(self.classes), "relations": len(self.relations), "instances": sum(len(c["instances"]) for c in self.classes.values())}

def run():
    om = OntologyManager()
    om.add_class("Animal")
    om.add_class("Mammal", "Animal")
    om.add_class("Dog", "Mammal")
    om.add_instance("Buddy", "Dog")
    print("Animal instances:", om.get_instances("Animal"))
    print("Stats:", om.stats())

if __name__ == "__main__": run()
