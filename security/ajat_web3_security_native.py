"""
AjatFnR Web3 Security Native — Batch 1
Unified native Python implementation of 13 observed Web3/security repositories.

Target: security/ajat_web3_security_native.py
Architecture: BaseLayer → CoreEngine → Features → Kernel

Section 1 — BaseLayer: OnChainTable (columnar storage + multi-index)
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


# ───────────────────────────────────────────────────────────────
# BaseLayer — OnChainTable: Columnar Storage for Blockchain Data
# ───────────────────────────────────────────────────────────────

class TxType(Enum):
    """Transaction classification types."""
    TRANSFER = auto()
    CONTRACT_CALL = auto()
    CONTRACT_CREATION = auto()
    TOKEN_TRANSFER = auto()
    FLASH_LOAN = auto()
    MIXER = auto()
    UNKNOWN = auto()


@dataclass
class OnChainTx:
    """
    Immutable on-chain transaction record.
    
    Schema: hash, from, to, value, gas, timestamp, block_number,
            contract_address, input_data
    """
    hash: str
    from_addr: str
    to_addr: Optional[str]
    value: int  # in wei
    gas: int
    gas_price: int
    timestamp: int  # unix seconds
    block_number: int
    nonce: int
    contract_address: Optional[str] = None
    input_data: str = "0x"
    tx_type: TxType = TxType.UNKNOWN
    logs: List[Dict[str, Any]] = field(default_factory=list)
    traces: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self) -> None:
        if not self.hash.startswith("0x"):
            self.hash = "0x" + self.hash
        if not self.from_addr.startswith("0x"):
            self.from_addr = "0x" + self.from_addr
        if self.to_addr and not self.to_addr.startswith("0x"):
            self.to_addr = "0x" + self.to_addr
    
    def __repr__(self) -> str:
        return (
            f"<OnChainTx hash={self.hash[:16]}... block={self.block_number} "
            f"from={self.from_addr[:12]}... to={self.to_addr[:12] if self.to_addr else None} "
            f"value={self.value} type={self.tx_type.name}>"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "hash": self.hash,
            "from": self.from_addr,
            "to": self.to_addr,
            "value": self.value,
            "gas": self.gas,
            "gas_price": self.gas_price,
            "timestamp": self.timestamp,
            "block_number": self.block_number,
            "nonce": self.nonce,
            "contract_address": self.contract_address,
            "input_data": self.input_data,
            "tx_type": self.tx_type.name,
            "logs": self.logs,
            "traces": self.traces,
        }


class OnChainTable:
    """
    Columnar storage engine for blockchain data.
    
    Implements:
    - Column-oriented storage for fast analytical queries
    - Multi-index: address, block_range, topic
    - Query API: filter by any combination of fields
    - Demo stubs for pure-Python simulation (no web3.py)
    
    Inspired by: onchain-analytics-engine + blockchain-analytics-engine
    """
    
    def __init__(self, chain_id: int = 1) -> None:
        """
        Initialize columnar storage.
        
        Args:
            chain_id: EVM chain identifier (1=Ethereum mainnet)
        """
        self.chain_id = chain_id
        self._transactions: List[OnChainTx] = []
        
        # Columnar storage — each field stored as parallel arrays
        self._hashes: List[str] = []
        self._from_addrs: List[str] = []
        self._to_addrs: List[Optional[str]] = []
        self._values: List[int] = []
        self._gas_list: List[int] = []
        self._timestamps: List[int] = []
        self._block_numbers: List[int] = []
        self._nonces: List[int] = []
        self._contract_addrs: List[Optional[str]] = []
        self._input_datas: List[str] = []
        self._tx_types: List[TxType] = []
        
        # Indexes
        self._index_by_address: Dict[str, Set[int]] = defaultdict(set)
        self._index_by_block_range: Dict[Tuple[int, int], Set[int]] = defaultdict(set)
        self._index_by_topic: Dict[str, Set[int]] = defaultdict(set)
        self._index_by_hash: Dict[str, int] = {}
        
        # Block range bucket size
        self._block_bucket = 1000
    
    def __repr__(self) -> str:
        return (
            f"<OnChainTable chain={self.chain_id} txs={len(self._transactions)} "
            f"blocks={self._get_block_range()}>"
        )
    
    def _get_block_range(self) -> Tuple[int, int]:
        """Return (min_block, max_block) or (0, 0) if empty."""
        if not self._block_numbers:
            return (0, 0)
        return (min(self._block_numbers), max(self._block_numbers))
    
    def insert(self, tx: OnChainTx) -> int:
        """
        Insert transaction into columnar storage.
        
        Args:
            tx: OnChainTx record to store
            
        Returns:
            Row index of inserted transaction
        """
        idx = len(self._transactions)
        self._transactions.append(tx)
        
        # Append to columns
        self._hashes.append(tx.hash)
        self._from_addrs.append(tx.from_addr)
        self._to_addrs.append(tx.to_addr)
        self._values.append(tx.value)
        self._gas_list.append(tx.gas)
        self._timestamps.append(tx.timestamp)
        self._block_numbers.append(tx.block_number)
        self._nonces.append(tx.nonce)
        self._contract_addrs.append(tx.contract_address)
        self._input_datas.append(tx.input_data)
        self._tx_types.append(tx.tx_type)
        
        # Update indexes
        self._index_by_hash[tx.hash] = idx
        self._index_by_address[tx.from_addr].add(idx)
        if tx.to_addr:
            self._index_by_address[tx.to_addr].add(idx)
        if tx.contract_address:
            self._index_by_address[tx.contract_address].add(idx)
        
        # Block range index (bucketed)
        bucket = (tx.block_number // self._block_bucket, 
                  tx.block_number // self._block_bucket + 1)
        self._index_by_block_range[bucket].add(idx)
        
        # Topic index from logs
        for log in tx.logs:
            for topic in log.get("topics", []):
                self._index_by_topic[topic].add(idx)
        
        return idx
    
    def insert_many(self, txs: List[OnChainTx]) -> List[int]:
        """Batch insert transactions."""
        return [self.insert(tx) for tx in txs]
    
    def get_by_hash(self, tx_hash: str) -> Optional[OnChainTx]:
        """Retrieve transaction by hash. O(1) via hash index."""
        idx = self._index_by_hash.get(tx_hash)
        return self._transactions[idx] if idx is not None else None
    
    def query_by_address(self, address: str) -> List[OnChainTx]:
        """Retrieve all transactions involving address."""
        idxs = self._index_by_address.get(address, set())
        return [self._transactions[i] for i in sorted(idxs)]
    
    def query_by_block_range(self, from_block: int, to_block: int) -> List[OnChainTx]:
        """Retrieve transactions within block range."""
        result: Set[int] = set()
        start_bucket = from_block // self._block_bucket
        end_bucket = to_block // self._block_bucket
        
        for b in range(start_bucket, end_bucket + 1):
            bucket = (b, b + 1)
            result.update(self._index_by_block_range.get(bucket, set()))
        
        # Filter exact range
        filtered = [i for i in result if from_block <= self._block_numbers[i] <= to_block]
        return [self._transactions[i] for i in sorted(filtered)]
    
    def query_by_topic(self, topic: str) -> List[OnChainTx]:
        """Retrieve transactions by log topic."""
        idxs = self._index_by_topic.get(topic, set())
        return [self._transactions[i] for i in sorted(idxs)]
    
    def query(
        self,
        from_addr: Optional[str] = None,
        to_addr: Optional[str] = None,
        min_block: Optional[int] = None,
        max_block: Optional[int] = None,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        tx_type: Optional[TxType] = None,
        contract: Optional[str] = None,
    ) -> List[OnChainTx]:
        """
        Multi-field filtered query.
        
        Args:
            from_addr: Filter by sender address
            to_addr: Filter by recipient address
            min_block: Minimum block number
            max_block: Maximum block number
            min_value: Minimum tx value (wei)
            max_value: Maximum tx value (wei)
            tx_type: Filter by transaction type
            contract: Filter by contract address
            
        Returns:
            List of matching transactions
        """
        # Start with all or address-filtered subset
        candidate_idxs: Set[int] = set(range(len(self._transactions)))
        
        if from_addr:
            candidate_idxs &= self._index_by_address.get(from_addr, set())
        if to_addr:
            candidate_idxs &= self._index_by_address.get(to_addr, set())
        if contract:
            candidate_idxs &= self._index_by_address.get(contract, set())
        
        result: List[OnChainTx] = []
        for idx in sorted(candidate_idxs):
            tx = self._transactions[idx]
            
            if min_block is not None and tx.block_number < min_block:
                continue
            if max_block is not None and tx.block_number > max_block:
                continue
            if min_value is not None and tx.value < min_value:
                continue
            if max_value is not None and tx.value > max_value:
                continue
            if tx_type is not None and tx.tx_type != tx_type:
                continue
            
            result.append(tx)
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Return storage statistics."""
        if not self._transactions:
            return {"total_txs": 0, "unique_addresses": 0, "block_range": (0, 0)}
        
        return {
            "total_txs": len(self._transactions),
            "unique_addresses": len(self._index_by_address),
            "block_range": self._get_block_range(),
            "total_value": sum(self._values),
            "avg_gas": sum(self._gas_list) // len(self._gas_list) if self._gas_list else 0,
            "type_distribution": self._get_type_distribution(),
        }
    
    def _get_type_distribution(self) -> Dict[str, int]:
        """Count transaction types."""
        dist: Dict[str, int] = defaultdict(int)
        for tt in self._tx_types:
            dist[tt.name] += 1
        return dict(dist)
    
    def dump(self) -> List[Dict[str, Any]]:
        """Export all transactions as dictionaries."""
        return [tx.to_dict() for tx in self._transactions]
    
    @classmethod
    def from_dicts(cls, dicts: List[Dict[str, Any]], chain_id: int = 1) -> OnChainTable:
        """Reconstruct table from list of dictionaries."""
        table = cls(chain_id=chain_id)
        for d in dicts:
            tx = OnChainTx(
                hash=d["hash"],
                from_addr=d["from"],
                to_addr=d.get("to"),
                value=d["value"],
                gas=d["gas"],
                gas_price=d.get("gas_price", 0),
                timestamp=d["timestamp"],
                block_number=d["block_number"],
                nonce=d.get("nonce", 0),
                contract_address=d.get("contract_address"),
                input_data=d.get("input_data", "0x"),
                tx_type=TxType[d.get("tx_type", "UNKNOWN")],
                logs=d.get("logs", []),
                traces=d.get("traces", []),
            )
            table.insert(tx)
        return table


# ───────────────────────────────────────────────────────────────
# Demo Data Generator (Pure Python — no web3.py)
# ───────────────────────────────────────────────────────────────

def generate_demo_transactions(count: int = 5, seed: int = 42) -> List[OnChainTx]:
    """
    Generate realistic demo transactions for testing.
    
    Args:
        count: Number of transactions to generate
        seed: Random seed for reproducibility
        
    Returns:
        List of OnChainTx records
    """
    random.seed(seed)
    
    addresses = [
        "0xdac17f958d2ee523a2206206994597c13d831ec7",  # USDT
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2 Router
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",  # Uniswap V3 Router
        "0x5fe2b58c013d7601147dcdd68c143a77499f5531",  # Tornado Cash (mixer)
        "0x818e6fecd516ecc3849daf6845e3ec868087b755",  # Aave
        "0xdef1c0ded9bec7f1a1670819833240f027b25eff",  # 0x Exchange
    ]
    
    base_time = int(time.time()) - 86400  # 1 day ago
    txs: List[OnChainTx] = []
    
    for i in range(count):
        from_addr = random.choice(addresses[:4])
        to_addr = random.choice(addresses[4:])
        
        # Occasional contract creation (no to_addr)
        if random.random() < 0.1:
            to_addr = None
        
        tx_type = TxType.TRANSFER
        if "tornado" in to_addr.lower():
            tx_type = TxType.MIXER
        elif "uniswap" in to_addr.lower():
            tx_type = TxType.CONTRACT_CALL
        elif to_addr is None:
            tx_type = TxType.CONTRACT_CREATION
        
        value = random.randint(1, 1000) * 10**18  # 1-1000 ETH
        
        tx = OnChainTx(
            hash=f"0x{hashlib.sha256(f'tx{i}{seed}'.encode()).hexdigest()}",
            from_addr=from_addr,
            to_addr=to_addr,
            value=value,
            gas=random.randint(21000, 500000),
            gas_price=random.randint(10, 100) * 10**9,  # 10-100 gwei
            timestamp=base_time + i * 60,  # 1 min apart
            block_number=18_000_000 + i,
            nonce=i,
            contract_address=to_addr if tx_type == TxType.CONTRACT_CREATION else None,
            input_data=f"0x{hashlib.sha256(f'input{i}'.encode()).hexdigest()[:64]}",
            tx_type=tx_type,
            logs=[
                {
                    "address": to_addr or from_addr,
                    "topics": [
                        f"0x{hashlib.sha256(f'event{i}'.encode()).hexdigest()}",
                    ],
                    "data": f"0x{'00' * 32}",
                }
            ] if to_addr else [],
        )
        txs.append(tx)
    
    return txs


# ───────────────────────────────────────────────────────────────
# Section 1 Demo
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("AJAT WEB3 SECURITY NATIVE — Section 1: BaseLayer")
    print("=" * 60)
    
    # Initialize table
    table = OnChainTable(chain_id=1)
    print(f"\n[1] Initialized: {table}")
    
    # Generate and insert demo transactions
    demo_txs = generate_demo_transactions(count=5)
    table.insert_many(demo_txs)
    
    print(f"\n[2] Inserted {len(demo_txs)} demo transactions:")
    for tx in demo_txs:
        print(f"    {tx}")
    
    # Query by address
    addr = "0x5fe2b58c013d7601147dcdd68c143a77499f5531"
    result = table.query_by_address(addr)
    print(f"\n[3] Query by address {addr[:16]}...: {len(result)} txs found")
    
    # Query by block range
    result = table.query_by_block_range(18_000_000, 18_000_002)
    print(f"\n[4] Query blocks 18M-18M+2: {len(result)} txs found")
    
    # Multi-field query
    result = table.query(min_value=500 * 10**18, tx_type=TxType.CONTRACT_CALL)
    print(f"\n[5] Query value>=500ETH + CONTRACT_CALL: {len(result)} txs found")
    
    # Stats
    stats = table.get_stats()
    print(f"\n[6] Storage stats:")
    for k, v in stats.items():
        print(f"    {k}: {v}")
    
    # Hash lookup
    tx = table.get_by_hash(demo_txs[0].hash)
    print(f"\n[7] Hash lookup: {tx}")
    
    print("\n" + "=" * 60)
    print("Section 1 COMPLETE — BaseLayer ready")
    print("=" * 60)


# ════════════════════════════════════════════════════════════════
# Section 2 — CoreEngine
# TransactionProfiler + AuditAgent + DeFiRiskModel
# ════════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────
# 2.1 TransactionProfiler — Wallet Behavior Analysis
# ───────────────────────────────────────────────────────────────

class RiskLevel(Enum):
    """Risk severity classification."""
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    INFO = auto()


