# blockchain/qrbi_native.py
# AMATI-PELAJARI-TIRU: QRIS/BI-FAST Bridge Layer for Indonesia
# Unified payment interface: QRIS (merchant scan), BI-FAST (bank transfer), + e-Rupiah
# Layer blockchain of MAGNATRIX-OS — National Financial Infrastructure

"""
Native QRIS/BI-FAST Bridge Engine
==================================
Unified national payment infrastructure for Indonesia:
  - QRIS: Quick Response Code Indonesian Standard — merchant-presented, customer-presented, static/dynamic
  - BI-FAST: Bank Indonesia Fast Payment — real-time account-to-account transfer
  - e-Rupiah Bridge: CBDC integration with existing national payment rails
  - Merchant Network: MPM (Micro Payment Merchant), UMKM integration
  - Switching: automatic routing between QRIS, BI-FAST, e-Rupiah
  - Settlement: T+0 real-time settlement for all payment types
  - Reconciliation: automated end-of-day reconciliation
  - Fee Structure: BI-regulated interchange fee, merchant discount rate

Features:
  - Pure-Python payment switching simulation
  - QR code generation and validation (simulated hash)
  - Dynamic QR with amount, merchant ID, expiry
  - BI-FAST message format (ISO 20022 compatible)
  - Merchant onboarding with MPM category
  - Transaction routing with fallback
  - Real-time settlement tracking
  - Daily reconciliation report
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime, timedelta


class QRType(Enum):
    STATIC = auto()    # Fixed amount, merchant-presented
    DYNAMIC = auto()   # Variable amount, merchant or customer presented
    CUSTOMER_PRESENTED = auto()  # Customer shows QR to merchant
    MERCHANT_PRESENTED = auto()  # Merchant shows QR to customer


class PaymentChannel(Enum):
    QRIS = auto()
    BI_FAST = auto()
    E_RUPIAH = auto()
    RTGS = auto()
    SKN = auto()


class TransactionStatus(Enum):
    INITIATED = auto()
    AUTHENTICATED = auto()
    SWITCHED = auto()
    SETTLED = auto()
    FAILED = auto()
    REVERSED = auto()
    REFUNDED = auto()


@dataclass
class QRMerchant:
    merchant_id: str
    name: str
    category: str  # MPM, retail, F&B, transport, etc.
    mpm_category: str  # UMKM, enterprise, government
    bank_account: str
    bank_code: str
    qris_id: str
    fee_rate: float = 0.007  # 0.7% MDR default
    daily_volume: float = 0.0
    settlement_account: str = ""
    is_active: bool = True


@dataclass
class QRCode:
    qr_id: str
    merchant_id: str
    qr_type: QRType
    amount: float
    currency: str = "IDR"
    expiry: str = ""
    payload: str = ""  # Simulated QR payload
    transaction_ref: str = ""
    scanned_count: int = 0


@dataclass
class BIFASTMessage:
    msg_id: str
    msg_type: str  # pain.001, pain.002, camt.053, etc.
    sender_bank: str
    receiver_bank: str
    sender_account: str
    receiver_account: str
    amount: float
    currency: str
    reference: str
    status: str = "pending"
    timestamp: str = ""
    settlement_time: Optional[str] = None


@dataclass
class UnifiedTransaction:
    tx_id: str
    channel: PaymentChannel
    amount: float
    currency: str
    sender: str
    receiver: str
    merchant: Optional[str] = None
    qr_code: Optional[str] = None
    status: TransactionStatus = TransactionStatus.INITIATED
    bi_fast_msg: Optional[BIFASTMessage] = None
    fees: Dict[str, float] = field(default_factory=dict)
    settlement_time: Optional[str] = None
    reversal_reason: str = ""


class QRISNetwork:
    """QRIS merchant network and QR generation."""

    def __init__(self):
        self.merchants: Dict[str, QRMerchant] = {}
        self.qr_codes: Dict[str, QRCode] = {}
        self.qr_scans: Dict[str, List[Dict[str, Any]]] = {}
        self.mpm_registry: Dict[str, List[str]] = {}  # category -> merchant_ids

    def register_merchant(self, merchant_id: str, name: str, category: str, mpm: str, bank_account: str, bank_code: str, fee_rate: float = 0.007) -> QRMerchant:
        merchant = QRMerchant(
            merchant_id=merchant_id, name=name, category=category, mpm_category=mpm,
            bank_account=bank_account, bank_code=bank_code, qris_id=f"QRIS-{merchant_id}",
            fee_rate=fee_rate, settlement_account=bank_account,
        )
        self.merchants[merchant_id] = merchant
        self.mpm_registry.setdefault(mpm, []).append(merchant_id)
        return merchant

    def generate_qr(self, merchant_id: str, amount: float, qr_type: QRType = QRType.DYNAMIC, expiry_minutes: int = 5) -> QRCode:
        merchant = self.merchants.get(merchant_id)
        if not merchant:
            raise ValueError("Merchant not found")
        qr_id = f"QR-{hashlib.sha256(f'{merchant_id}:{amount}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        payload = hashlib.sha256(f"QRIS|{merchant.qris_id}|{amount}|{qr_id}".encode()).hexdigest()[:64]
        qr = QRCode(
            qr_id=qr_id, merchant_id=merchant_id, qr_type=qr_type, amount=amount,
            expiry=(datetime.utcnow() + timedelta(minutes=expiry_minutes)).isoformat(),
            payload=payload,
        )
        self.qr_codes[qr_id] = qr
        return qr

    def scan_qr(self, qr_id: str, customer_id: str) -> Dict[str, Any]:
        qr = self.qr_codes.get(qr_id)
        if not qr:
            return {"error": "QR not found"}
        if datetime.utcnow().isoformat() > qr.expiry:
            return {"error": "QR expired"}
        qr.scanned_count += 1
        self.qr_scans.setdefault(qr_id, []).append({"customer": customer_id, "time": datetime.utcnow().isoformat()})
        merchant = self.merchants.get(qr.merchant_id)
        return {
            "qr_id": qr_id, "merchant": merchant.name if merchant else "Unknown",
            "amount": qr.amount, "valid": True,
        }

    def get_merchant_stats(self, merchant_id: str) -> Dict[str, Any]:
        merchant = self.merchants.get(merchant_id)
        if not merchant:
            return {"error": "Merchant not found"}
        qr_count = sum(1 for q in self.qr_codes.values() if q.merchant_id == merchant_id)
        scans = sum(q.scanned_count for q in self.qr_codes.values() if q.merchant_id == merchant_id)
        return {"merchant": merchant_id, "qr_generated": qr_count, "scans": scans, "fee_rate": merchant.fee_rate}


class BIFASTNetwork:
    """BI-FAST real-time payment network."""

    def __init__(self):
        self.banks: Dict[str, Dict[str, Any]] = {}
        self.messages: Dict[str, BIFASTMessage] = {}
        self.participants: Set[str] = set()

    def register_bank(self, bank_code: str, name: str, bi_fast_participant: bool = True) -> None:
        self.banks[bank_code] = {"name": name, "participant": bi_fast_participant, "accounts": {}}
        if bi_fast_participant:
            self.participants.add(bank_code)

    def create_message(self, msg_type: str, sender_bank: str, receiver_bank: str, sender_account: str, receiver_account: str, amount: float, currency: str = "IDR", reference: str = "") -> BIFASTMessage:
        if sender_bank not in self.participants or receiver_bank not in self.participants:
            raise ValueError("Bank not BI-FAST participant")
        msg_id = f"BIF-{hashlib.sha256(f'{sender_bank}:{receiver_bank}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        msg = BIFASTMessage(
            msg_id=msg_id, msg_type=msg_type, sender_bank=sender_bank, receiver_bank=receiver_bank,
            sender_account=sender_account, receiver_account=receiver_account,
            amount=amount, currency=currency, reference=reference or msg_id,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.messages[msg_id] = msg
        return msg

    def execute_transfer(self, msg_id: str) -> Dict[str, Any]:
        msg = self.messages.get(msg_id)
        if not msg:
            return {"error": "Message not found"}
        msg.status = "settled"
        msg.settlement_time = datetime.utcnow().isoformat()
        return {"msg_id": msg_id, "status": "settled", "settled_at": msg.settlement_time}

    def get_bank_stats(self, bank_code: str) -> Dict[str, Any]:
        bank = self.banks.get(bank_code)
        if not bank:
            return {"error": "Bank not found"}
        msgs = [m for m in self.messages.values() if m.sender_bank == bank_code or m.receiver_bank == bank_code]
        settled = [m for m in msgs if m.status == "settled"]
        return {"bank": bank_code, "total_messages": len(msgs), "settled": len(settled), "participant": bank_code in self.participants}


class PaymentSwitch:
    """Routes transactions between QRIS, BI-FAST, and e-Rupiah."""

    def __init__(self, qris: QRISNetwork, bifast: BIFASTNetwork):
        self.qris = qris
        self.bifast = bifast
        self.transactions: Dict[str, UnifiedTransaction] = {}
        self.fee_schedule: Dict[str, float] = {
            "interchange": 0.002, "switching": 0.001, "settlement": 0.0005, "mdr": 0.007,
        }
        self.daily_settlements: Dict[str, List[str]] = {}  # merchant_id -> tx_ids

    def pay_qris(self, qr_id: str, customer_id: str, customer_bank: str, customer_account: str) -> Dict[str, Any]:
        scan = self.qris.scan_qr(qr_id, customer_id)
        if "error" in scan:
            return scan
        qr = self.qris.qr_codes.get(qr_id)
        merchant = self.qris.merchants.get(qr.merchant_id)
        # Route via BI-FAST
        msg = self.bifast.create_message(
            "pain.001", customer_bank, merchant.bank_code,
            customer_account, merchant.bank_account, qr.amount, "IDR", qr_id,
        )
        result = self.bifast.execute_transfer(msg.msg_id)
        # Record unified transaction
        tx_id = f"U-{hashlib.sha256(f'{qr_id}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        fees = {
            "interchange": qr.amount * self.fee_schedule["interchange"],
            "switching": qr.amount * self.fee_schedule["switching"],
            "mdr": qr.amount * merchant.fee_rate,
            "settlement": qr.amount * self.fee_schedule["settlement"],
        }
        tx = UnifiedTransaction(
            tx_id=tx_id, channel=PaymentChannel.QRIS, amount=qr.amount, currency="IDR",
            sender=customer_id, receiver=merchant.merchant_id, merchant=merchant.merchant_id,
            qr_code=qr_id, status=TransactionStatus.SETTLED,
            bi_fast_msg=msg, fees=fees, settlement_time=result.get("settled_at"),
        )
        self.transactions[tx_id] = tx
        self.daily_settlements.setdefault(merchant.merchant_id, []).append(tx_id)
        merchant.daily_volume += qr.amount
        return {"tx_id": tx_id, "status": "settled", "amount": qr.amount, "fees": fees, "net_to_merchant": qr.amount - sum(fees.values())}

    def pay_bifast(self, sender_bank: str, sender_account: str, receiver_bank: str, receiver_account: str, amount: float, reference: str = "") -> Dict[str, Any]:
        msg = self.bifast.create_message("pain.001", sender_bank, receiver_bank, sender_account, receiver_account, amount, "IDR", reference)
        result = self.bifast.execute_transfer(msg.msg_id)
        tx_id = f"U-{hashlib.sha256(f'{msg.msg_id}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        fees = {"switching": amount * self.fee_schedule["switching"], "settlement": amount * self.fee_schedule["settlement"]}
        tx = UnifiedTransaction(
            tx_id=tx_id, channel=PaymentChannel.BI_FAST, amount=amount, currency="IDR",
            sender=sender_account, receiver=receiver_account, status=TransactionStatus.SETTLED,
            bi_fast_msg=msg, fees=fees, settlement_time=result.get("settled_at"),
        )
        self.transactions[tx_id] = tx
        return {"tx_id": tx_id, "status": "settled", "amount": amount, "fees": fees}

    def pay_erupiah(self, from_wallet: str, to_wallet: str, amount: float, qr_id: Optional[str] = None) -> Dict[str, Any]:
        tx_id = f"U-{hashlib.sha256(f'{from_wallet}:{to_wallet}:{time.time()}'.encode()).hexdigest()[:12].upper()}"
        tx = UnifiedTransaction(
            tx_id=tx_id, channel=PaymentChannel.E_RUPIAH, amount=amount, currency="IDR",
            sender=from_wallet, receiver=to_wallet, qr_code=qr_id, status=TransactionStatus.SETTLED,
            settlement_time=datetime.utcnow().isoformat(), fees={},
        )
        self.transactions[tx_id] = tx
        return {"tx_id": tx_id, "status": "settled", "amount": amount, "channel": "e-Rupiah"}

    def reconcile_daily(self, merchant_id: str) -> Dict[str, Any]:
        tx_ids = self.daily_settlements.get(merchant_id, [])
        txs = [self.transactions[t] for t in tx_ids]
        total = sum(t.amount for t in txs)
        total_fees = sum(sum(t.fees.values()) for t in txs)
        return {
            "merchant": merchant_id, "transactions": len(txs), "gross": total,
            "fees": total_fees, "net": total - total_fees, "settled_at": datetime.utcnow().isoformat(),
        }

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.transactions)
        by_channel = {}
        for t in self.transactions.values():
            by_channel[t.channel.name] = by_channel.get(t.channel.name, 0) + t.amount
        return {"total_transactions": total, "by_channel": by_channel, "merchants": len(self.qris.merchants), "banks": len(self.bifast.participants)}


class QRBIEngine:
    """End-to-end QRIS/BI-FAST/e-Rupiah orchestrator."""

    def __init__(self):
        self.qris = QRISNetwork()
        self.bifast = BIFASTNetwork()
        self.switch = PaymentSwitch(self.qris, self.bifast)
        self._init_defaults()

    def _init_defaults(self) -> None:
        # Register major Indonesian banks
        banks = [
            ("BMRI", "Bank Mandiri", True), ("BBRI", "Bank Rakyat Indonesia", True),
            ("BBCA", "Bank Central Asia", True), ("BNI", "Bank Negara Indonesia", True),
            ("BTN", "Bank Tabungan Negara", True), ("CIMB", "Bank CIMB Niaga", True),
        ]
        for code, name, participant in banks:
            self.bifast.register_bank(code, name, participant)
        # Register sample merchants
        merchants = [
            ("WARUNG-001", "Warung Pak Budi", "food", "UMKM", "BMRI", "1234567890"),
            ("TOKO-001", "Toko Sejahtera", "retail", "UMKM", "BBRI", "2345678901"),
            ("MALL-001", "Mall Indonesia", "retail", "enterprise", "BBCA", "3456789012"),
        ]
        for mid, name, cat, mpm, bank, acc in merchants:
            self.qris.register_merchant(mid, name, cat, mpm, acc, bank)

    def merchant_qr_payment(self, merchant_id: str, amount: float, customer_bank: str, customer_account: str, customer_id: str) -> Dict[str, Any]:
        qr = self.qris.generate_qr(merchant_id, amount)
        return self.switch.pay_qris(qr.qr_id, customer_id, customer_bank, customer_account)

    def bank_transfer(self, sender_bank: str, sender_account: str, receiver_bank: str, receiver_account: str, amount: float) -> Dict[str, Any]:
        return self.switch.pay_bifast(sender_bank, sender_account, receiver_bank, receiver_account, amount)

    def get_merchant_reconciliation(self, merchant_id: str) -> Dict[str, Any]:
        return self.switch.reconcile_daily(merchant_id)

    def get_stats(self) -> Dict[str, Any]:
        return self.switch.get_stats()


# --- Standalone test ---
if __name__ == "__main__":
    print("=== QRIS/BI-FAST Bridge Engine ===")
    engine = QRBIEngine()

    # Merchant QR payment
    result = engine.merchant_qr_payment("WARUNG-001", 50_000.0, "BBCA", "9876543210", "customer-1")
    print(f"QR Payment: {result}")

    # Bank transfer
    result2 = engine.bank_transfer("BBCA", "9876543210", "BMRI", "1234567890", 1_000_000.0)
    print(f"BI-FAST Transfer: {result2}")

    # Reconciliation
    rec = engine.get_merchant_reconciliation("WARUNG-001")
    print(f"Reconciliation: {rec}")

    # Stats
    print(f"Stats: {engine.get_stats()}")
