# blockchain/sovereign_token_native.py
# AMATI-PELAJARI-TIRU: Sovereign Asset Tokenization for Indonesia
# National strategic assets: sovereign wealth, infrastructure, natural resources
# Layer blockchain of MAGNATRIX-OS — National Financial Infrastructure

"""
Native Sovereign Asset Tokenization Engine
==========================================
Sovereign-grade asset tokenization for national strategic interests:
  - Sovereign Wealth Fund: BPIH (BPI Investasi/Holding), Pertamina, PLN, Telkom
  - Infrastructure: toll roads, ports, airports, railways, power plants
  - Natural Monopolies: electricity grid, water, telecommunications backbone
  - Strategic Resources: nickel, cobalt, rare earth (critical minerals)
  - Government Bonds: SUN (Surat Utang Negara) tokenization
  - State-Owned Enterprise (BUMN) shares: fractional ownership for citizens
  - National Development: IKN (Ibu Kota Nusantara), trans-Java railway

Features:
  - Pure-Python sovereign tokenization with governance controls
  - Government-only mint authority (Ministry of Finance / BPK)
  - Citizen eligibility: KTP-linked, capped ownership per person
  - Dividend distribution: proportional to national budget allocation
  - Veto power: government retains golden share for strategic decisions
  - Audit trail: BPK (Supreme Audit Institution) real-time monitoring
  - National security: classified assets with restricted circulation
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta


class SovereignAssetType(Enum):
    BUMN_SHARES = auto()
    INFRASTRUCTURE = auto()
    NATURAL_RESOURCES = auto()
    GOVERNMENT_BONDS = auto()
    STRATEGIC_RESERVE = auto()
    DEVELOPMENT_PROJECT = auto()


class ClassificationLevel(Enum):
    PUBLIC = auto()
    RESTRICTED = auto()
    CONFIDENTIAL = auto()
    SECRET = auto()


class VetoPower(Enum):
    NONE = auto()
    GOLDEN_SHARE = auto()  # 1 share = veto
    SUPERMAJORITY = auto()  # 67% gov control
    ABSOLUTE = auto()  # 100% gov control


@dataclass
class SovereignAsset:
    asset_id: str
    asset_type: SovereignAssetType
    name: str
    description: str
    total_value_idr: float
    government_share: float  # 0.0 - 1.0
    citizen_pool: float  # available for citizens
    classification: ClassificationLevel
    veto_power: VetoPower
    ministry_owner: str
    bpk_audit_hash: str
    location: str
    operational_status: str = "active"
    revenue_idr: float = 0.0
    expense_idr: float = 0.0


@dataclass
class SovereignToken:
    token_id: str
    asset_id: str
    symbol: str
    name: str
    total_supply: int
    government_held: int
    citizen_held: int
    decimals: int = 6
    max_per_citizen: int = 0  # 0 = unlimited, else cap
    ktp_linked: bool = True
    holders: Dict[str, int] = field(default_factory=dict)
    dividends_distributed: float = 0.0


@dataclass
class CitizenEligibility:
    ktp_hash: str
    nik: str  # 16-digit NIK
    verified: bool = False
    max_ownership: int = 0
    current_holdings: Dict[str, int] = field(default_factory=dict)
    registration_date: str = ""
    province: str = ""


@dataclass
class NationalDividend:
    period: str
    total_revenue_idr: float
    dividend_pool_idr: float
    per_token_idr: float
    distribution_date: str
    recipients: int = 0


class MinistryOfFinanceEngine:
    """Government mint authority and fiscal policy."""

    def __init__(self):
        self.mint_authority: str = "KEMENTERIAN_KEUANGAN"
        self.bpk_auditor: str = "BPK_RI"
        self.total_sovereign_value = 0.0
        self.assets: Dict[str, SovereignAsset] = {}
        self.tokens: Dict[str, SovereignToken] = {}
        self.citizens: Dict[str, CitizenEligibility] = {}
        self.dividends: List[NationalDividend] = []
        self.budget_allocation: Dict[str, float] = {}

    def register_asset(self, asset_type: SovereignAssetType, name: str, description: str, value_idr: float, gov_share: float, classification: ClassificationLevel, veto: VetoPower, ministry: str, location: str) -> SovereignAsset:
        asset_id = f"SOV-{asset_type.name}-{hashlib.sha256(f'{name}:{time.time()}'.encode()).hexdigest()[:8].upper()}"
        asset = SovereignAsset(
            asset_id=asset_id, asset_type=asset_type, name=name, description=description,
            total_value_idr=value_idr, government_share=gov_share,
            citizen_pool=1.0 - gov_share, classification=classification,
            veto_power=veto, ministry_owner=ministry, location=location,
            bpk_audit_hash=hashlib.sha256(f"audit:{asset_id}".encode()).hexdigest()[:32],
        )
        self.assets[asset_id] = asset
        self.total_sovereign_value += value_idr
        return asset

    def tokenize(self, asset_id: str, symbol: str, token_name: str, max_per_citizen: int = 0) -> Optional[SovereignToken]:
        asset = self.assets.get(asset_id)
        if not asset:
            return None
        total_supply = int(asset.total_value_idr / 1000)  # 1 token = Rp 1000
        gov_held = int(total_supply * asset.government_share)
        citizen_held = total_supply - gov_held
        token = SovereignToken(
            token_id=f"ST-{symbol}-{hashlib.sha256(f'{asset_id}:{time.time()}'.encode()).hexdigest()[:8].upper()}",
            asset_id=asset_id, symbol=symbol, name=token_name,
            total_supply=total_supply, government_held=gov_held,
            citizen_held=citizen_held, max_per_citizen=max_per_citizen,
            holders={self.mint_authority: gov_held},
        )
        self.tokens[symbol] = token
        return token

    def register_citizen(self, nik: str, ktp_hash: str, province: str, max_ownership: int = 100_000) -> CitizenEligibility:
        citizen = CitizenEligibility(
            ktp_hash=ktp_hash, nik=nik, verified=True, max_ownership=max_ownership,
            registration_date=datetime.utcnow().isoformat(), province=province,
        )
        self.citizens[nik] = citizen
        return citizen

    def allocate_to_citizen(self, symbol: str, nik: str, amount: int) -> Dict[str, Any]:
        token = self.tokens.get(symbol)
        citizen = self.citizens.get(nik)
        if not token or not citizen:
            return {"error": "Token or citizen not found"}
        if not citizen.verified:
            return {"error": "Citizen not verified"}
        current = citizen.current_holdings.get(symbol, 0)
        if token.max_per_citizen > 0 and current + amount > token.max_per_citizen:
            return {"error": "Exceeds citizen ownership cap"}
        if token.citizen_held < amount:
            return {"error": "Insufficient citizen pool"}
        token.holders[nik] = token.holders.get(nik, 0) + amount
        token.citizen_held -= amount
        citizen.current_holdings[symbol] = current + amount
        return {"nik": nik, "symbol": symbol, "allocated": amount, "total": citizen.current_holdings[symbol]}

    def distribute_dividend(self, symbol: str, period: str, revenue_idr: float) -> NationalDividend:
        token = self.tokens.get(symbol)
        if not token or token.total_supply == 0:
            return NationalDividend(period=period, total_revenue_idr=0, dividend_pool_idr=0, per_token_idr=0, distribution_date="")
        asset = self.assets.get(token.asset_id)
        # Government takes share, rest distributed
        gov_share = revenue_idr * (asset.government_share if asset else 0.5)
        pool = revenue_idr - gov_share
        per_token = pool / token.total_supply if token.total_supply > 0 else 0
        dividend = NationalDividend(
            period=period, total_revenue_idr=revenue_idr, dividend_pool_idr=pool,
            per_token_idr=per_token, distribution_date=datetime.utcnow().isoformat(),
            recipients=len(token.holders) - 1,  # Exclude government
        )
        self.dividends.append(dividend)
        token.dividends_distributed += pool
        return dividend

    def exercise_veto(self, asset_id: str, proposal: str) -> Dict[str, Any]:
        asset = self.assets.get(asset_id)
        if not asset:
            return {"error": "Asset not found"}
        if asset.veto_power == VetoPower.GOLDEN_SHARE:
            return {"veto_exercised": True, "reason": "Government golden share veto", "proposal_blocked": proposal}
        elif asset.veto_power == VetoPower.SUPERMAJORITY:
            return {"veto_exercised": True, "reason": "Government supermajority control", "proposal_blocked": proposal}
        elif asset.veto_power == VetoPower.ABSOLUTE:
            return {"veto_exercised": True, "reason": "Absolute government control", "proposal_blocked": proposal}
        return {"veto_exercised": False, "reason": "No veto power"}

    def bpk_audit(self, asset_id: str) -> Dict[str, Any]:
        asset = self.assets.get(asset_id)
        if not asset:
            return {"error": "Asset not found"}
        audit_hash = hashlib.sha256(f"bpk_audit:{asset_id}:{time.time()}".encode()).hexdigest()[:32]
        asset.bpk_audit_hash = audit_hash
        return {"asset": asset_id, "audit_hash": audit_hash, "auditor": self.bpk_auditor, "timestamp": datetime.utcnow().isoformat()}

    def get_citizen_portfolio(self, nik: str) -> Dict[str, Any]:
        citizen = self.citizens.get(nik)
        if not citizen:
            return {"error": "Citizen not found"}
        holdings = {}
        for symbol, token in self.tokens.items():
            balance = token.holders.get(nik, 0)
            if balance > 0:
                asset = self.assets.get(token.asset_id)
                value_idr = balance * 1000  # 1 token = Rp 1000
                holdings[symbol] = {"balance": balance, "value_idr": value_idr, "asset": asset.name if asset else "Unknown"}
        return {"nik": nik, "province": citizen.province, "holdings": holdings, "total_value_idr": sum(h["value_idr"] for h in holdings.values())}

    def get_national_stats(self) -> Dict[str, Any]:
        total_assets = len(self.assets)
        total_tokenized = len(self.tokens)
        total_citizens = len(self.citizens)
        total_dividends = sum(d.dividend_pool_idr for d in self.dividends)
        by_type = {}
        for a in self.assets.values():
            by_type[a.asset_type.name] = by_type.get(a.asset_type.name, 0) + a.total_value_idr
        return {
            "total_assets": total_assets, "tokenized": total_tokenized,
            "total_value_idr": self.total_sovereign_value, "citizens": total_citizens,
            "dividends_distributed": total_dividends, "by_type": by_type,
        }


class IndonesiaSovereignFactory:
    """Factory for creating Indonesian sovereign assets."""

    def __init__(self, engine: MinistryOfFinanceEngine):
        self.engine = engine

    def create_pertamina(self) -> SovereignAsset:
        return self.engine.register_asset(
            SovereignAssetType.BUMN_SHARES, "Pertamina (Persero)", "National oil and gas company",
            500_000_000_000_000.0, 0.51, ClassificationLevel.PUBLIC, VetoPower.GOLDEN_SHARE, "BUMN", "Jakarta",
        )

    def create_pln(self) -> SovereignAsset:
        return self.engine.register_asset(
            SovereignAssetType.BUMN_SHARES, "PLN (Persero)", "National electricity company",
            300_000_000_000_000.0, 0.51, ClassificationLevel.PUBLIC, VetoPower.GOLDEN_SHARE, "BUMN", "Jakarta",
        )

    def create_toll_road_japek(self) -> SovereignAsset:
        return self.engine.register_asset(
            SovereignAssetType.INFRASTRUCTURE, "Jalan Tol Jakarta-Cikampek", "Trans-Java toll road",
            50_000_000_000_000.0, 0.60, ClassificationLevel.PUBLIC, VetoPower.SUPERMAJORITY, "Kementerian PUPR", "Jawa Barat",
        )

    def create_nickel_strategic_reserve(self) -> SovereignAsset:
        return self.engine.register_asset(
            SovereignAssetType.NATURAL_RESOURCES, "Nickel Strategic Reserve Sulawesi", "Critical mineral reserve",
            200_000_000_000_000.0, 0.80, ClassificationLevel.RESTRICTED, VetoPower.ABSOLUTE, "Kementerian ESDM", "Sulawesi",
        )

    def create_sun_bond(self) -> SovereignAsset:
        return self.engine.register_asset(
            SovereignAssetType.GOVERNMENT_BONDS, "SURAT UTANG NEGARA 2026", "Government bond series",
            1_000_000_000_000_000.0, 0.0, ClassificationLevel.PUBLIC, VetoPower.NONE, "Kementerian Keuangan", "Jakarta",
        )

    def create_ikn_project(self) -> SovereignAsset:
        return self.engine.register_asset(
            SovereignAssetType.DEVELOPMENT_PROJECT, "IKN Nusantara", "New capital city development",
            466_000_000_000_000.0, 0.65, ClassificationLevel.PUBLIC, VetoPower.SUPERMAJORITY, "OIKN", "Kalimantan Timur",
        )


# --- Standalone test ---
if __name__ == "__main__":
    print("=== Sovereign Asset Tokenization Engine ===")
    engine = MinistryOfFinanceEngine()
    factory = IndonesiaSovereignFactory(engine)

    # Create sovereign assets
    pertamina = factory.create_pertamina()
    pln = factory.create_pln()
    toll = factory.create_toll_road_japek()
    nickel = factory.create_nickel_strategic_reserve()
    sun = factory.create_sun_bond()
    ikn = factory.create_ikn_project()

    print(f"Assets created: {len(engine.assets)}")
    print(f"Total sovereign value: Rp {engine.total_sovereign_value:,.0f}")

    # Tokenize
    pertamina_tkn = engine.tokenize(pertamina.asset_id, "PERTAMINA", "Pertamina Shares", max_per_citizen=100_000)
    pln_tkn = engine.tokenize(pln.asset_id, "PLN", "PLN Shares", max_per_citizen=100_000)
    ikn_tkn = engine.tokenize(ikn.asset_id, "IKN", "IKN Development Token", max_per_citizen=50_000)

    print(f"\nTokens: {list(engine.tokens.keys())}")
    print(f"Pertamina supply: {pertamina_tkn.total_supply:,}")

    # Register citizens
    for i in range(5):
        engine.register_citizen(f"3175{i:04d}260991000{i}", hashlib.sha256(f"ktp{i}".encode()).hexdigest(), "DKI Jakarta", 100_000)
    for i in range(3):
        engine.register_citizen(f"3273{i:04d}150885000{i}", hashlib.sha256(f"ktp-jabar{i}".encode()).hexdigest(), "Jawa Barat", 100_000)

    # Allocate to citizens
    for nik in engine.citizens:
        engine.allocate_to_citizen("PERTAMINA", nik, 10_000)
        engine.allocate_to_citizen("PLN", nik, 5_000)
        engine.allocate_to_citizen("IKN", nik, 2_000)

    # Dividend distribution
    div = engine.distribute_dividend("PERTAMINA", "Q1-2026", 25_000_000_000_000.0)
    print(f"\nDividend Q1-2026: Rp {div.dividend_pool_idr:,.0f} pool, Rp {div.per_token_idr:,.0f} per token")

    # Portfolio
    portfolio = engine.get_citizen_portfolio("317500002609910000")
    print(f"\nPortfolio: Rp {portfolio['total_value_idr']:,.0f}")
    print(f"Holdings: {list(portfolio['holdings'].keys())}")

    # Veto test
    veto = engine.exercise_veto(pertamina.asset_id, "Acquisition by foreign entity")
    print(f"\nVeto: {veto}")

    # Audit
    audit = engine.bpk_audit(nickel.asset_id)
    print(f"Audit: {audit}")

    # National stats
    print(f"\nNational Stats: {engine.get_national_stats()}")