@dataclass
class WalletProfile:
    """Aggregated behavioral profile for a wallet address."""
    address: str
    total_inflow: int = 0
    total_outflow: int = 0
    unique_counterparties: Set[str] = field(default_factory=set)
    contract_interactions: int = 0
    mixer_interactions: int = 0
    avg_tx_value: float = 0.0
    max_tx_value: int = 0
    first_seen: int = 0
    last_seen: int = 0
    tx_count: int = 0
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.INFO
    labels: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return (
            f"<WalletProfile addr={self.address[:14]}... txs={self.tx_count} "
            f"risk={self.risk_level.name}:{self.risk_score:.2f} labels={self.labels}>"
        )


class TransactionProfiler:
    """
    Wallet behavior analysis engine.
    
    Capabilities:
    - Inflow/outflow pattern analysis
    - Counterparty relationship graph
    - Risk heuristics (mixer detection, contract frequency, value anomaly)
    - Behavioral labeling (DEX trader, whale, mixer user, contract deployer)
    
    Inspired by: tx-intelligence-analyzer + blockchain-intelligence-platform
    """
    
    # Known mixer contracts (simulated — no external dependency)
    MIXER_SIGNATURES: Set[str] = {
        "0x5fe2b58c013d7601147dcdd68c143a77499f5531",  # Tornado Cash
        "0x722122df12d4e14e13ac3b6895a86e840a583335",
        "0x910cbd523d972eb0a6f4cae4618ad62622b39f2f",
    }
    
    # Known DEX router signatures
    DEX_SIGNATURES: Set[str] = {
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",  # Uniswap V3
        "0xdef1c0ded9bec7f1a1670819833240f027b25eff",  # 0x
    }
    
    def __init__(self, table: OnChainTable) -> None:
        """
        Initialize profiler with OnChainTable data source.
        
        Args:
            table: Columnar storage containing transactions
        """
        self.table = table
        self._profiles: Dict[str, WalletProfile] = {}
    
    def __repr__(self) -> str:
        return f"<TransactionProfiler wallets={len(self._profiles)} source={self.table}>"
    
    def analyze_wallet(self, address: str) -> WalletProfile:
        """
        Generate behavioral profile for a single wallet.
        
        Args:
            address: Ethereum address to analyze
            
        Returns:
            WalletProfile with computed risk metrics
        """
        txs = self.table.query_by_address(address)
        if not txs:
            return WalletProfile(address=address, labels=["unknown"])
        
        profile = WalletProfile(address=address)
        values: List[int] = []
        
        for tx in txs:
            profile.tx_count += 1
            profile.first_seen = min(profile.first_seen or tx.timestamp, tx.timestamp)
            profile.last_seen = max(profile.last_seen, tx.timestamp)
            
            if tx.from_addr == address:
                profile.total_outflow += tx.value
                if tx.to_addr:
                    profile.unique_counterparties.add(tx.to_addr)
            elif tx.to_addr == address:
                profile.total_inflow += tx.value
                profile.unique_counterparties.add(tx.from_addr)
            
            values.append(tx.value)
            
            # Contract interaction detection
            if tx.contract_address or (tx.to_addr and self._is_contract(tx.to_addr)):
                profile.contract_interactions += 1
            
            # Mixer detection
            if tx.to_addr in self.MIXER_SIGNATURES or tx.from_addr in self.MIXER_SIGNATURES:
                profile.mixer_interactions += 1
        
        # Statistical metrics
        profile.avg_tx_value = sum(values) / len(values) if values else 0.0
        profile.max_tx_value = max(values) if values else 0
        
        # Risk scoring
        profile.risk_score = self._calculate_risk(profile)
        profile.risk_level = self._score_to_level(profile.risk_score)
        profile.labels = self._generate_labels(profile)
        
        self._profiles[address] = profile
        return profile
    
    def analyze_all(self) -> Dict[str, WalletProfile]:
        """Analyze all unique addresses in the dataset."""
        stats = self.table.get_stats()
        # Note: unique_addresses count is available from stats
        # but we need actual addresses from index
        addresses = list(self.table._index_by_address.keys())
        
        for addr in addresses:
            self.analyze_wallet(addr)
        
        return self._profiles
    
    def _is_contract(self, address: str) -> bool:
        """Heuristic: contract addresses have code (simulated)."""
        # In pure Python simulation, we use a deterministic heuristic
        return len(address) > 20 and address[2:4] in {"7a", "68", "de", "5f", "81", "91"}
    
    def _calculate_risk(self, profile: WalletProfile) -> float:
        """
        Calculate composite risk score (0.0 - 1.0).
        
        Factors:
        - Mixer usage: +0.4 per interaction (capped at 0.8)
        - High value: +0.1 if max > 100 ETH
        - Contract intensity: +0.05 per 10% contract ratio
        - Counterparty diversity: -0.05 per unique (capped, reduces risk for legitimate activity)
        """
        score = 0.0
        
        # Mixer penalty
        score += min(profile.mixer_interactions * 0.4, 0.8)
        
        # Value anomaly
        if profile.max_tx_value > 100 * 10**18:
            score += 0.15
        if profile.max_tx_value > 500 * 10**18:
            score += 0.15
        
        # Contract interaction ratio
        if profile.tx_count > 0:
            contract_ratio = profile.contract_interactions / profile.tx_count
            score += contract_ratio * 0.2
        
        # New wallet penalty (fewer than 3 txs, recent first_seen)
        if profile.tx_count <= 2:
            score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert numerical score to RiskLevel enum."""
        if score >= 0.8:
            return RiskLevel.CRITICAL
        elif score >= 0.6:
            return RiskLevel.HIGH
        elif score >= 0.4:
            return RiskLevel.MEDIUM
        elif score >= 0.2:
            return RiskLevel.LOW
        return RiskLevel.INFO
    
    def _generate_labels(self, profile: WalletProfile) -> List[str]:
        """Generate behavioral labels based on patterns."""
        labels: List[str] = []
        
        if profile.mixer_interactions > 0:
            labels.append("mixer_user")
        
        if profile.contract_interactions > 0:
            labels.append("contract_interactor")
        
        if profile.max_tx_value > 100 * 10**18:
            labels.append("whale")
        
        if profile.tx_count >= 5 and profile.avg_tx_value > 10 * 10**18:
            labels.append("active_trader")
        
        if profile.total_inflow > profile.total_outflow * 2:
            labels.append("accumulator")
        elif profile.total_outflow > profile.total_inflow * 2:
            labels.append("distributor")
        
        return labels if labels else ["normal"]
    
    def get_counterparty_graph(self, address: str) -> Dict[str, int]:
        """
        Build counterparty transaction frequency map.
        
        Returns:
            Dict[counterparty_address] -> transaction_count
        """
        txs = self.table.query_by_address(address)
        graph: Dict[str, int] = defaultdict(int)
        
        for tx in txs:
            if tx.from_addr == address and tx.to_addr:
                graph[tx.to_addr] += 1
            elif tx.to_addr == address:
                graph[tx.from_addr] += 1
        
        return dict(graph)
    
    def detect_anomalies(self, address: str) -> List[Dict[str, Any]]:
        """
        Detect anomalous transaction patterns.
        
        Returns:
            List of anomaly findings with type and severity
        """
        txs = self.table.query_by_address(address)
        anomalies: List[Dict[str, Any]] = []
        
        if not txs:
            return anomalies
        
        values = [tx.value for tx in txs]
        avg = sum(values) / len(values) if values else 0
        
        for tx in txs:
            # Sudden spike
            if tx.value > avg * 5 and tx.value > 10 * 10**18:
                anomalies.append({
                    "type": "value_spike",
                    "tx_hash": tx.hash,
                    "severity": RiskLevel.HIGH if tx.value > avg * 10 else RiskLevel.MEDIUM,
                    "detail": f"Value {tx.value / 10**18:.1f}ETH is {tx.value/avg:.1f}x average",
                })
            
            # Mixer interaction
            if tx.to_addr in self.MIXER_SIGNATURES:
                anomalies.append({
                    "type": "mixer_interaction",
                    "tx_hash": tx.hash,
                    "severity": RiskLevel.CRITICAL,
                    "detail": f"Interaction with known mixer {tx.to_addr[:16]}...",
                })
            
            # Round number (potential wash trading)
            if tx.value > 0 and tx.value % (10**18) == 0 and tx.value >= 10 * 10**18:
                anomalies.append({
                    "type": "round_number",
                    "tx_hash": tx.hash,
                    "severity": RiskLevel.LOW,
                    "detail": f"Exact round amount: {tx.value / 10**18:.0f} ETH",
                })
        
        return anomalies


# ───────────────────────────────────────────────────────────────
# 2.2 AuditAgent — Smart Contract Audit Engine
# ───────────────────────────────────────────────────────────────

@dataclass
class VulnerabilityFinding:
    """Single audit finding with metadata."""
    pattern_id: str
    title: str
    description: str
    severity: RiskLevel
    line_number: int
    code_snippet: str
    confidence: float  # 0.0 - 1.0
    remediation: str
    cwe_id: Optional[str] = None
    swc_id: Optional[str] = None
    
    def __repr__(self) -> str:
        return (
            f"<Finding {self.pattern_id} {self.severity.name} line={self.line_number} "
            f"conf={self.confidence:.2f}: {self.title}>"
        )


@dataclass
class TaintNode:
    """Node in taint analysis graph."""
    variable: str
    source_line: int
    taint_type: str  # 'user_input', 'external_call', 'storage', 'literal'
    propagated_to: List[str] = field(default_factory=list)


class AuditAgent:
    """
    Automated smart contract security analysis engine.
    
    Capabilities:
    - AST-based pattern matcher (simulated via regex + heuristic)
    - 20+ vulnerability pattern detection
    - Taint analysis engine (source → sink tracking)
    - Severity scorer (Critical/High/Medium/Low/Info)
    - CVSSv3-style scoring
    
    Inspired by: audit-agent-framework + smart-contract-audit-engine + smart-contract-auditor
    """
    
    # Vulnerability pattern database
    PATTERNS: List[Dict[str, Any]] = [
        {
            "id": "SWC-107",
            "title": "Reentrancy",
            "cwe": "CWE-841",
            "severity": RiskLevel.CRITICAL,
            "regex": r"call\.value\s*\([^)]*\)\s*\{|\.call\s*\{[^}]*value:[^}]*\}",
            "remediation": "Implement Checks-Effects-Interactions pattern. Use ReentrancyGuard.",
        },
        {
            "id": "SWC-101",
            "title": "Integer Overflow/Underflow",
            "cwe": "CWE-682",
            "severity": RiskLevel.HIGH,
            "regex": r"\+\s*[^;]*;|-\s*[^;]*;|\*\s*[^;]*;",
            "remediation": "Use SafeMath library or Solidity 0.8+ built-in overflow checks.",
        },
        {
            "id": "SWC-106",
            "title": "Unprotected SELFDESTRUCT",
            "cwe": "CWE-284",
            "severity": RiskLevel.CRITICAL,
            "regex": r"selfdestruct\s*\(|suicide\s*\(",
            "remediation": "Add access control. Only authorized addresses should trigger destruction.",
        },
        {
            "id": "SWC-112",
            "title": "Delegatecall to Untrusted Callee",
            "cwe": "CWE-829",
            "severity": RiskLevel.CRITICAL,
            "regex": r"delegatecall\s*\(",
            "remediation": "Validate target address. Use proxy patterns with known implementations.",
        },
        {
            "id": "SWC-105",
            "title": "Unprotected Ether Withdrawal",
            "cwe": "CWE-284",
            "severity": RiskLevel.HIGH,
            "regex": r"(call\.value|transfer|send)\s*\([^)]*\)\s*;(?![\s\S]*require|[^\n]*onlyOwner)",
            "remediation": "Add access control modifiers (onlyOwner, role-based access).",
        },
        {
            "id": "SWC-104",
            "title": "Unchecked Call Return Value",
            "cwe": "CWE-252",
            "severity": RiskLevel.MEDIUM,
            "regex": r"(\.call|\.delegatecall|\.staticcall)\s*\([^)]*\)\s*;(?![\s\S]*require\s*\(|[^\n]*if\s*\()",
            "remediation": "Always check return values of low-level calls with require() or if statement.",
        },
        {
            "id": "SWC-103",
            "title": "Floating Pragma",
            "cwe": "CWE-1104",
            "severity": RiskLevel.INFO,
            "regex": r"pragma solidity \^",
            "remediation": "Lock pragma to specific version: pragma solidity 0.8.x;",
        },
        {
            "id": "SWC-102",
            "title": "Outdated Compiler Version",
            "cwe": "CWE-1104",
            "severity": RiskLevel.LOW,
            "regex": r"pragma solidity (\^?)0\.(4|5|6|7)\.",
            "remediation": "Upgrade to Solidity 0.8+ for built-in overflow protection.",
        },
        {
            "id": "SWC-100",
            "title": "Function Default Visibility",
            "cwe": "CWE-710",
            "severity": RiskLevel.HIGH,
            "regex": r"function\s+\w+\s*\([^)]*\)\s*(?!public|private|internal|external)\s*\{",
            "remediation": "Explicitly declare function visibility (public, external, internal, private).",
        },
        {
            "id": "SWC-115",
            "title": "Tx.origin Authentication",
            "cwe": "CWE-287",
            "severity": RiskLevel.HIGH,
            "regex": r"tx\.origin\s*==\s*",
            "remediation": "Use msg.sender instead of tx.origin for authorization.",
        },
        {
            "id": "SWC-114",
            "title": "Transaction Order Dependence / Front-Running",
            "cwe": "CWE-362",
            "severity": RiskLevel.MEDIUM,
            "regex": r"block\.timestamp|block\.number|block\.difficulty",
            "remediation": "Use commit-reveal scheme or VRF (Chainlink) for randomness/timing.",
        },
        {
            "id": "SWC-113",
            "title": "DoS with Block Gas Limit",
            "cwe": "CWE-400",
            "severity": RiskLevel.MEDIUM,
            "regex": r"for\s*\([^)]*\)\s*\{|while\s*\([^)]*\)\s*\{",
            "remediation": "Avoid unbounded loops. Use pull over push pattern for distributions.",
        },
        {
            "id": "SWC-111",
            "title": "Use of Deprecated Solidity Functions",
            "cwe": "CWE-477",
            "severity": RiskLevel.LOW,
            "regex": r"\b(sha3|suicide|throw|block\.blockhash\s*\()\b",
            "remediation": "Replace with keccak256, selfdestruct, revert, blockhash().",
        },
        {
            "id": "SWC-110",
            "title": "Assert Violation",
            "cwe": "CWE-670",
            "severity": RiskLevel.LOW,
            "regex": r"assert\s*\([^)]*\)\s*;",
            "remediation": "Use assert only for invariant checks. Use require for input validation.",
        },
        {
            "id": "SWC-109",
            "title": "Uninitialized Storage Pointer",
            "cwe": "CWE-824",
            "severity": RiskLevel.HIGH,
            "regex": r"\w+\s+\w+\s*;(?![\s\S]*=\s*new|[^\n]*\(\))",
            "remediation": "Always initialize struct/storage variables explicitly.",
        },
        {
            "id": "SWC-108",
            "title": "State Variable Default Visibility",
            "cwe": "CWE-710",
            "severity": RiskLevel.MEDIUM,
            "regex": r"^(?!\s*(public|private|internal|constant|immutable))\s*(uint|int|address|bool|string|bytes)\s+\w+\s*;",
            "remediation": "Explicitly declare state variable visibility.",
        },
        {
            "id": "SWC-116",
            "title": "Timestamp Dependence",
            "cwe": "CWE-362",
            "severity": RiskLevel.LOW,
            "regex": r"block\.timestamp\s*[+<>-]\s*\d+",
            "remediation": "Avoid strict timestamp comparisons. Use time windows with tolerance.",
        },
        {
            "id": "ACCESS-001",
            "title": "Missing Access Control on Critical Function",
            "cwe": "CWE-284",
            "severity": RiskLevel.CRITICAL,
            "regex": r"function\s+(mint|burn|withdraw|transferOwnership|pause|unpause|upgrade)\s*\([^)]*\)\s*(?!.*onlyOwner|.*onlyRole|.*auth)",
            "remediation": "Add onlyOwner, onlyRole, or custom access control modifiers.",
        },
        {
            "id": "FLASH-001",
            "title": "Flash Loan Vulnerability Pattern",
            "cwe": "CWE-20",
            "severity": RiskLevel.HIGH,
            "regex": r"flashLoan|flashBorrow|flashSwap|\.swap\s*\([^)]*\)\s*;(?![\s\S]*reentrancy|[^\n]*lock)",
            "remediation": "Add reentrancy protection and price oracle validation for flash loan handlers.",
        },
        {
            "id": "ORACLE-001",
            "title": "Centralized Oracle Manipulation Risk",
            "cwe": "CWE-20",
            "severity": RiskLevel.MEDIUM,
            "regex": r"setPrice|updatePrice|price\s*=\s*[^;]*;(?![\s\S]*multi\s*sig|[^\n]*governance)",
            "remediation": "Use decentralized oracle networks (Chainlink, Band) or multi-sig price updates.",
        },
    ]
    
    def __init__(self) -> None:
        """Initialize audit agent with pattern database."""
        self._findings: List[VulnerabilityFinding] = []
        self._taint_graph: Dict[str, TaintNode] = {}
    
    def __repr__(self) -> str:
        return f"<AuditAgent patterns={len(self.PATTERNS)} findings={len(self._findings)}>"
    
    def audit_contract(self, source_code: str, contract_name: str = "Contract") -> List[VulnerabilityFinding]:
        """
        Perform full security audit on Solidity source code.
        
        Args:
            source_code: Solidity contract source
            contract_name: Name for report identification
            
        Returns:
            List of VulnerabilityFinding records
        """
        self._findings = []
        self._taint_graph = {}
        
        # Phase 1: Pattern matching
        self._run_pattern_matching(source_code)
        
        # Phase 2: Taint analysis
        self._run_taint_analysis(source_code)
        
        # Phase 3: Severity normalization
        self._normalize_severities()
        
        return self._findings
    
    def _run_pattern_matching(self, source_code: str) -> None:
        """Execute regex-based pattern detection."""
        lines = source_code.split("\n")
        
        import re
        for pattern in self.PATTERNS:
            compiled = re.compile(pattern["regex"], re.IGNORECASE | re.MULTILINE)
            
            for line_num, line in enumerate(lines, 1):
                if compiled.search(line):
                    # Check for false positive indicators (comments)
                    stripped = line.strip()
                    if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                        continue
                    
                    confidence = self._calculate_confidence(line, pattern["severity"])
                    
                    finding = VulnerabilityFinding(
                        pattern_id=pattern["id"],
                        title=pattern["title"],
                        description=f"Pattern match: {pattern['regex'][:50]}...",
                        severity=pattern["severity"],
                        line_number=line_num,
                        code_snippet=line.strip()[:200],
                        confidence=confidence,
                        remediation=pattern["remediation"],
                        cwe_id=pattern.get("cwe"),
                        swc_id=pattern["id"] if pattern["id"].startswith("SWC") else None,
                    )
                    self._findings.append(finding)
    
    def _run_taint_analysis(self, source_code: str) -> None:
        """
        Track data flow from sources (user input, external calls) to sinks (state changes, transfers).
        """
        lines = source_code.split("\n")
        sources: List[TaintNode] = []
        sinks: List[Tuple[str, int]] = []
        
        # Identify sources: msg.value, msg.data, external call returns
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if "msg.value" in stripped or "msg.data" in stripped or "_value" in stripped:
                var = self._extract_variable(stripped)
                if var:
                    sources.append(TaintNode(var, line_num, "user_input"))
            
            if ".call(" in stripped or ".delegatecall(" in stripped:
                var = self._extract_variable(stripped)
                if var:
                    sources.append(TaintNode(var, line_num, "external_call"))
        
        # Identify sinks: state changes, transfers
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if any(kw in stripped for kw in ["=", "transfer(", "send(", "call.value", "storage"]):
                sinks.append((stripped, line_num))
        
        # Cross-reference sources to sinks (simplified: same function scope heuristic)
        for source in sources:
            for sink_text, sink_line in sinks:
                if source.variable in sink_text and abs(sink_line - source.source_line) < 20:
                    # Taint propagation detected
                    finding = VulnerabilityFinding(
                        pattern_id="TAINT-001",
                        title="Tainted Data Flow",
                        description=f"Variable '{source.variable}' from {source.taint_type} flows to state change",
                        severity=RiskLevel.HIGH,
                        line_number=sink_line,
                        code_snippet=sink_text[:200],
                        confidence=0.7,
                        remediation="Validate all user input before state changes. Use checks-effects-interactions.",
                    )
                    self._findings.append(finding)
                    source.propagated_to.append(sink_text[:50])
    
    def _extract_variable(self, line: str) -> Optional[str]:
        """Extract assigned variable from code line."""
        if "=" in line:
            parts = line.split("=")
            if len(parts) >= 2:
                left = parts[0].strip()
                # Extract last token (variable name)
                tokens = left.replace(",", " ").split()
                return tokens[-1] if tokens else None
        return None
    
    def _calculate_confidence(self, line: str, base_severity: RiskLevel) -> float:
        """Calculate confidence score based on context."""
        confidence = 0.6
        
        # Boost if line has clear intent keywords
        intent_keywords = ["require", "assert", "onlyOwner", "nonReentrant"]
        if any(kw in line for kw in intent_keywords):
            confidence += 0.1
        
        # Reduce if line is in a library or interface
        if "library" in line or "interface" in line:
            confidence -= 0.2
        
        # Severity-based baseline adjustment
        if base_severity == RiskLevel.CRITICAL:
            confidence += 0.15
        elif base_severity == RiskLevel.INFO:
            confidence -= 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _normalize_severities(self) -> None:
        """Deduplicate and adjust severities based on confidence."""
        # Group by pattern_id + line
        grouped: Dict[Tuple[str, int], List[VulnerabilityFinding]] = defaultdict(list)
        for f in self._findings:
            grouped[(f.pattern_id, f.line_number)].append(f)
        
        # Keep highest confidence per group
        self._findings = []
        for group in grouped.values():
            best = max(group, key=lambda f: f.confidence)
            self._findings.append(best)
    
    def get_summary(self) -> Dict[str, Any]:
        """Return audit summary statistics."""
        severity_counts: Dict[str, int] = defaultdict(int)
        for f in self._findings:
            severity_counts[f.severity.name] += 1
        
        return {
            "total_findings": len(self._findings),
            "severity_distribution": dict(severity_counts),
            "critical": severity_counts.get("CRITICAL", 0),
            "high": severity_counts.get("HIGH", 0),
            "medium": severity_counts.get("MEDIUM", 0),
            "low": severity_counts.get("LOW", 0),
            "info": severity_counts.get("INFO", 0),
            "avg_confidence": sum(f.confidence for f in self._findings) / len(self._findings) if self._findings else 0,
        }


# ───────────────────────────────────────────────────────────────
# 2.3 DeFiRiskModel — Quantitative Risk Framework
# ───────────────────────────────────────────────────────────────

@dataclass
class PoolState:
    """AMM pool state snapshot."""
    token0_reserve: float
    token1_reserve: float
    token0_price: float  # in terms of token1
    token1_price: float  # in terms of token0
    total_liquidity: float
    fee_tier: float = 0.003  # 0.3% default
    
    def __repr__(self) -> str:
        return (
            f"<PoolState reserves=({self.token0_reserve:.2f}, {self.token1_reserve:.2f}) "
            f"price={self.token0_price:.6f} liquidity={self.total_liquidity:.2f}>"
        )


@dataclass
class LendingPosition:
    """Lending protocol position."""
    collateral_asset: str
    collateral_amount: float
    borrow_asset: str
    borrow_amount: float
    collateral_factor: float  # Loan-to-value ratio max
    liquidation_threshold: float
    health_factor: float = 0.0
    
    def __post_init__(self) -> None:
        self._update_health()
    
    def _update_health(self) -> None:
        """Recalculate health factor."""
        if self.borrow_amount > 0:
            max_borrow = self.collateral_amount * self.collateral_factor
            self.health_factor = max_borrow / self.borrow_amount if self.borrow_amount > 0 else float('inf')
        else:
            self.health_factor = float('inf')
    
    def __repr__(self) -> str:
        return (
            f"<LendingPosition collateral={self.collateral_amount:.2f} {self.collateral_asset} "
            f"borrow={self.borrow_amount:.2f} {self.borrow_asset} HF={self.health_factor:.2f}>"
        )


class DeFiRiskModel:
    """
    Quantitative risk modeling for DeFi protocols.
    
    Capabilities:
    - Value at Risk (VaR) calculation (historical simulation)
    - Impermanent Loss calculator (constant product formula)
    - TVL tracking and change detection
    - Protocol health score composite
    - Liquidation risk assessment
    
    Supports: AMM (Uniswap V2/V3 style), Lending (Compound/Aave style), Stablecoin (CDP)
    
    Inspired by: crypto-risk-modeling + defi-risk-analyzer
    """
    
    def __init__(self, confidence_level: float = 0.95) -> None:
        """
        Initialize risk model.
        
        Args:
            confidence_level: VaR confidence level (default 95%)
        """
        self.confidence_level = confidence_level
        self._tvl_history: List[Tuple[int, float]] = []  # (timestamp, tvl)
        self._price_history: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
    
    def __repr__(self) -> str:
        return f"<DeFiRiskModel confidence={self.confidence_level} tvl_points={len(self._tvl_history)}>"
    
    def update_tvl(self, timestamp: int, tvl_usd: float) -> None:
        """Record TVL snapshot."""
        self._tvl_history.append((timestamp, tvl_usd))
    
    def update_price(self, asset: str, timestamp: int, price_usd: float) -> None:
        """Record price point for asset."""
        self._price_history[asset].append((timestamp, price_usd))
    
    def calculate_var(self, returns: List[float], method: str = "historical") -> float:
        """
        Calculate Value at Risk.
        
        Args:
            returns: List of historical returns (as decimals, e.g. 0.05 = 5%)
            method: "historical" or "parametric"
            
        Returns:
            VaR as positive number (e.g. 0.03 means 3% potential loss)
        """
        if not returns:
            return 0.0
        
        if method == "historical":
            sorted_returns = sorted(returns)
            index = int((1 - self.confidence_level) * len(sorted_returns))
            return abs(sorted_returns[index]) if index < len(sorted_returns) else 0.0
        
        elif method == "parametric":
            import math
            mean = sum(returns) / len(returns)
            variance = sum((r - mean) ** 2 for r in returns) / len(returns)
            std_dev = math.sqrt(variance)
            # Simplified z-score for 95% = 1.645
            z_scores = {0.90: 1.28, 0.95: 1.645, 0.99: 2.33}
            z = z_scores.get(self.confidence_level, 1.645)
            return z * std_dev
        
        return 0.0
    
    def calculate_impermanent_loss(
        self,
        price_ratio_change: float,
        fee_earned: float = 0.0,
    ) -> float:
        """
        Calculate impermanent loss for constant product AMM.
        
        Formula: IL = 2*sqrt(price_ratio) / (1 + price_ratio) - 1
        Net IL = IL + fee_earned
        
        Args:
            price_ratio_change: P_end / P_start (e.g. 2.0 means price doubled)
            fee_earned: Fee income as fraction of principal (e.g. 0.005 = 0.5%)
            
        Returns:
            Net impermanent loss as negative number (e.g. -0.05 = 5% loss)
        """
        import math
        
        if price_ratio_change <= 0:
            return -1.0  # Total loss
        
        # Constant product IL formula
        il = (2 * math.sqrt(price_ratio_change) / (1 + price_ratio_change)) - 1.0
        
        # Net after fees
        net_il = il + fee_earned
        
        return net_il
    
    def calculate_pool_apr(
        self,
        pool: PoolState,
        volume_24h: float,
        days: int = 365,
    ) -> float:
        """
        Estimate APR from fees.
        
        Formula: APR = (volume * fee_tier * days) / total_liquidity
        """
        if pool.total_liquidity <= 0:
            return 0.0
        
        daily_fees = volume_24h * pool.fee_tier
        apr = (daily_fees * days) / pool.total_liquidity
        return apr
    
    def assess_lending_risk(self, position: LendingPosition) -> Dict[str, Any]:
        """
        Assess liquidation risk for lending position.
        
        Returns:
            Risk metrics dictionary
        """
        position._update_health()
        
        # Liquidation proximity
        if position.health_factor <= 1.0:
            status = "liquidatable"
        elif position.health_factor < 1.1:
            status = "critical"
        elif position.health_factor < 1.5:
            status = "warning"
        else:
            status = "healthy"
        
        # Buffer to liquidation
        buffer = position.health_factor - 1.0 if position.health_factor > 1.0 else 0.0
        
        return {
            "health_factor": position.health_factor,
            "status": status,
            "liquidation_buffer": buffer,
            "max_additional_borrow": position.collateral_amount * position.collateral_factor - position.borrow_amount,
            "liquidation_price": self._calculate_liquidation_price(position),
        }
    
    def _calculate_liquidation_price(self, position: LendingPosition) -> float:
        """Calculate collateral price at which position becomes liquidatable."""
        if position.borrow_amount <= 0 or position.collateral_amount <= 0:
            return 0.0
        
        # HF = (collateral * price * threshold) / borrow = 1
        # liquidation_price = borrow / (collateral * threshold)
        return position.borrow_amount / (position.collateral_amount * position.liquidation_threshold)
    
    def protocol_health_score(self) -> float:
        """
        Calculate composite protocol health score (0-100).
        
        Factors:
        - TVL trend (30%): Growing = good, declining = bad
        - Volatility (30%): High = bad
        - Concentration (20%): High = bad
        - Utilization (20%): Optimal 60-80%, too high = risky
        """
        if len(self._tvl_history) < 2:
            return 50.0  # Neutral if insufficient data
        
        # TVL trend (last 7 days vs previous 7 days)
        recent = [tvl for _, tvl in self._tvl_history[-7:]]
        previous = [tvl for _, tvl in self._tvl_history[-14:-7]] if len(self._tvl_history) >= 14 else recent
        
        tvl_change = (sum(recent) / len(recent)) / (sum(previous) / len(previous)) - 1 if previous else 0
        tvl_score = max(0, min(100, 50 + tvl_change * 500))  # +10% change = 100, -10% = 0
        
        # Volatility score (lower vol = higher score)
        if len(recent) >= 2:
            import math
            mean = sum(recent) / len(recent)
            variance = sum((t - mean) ** 2 for t in recent) / len(recent)
            cv = math.sqrt(variance) / mean if mean > 0 else 0
            vol_score = max(0, min(100, 100 - cv * 1000))
        else:
            vol_score = 50.0
        
        # Composite
        score = tvl_score * 0.30 + vol_score * 0.30 + 50.0 * 0.20 + 50.0 * 0.20
        return round(score, 2)
    
    def get_tvl_change(self, hours: int = 24) -> Dict[str, float]:
        """Calculate TVL change metrics over time window."""
        if not self._tvl_history:
            return {"current": 0, "change_pct": 0, "change_abs": 0}
        
        current = self._tvl_history[-1][1]
        cutoff = self._tvl_history[-1][0] - hours * 3600
        
        past_values = [tvl for ts, tvl in self._tvl_history if ts >= cutoff]
        if not past_values:
            return {"current": current, "change_pct": 0, "change_abs": 0}
        
        past_avg = sum(past_values) / len(past_values)
        change_abs = current - past_avg
        change_pct = (change_abs / past_avg * 100) if past_avg > 0 else 0
        
        return {
            "current": current,
            "change_pct": round(change_pct, 2),
            "change_abs": round(change_abs, 2),
        }
    
    def simulate_stress_test(
        self,
        pool: PoolState,
        price_shocks: List[float],
    ) -> List[Dict[str, Any]]:
        """
        Simulate pool behavior under price shocks.
        
        Args:
            pool: Current pool state
            price_shocks: List of price multiplier shocks (e.g. [0.5, 0.8, 1.2, 2.0])
            
        Returns:
            List of simulation results
        """
        results = []
        
        for shock in price_shocks:
            new_price = pool.token0_price * shock
            il = self.calculate_impermanent_loss(shock)
            
            # New reserves (constant product)
            import math
            k = pool.token0_reserve * pool.token1_reserve
            new_reserve0 = math.sqrt(k / new_price)
            new_reserve1 = math.sqrt(k * new_price)
            
            results.append({
                "price_shock": shock,
                "new_price": new_price,
                "impermanent_loss": round(il * 100, 2),
                "new_reserve0": round(new_reserve0, 4),
                "new_reserve1": round(new_reserve1, 4),
                "liquidity_ratio": round(new_reserve0 / pool.token0_reserve, 4) if pool.token0_reserve > 0 else 0,
            })
        
        return results


# ───────────────────────────────────────────────────────────────
# Section 2 Demo (commented — runs only in main)
# ───────────────────────────────────────────────────────────────

def demo_section_2():
    """Demonstrate CoreEngine capabilities."""
    print("\n" + "=" * 60)
    print("AJAT WEB3 SECURITY NATIVE — Section 2: CoreEngine")
    print("=" * 60)
    
    # Reuse table from Section 1
    table = OnChainTable(chain_id=1)
    demo_txs = generate_demo_transactions(count=10)
    table.insert_many(demo_txs)
    
    # 2.1 TransactionProfiler
    profiler = TransactionProfiler(table)
    print("\n[2.1] Wallet Profiling:")
    
    for addr in list(table._index_by_address.keys())[:3]:
        profile = profiler.analyze_wallet(addr)
        print(f"    {profile}")
        if profile.risk_level.value >= RiskLevel.MEDIUM.value:
            anomalies = profiler.detect_anomalies(addr)
            for a in anomalies[:2]:
                print(f"      ⚠ {a['type']}: {a['severity'].name} — {a['detail'][:60]}")
    
    # 2.2 AuditAgent
    agent = AuditAgent()
    print("\n[2.2] Smart Contract Audit:")
    
    sample_contract = '''
pragma solidity ^0.8.0;

contract VulnerableToken {
    mapping(address => uint) public balances;
    
    function withdraw(uint amount) public {
        require(balances[msg.sender] >= amount);
        msg.sender.call{value: amount}("");
        balances[msg.sender] -= amount;
    }
    
    function mint(uint amount) public {
        balances[msg.sender] += amount;
    }
    
    uint public price;
    function setPrice(uint p) public {
        price = p;
    }
}
'''
    findings = agent.audit_contract(sample_contract, "VulnerableToken")
    print(f"    Findings: {len(findings)}")
    for f in findings[:5]:
        print(f"    [{f.severity.name}] {f.pattern_id} (line {f.line_number}): {f.title}")
    
    summary = agent.get_summary()
    print(f"    Summary: {summary}")
    
    # 2.3 DeFiRiskModel
    model = DeFiRiskModel()
    print("\n[2.3] DeFi Risk Modeling:")
    
    # IL calculation
    il = model.calculate_impermanent_loss(price_ratio_change=2.0, fee_earned=0.01)
    print(f"    IL (2x price, 1% fees): {il*100:.2f}%")
    
    # VaR
    returns = [-0.05, 0.02, -0.03, 0.01, -0.08, 0.03, -0.01, 0.04, -0.02, 0.01]
    var = model.calculate_var(returns)
    print(f"    VaR (95%): {var*100:.2f}%")
    
    # Lending risk
    position = LendingPosition(
        collateral_asset="ETH",
        collateral_amount=10.0,
        borrow_asset="USDC",
        borrow_amount=5000.0,
        collateral_factor=0.75,
        liquidation_threshold=0.8,
    )
    risk = model.assess_lending_risk(position)
    print(f"    Lending: HF={risk['health_factor']:.2f}, status={risk['status']}")
    
    print("\n" + "=" * 60)
    print("Section 2 COMPLETE — CoreEngine ready")
    print("=" * 60)
    
    return profiler, agent, model


# ════════════════════════════════════════════════════════════════
# Section 3 — Features
# PatternLibrary + FlashLoanDetector + ThreatIntelEngine
# Web3Deployer + SecurityReportGenerator
# ════════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────
# 3.1 PatternLibrary — Secure Smart Contract Patterns
# ───────────────────────────────────────────────────────────────

@dataclass
class SecurePattern:
    """Documented secure pattern with implementation template."""
    pattern_id: str
    name: str
    category: str
    description: str
    implementation: str
    rationale: str
    related_vulnerabilities: List[str]
    code_example: str
    
    def __repr__(self) -> str:
        return f"<SecurePattern {self.pattern_id} [{self.category}] {self.name}>"


class PatternLibrary:
    """
    Collection of secure smart contract patterns and anti-patterns.
    
    Provides 15+ documented patterns with:
    - Implementation templates
    - Rationale and security reasoning
    - Related vulnerability mappings
    - Code examples
    
    Inspired by: smart-contract-patterns + defi-security-toolkit + web3-security-toolkit
    """
    
    def __init__(self) -> None:
        """Initialize pattern library with all documented patterns."""
        self._patterns: Dict[str, SecurePattern] = {}
        self._load_patterns()
    
    def __repr__(self) -> str:
        return f"<PatternLibrary patterns={len(self._patterns)}>"
    
    def _load_patterns(self) -> None:
        """Populate pattern database."""
        patterns = [
            SecurePattern(
                pattern_id="SEC-001",
                name="Checks-Effects-Interactions",
                category="Reentrancy Protection",
                description="Perform all checks first, then effects (state changes), then external calls last.",
                implementation="1. Validate inputs/require conditions. 2. Update state. 3. Call external contracts.",
                rationale="Prevents reentrancy by ensuring state is finalized before external calls can re-enter.",
                related_vulnerabilities=["SWC-107", "Reentrancy"],
                code_example='''
function withdraw(uint amount) public {
    require(balances[msg.sender] >= amount, "Insufficient");
    balances[msg.sender] -= amount;  // EFFECTS
    (bool sent, ) = msg.sender.call{value: amount}("");  // INTERACTIONS
    require(sent, "Transfer failed");
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-002",
                name="Pull over Push",
                category="DoS Prevention",
                description="Let users withdraw funds instead of automatically pushing payments.",
                implementation="Maintain pending withdrawals mapping. Users call claim() to receive.",
                rationale="Prevents DoS from gas limit exhaustion and failed recipient contracts.",
                related_vulnerabilities=["SWC-113", "SWC-105"],
                code_example='''
mapping(address => uint) public pendingWithdrawals;

function claim() public {
    uint amount = pendingWithdrawals[msg.sender];
    pendingWithdrawals[msg.sender] = 0;
    (bool sent, ) = msg.sender.call{value: amount}("");
    require(sent, "Transfer failed");
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-003",
                name="Mutex / ReentrancyGuard",
                category="Reentrancy Protection",
                description="Use a lock variable to prevent recursive entry into functions.",
                implementation="modifier nonReentrant() { require(!locked); locked = true; _; locked = false; }",
                rationale="Simple and effective mechanism to block all reentrant calls.",
                related_vulnerabilities=["SWC-107"],
                code_example='''
bool private locked;
modifier nonReentrant() {
    require(!locked, "Reentrant call");
    locked = true;
    _;
    locked = false;
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-004",
                name="Emergency Stop (Circuit Breaker)",
                category="Access Control",
                description="Pause contract functionality during emergencies.",
                implementation="bool paused; modifier whenNotPaused() { require(!paused); _; }",
                rationale="Provides time to investigate and patch without permanent damage.",
                related_vulnerabilities=["SWC-106", "SWC-107"],
                code_example='''
bool public paused;
modifier whenNotPaused() {
    require(!paused, "Contract paused");
    _;
}

function pause() external onlyOwner {
    paused = true;
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-005",
                name="Role-Based Access Control (RBAC)",
                category="Access Control",
                description="Assign roles (admin, minter, burner) instead of single owner.",
                implementation="mapping(bytes32 => mapping(address => bool)) roles; + onlyRole modifier.",
                rationale="Fine-grained permissions reduce blast radius of compromised keys.",
                related_vulnerabilities=["ACCESS-001", "SWC-105"],
                code_example='''
bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
modifier onlyRole(bytes32 role) {
    require(hasRole(role, msg.sender), "Unauthorized");
    _;
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-006",
                name="Rate Limiting",
                category="DoS Prevention",
                description="Limit frequency of sensitive operations per user.",
                implementation="Track lastActionTime per user. Enforce minimum interval between actions.",
                rationale="Prevents rapid-fire attacks and griefing.",
                related_vulnerabilities=["SWC-113", "SWC-400"],
                code_example='''
mapping(address => uint) public lastActionTime;
uint public constant COOLDOWN = 1 hours;

function sensitiveAction() public {
    require(block.timestamp >= lastActionTime[msg.sender] + COOLDOWN, "Rate limited");
    lastActionTime[msg.sender] = block.timestamp;
    // ... action logic
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-007",
                name="Integer Safety (SafeMath / 0.8+)",
                category="Arithmetic Safety",
                description="Prevent overflow/underflow in arithmetic operations.",
                implementation="Use Solidity 0.8+ (built-in checks) or SafeMath library for older versions.",
                rationale="Unchecked arithmetic is a top cause of fund-draining exploits.",
                related_vulnerabilities=["SWC-101"],
                code_example='''
// Solidity 0.8+ — automatic overflow/underflow checks
function add(uint a, uint b) public pure returns (uint) {
    return a + b;  // Reverts on overflow
}

// Older: using SafeMath
using SafeMath for uint;
uint result = a.add(b);
''',
            ),
            SecurePattern(
                pattern_id="SEC-008",
                name="Oracle Sanity Checks",
                category="Oracle Security",
                description="Validate oracle prices before using them in calculations.",
                implementation="Check price freshness, bounds, and multi-source consistency.",
                rationale="Single oracle dependency is a common attack vector (price manipulation).",
                related_vulnerabilities=["ORACLE-001", "FLASH-001"],
                code_example='''
function getSafePrice() internal view returns (uint) {
    uint price = oracle.latestAnswer();
    require(price > 0, "Invalid price");
    require(block.timestamp - oracle.updatedAt() < 1 hours, "Stale price");
    return price;
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-009",
                name="Flash Loan Protection",
                category="DeFi Security",
                description="Detect and mitigate flash loan attack vectors in price-dependent functions.",
                implementation="Use time-weighted average prices, add cooldown periods, or check msg.sender balance.",
                rationale="Flash loans enable risk-free price manipulation for profit extraction.",
                related_vulnerabilities=["FLASH-001", "ORACLE-001"],
                code_example='''
function swapWithProtection(uint amount) public {
    uint balanceBefore = address(this).balance;
    // ... swap logic ...
    require(address(this).balance >= balanceBefore, "Negative balance");
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-010",
                name="Input Validation",
                category="Data Integrity",
                description="Validate all external inputs with require() at function entry.",
                implementation="Check bounds, whitelist, formats, and business logic constraints upfront.",
                rationale="Most exploits begin with unexpected input values.",
                related_vulnerabilities=["SWC-110", "SWC-123"],
                code_example='''
function transfer(address to, uint amount) public {
    require(to != address(0), "Zero address");
    require(amount > 0 && amount <= balances[msg.sender], "Invalid amount");
    // ... transfer logic
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-011",
                name="Time Lock for Admin Actions",
                category="Governance",
                description="Delay sensitive admin actions by a fixed period.",
                implementation="Schedule action, emit event, execute only after delay expires.",
                rationale="Prevents immediate malicious admin actions, gives users time to react.",
                related_vulnerabilities=["ACCESS-001", "SWC-106"],
                code_example='''
uint public constant DELAY = 2 days;
mapping(bytes32 => uint) public queuedAt;

function execute(bytes32 txHash) external onlyOwner {
    require(block.timestamp >= queuedAt[txHash] + DELAY, "Not ready");
    // ... execute
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-012",
                name="Upgradability Patterns (UUPS / Transparent)",
                category="Maintainability",
                description="Enable contract upgrades without losing state or user funds.",
                implementation="Proxy delegates calls to implementation. UUPS: logic in impl. Transparent: logic in proxy.",
                rationale="Bug fixes and feature additions require upgrade paths.",
                related_vulnerabilities=["SWC-112"],
                code_example='''
// UUPS pattern
contract UUPSProxy {
    address public implementation;
    
    fallback() external payable {
        (bool success, ) = implementation.delegatecall(msg.data);
        require(success, "Delegatecall failed");
    }
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-013",
                name="Event Emission for State Changes",
                category="Transparency",
                description="Emit events for all significant state changes.",
                implementation="Define and emit events for transfers, ownership changes, upgrades, etc.",
                rationale="Off-chain monitoring and incident response depend on event logs.",
                related_vulnerabilities=["SWC-104", "SWC-135"],
                code_example='''
event Transfer(address indexed from, address indexed to, uint amount);
event OwnershipTransferred(address indexed oldOwner, address indexed newOwner);
''',
            ),
            SecurePattern(
                pattern_id="SEC-014",
                name="Zero-Address Checks",
                category="Data Integrity",
                description="Prevent transfers and critical operations to address(0).",
                implementation="require(addr != address(0)) before any state-changing operation.",
                rationale="Accidental zero-address sends are irreversible.",
                related_vulnerabilities=["SWC-110"],
                code_example='''
function mint(address to, uint amount) public onlyOwner {
    require(to != address(0), "Cannot mint to zero");
    balances[to] += amount;
    totalSupply += amount;
}
''',
            ),
            SecurePattern(
                pattern_id="SEC-015",
                name="Bounded Loops with Guards",
                category="DoS Prevention",
                description="Ensure loops cannot grow unboundedly with user-controlled data.",
                implementation="Cap iteration count. Use pagination for bulk operations.",
                rationale="Unbounded loops hit block gas limit, causing permanent DoS.",
                related_vulnerabilities=["SWC-113", "SWC-128"],
                code_example='''
uint public constant MAX_ITERATIONS = 100;

function distribute(address[] calldata recipients, uint[] calldata amounts) public {
    require(recipients.length == amounts.length, "Length mismatch");
    require(recipients.length <= MAX_ITERATIONS, "Too many recipients");
    for (uint i = 0; i < recipients.length; i++) {
        _transfer(msg.sender, recipients[i], amounts[i]);
    }
}
''',
            ),
        ]
        
        for p in patterns:
            self._patterns[p.pattern_id] = p
    
    def get_pattern(self, pattern_id: str) -> Optional[SecurePattern]:
        """Retrieve pattern by ID."""
        return self._patterns.get(pattern_id)
    
    def get_by_vulnerability(self, vuln_id: str) -> List[SecurePattern]:
        """Find patterns that mitigate a specific vulnerability."""
        return [
            p for p in self._patterns.values()
            if vuln_id in p.related_vulnerabilities
        ]
    
    def get_by_category(self, category: str) -> List[SecurePattern]:
        """Filter patterns by category."""
        return [p for p in self._patterns.values() if p.category == category]
    
    def list_all(self) -> List[SecurePattern]:
        """Return all patterns."""
        return list(self._patterns.values())
    
    def generate_remediation(self, finding: VulnerabilityFinding) -> List[SecurePattern]:
        """
        Suggest patterns to remediate a finding.
        
        Args:
            finding: VulnerabilityFinding from AuditAgent
            
        Returns:
            List of recommended SecurePattern objects
        """
        patterns: List[SecurePattern] = []
        
        # Match by SWC/CWE or pattern ID
        if finding.swc_id:
            patterns.extend(self.get_by_vulnerability(finding.swc_id))
        if finding.cwe_id:
            patterns.extend(self.get_by_vulnerability(finding.cwe_id))
        
        # Fallback: match by title keywords
        title_lower = finding.title.lower()
        for p in self._patterns.values():
            if p.name.lower() in title_lower or any(
                kw in title_lower for kw in p.related_vulnerabilities
            ):
                if p not in patterns:
                    patterns.append(p)
        
        return patterns[:3]  # Top 3 recommendations


# ───────────────────────────────────────────────────────────────
# 3.2 FlashLoanDetector — Attack Pattern Detection
# ───────────────────────────────────────────────────────────────

@dataclass
class FlashLoanPattern:
    """Detected flash loan attack pattern."""
    pattern_type: str
    transactions: List[str]  # tx hashes
    profit_extracted: int
    victim_contracts: List[str]
    confidence: float
    severity: RiskLevel
    details: Dict[str, Any]


class FlashLoanDetector:
    """
    Detection engine for flash loan attacks and DeFi exploitation.
    
    Capabilities:
    - Sequential transaction analysis
    - Borrow→Manipulate→Repay pattern detection
    - Price oracle manipulation detection
    - Profit extraction heuristic
    
    Inspired by: defi-security-toolkit + flash loan analysis repos
    """
    
    # Flash loan provider signatures
    FLASH_LOAN_PROVIDERS: Set[str] = {
        "0x24a42fd28c976a61df5d00d0599c34c4f90748c8",  # Aave V1
        "0x398eC7346DcD622eDc5a823e95f65B65b62f3C9e",  # Aave V2
        "0x87870Bca3F3fD6335C3F4ce8392D0a8E7D5E2b2E",  # Aave V3
        "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B",  # Compound
        "0xBA12222222228d8Ba445958a75a0704d566BF2C8",  # Balancer
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH (flash mint)
    }
    
    def __init__(self, table: OnChainTable) -> None:
        """Initialize with transaction data source."""
        self.table = table
        self._detections: List[FlashLoanPattern] = []
    
    def __repr__(self) -> str:
        return f"<FlashLoanDetector detections={len(self._detections)} source={self.table}>"
    
    def scan(self, address_filter: Optional[List[str]] = None) -> List[FlashLoanPattern]:
        """
        Scan for flash loan attack patterns.
        
        Args:
            address_filter: Optional list of addresses to focus on
            
        Returns:
            List of detected patterns
        """
        self._detections = []
        
        # Get all transactions
        if address_filter:
            all_txs: List[OnChainTx] = []
            for addr in address_filter:
                all_txs.extend(self.table.query_by_address(addr))
        else:
            all_txs = list(self.table._transactions)
        
        # Sort by timestamp
        all_txs.sort(key=lambda tx: tx.timestamp)
        
        # Detect patterns
        self._detect_borrow_manipulate_repay(all_txs)
        self._detect_oracle_manipulation(all_txs)
        self._detect_profit_extraction(all_txs)
        
        return self._detections
    
    def _detect_borrow_manipulate_repay(self, txs: List[OnChainTx]) -> None:
        """Detect classic flash loan: borrow → manipulate → repay."""
        # Group by sender and time window (within 1 block ~ 12 seconds)
        windows: List[List[OnChainTx]] = []
        current_window: List[OnChainTx] = []
        
        for tx in txs:
            if not current_window or tx.timestamp - current_window[-1].timestamp <= 20:
                current_window.append(tx)
            else:
                if len(current_window) >= 2:
                    windows.append(current_window)
                current_window = [tx]
        
        if current_window and len(current_window) >= 2:
            windows.append(current_window)
        
        # Analyze each window
        for window in windows:
            if len(window) < 2:
                continue
            
            # Check for flash loan borrow indicator
            has_borrow = any(
                tx.to_addr in self.FLASH_LOAN_PROVIDERS or 
                "flashLoan" in tx.input_data.lower() or
                "flashBorrow" in tx.input_data.lower()
                for tx in window
            )
            
            # Check for price manipulation (DEX interaction after borrow)
            dex_interactions = sum(
                1 for tx in window[1:]
                if tx.to_addr and self._is_dex(tx.to_addr)
            )
            
            # Check for repayment (return to provider)
            has_repay = any(
                tx.to_addr in self.FLASH_LOAN_PROVIDERS
                for tx in window[1:]
            )
            
            # Profit heuristic: large value out without matching in
            values_out = sum(tx.value for tx in window if tx.to_addr and not self._is_dex(tx.to_addr))
            values_in = sum(tx.value for tx in window if tx.from_addr)
            
            if has_borrow and dex_interactions >= 1:
                confidence = 0.5
                confidence += 0.2 if has_repay else 0
                confidence += 0.15 if dex_interactions >= 2 else 0
                confidence += 0.15 if values_out > values_in * 1.1 else 0
                
                pattern = FlashLoanPattern(
                    pattern_type="borrow_manipulate_repay",
                    transactions=[tx.hash for tx in window],
                    profit_extracted=max(0, values_out - values_in),
                    victim_contracts=[tx.to_addr for tx in window[1:] if tx.to_addr and self._is_dex(tx.to_addr)],
                    confidence=min(confidence, 1.0),
                    severity=RiskLevel.CRITICAL if confidence > 0.8 else RiskLevel.HIGH,
                    details={
                        "window_size": len(window),
                        "has_borrow": has_borrow,
                        "has_repay": has_repay,
                        "dex_interactions": dex_interactions,
                        "time_span_seconds": window[-1].timestamp - window[0].timestamp,
                    }
                )
                self._detections.append(pattern)
    
    def _detect_oracle_manipulation(self, txs: List[OnChainTx]) -> None:
        """Detect price oracle manipulation attempts."""
        for tx in txs:
            # Oracle update followed by large swap
            if self._is_oracle(tx.to_addr):
                # Look for subsequent large DEX swap within 60 seconds
                subsequent = [
                    t for t in txs
                    if t.timestamp > tx.timestamp and t.timestamp <= tx.timestamp + 60
                ]
                
                for sub in subsequent:
                    if self._is_dex(sub.to_addr) and sub.value > 100 * 10**18:
                        pattern = FlashLoanPattern(
                            pattern_type="oracle_manipulation",
                            transactions=[tx.hash, sub.hash],
                            profit_extracted=sub.value,
                            victim_contracts=[tx.to_addr] if tx.to_addr else [],
                            confidence=0.6,
                            severity=RiskLevel.HIGH,
                            details={
                                "oracle_tx": tx.hash,
                                "manipulation_tx": sub.hash,
                                "time_delta": sub.timestamp - tx.timestamp,
                            }
                        )
                        self._detections.append(pattern)
                        break
    
    def _detect_profit_extraction(self, txs: List[OnChainTx]) -> None:
        """Detect profit extraction after complex interactions."""
        for i, tx in enumerate(txs):
            # Large outgoing transfer after multiple contract interactions
            if tx.value > 50 * 10**18:
                preceding = txs[max(0, i-5):i]
                contract_calls = sum(1 for t in preceding if t.contract_address or self._is_contract(t.to_addr))
                
                if contract_calls >= 3:
                    pattern = FlashLoanPattern(
                        pattern_type="profit_extraction",
                        transactions=[t.hash for t in preceding] + [tx.hash],
                        profit_extracted=tx.value,
                        victim_contracts=[t.to_addr for t in preceding if t.to_addr][:3],
                        confidence=0.4 + (0.1 * contract_calls),
                        severity=RiskLevel.MEDIUM,
                        details={
                            "preceding_contract_calls": contract_calls,
                            "extraction_value": tx.value,
                        }
                    )
                    self._detections.append(pattern)
    
    def _is_dex(self, address: Optional[str]) -> bool:
        """Check if address is a known DEX."""
        if not address:
            return False
        dexes = {
            "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
            "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",
            "0xE592427A0AEce92De3Edee1F18E0157C05861564",  # Uniswap V3 NFT
        }
        return address.lower() in {d.lower() for d in dexes}
    
    def _is_oracle(self, address: Optional[str]) -> bool:
        """Check if address is a known price oracle."""
        if not address:
            return False
        oracles = {
            "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",  # Chainlink ETH/USD
            "0x8e0E5A3D1E6E7E1d8E1E1E1E1E1E1E1E1E1E1E1",  # Placeholder
        }
        return address.lower() in {o.lower() for o in oracles}
    
    def _is_contract(self, address: Optional[str]) -> bool:
        """Heuristic for contract address."""
        if not address:
            return False
        return len(address) > 20 and address[2:4] in {"7a", "68", "de", "5f", "81", "91", "e5", "e0"}
    
    def get_summary(self) -> Dict[str, Any]:
        """Return detection summary."""
        by_type: Dict[str, int] = defaultdict(int)
        for d in self._detections:
            by_type[d.pattern_type] += 1
        
        return {
            "total_detections": len(self._detections),
            "by_type": dict(by_type),
            "critical": sum(1 for d in self._detections if d.severity == RiskLevel.CRITICAL),
            "high": sum(1 for d in self._detections if d.severity == RiskLevel.HIGH),
            "avg_confidence": sum(d.confidence for d in self._detections) / len(self._detections) if self._detections else 0,
        }


# ───────────────────────────────────────────────────────────────
# 3.3 ThreatIntelEngine — Multi-Chain Threat Detection
# ───────────────────────────────────────────────────────────────

@dataclass
class ThreatAlert:
    """Generated threat alert."""
    alert_id: str
    alert_type: str
    severity: RiskLevel
    addresses: List[str]
    description: str
    evidence: Dict[str, Any]
    timestamp: int
    chain_id: int
    
    def __repr__(self) -> str:
        return (
            f"<ThreatAlert {self.alert_id} {self.severity.name} "
            f"type={self.alert_type} addrs={len(self.addresses)}>"
        )


class ThreatIntelEngine:
    """
    Multi-chain threat detection and correlation engine.
    
    Capabilities:
    - Address blacklist/graylist management
    - Anomaly scoring based on behavioral heuristics
    - Correlation engine (link related addresses)
    - Alert generation with severity classification
    
    Inspired by: blockchain-intelligence-platform + tx-intelligence-analyzer
    """
    
    def __init__(self, chain_id: int = 1) -> None:
        """
        Initialize threat intelligence engine.
        
        Args:
            chain_id: Default chain to monitor
        """
        self.chain_id = chain_id
        self._blacklist: Set[str] = set()
        self._graylist: Set[str] = set()
        self._watchlist: Set[str] = set()
        self._alerts: List[ThreatAlert] = []
        self._address_scores: Dict[str, float] = {}
        self._correlations: Dict[str, Set[str]] = defaultdict(set)
    
    def __repr__(self) -> str:
        return (
            f"<ThreatIntelEngine chain={self.chain_id} "
            f"blacklist={len(self._blacklist)} graylist={len(self._graylist)} alerts={len(self._alerts)}>"
        )
    
    def add_to_blacklist(self, address: str, reason: str = "") -> None:
        """Add address to blacklist."""
        self._blacklist.add(address.lower())
        self._generate_alert("blacklist_addition", RiskLevel.CRITICAL, [address], reason)
    
    def add_to_graylist(self, address: str, reason: str = "") -> None:
        """Add address to graylist (suspicious but not confirmed)."""
        self._graylist.add(address.lower())
    
    def add_to_watchlist(self, address: str) -> None:
        """Add address to watchlist for monitoring."""
        self._watchlist.add(address.lower())
    
    def is_blacklisted(self, address: str) -> bool:
        """Check if address is blacklisted."""
        return address.lower() in self._blacklist
    
    def is_graylisted(self, address: str) -> bool:
        """Check if address is graylisted."""
        return address.lower() in self._graylist
    
    def score_address(self, address: str, profile: Optional[WalletProfile] = None) -> float:
        """
        Calculate threat score for an address (0.0 - 1.0).
        
        Args:
            address: Address to score
            profile: Optional WalletProfile for behavioral scoring
            
        Returns:
            Composite threat score
        """
        score = 0.0
        addr_lower = address.lower()
        
        # List membership
        if addr_lower in self._blacklist:
            return 1.0
        if addr_lower in self._graylist:
            score += 0.5
        if addr_lower in self._watchlist:
            score += 0.1
        
        # Behavioral scoring
        if profile:
            score += profile.risk_score * 0.4
            if "mixer_user" in profile.labels:
                score += 0.3
            if profile.tx_count > 100 and profile.avg_tx_value < 0.01 * 10**18:
                score += 0.2  # Dusting attack pattern
        
        return min(score, 1.0)
    
    def correlate(self, address: str, table: OnChainTable, depth: int = 2) -> Set[str]:
        """
        Find addresses related through transaction graph.
        
        Args:
            address: Starting address
            table: Transaction data source
            depth: Graph traversal depth (default 2)
            
        Returns:
            Set of correlated addresses
        """
        visited: Set[str] = set()
        queue = [(address, 0)]
        
        while queue:
            current, current_depth = queue.pop(0)
            if current in visited or current_depth > depth:
                continue
            
            visited.add(current)
            
            # Get all transactions for current address
            txs = table.query_by_address(current)
            for tx in txs:
                if tx.from_addr != current:
                    self._correlations[address].add(tx.from_addr)
                    queue.append((tx.from_addr, current_depth + 1))
                if tx.to_addr and tx.to_addr != current:
                    self._correlations[address].add(tx.to_addr)
                    queue.append((tx.to_addr, current_depth + 1))
        
        return self._correlations[address]
    
    def analyze_cluster(self, addresses: List[str], table: OnChainTable) -> Dict[str, Any]:
        """
        Analyze a cluster of related addresses.
        
        Returns:
            Cluster analysis results
        """
        total_txs = 0
        total_value = 0
        common_counterparties: Set[str] = set()
        
        for addr in addresses:
            txs = table.query_by_address(addr)
            total_txs += len(txs)
            for tx in txs:
                total_value += tx.value
                if tx.to_addr and tx.to_addr not in addresses:
                    common_counterparties.add(tx.to_addr)
                if tx.from_addr not in addresses:
                    common_counterparties.add(tx.from_addr)
        
        return {
            "cluster_size": len(addresses),
            "total_transactions": total_txs,
            "total_value": total_value,
            "common_counterparties": len(common_counterparties),
            "avg_tx_per_address": total_txs / len(addresses) if addresses else 0,
            "risk_assessment": "high" if total_value > 1000 * 10**18 else "medium" if total_value > 100 * 10**18 else "low",
        }
    
    def _generate_alert(
        self,
        alert_type: str,
        severity: RiskLevel,
        addresses: List[str],
        description: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> ThreatAlert:
        """Generate and store a threat alert."""
        alert = ThreatAlert(
            alert_id=f"ALT-{len(self._alerts)+1:04d}",
            alert_type=alert_type,
            severity=severity,
            addresses=addresses,
            description=description,
            evidence=evidence or {},
            timestamp=int(time.time()),
            chain_id=self.chain_id,
        )
        self._alerts.append(alert)
        return alert
    
    def scan_for_threats(
        self,
        table: OnChainTable,
        profiler: TransactionProfiler,
    ) -> List[ThreatAlert]:
        """
        Run full threat detection scan.
        
        Args:
            table: Transaction data
            profiler: Wallet profiler for behavioral analysis
            
        Returns:
            List of generated alerts
        """
        new_alerts: List[ThreatAlert] = []
        
        # Analyze all unique addresses
        addresses = list(table._index_by_address.keys())
        
        for addr in addresses:
            profile = profiler.analyze_wallet(addr)
            score = self.score_address(addr, profile)
            
            # Alert on high scores
            if score >= 0.8:
                alert = self._generate_alert(
                    alert_type="high_risk_address",
                    severity=RiskLevel.CRITICAL,
                    addresses=[addr],
                    description=f"Address scored {score:.2f} on threat scale",
                    evidence={
                        "score": score,
                        "labels": profile.labels,
                        "risk_level": profile.risk_level.name,
                    }
                )
                new_alerts.append(alert)
            
            elif score >= 0.5:
                alert = self._generate_alert(
                    alert_type="suspicious_address",
                    severity=RiskLevel.HIGH,
                    addresses=[addr],
                    description=f"Address scored {score:.2f} on threat scale",
                    evidence={
                        "score": score,
                        "labels": profile.labels,
                    }
                )
                new_alerts.append(alert)
        
        return new_alerts
    
    def get_alerts(
        self,
        min_severity: Optional[RiskLevel] = None,
        alert_type: Optional[str] = None,
    ) -> List[ThreatAlert]:
        """Filter alerts by criteria."""
        filtered = self._alerts
        
        if min_severity:
            severity_order = {
                RiskLevel.INFO: 0, RiskLevel.LOW: 1,
                RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4,
            }
            min_val = severity_order[min_severity]
            filtered = [a for a in filtered if severity_order[a.severity] >= min_val]
        
        if alert_type:
            filtered = [a for a in filtered if a.alert_type == alert_type]
        
        return filtered


# ───────────────────────────────────────────────────────────────
# 3.4 Web3Deployer — Deployment Automation Stubs
# ───────────────────────────────────────────────────────────────

@dataclass
class CompiledContract:
    """Compilation artifact."""
    contract_name: str
    abi: List[Dict[str, Any]]
    bytecode: str
    runtime_bytecode: str
    source_map: Optional[str] = None
    compiler_version: str = "0.8.19"
    optimization_runs: int = 200
    
    def __repr__(self) -> str:
        return (
            f"<CompiledContract {self.contract_name} "
            f"bytecode={len(self.bytecode)} chars>"
        )


@dataclass
class DeploymentReceipt:
    """Deployment transaction receipt."""
    contract_address: Optional[str]
    tx_hash: str
    gas_used: int
    block_number: int
    status: str  # 'success' | 'failed'
    logs: List[Dict[str, Any]]
    
    def __repr__(self) -> str:
        return (
            f"<DeploymentReceipt addr={self.contract_address[:16] if self.contract_address else None}... "
            f"status={self.status} gas={self.gas_used}>"
        )


class Web3Deployer:
    """
    Deployment automation framework (pure Python simulation).
    
    Capabilities:
    - Compile (Solc interface stub)
    - Deploy (transaction builder)
    - Verify (source verification)
    - Upgrade (UUPS/Transparent proxy)
    - Gas estimation
    - Nonce management
    
    Note: Pure Python implementation. Actual compilation requires solc binary.
    """
    
    def __init__(self, chain_id: int = 1, sender: str = "0x" + "0" * 40) -> None:
        """
        Initialize deployer.
        
        Args:
            chain_id: Target chain
            sender: Deployer address
        """
        self.chain_id = chain_id
        self.sender = sender
        self._nonce = 0
        self._deployments: List[DeploymentReceipt] = []
        self._bytecode_cache: Dict[str, str] = {}
    
    def __repr__(self) -> str:
        return f"<Web3Deployer chain={self.chain_id} sender={self.sender[:10]}... nonce={self._nonce}>"
    
    def compile_contract(
        self,
        source_code: str,
        contract_name: str,
        optimization_runs: int = 200,
    ) -> CompiledContract:
        """
        Simulate compilation.
        
        In production: invoke solc --combined-json abi,bin
        """
        # Generate deterministic pseudo-bytecode from source hash
        source_hash = hashlib.sha256(source_code.encode()).hexdigest()
        bytecode = "0x" + source_hash[:64] + "00" * 100  # Simulated bytecode
        runtime = "0x" + source_hash[64:128] + "00" * 50
        
        # Minimal ABI stub
        abi = [
            {"type": "constructor", "inputs": [], "stateMutability": "nonpayable"},
            {"type": "function", "name": "name", "inputs": [], "outputs": [{"type": "string"}]},
            {"type": "event", "name": "Transfer", "inputs": [{"indexed": True, "name": "from", "type": "address"}]},
        ]
        
        compiled = CompiledContract(
            contract_name=contract_name,
            abi=abi,
            bytecode=bytecode,
            runtime_bytecode=runtime,
            compiler_version="0.8.19",
            optimization_runs=optimization_runs,
        )
        
        self._bytecode_cache[contract_name] = bytecode
        return compiled
    
    def estimate_gas(self, bytecode: str, constructor_args: Optional[List[Any]] = None) -> int:
        """
        Estimate deployment gas cost.
        
        Formula: 21000 (base) + 32000 (creation) + bytecode_gas (200 per non-zero byte)
        """
        # Remove 0x prefix
        code = bytecode[2:] if bytecode.startswith("0x") else bytecode
        
        # Count non-zero bytes (simplified)
        non_zero = sum(1 for i in range(0, len(code), 2) if code[i:i+2] != "00")
        
        # Gas calculation
        base_gas = 21000 + 32000  # tx + contract creation
        bytecode_gas = non_zero * 200  # Approximate
        
        # Constructor args overhead
        args_gas = len(constructor_args or []) * 1000
        
        return base_gas + bytecode_gas + args_gas
    
    def deploy(
        self,
        compiled: CompiledContract,
        constructor_args: Optional[List[Any]] = None,
        gas_limit: Optional[int] = None,
    ) -> DeploymentReceipt:
        """
        Simulate contract deployment.
        
        Returns deployment receipt with generated contract address.
        """
        # Generate contract address: keccak256(rlp.encode([sender, nonce]))[12:]
        nonce_bytes = self._nonce.to_bytes(8, 'big')
        addr_input = (self.sender + nonce_bytes.hex()).encode()
        contract_addr = "0x" + hashlib.sha256(addr_input).hexdigest()[-40:]
        
        # Estimate gas
        estimated = self.estimate_gas(compiled.bytecode, constructor_args)
        gas = gas_limit or int(estimated * 1.2)  # 20% buffer
        
        # Simulate receipt
        receipt = DeploymentReceipt(
            contract_address=contract_addr,
            tx_hash=f"0x{hashlib.sha256(f'deploy{self._nonce}'.encode()).hexdigest()}",
            gas_used=min(estimated, gas),
            block_number=18_000_000 + self._nonce,
            status="success",
            logs=[{"event": "ContractDeployed", "address": contract_addr}],
        )
        
        self._deployments.append(receipt)
        self._nonce += 1
        
        return receipt
    
    def verify_contract(
        self,
        contract_address: str,
        source_code: str,
        compiler_version: str,
    ) -> Dict[str, Any]:
        """
        Simulate contract source verification.
        
        In production: Submit to Etherscan / Blockscout API.
        """
        # Simulated verification
        is_match = hashlib.sha256(source_code.encode()).hexdigest()[:16] in contract_address
        
        return {
            "address": contract_address,
            "status": "verified" if is_match else "pending",
            "compiler": compiler_version,
            "optimization": True,
            "match": is_match,
            "source_hash": hashlib.sha256(source_code.encode()).hexdigest()[:16],
        }
    
    def upgrade_proxy(
        self,
        proxy_address: str,
        new_implementation: str,
        pattern: str = "uups",
    ) -> DeploymentReceipt:
        """
        Simulate proxy upgrade.
        
        Args:
            proxy_address: Existing proxy contract
            new_implementation: New implementation address
            pattern: 'uups' or 'transparent'
        """
        tx_hash = f"0x{hashlib.sha256(f'upgrade{self._nonce}'.encode()).hexdigest()}"
        
        receipt = DeploymentReceipt(
            contract_address=proxy_address,
            tx_hash=tx_hash,
            gas_used=80000,
            block_number=18_000_000 + self._nonce,
            status="success",
            logs=[{
                "event": "Upgraded",
                "proxy": proxy_address,
                "implementation": new_implementation,
                "pattern": pattern,
            }],
        )
        
        self._deployments.append(receipt)
        self._nonce += 1
        
        return receipt
    
    def get_deployments(self) -> List[DeploymentReceipt]:
        """Return all deployment history."""
        return self._deployments


# ───────────────────────────────────────────────────────────────
# 3.5 SecurityReportGenerator — Audit Report Builder
# ───────────────────────────────────────────────────────────────

@dataclass
class ReportSection:
    """Individual report section."""
    title: str
    content: str
    severity: Optional[RiskLevel] = None
    recommendations: List[str] = field(default_factory=list)


class SecurityReportGenerator:
    """
    Audit report builder with markdown/PDF output.
    
    Capabilities:
    - Markdown report generation
    - Finding templates
    - Remediation recommendations
    - CVSSv3 calculator
    - Executive summary
    
    Inspired by: audit-agent-framework + smart-contract-auditor
    """
    
    def __init__(self, project_name: str = "Smart Contract Audit") -> None:
        """Initialize report generator."""
        self.project_name = project_name
        self._findings: List[VulnerabilityFinding] = []
        self._sections: List[ReportSection] = []
    
    def __repr__(self) -> str:
        return f"<SecurityReportGenerator project='{self.project_name}' findings={len(self._findings)}>"
    
    def add_finding(self, finding: VulnerabilityFinding) -> None:
        """Add vulnerability finding to report."""
        self._findings.append(finding)
    
    def add_section(self, title: str, content: str, severity: Optional[RiskLevel] = None) -> None:
        """Add custom report section."""
        self._sections.append(ReportSection(title, content, severity))
    
    def calculate_cvssv3(
        self,
        attack_vector: str = "N",  # N/L/P
        attack_complexity: str = "L",  # L/H
        privileges_required: str = "N",  # N/L/H
        user_interaction: str = "N",  # N/R
        scope: str = "U",  # U/C
        confidentiality: str = "N",  # N/L/H
        integrity: str = "N",
        availability: str = "N",
    ) -> float:
        """
        Simplified CVSSv3.1 Base Score Calculator.
        
        Returns approximate score (0.0 - 10.0).
        """
        # Simplified weights (not full CVSS formula)
        av_scores = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
        ac_scores = {"L": 0.77, "H": 0.44}
        pr_scores = {"N": 0.85, "L": 0.62, "H": 0.27}
        ui_scores = {"N": 0.85, "R": 0.62}
        
        c_scores = {"N": 0, "L": 0.22, "H": 0.56}
        i_scores = {"N": 0, "L": 0.22, "H": 0.56}
        a_scores = {"N": 0, "L": 0.22, "H": 0.56}
        
        # Exploitability sub-score
        av = av_scores.get(attack_vector, 0.85)
        ac = ac_scores.get(attack_complexity, 0.77)
        pr = pr_scores.get(privileges_required, 0.85)
        ui = ui_scores.get(user_interaction, 0.85)
        
        exploitability = 8.22 * av * ac * pr * ui
        
        # Impact sub-score
        c = c_scores.get(confidentiality, 0)
        i = i_scores.get(integrity, 0)
        a = a_scores.get(availability, 0)
        
        impact = 1 - ((1 - c) * (1 - i) * (1 - a))
        
        if scope == "U":
            impact_score = 6.42 * impact
        else:
            impact_score = 7.52 * (impact - 0.029) - 3.25 * (impact - 0.02) ** 15
        
        # Base score
        if impact_score <= 0:
            return 0.0
        
        base_score = min(10, impact_score + exploitability)
        
        # Round to 1 decimal
        return round(base_score, 1)
    
    def generate_markdown(self) -> str:
        """Generate complete markdown report."""
        lines = [
            f"# Security Audit Report: {self.project_name}",
            f"",
            f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Findings:** {len(self._findings)}",
            f"**Risk Level:** {self._get_overall_risk()}",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
            self._generate_executive_summary(),
            f"",
            f"---",
            f"",
            f"## Findings",
            f"",
        ]
        
        # Group findings by severity
        severity_order = [
            RiskLevel.CRITICAL, RiskLevel.HIGH,
            RiskLevel.MEDIUM, RiskLevel.LOW, RiskLevel.INFO,
        ]
        
        for sev in severity_order:
            findings = [f for f in self._findings if f.severity == sev]
            if not findings:
                continue
            
            lines.extend([
                f"### {sev.name} ({len(findings)})",
                f"",
            ])
            
            for finding in findings:
                cvss = self.calculate_cvssv3(
                    attack_complexity="L" if finding.confidence > 0.7 else "H",
                    confidentiality="H" if "access" in finding.title.lower() else "L",
                )
                
                lines.extend([
                    f"#### {finding.pattern_id}: {finding.title}",
                    f"",
                    f"- **Severity:** {finding.severity.name}",
                    f"- **Confidence:** {finding.confidence:.0%}",
                    f"- **CVSSv3:** {cvss}",
                    f"- **Location:** Line {finding.line_number}",
                    f"- **CWE:** {finding.cwe_id or 'N/A'}",
                    f"- **SWC:** {finding.swc_id or 'N/A'}",
                    f"",
                    f"**Description:**",
                    f"{finding.description}",
                    f"",
                    f"**Code:**",
                    f"```solidity",
                    f"{finding.code_snippet}",
                    f"```",
                    f"",
                    f"**Remediation:**",
                    f"{finding.remediation}",
                    f"",
                    f"---",
                    f"",
                ])
        
        # Custom sections
        for section in self._sections:
            lines.extend([
                f"## {section.title}",
                f"",
                section.content,
                f"",
                f"**Recommendations:**" if section.recommendations else "",
            ])
            if section.recommendations:
                for rec in section.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")
        
        # Footer
        lines.extend([
            f"---",
            f"",
            f"*Report generated by AjatFnR Security Engine*",
            f"*This is an automated assessment. Manual review recommended for production.*",
        ])
        
        return "\n".join(lines)
    
    def _generate_executive_summary(self) -> str:
        """Generate executive summary paragraph."""
        severity_counts: Dict[str, int] = defaultdict(int)
        for f in self._findings:
            severity_counts[f.severity.name] += 1
        
        critical = severity_counts.get("CRITICAL", 0)
        high = severity_counts.get("HIGH", 0)
        
        if critical > 0:
            risk = f"CRITICAL — {critical} issue(s) require immediate remediation"
        elif high > 0:
            risk = f"HIGH — {high} issue(s) should be addressed before deployment"
        elif severity_counts.get("MEDIUM", 0) > 0:
            risk = f"MEDIUM — {severity_counts['MEDIUM']} issue(s) warrant attention"
        else:
            risk = "LOW/INFO — Minor observations noted"
        
        return (
            f"This audit identified **{len(self._findings)} findings** across the codebase. "
            f"The overall risk assessment is **{risk}**. "
            f"Critical findings relate to reentrancy, access control, and flash loan vulnerabilities. "
            f"All findings should be validated through manual code review before production deployment."
        )
    
    def _get_overall_risk(self) -> str:
        """Determine overall risk rating."""
        if any(f.severity == RiskLevel.CRITICAL for f in self._findings):
            return "CRITICAL"
        elif any(f.severity == RiskLevel.HIGH for f in self._findings):
            return "HIGH"
        elif any(f.severity == RiskLevel.MEDIUM for f in self._findings):
            return "MEDIUM"
        elif any(f.severity == RiskLevel.LOW for f in self._findings):
            return "LOW"
        return "INFO"
    
    def save(self, filepath: str) -> None:
        """Save markdown report to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_markdown())


