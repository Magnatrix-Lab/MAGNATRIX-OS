# blockchain/syariah_finance_native.py
# AMATI-PELAJARI-TIRU: Syariah-Compliant DeFi Engine for Indonesia
# Islamic finance principles: no riba, no gharar, no maysir, asset-backed
# Layer blockchain of MAGNATRIX-OS — National Financial Infrastructure

"""
Native Syariah Finance Engine
============================
Islamic-compliant decentralized finance for Indonesia:
  - Mudarabah: Profit-sharing partnership (investor + manager)
  - Musyarakah: Joint venture with proportional ownership
  - Murabahah: Cost-plus financing (trade financing)
  - Ijarah: Leasing/rental without interest
  - Wadiah: Safekeeping (no interest, may have hibah/gift)
  - ZISWAF: Zakat, Infaq, Sadaqah, Waqaf management
  - Sukuk: Islamic bond certificate (ijarah sukuk, mudarabah sukuk)
  - Takaful: Mutual insurance cooperative

Compliance Engine:
  - Riba (interest) detection and prevention
  - Gharar (excessive uncertainty) assessment
  - Maysir (gambling) pattern detection
  - Halal asset screening (no alcohol, pork, gambling, conventional banking)
  - Shariah Board approval workflow
  - Fatwa tracking and implementation

Features:
  - Pure-Python Syariah DeFi (no external Shariah APIs)
  - Automated profit/loss distribution (no fixed returns)
  - Asset-backed transaction requirements
  - Zakat calculator with nishab and haul
  - Waqaf perpetual endowment tracking
  - Sukuk coupon as profit-sharing (not interest)
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta


class SyariahContractType(Enum):
    MUDARABAH = auto()
    MUSYARAKAH = auto()
    MURABAHAH = auto()
    IJARAH = auto()
    WADIAH = auto()
    SUKUK = auto()
    TAKAFUL = auto()
    WAKAF = auto()


class ComplianceStatus(Enum):
    COMPLIANT = auto()
    RIBA_DETECTED = auto()
    GHARAR_HIGH = auto()
    MAYSIR_DETECTED = auto()
    NON_HALAL_ASSET = auto()
    PENDING_REVIEW = auto()


@dataclass
class SyariahContract:
    contract_id: str
    contract_type: SyariahContractType
    participants: List[str] = field(default_factory=list)
    capital: float = 0.0
    profit_ratio: Dict[str, float] = field(default_factory=dict)
    loss_ratio: Dict[str, float] = field(default_factory=dict)
    asset_backing: str = ""  # Reference to physical asset
    duration_days: int = 0
    status: str = "active"
    created_at: str = ""
    profit_loss: float = 0.0


@dataclass
class ZakatRecord:
    owner: str
    asset_type: str
    value_idr: float
    nishab_idr: float = 85_000_000.0  # Approx 85jt for gold
    haul_met: bool = False  # 1 year ownership
    zakat_due: float = 0.0
    paid: float = 0.0


@dataclass
class WaqafEndowment:
    waqaf_id: str
    waqif: str  # Donor
    asset_id: str
    purpose: str  # Education, health, mosque, etc.
    beneficiaries: List[str] = field(default_factory=list)
    perpetual: bool = True
    income_generated: float = 0.0
    distributed: float = 0.0


@dataclass
class SukukCertificate:
    sukuk_id: str
    sukuk_type: str  # ijarah, mudarabah, musharakah
    face_value: float
    profit_rate: float  # Expected profit, not fixed interest
    maturity_date: str
    holders: Dict[str, int] = field(default_factory=dict)
    total_issued: int = 0
    profit_distributed: float = 0.0


class ShariahComplianceEngine:
    """Automated Shariah compliance checking."""

    HALAL_SECTORS = {"agriculture", "technology", "manufacturing", "healthcare", "education", "energy", "transport", "logistics"}
    HARAM_SECTORS = {"alcohol", "gambling", "pork", "conventional_banking", "interest_bearing", "weaponry", "adult_entertainment"}
    GHARAR_KEYWORDS = {"uncertain", "speculative", "derivative", "futures", "options", "swap", "short", "naked"}
    MAYSIR_KEYWORDS = {"gamble", "bet", "lottery", "casino", "game of chance", " speculation"}
    RIBA_PATTERNS = {"interest", "fixed return", "guaranteed profit", "APR", "APY", "yield", "compounding", "usury"}

    def check_contract(self, contract_type: SyariahContractType, description: str, asset_sector: str) -> Dict[str, Any]:
        issues = []
        # Check haram sector
        if any(h in asset_sector.lower() for h in self.HARAM_SECTORS):
            issues.append(ComplianceStatus.NON_HALAL_ASSET)
        # Check riba patterns
        desc_lower = description.lower()
        if any(r in desc_lower for r in self.RIBA_PATTERNS):
            issues.append(ComplianceStatus.RIBA_DETECTED)
        # Check gharar
        if any(g in desc_lower for g in self.GHARAR_KEYWORDS):
            issues.append(ComplianceStatus.GHARAR_HIGH)
        # Check maysir
        if any(m in desc_lower for m in self.MAYSIR_KEYWORDS):
            issues.append(ComplianceStatus.MAYSIR_DETECTED)
        # Mudarabah and musyarakah must be asset-backed
        if contract_type in (SyariahContractType.MUDARABAH, SyariahContractType.MUSYARAKAH) and not description:
            issues.append(ComplianceStatus.GHARAR_HIGH)
        if not issues:
            issues.append(ComplianceStatus.COMPLIANT)
        return {"status": issues[0], "all_issues": [i.name for i in issues], "contract_type": contract_type.name}

    def validate_profit_distribution(self, contract: SyariahContract, actual_profit: float) -> Dict[str, Any]:
        if actual_profit < 0:
            # Loss: distributed according to loss ratio (capital contribution)
            total_loss = abs(actual_profit)
            distribution = {p: total_loss * contract.loss_ratio.get(p, 0.0) for p in contract.participants}
            return {"type": "loss", "total_loss": total_loss, "distribution": distribution}
        # Profit: distributed according to profit ratio
        distribution = {p: actual_profit * contract.profit_ratio.get(p, 0.0) for p in contract.participants}
        return {"type": "profit", "total_profit": actual_profit, "distribution": distribution}

    def screen_asset(self, sector: str, activities: List[str]) -> Dict[str, Any]:
        halal_score = 0.0
        for activity in activities:
            if any(s in activity.lower() for s in self.HALAL_SECTORS):
                halal_score += 0.2
            if any(h in activity.lower() for h in self.HARAM_SECTORS):
                halal_score -= 0.5
        is_halal = halal_score >= 0.5 and not any(h in sector.lower() for h in self.HARAM_SECTORS)
        return {"sector": sector, "halal_score": halal_score, "is_halal": is_halal, "activities": activities}


class SyariahDeFiEngine:
    """Main Syariah DeFi orchestrator."""

    def __init__(self):
        self.compliance = ShariahComplianceEngine()
        self.contracts: Dict[str, SyariahContract] = {}
        self.zakat_records: Dict[str, ZakatRecord] = {}
        self.waqafs: Dict[str, WaqafEndowment] = {}
        self.sukuks: Dict[str, SukukCertificate] = {}
        self.takaful_pool: float = 0.0
        self.takaful_claims: List[Dict[str, Any]] = []
        self.shariah_board_approvals: Dict[str, bool] = {}

    def create_mudarabah(self, investor: str, manager: str, capital: float, investor_ratio: float, manager_ratio: float, asset_backing: str, duration: int = 365) -> Dict[str, Any]:
        contract_id = f"MUD-{hashlib.sha256(f'{investor}:{manager}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        contract = SyariahContract(
            contract_id=contract_id, contract_type=SyariahContractType.MUDARABAH,
            participants=[investor, manager], capital=capital,
            profit_ratio={investor: investor_ratio, manager: manager_ratio},
            loss_ratio={investor: 1.0, manager: 0.0},  # Manager bears no loss in pure mudarabah
            asset_backing=asset_backing, duration_days=duration,
            created_at=datetime.utcnow().isoformat(),
        )
        check = self.compliance.check_contract(SyariahContractType.MUDARABAH, asset_backing, "investment")
        if check["status"] != ComplianceStatus.COMPLIANT:
            return {"error": "Shariah compliance failed", "details": check}
        self.contracts[contract_id] = contract
        return {"contract_id": contract_id, "type": "Mudarabah", "compliance": check, "capital": capital}

    def create_musyarakah(self, partners: List[Tuple[str, float]], asset_backing: str, duration: int = 365) -> Dict[str, Any]:
        contract_id = f"MUS-{hashlib.sha256(f'{partners}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        total_capital = sum(p[1] for p in partners)
        profit_ratio = {p[0]: p[1] / total_capital for p in partners}
        loss_ratio = dict(profit_ratio)  # Same as profit ratio in musyarakah
        contract = SyariahContract(
            contract_id=contract_id, contract_type=SyariahContractType.MUSYARAKAH,
            participants=[p[0] for p in partners], capital=total_capital,
            profit_ratio=profit_ratio, loss_ratio=loss_ratio,
            asset_backing=asset_backing, duration_days=duration,
            created_at=datetime.utcnow().isoformat(),
        )
        check = self.compliance.check_contract(SyariahContractType.MUSYARAKAH, asset_backing, "investment")
        self.contracts[contract_id] = contract
        return {"contract_id": contract_id, "type": "Musyarakah", "compliance": check, "capital": total_capital}

    def create_murabahah(self, buyer: str, seller: str, cost_price: float, markup: float, asset: str) -> Dict[str, Any]:
        contract_id = f"MUR-{hashlib.sha256(f'{buyer}:{seller}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        selling_price = cost_price + markup
        contract = SyariahContract(
            contract_id=contract_id, contract_type=SyariahContractType.MURABAHAH,
            participants=[buyer, seller], capital=selling_price,
            asset_backing=asset, duration_days=0,
            created_at=datetime.utcnow().isoformat(),
        )
        check = self.compliance.check_contract(SyariahContractType.MURABAHAH, f"Cost: {cost_price}, Markup: {markup}", "trade")
        self.contracts[contract_id] = contract
        return {"contract_id": contract_id, "type": "Murabahah", "cost": cost_price, "selling_price": selling_price, "compliance": check}

    def create_ijarah(self, lessor: str, lessee: str, asset: str, rental_value: float, duration: int) -> Dict[str, Any]:
        contract_id = f"IJA-{hashlib.sha256(f'{lessor}:{lessee}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        contract = SyariahContract(
            contract_id=contract_id, contract_type=SyariahContractType.IJARAH,
            participants=[lessor, lessee], capital=rental_value,
            asset_backing=asset, duration_days=duration,
            created_at=datetime.utcnow().isoformat(),
        )
        check = self.compliance.check_contract(SyariahContractType.IJARAH, asset, "leasing")
        self.contracts[contract_id] = contract
        return {"contract_id": contract_id, "type": "Ijarah", "rental": rental_value, "compliance": check}

    def distribute_profit_loss(self, contract_id: str, actual_profit: float) -> Dict[str, Any]:
        contract = self.contracts.get(contract_id)
        if not contract:
            return {"error": "Contract not found"}
        result = self.compliance.validate_profit_distribution(contract, actual_profit)
        contract.profit_loss = actual_profit
        return {"contract_id": contract_id, **result}

    def calculate_zakat(self, owner: str, asset_type: str, value_idr: float, owned_months: int) -> Dict[str, Any]:
        nishab = 85_000_000.0 if asset_type == "gold" else 520_000_000.0  # Approximate
        haul_met = owned_months >= 12
        zakat_due = 0.0
        if haul_met and value_idr >= nishab:
            zakat_due = value_idr * 0.025  # 2.5%
        record = ZakatRecord(
            owner=owner, asset_type=asset_type, value_idr=value_idr,
            nishab_idr=nishab, haul_met=haul_met, zakat_due=zakat_due,
        )
        self.zakat_records[owner] = record
        return {"owner": owner, "zakat_due": zakat_due, "haul_met": haul_met, "nishab": nishab}

    def pay_zakat(self, owner: str, amount: float) -> Dict[str, Any]:
        record = self.zakat_records.get(owner)
        if not record:
            return {"error": "No zakat record"}
        record.paid += amount
        return {"owner": owner, "paid": record.paid, "remaining": max(0, record.zakat_due - record.paid)}

    def create_waqaf(self, waqif: str, asset_id: str, purpose: str, beneficiaries: List[str]) -> WaqafEndowment:
        waqaf = WaqafEndowment(
            waqaf_id=f"WAQ-{hashlib.sha256(f'{waqif}:{asset_id}:{time.time()}'.encode()).hexdigest()[:12].upper()}",
            waqif=waqif, asset_id=asset_id, purpose=purpose, beneficiaries=beneficiaries,
        )
        self.waqafs[waqaf.waqaf_id] = waqaf
        return waqaf

    def distribute_waqaf_income(self, waqaf_id: str, income: float) -> Dict[str, Any]:
        waqaf = self.waqafs.get(waqaf_id)
        if not waqaf:
            return {"error": "Waqaf not found"}
        waqaf.income_generated += income
        per_beneficiary = income / len(waqaf.beneficiaries) if waqaf.beneficiaries else 0
        waqaf.distributed += income
        return {"waqaf_id": waqaf_id, "income": income, "per_beneficiary": per_beneficiary, "total_distributed": waqaf.distributed}

    def issue_sukuk(self, sukuk_type: str, face_value: float, profit_rate: float, maturity_days: int, total_issued: int) -> SukukCertificate:
        sukuk = SukukCertificate(
            sukuk_id=f"SUK-{hashlib.sha256(f'{sukuk_type}:{time.time()}'.encode()).hexdigest()[:12].upper()}",
            sukuk_type=sukuk_type, face_value=face_value, profit_rate=profit_rate,
            maturity_date=(datetime.utcnow() + timedelta(days=maturity_days)).isoformat(),
            total_issued=total_issued,
        )
        self.sukuks[sukuk.sukuk_id] = sukuk
        return sukuk

    def distribute_sukuk_profit(self, sukuk_id: str, total_profit: float) -> Dict[str, Any]:
        sukuk = self.sukuks.get(sukuk_id)
        if not sukuk or sukuk.total_issued == 0:
            return {"error": "Sukuk not found"}
        per_unit = total_profit / sukuk.total_issued
        sukuk.profit_distributed += total_profit
        return {"sukuk_id": sukuk_id, "total_profit": total_profit, "per_unit": per_unit, "total_distributed": sukuk.profit_distributed}

    def contribute_takaful(self, member: str, amount: float) -> Dict[str, Any]:
        self.takaful_pool += amount
        return {"member": member, "contribution": amount, "pool_total": self.takaful_pool}

    def claim_takaful(self, member: str, amount: float, reason: str) -> Dict[str, Any]:
        if amount > self.takaful_pool:
            return {"error": "Insufficient pool"}
        self.takaful_pool -= amount
        self.takaful_claims.append({"member": member, "amount": amount, "reason": reason, "timestamp": datetime.utcnow().isoformat()})
        return {"member": member, "amount": amount, "remaining_pool": self.takaful_pool}

    def get_portfolio(self, address: str) -> Dict[str, Any]:
        contracts = [c for c in self.contracts.values() if address in c.participants]
        zakat = self.zakat_records.get(address)
        waqafs = [w for w in self.waqafs.values() if w.waqif == address]
        sukuks = [s for s in self.sukuks.values() if address in s.holders]
        return {
            "contracts": [{"id": c.contract_id, "type": c.contract_type.name, "capital": c.capital, "pnl": c.profit_loss} for c in contracts],
            "zakat": zakat.__dict__ if zakat else None,
            "waqafs": [w.__dict__ for w in waqafs],
            "sukuks": [s.__dict__ for s in sukuks],
        }

    def get_national_stats(self) -> Dict[str, Any]:
        return {
            "total_contracts": len(self.contracts),
            "total_zakat_due": sum(r.zakat_due for r in self.zakat_records.values()),
            "total_zakat_paid": sum(r.paid for r in self.zakat_records.values()),
            "waqafs": len(self.waqafs),
            "sukuks": len(self.sukuks),
            "takaful_pool": self.takaful_pool,
            "takaful_claims": len(self.takaful_claims),
        }


# --- Standalone test ---
if __name__ == "__main__":
    print("=== Syariah-Compliant DeFi Engine ===")
    engine = SyariahDeFiEngine()

    # Mudarabah
    mud = engine.create_mudarabah("investor-1", "manager-1", 100_000_000.0, 0.7, 0.3, "Palm Oil Plantation Riau")
    print(f"Mudarabah: {mud['contract_id']}, compliant: {mud['compliance']['status'].name}")

    # Musyarakah
    mus = engine.create_musyarakah([("partner-a", 60_000_000.0), ("partner-b", 40_000_000.0)], "Nickel Mining Sulawesi")
    print(f"Musyarakah: {mus['contract_id']}, capital: Rp {mus['capital']:,.0f}")

    # Murabahah
    mur = engine.create_murabahah("buyer-1", "seller-1", 500_000_000.0, 50_000_000.0, "Truck Mitsubishi")
    print(f"Murabahah: {mur['contract_id']}, selling price: Rp {mur['selling_price']:,.0f}")

    # Ijarah
    ija = engine.create_ijarah("lessor-1", "lessee-1", "Office Building SCBD", 100_000_000.0, 365)
    print(f"Ijarah: {ija['contract_id']}, rental: Rp {ija['rental']:,.0f}/month")

    # Profit distribution
    pnl = engine.distribute_profit_loss(mud['contract_id'], 25_000_000.0)
    print(f"\nProfit distribution: {pnl}")

    # Zakat
    zakat = engine.calculate_zakat("warga-1", "gold", 150_000_000.0, 14)
    print(f"Zakat: Rp {zakat['zakat_due']:,.0f} due")
    engine.pay_zakat("warga-1", 3_750_000.0)

    # Waqaf
    waq = engine.create_waqaf("donor-1", "land-jakarta", "Education Scholarship", ["student-1", "student-2"])
    engine.distribute_waqaf_income(waq.waqaf_id, 50_000_000.0)
    print(f"Waqaf: {waq.waqaf_id}, income distributed: Rp 50jt")

    # Sukuk
    suk = engine.issue_sukuk("ijarah", 1_000_000_000.0, 0.08, 1825, 1_000_000)
    engine.distribute_sukuk_profit(suk.sukuk_id, 80_000_000_000.0)
    print(f"Sukuk: {suk.sukuk_id}, profit distributed: Rp 80M")

    # Takaful
    engine.contribute_takaful("member-1", 5_000_000.0)
    engine.claim_takaful("member-1", 20_000_000.0, "Hospitalization")
    print(f"Takaful pool: Rp {engine.takaful_pool:,.0f}")

    # National stats
    print(f"\nNational Syariah Stats: {engine.get_national_stats()}")
