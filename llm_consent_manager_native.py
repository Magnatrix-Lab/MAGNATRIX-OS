"""Consent Manager — user consent tracking, withdrawal, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto
import time

class ConsentType(Enum):
    MARKETING = auto()
    ANALYTICS = auto()
    PERSONALIZATION = auto()
    THIRD_PARTY = auto()
    DATA_SHARING = auto()

class ConsentStatus(Enum):
    GRANTED = auto()
    DENIED = auto()
    WITHDRAWN = auto()
    EXPIRED = auto()

@dataclass
class ConsentRecord:
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: float
    expires_at: float
    version: str = "1.0"

class ConsentManager:
    def __init__(self):
        self.consents: Dict[str, List[ConsentRecord]] = {}
        self.required_types: Set[ConsentType] = set()

    def set_required(self, consent_types: List[ConsentType]):
        self.required_types = set(consent_types)

    def grant(self, user_id: str, consent_type: ConsentType, duration_days: float = 365, version: str = "1.0"):
        record = ConsentRecord(user_id, consent_type, ConsentStatus.GRANTED, time.time(), time.time() + duration_days * 86400, version)
        if user_id not in self.consents:
            self.consents[user_id] = []
        self.consents[user_id].append(record)

    def withdraw(self, user_id: str, consent_type: ConsentType):
        for record in self.consents.get(user_id, []):
            if record.consent_type == consent_type and record.status == ConsentStatus.GRANTED:
                record.status = ConsentStatus.WITHDRAWN

    def check(self, user_id: str, consent_type: ConsentType) -> bool:
        for record in self.consents.get(user_id, []):
            if record.consent_type == consent_type and record.status == ConsentStatus.GRANTED and record.expires_at > time.time():
                return True
        return False

    def get_all(self, user_id: str) -> List[ConsentRecord]:
        return self.consents.get(user_id, [])

    def has_all_required(self, user_id: str) -> bool:
        return all(self.check(user_id, ct) for ct in self.required_types)

    def expire_old(self):
        now = time.time()
        for records in self.consents.values():
            for r in records:
                if r.status == ConsentStatus.GRANTED and r.expires_at <= now:
                    r.status = ConsentStatus.EXPIRED

    def stats(self) -> Dict:
        total = sum(len(v) for v in self.consents.values())
        active = sum(1 for v in self.consents.values() for r in v if r.status == ConsentStatus.GRANTED and r.expires_at > time.time())
        return {"users": len(self.consents), "total_records": total, "active_consents": active, "required_types": len(self.required_types)}

def run():
    cm = ConsentManager()
    cm.set_required([ConsentType.ANALYTICS])
    cm.grant("user1", ConsentType.ANALYTICS, 30)
    cm.grant("user1", ConsentType.MARKETING, 30)
    print(cm.check("user1", ConsentType.ANALYTICS))
    cm.withdraw("user1", ConsentType.ANALYTICS)
    print(cm.check("user1", ConsentType.ANALYTICS))
    print(cm.has_all_required("user1"))
    print(cm.stats())

if __name__ == "__main__":
    run()