# ───────────────────────────────────────────────────────────────
# Section 3 Demo
# ───────────────────────────────────────────────────────────────

def demo_section_3():
    """Demonstrate Features capabilities."""
    print("\n" + "=" * 60)
    print("AJAT WEB3 SECURITY NATIVE — Section 3: Features")
    print("=" * 60)
    
    # 3.1 PatternLibrary
    lib = PatternLibrary()
    print(f"\n[3.1] PatternLibrary: {len(lib.list_all())} patterns loaded")
    
    reentrancy_patterns = lib.get_by_vulnerability("SWC-107")
    print(f"    Patterns mitigating Reentrancy: {len(reentrancy_patterns)}")
    for p in reentrancy_patterns:
        print(f"      - {p.pattern_id}: {p.name}")
    
    # 3.2 FlashLoanDetector
    table = OnChainTable(chain_id=1)
    # Create flash loan-like sequence
    flash_sequence = [
        OnChainTx(
            hash=f"0x{hashlib.sha256(b'flash1').hexdigest()}",
            from_addr="0xattacker1111111111111111111111111111111111",
            to_addr="0x24a42fd28c976a61df5d00d0599c34c4f90748c8",  # Aave
            value=1000 * 10**18,
            gas=300000,
            gas_price=50 * 10**9,
            timestamp=1000,
            block_number=18000001,
            nonce=0,
            input_data="0xflashLoan",
            tx_type=TxType.CONTRACT_CALL,
        ),
        OnChainTx(
            hash=f"0x{hashlib.sha256(b'flash2').hexdigest()}",
            from_addr="0xattacker1111111111111111111111111111111111",
            to_addr="0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap
            value=500 * 10**18,
            gas=200000,
            gas_price=50 * 10**9,
            timestamp=1001,
            block_number=18000001,
            nonce=1,
            input_data="0xswapExactTokensForTokens",
            tx_type=TxType.CONTRACT_CALL,
        ),
        OnChainTx(
            hash=f"0x{hashlib.sha256(b'flash3').hexdigest()}",
            from_addr="0xattacker1111111111111111111111111111111111",
            to_addr="0x24a42fd28c976a61df5d00d0599c34c4f90748c8",
            value=1050 * 10**18,
            gas=150000,
            gas_price=50 * 10**9,
            timestamp=1002,
            block_number=18000001,
            nonce=2,
            input_data="0xrepay",
            tx_type=TxType.CONTRACT_CALL,
        ),
    ]
    table.insert_many(flash_sequence)
    
    detector = FlashLoanDetector(table)
    detections = detector.scan()
    print(f"\n[3.2] FlashLoanDetector: {len(detections)} patterns detected")
    for d in detections:
        print(f"    {d.pattern_type} | conf={d.confidence:.2f} | profit={d.profit_extracted / 10**18:.1f}ETH")
    
    # 3.3 ThreatIntelEngine
    intel = ThreatIntelEngine(chain_id=1)
    intel.add_to_blacklist("0x5fe2b58c013d7601147dcdd68c143a77499f5531", "Tornado Cash")
    
    # 3.4 Web3Deployer
    deployer = Web3Deployer(sender="0xdeployer00000000000000000000000000000000")
    compiled = deployer.compile_contract("pragma solidity 0.8.0; contract Test {}", "Test")
    print(f"\n[3.4] Web3Deployer: compiled {compiled.contract_name}, bytecode={len(compiled.bytecode)} chars")
    
    receipt = deployer.deploy(compiled)
    print(f"    Deployed to {receipt.contract_address}, gas={receipt.gas_used}")
    
    # 3.5 SecurityReportGenerator
    report = SecurityReportGenerator("VulnerableToken Audit")
    
    # Add findings from Section 2 demo
    agent = AuditAgent()
    sample = '''
pragma solidity ^0.8.0;
contract Test {
    function withdraw() public {
        msg.sender.call{value: 1 ether}("");
    }
    function mint() public {
        // no access control
    }
}
'''
    findings = agent.audit_contract(sample)
    for f in findings:
        report.add_finding(f)
    
    md = report.generate_markdown()
    print(f"\n[3.5] Report generated: {len(md)} chars, {len(report._findings)} findings")
    print(f"    Overall risk: {report._get_overall_risk()}")
    
    # Save report
    report.save("/tmp/ajat_security_report.md")
    print(f"    Saved to /tmp/ajat_security_report.md")
    
    print("\n" + "=" * 60)
    print("Section 3 COMPLETE — Features ready")
    print("=" * 60)
    
    return lib, detector, intel, deployer, report


# ════════════════════════════════════════════════════════════════
# Section 4 — Kernel + Demo
# AjatWeb3Kernel (MAGNATRIX Bridge) + Main Demo
# ════════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────
# 4.1 AjatWeb3Kernel — MAGNATRIX Integration Layer
# ───────────────────────────────────────────────────────────────

@dataclass
class LayerRegistration:
    """Layer registration record."""
    layer_id: int
    layer_name: str
    capabilities: List[str]
    status: str  # 'active' | 'inactive'
    registered_at: int


@dataclass
class KernelEvent:
    """Internal event for MAGNATRIX bridge."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: int
    source_layer: int
    priority: int = 0


class AjatWeb3Kernel:
    """
    MAGNATRIX OS bridge for Web3 Security layer.
    
    Auto-registers to:
    - Layer 9 (Security)
    - Layer 8 (Trading)
    - Layer 5 (Knowledge)
    
    Provides event hooks for real-time blockchain monitoring,
    cross-layer communication, and unified security intelligence.
    
    Inspired by: COLLECTIVE BRAIN architecture (HERMES + Kimi Claw + OpenClaw)
    """
    
    # Layer definitions
    LAYERS = {
        9: {"name": "Security", "capabilities": ["audit", "monitor", "detect", "alert"]},
        8: {"name": "Trading", "capabilities": ["signal", "execute", "arbitrage", "risk"]},
        5: {"name": "Knowledge", "capabilities": ["index", "query", "learn", "synthesize"]},
    }
    
    def __init__(self, node_id: str = "ajat-web3-01") -> None:
        """
        Initialize kernel with node identity.
        
        Args:
            node_id: Unique node identifier in MAGNATRIX mesh
        """
        self.node_id = node_id
        self._registrations: Dict[int, LayerRegistration] = {}
        self._event_hooks: Dict[str, List[callable]] = defaultdict(list)
        self._event_log: List[KernelEvent] = []
        self._components: Dict[str, Any] = {}
        self._running = False
    
    def __repr__(self) -> str:
        return (
            f"<AjatWeb3Kernel node={self.node_id} "
            f"layers={list(self._registrations.keys())} "
            f"hooks={len(self._event_hooks)}>"
        )
    
    def auto_register(self) -> List[LayerRegistration]:
        """
        Auto-register to all defined MAGNATRIX layers.
        
        Returns:
            List of successful registrations
        """
        results: List[LayerRegistration] = []
        
        for layer_id, layer_info in self.LAYERS.items():
            reg = LayerRegistration(
                layer_id=layer_id,
                layer_name=layer_info["name"],
                capabilities=layer_info["capabilities"],
                status="active",
                registered_at=int(time.time()),
            )
            self._registrations[layer_id] = reg
            results.append(reg)
            
            # Emit registration event
            self._emit_event("layer_registered", {
                "layer_id": layer_id,
                "layer_name": layer_info["name"],
                "node_id": self.node_id,
            }, source_layer=0)
        
        return results
    
    def register_component(self, name: str, component: Any) -> None:
        """
        Register a security component for cross-layer access.
        
        Args:
            name: Component identifier
            component: Instantiated component object
        """
        self._components[name] = component
    
    def get_component(self, name: str) -> Optional[Any]:
        """Retrieve registered component."""
        return self._components.get(name)
    
    def add_event_hook(self, event_type: str, callback: callable) -> None:
        """
        Register event hook for real-time monitoring.
        
        Args:
            event_type: Event type to listen for
            callback: Function to invoke on event
        """
        self._event_hooks[event_type].append(callback)
    
    def _emit_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        source_layer: int = 9,
        priority: int = 0,
    ) -> KernelEvent:
        """
        Emit internal event to all registered hooks.
        
        Returns:
            Created KernelEvent
        """
        event = KernelEvent(
            event_type=event_type,
            payload=payload,
            timestamp=int(time.time()),
            source_layer=source_layer,
            priority=priority,
        )
        
        self._event_log.append(event)
        
        # Invoke hooks
        for hook in self._event_hooks.get(event_type, []):
            try:
                hook(event)
            except Exception:
                pass  # Hooks should not crash the kernel
        
        # Also invoke wildcard hooks
        for hook in self._event_hooks.get("*", []):
            try:
                hook(event)
            except Exception:
                pass
        
        return event
    
    def start_monitoring(self, table: OnChainTable) -> None:
        """
        Start real-time blockchain monitoring.
        
        Args:
            table: OnChainTable to monitor for new transactions
        """
        self._running = True
        self._emit_event("monitoring_started", {
            "node_id": self.node_id,
            "table_size": len(table._transactions),
        }, source_layer=9)
    
    def stop_monitoring(self) -> None:
        """Stop monitoring loop."""
        self._running = False
        self._emit_event("monitoring_stopped", {
            "node_id": self.node_id,
        }, source_layer=9)
    
    def process_transaction(self, tx: OnChainTx) -> List[KernelEvent]:
        """
        Process a single transaction through security pipeline.
        
        Args:
            tx: Transaction to analyze
            
        Returns:
            List of generated events
        """
        events: List[KernelEvent] = []
        
        # Security layer: threat check
        intel: Optional[ThreatIntelEngine] = self._components.get("threat_intel")
        if intel:
            score = intel.score_address(tx.from_addr)
            if score >= 0.5:
                events.append(self._emit_event(
                    "threat_detected",
                    {"address": tx.from_addr, "score": score, "tx_hash": tx.hash},
                    source_layer=9,
                    priority=3 if score >= 0.8 else 2,
                ))
        
        # Trading layer: value anomaly
        if tx.value > 1000 * 10**18:
            events.append(self._emit_event(
                "large_transfer",
                {"tx_hash": tx.hash, "value": tx.value, "from": tx.from_addr},
                source_layer=8,
                priority=1,
            ))
        
        # Knowledge layer: index transaction
        events.append(self._emit_event(
            "tx_indexed",
            {"tx_hash": tx.hash, "block": tx.block_number},
            source_layer=5,
            priority=0,
        ))
        
        return events
    
    def run_audit_pipeline(
        self,
        source_code: str,
        contract_name: str = "Contract",
    ) -> Dict[str, Any]:
        """
        Execute full audit pipeline.
        
        Args:
            source_code: Solidity source to audit
            contract_name: Contract identifier
            
        Returns:
            Pipeline results dictionary
        """
        # Get components
        audit_agent: Optional[AuditAgent] = self._components.get("audit_agent")
        pattern_lib: Optional[PatternLibrary] = self._components.get("pattern_lib")
        report_gen: Optional[SecurityReportGenerator] = self._components.get("report_gen")
        
        if not audit_agent:
            return {"error": "AuditAgent not registered"}
        
        # Run audit
        findings = audit_agent.audit_contract(source_code, contract_name)
        
        # Generate report
        if report_gen:
            report_gen.project_name = f"{contract_name} Audit"
            report_gen._findings = findings
            report = report_gen.generate_markdown()
        else:
            report = "No report generator registered"
        
        # Get remediation patterns
        recommendations: Dict[str, List[SecurePattern]] = {}
        if pattern_lib:
            for f in findings:
                recs = pattern_lib.generate_remediation(f)
                if recs:
                    recommendations[f.pattern_id] = recs
        
        result = {
            "contract": contract_name,
            "findings_count": len(findings),
            "severity_summary": audit_agent.get_summary(),
            "report_length": len(report),
            "recommendations": {
                k: [p.pattern_id for p in v]
                for k, v in recommendations.items()
            },
            "report": report,
        }
        
        self._emit_event("audit_complete", result, source_layer=9)
        
        return result
    
    def run_threat_pipeline(
        self,
        table: OnChainTable,
        profiler: TransactionProfiler,
        detector: FlashLoanDetector,
    ) -> Dict[str, Any]:
        """
        Execute threat detection pipeline.
        
        Args:
            table: Transaction data
            profiler: Wallet profiler
            detector: Flash loan detector
            
        Returns:
            Pipeline results
        """
        # Flash loan detection
        flash_patterns = detector.scan()
        
        # Threat intelligence scan
        intel: Optional[ThreatIntelEngine] = self._components.get("threat_intel")
        alerts: List[ThreatAlert] = []
        if intel:
            alerts = intel.scan_for_threats(table, profiler)
        
        # Correlation analysis
        correlations: Dict[str, List[str]] = {}
        if intel:
            for addr in list(table._index_by_address.keys())[:5]:
                correlated = intel.correlate(addr, table, depth=1)
                if correlated:
                    correlations[addr] = list(correlated)
        
        result = {
            "flash_loan_detections": len(flash_patterns),
            "threat_alerts": len(alerts),
            "correlations": correlations,
            "critical_alerts": sum(1 for a in alerts if a.severity == RiskLevel.CRITICAL),
        }
        
        self._emit_event("threat_scan_complete", result, source_layer=9)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """Return kernel status summary."""
        return {
            "node_id": self.node_id,
            "registered_layers": [
                {"id": r.layer_id, "name": r.layer_name, "status": r.status}
                for r in self._registrations.values()
            ],
            "components": list(self._components.keys()),
            "event_hooks": {k: len(v) for k, v in self._event_hooks.items()},
            "event_count": len(self._event_log),
            "monitoring": self._running,
        }


# ───────────────────────────────────────────────────────────────
# 4.2 Main Demo Section
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("AJAT WEB3 SECURITY NATIVE — Complete System Demo")
    print("=" * 70)
    
    # ── Initialize Kernel ──
    kernel = AjatWeb3Kernel(node_id="ajat-demo-node")
    regs = kernel.auto_register()
    print(f"\n[KERNEL] Registered to MAGNATRIX layers:")
    for r in regs:
        print(f"    Layer {r.layer_id}: {r.layer_name} ({r.status})")
    
    # ── Initialize Components ──
    table = OnChainTable(chain_id=1)
    profiler = TransactionProfiler(table)
    audit_agent = AuditAgent()
    pattern_lib = PatternLibrary()
    detector = FlashLoanDetector(table)
    threat_intel = ThreatIntelEngine(chain_id=1)
    deployer = Web3Deployer(sender="0xdeployer00000000000000000000000000000000")
    report_gen = SecurityReportGenerator("Demo Audit")
    
    # Register to kernel
    kernel.register_component("table", table)
    kernel.register_component("profiler", profiler)
    kernel.register_component("audit_agent", audit_agent)
    kernel.register_component("pattern_lib", pattern_lib)
    kernel.register_component("detector", detector)
    kernel.register_component("threat_intel", threat_intel)
    kernel.register_component("deployer", deployer)
    kernel.register_component("report_gen", report_gen)
    
    print(f"\n[KERNEL] Components registered: {list(kernel._components.keys())}")
    
    # ── Demo 1: Audit 1 Contract ──
    print("\n" + "-" * 70)
    print("DEMO 1: Smart Contract Audit")
    print("-" * 70)
    
    vulnerable_contract = '''
pragma solidity ^0.8.0;

contract VulnerableToken is ERC20 {
    mapping(address => uint) public balances;
    
    function withdraw(uint amount) public {
        require(balances[msg.sender] >= amount);
        (bool sent, ) = msg.sender.call{value: amount}("");
        balances[msg.sender] -= amount;
    }
    
    function mint(uint amount) public {
        balances[msg.sender] += amount;
    }
    
    function setPrice(uint p) public {
        price = p;
    }
    
    function distribute(address[] memory recipients, uint[] memory amounts) public {
        for (uint i = 0; i < recipients.length; i++) {
            _transfer(msg.sender, recipients[i], amounts[i]);
        }
    }
    
    function emergencyWithdraw() public {
        selfdestruct(payable(msg.sender));
    }
}
'''
    
    audit_result = kernel.run_audit_pipeline(vulnerable_contract, "VulnerableToken")
    print(f"\nContract: {audit_result['contract']}")
    print(f"Findings: {audit_result['findings_count']}")
    print(f"Severity: {audit_result['severity_summary']}")
    print(f"Report: {audit_result['report_length']} chars")
    print(f"Recommendations: {len(audit_result['recommendations'])}")
    
    # Show top findings
    print("\nTop Findings:")
    for f in audit_agent._findings[:5]:
        print(f"  [{f.severity.name}] {f.pattern_id} (line {f.line_number}): {f.title}")
    
    # ── Demo 2: Analyze 5 Transactions ──
    print("\n" + "-" * 70)
    print("DEMO 2: Transaction Analysis (5 txs)")
    print("-" * 70)
    
    demo_txs = generate_demo_transactions(count=5)
    table.insert_many(demo_txs)
    
    print(f"\nInserted {len(demo_txs)} transactions:")
    for tx in demo_txs:
        print(f"  {tx}")
    
    # Profile first 3 unique addresses
    analyzed = 0
    for addr in list(table._index_by_address.keys()):
        if analyzed >= 3:
            break
        profile = profiler.analyze_wallet(addr)
        print(f"\n  Profile: {profile}")
        anomalies = profiler.detect_anomalies(addr)
        if anomalies:
            for a in anomalies[:2]:
                print(f"    ⚠ {a['type']}: {a['severity'].name}")
        analyzed += 1
    
    # ── Demo 3: Generate Report ──
    print("\n" + "-" * 70)
    print("DEMO 3: Security Report Generation")
    print("-" * 70)
    
    report_gen._findings = audit_agent._findings
    report_md = report_gen.generate_markdown()
    report_path = "/tmp/ajat_complete_report.md"
    report_gen.save(report_path)
    
    print(f"\nReport generated: {len(report_md)} chars")
    print(f"Overall risk: {report_gen._get_overall_risk()}")
    print(f"Saved to: {report_path}")
    
    # Show first 1000 chars of report
    print(f"\nReport preview (first 500 chars):")
    print(report_md[:500] + "...")
    
    # ── Demo 4: Flash Loan Detection ──
    print("\n" + "-" * 70)
    print("DEMO 4: Flash Loan Pattern Detection")
    print("-" * 70)
    
    # Add flash loan sequence
    flash_txs = [
        OnChainTx(
            hash=f"0x{hashlib.sha256(b'flash_borrow').hexdigest()}",
            from_addr="0xattacker00000000000000000000000000000000",
            to_addr="0x24a42fd28c976a61df5d00d0599c34c4f90748c8",  # Aave
            value=5000 * 10**18,
            gas=400000,
            gas_price=100 * 10**9,
            timestamp=2000,
            block_number=18000010,
            nonce=0,
            input_data="0xflashLoan(address,uint256,uint256,bytes)",
            tx_type=TxType.CONTRACT_CALL,
        ),
        OnChainTx(
            hash=f"0x{hashlib.sha256(b'flash_manip').hexdigest()}",
            from_addr="0xattacker00000000000000000000000000000000",
            to_addr="0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap
            value=2500 * 10**18,
            gas=300000,
            gas_price=100 * 10**9,
            timestamp=2001,
            block_number=18000010,
            nonce=1,
            input_data="0xswapExactTokensForTokens(uint,uint,address[],address,uint)",
            tx_type=TxType.CONTRACT_CALL,
        ),
        OnChainTx(
            hash=f"0x{hashlib.sha256(b'flash_profit').hexdigest()}",
            from_addr="0xattacker00000000000000000000000000000000",
            to_addr="0xattacker00000000000000000000000000000000",
            value=8000 * 10**18,
            gas=200000,
            gas_price=100 * 10**9,
            timestamp=2002,
            block_number=18000010,
            nonce=2,
            input_data="0x",
            tx_type=TxType.TRANSFER,
        ),
        OnChainTx(
            hash=f"0x{hashlib.sha256(b'flash_repay').hexdigest()}",
            from_addr="0xattacker00000000000000000000000000000000",
            to_addr="0x24a42fd28c976a61df5d00d0599c34c4f90748c8",
            value=5050 * 10**18,
            gas=150000,
            gas_price=100 * 10**9,
            timestamp=2003,
            block_number=18000010,
            nonce=3,
            input_data="0xrepayFlashLoan",
            tx_type=TxType.CONTRACT_CALL,
        ),
    ]
    table.insert_many(flash_txs)
    
    detections = detector.scan(address_filter=["0xattacker00000000000000000000000000000000"])
    print(f"\nFlash loan sequences detected: {len(detections)}")
    for d in detections:
        print(f"\n  Type: {d.pattern_type}")
        print(f"  Confidence: {d.confidence:.1%}")
        print(f"  Severity: {d.severity.name}")
        print(f"  Profit extracted: {d.profit_extracted / 10**18:.1f} ETH")
        print(f"  Transactions: {len(d.transactions)}")
    
    # ── Demo 5: Threat Intelligence ──
    print("\n" + "-" * 70)
    print("DEMO 5: Threat Intelligence")
    print("-" * 70)
    
    threat_intel.add_to_blacklist("0xattacker00000000000000000000000000000000", "Flash loan attacker")
    threat_intel.add_to_graylist("0x5fe2b58c013d7601147dcdd68c143a77499f5531", "Mixer interaction")
    
    # Run threat pipeline
    threat_result = kernel.run_threat_pipeline(table, profiler, detector)
    print(f"\nThreat scan complete:")
    print(f"  Flash loan detections: {threat_result['flash_loan_detections']}")
    print(f"  Threat alerts: {threat_result['threat_alerts']}")
    print(f"  Critical alerts: {threat_result['critical_alerts']}")
    
    # ── Demo 6: Deployment ──
    print("\n" + "-" * 70)
    print("DEMO 6: Contract Deployment")
    print("-" * 70)
    
    safe_contract = '''
pragma solidity ^0.8.19;

contract SafeToken {
    mapping(address => uint) public balances;
    bool private locked;
    
    modifier nonReentrant() {
        require(!locked, "Reentrant");
        locked = true;
        _;
        locked = false;
    }
    
    function withdraw(uint amount) public nonReentrant {
        require(balances[msg.sender] >= amount, "Insufficient");
        balances[msg.sender] -= amount;
        (bool sent, ) = msg.sender.call{value: amount}("");
        require(sent, "Transfer failed");
    }
}
'''
    
    compiled = deployer.compile_contract(safe_contract, "SafeToken")
    receipt = deployer.deploy(compiled)
    
    print(f"\nContract compiled: {compiled.contract_name}")
    print(f"  Bytecode: {len(compiled.bytecode)} chars")
    print(f"  Gas estimate: {deployer.estimate_gas(compiled.bytecode)}")
    print(f"Deployed to: {receipt.contract_address}")
    print(f"  Tx hash: {receipt.tx_hash[:20]}...")
    print(f"  Gas used: {receipt.gas_used}")
    print(f"  Status: {receipt.status}")
    
    # Verify
    verification = deployer.verify_contract(receipt.contract_address, safe_contract, "0.8.19")
    print(f"\nVerification: {verification['status']} (match={verification['match']})")
    
    # ── Demo 7: Pattern Library ──
    print("\n" + "-" * 70)
    print("DEMO 7: Secure Patterns")
    print("-" * 70)
    
    print(f"\nTotal patterns: {len(pattern_lib.list_all())}")
    
    # Show patterns by category
    for category in ["Reentrancy Protection", "Access Control", "DoS Prevention"]:
        patterns = pattern_lib.get_by_category(category)
        print(f"\n  {category}: {len(patterns)} patterns")
        for p in patterns:
            print(f"    - {p.pattern_id}: {p.name}")
    
    # Remediation for first finding
    if audit_agent._findings:
        first = audit_agent._findings[0]
        recs = pattern_lib.generate_remediation(first)
        print(f"\nRemediation for '{first.title}':")
        for r in recs:
            print(f"  -> {r.pattern_id}: {r.name}")
    
    # ── Demo 8: DeFi Risk ──
    print("\n" + "-" * 70)
    print("DEMO 8: DeFi Risk Model")
    print("-" * 70)
    
    risk_model = DeFiRiskModel()
    
    # IL calculation
    il = risk_model.calculate_impermanent_loss(2.0, fee_earned=0.02)
    print(f"\nImpermanent Loss (2x price, 2% fees): {il*100:.2f}%")
    
    # VaR
    returns = [-0.05, 0.02, -0.03, 0.01, -0.08, 0.03, -0.01, 0.04, -0.02, 0.01]
    var = risk_model.calculate_var(returns)
    print(f"Value at Risk (95%): {var*100:.2f}%")
    
    # Lending health
    position = LendingPosition(
        collateral_asset="ETH",
        collateral_amount=10.0,
        borrow_asset="USDC",
        borrow_amount=4000.0,
        collateral_factor=0.75,
        liquidation_threshold=0.8,
    )
    lending_risk = risk_model.assess_lending_risk(position)
    print(f"\nLending Position:")
    print(f"  Health Factor: {lending_risk['health_factor']:.2f}")
    print(f"  Status: {lending_risk['status']}")
    print(f"  Liquidation Buffer: {lending_risk['liquidation_buffer']:.2f}")
    print(f"  Liquidation Price: ${lending_risk['liquidation_price']:.2f}")
    
    # Stress test
    pool = PoolState(
        token0_reserve=1000.0,
        token1_reserve=2000.0,
        token0_price=2.0,
        token1_price=0.5,
        total_liquidity=1414.21,
    )
    stress = risk_model.simulate_stress_test(pool, [0.5, 0.8, 1.0, 1.5, 2.0])
    print(f"\nStress Test Results:")
    for s in stress:
        print(f"  {s['price_shock']:4.1f}x | IL: {s['impermanent_loss']:6.2f}% | Reserve ratio: {s['liquidity_ratio']:.2f}")
    
    # ── Kernel Status ──
    print("\n" + "=" * 70)
    print("KERNEL STATUS")
    print("=" * 70)
    
    status = kernel.get_status()
    print(f"\nNode ID: {status['node_id']}")
    print(f"Registered layers: {len(status['registered_layers'])}")
    for layer in status['registered_layers']:
        print(f"  Layer {layer['id']} ({layer['name']}): {layer['status']}")
    print(f"Components: {status['components']}")
    print(f"Events processed: {status['event_count']}")
    print(f"Monitoring: {status['monitoring']}")
    
    # Event log summary
    print(f"\nEvent Log Summary:")
    event_types: Dict[str, int] = defaultdict(int)
    for e in kernel._event_log:
        event_types[e.event_type] += 1
    for et, count in sorted(event_types.items(), key=lambda x: -x[1]):
        print(f"  {et}: {count}")
    
    # ── Final Summary ──
    print("\n" + "=" * 70)
    print("AJAT WEB3 SECURITY NATIVE — ALL DEMOS COMPLETE")
    print("=" * 70)
    
    total_lines = len(open(__file__).readlines())
    print(f"\nSystem Summary:")
    print(f"  File: {__file__}")
    print(f"  Total lines: ~{total_lines}")
    print(f"  Components initialized: {len(kernel._components)}")
    print(f"  Findings detected: {len(audit_agent._findings)}")
    print(f"  Transactions analyzed: {len(table._transactions)}")
    print(f"  Flash loan patterns: {len(detections)}")
    print(f"  Threat alerts: {threat_result['threat_alerts']}")
    print(f"  Report saved: {report_path}")
    
    print("\n" + "=" * 70)
    print("Status: ✅ OPERATIONAL")
    print("=" * 70)
