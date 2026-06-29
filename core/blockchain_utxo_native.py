"""Blockchain UTXO Manager -- Unspent transaction output tracking."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class UTXO:
    utxo_id: str = ""
    tx_id: str = ""
    output_index: int = 0
    address: str = ""
    amount: float = 0.0
    spent: bool = False
    script: str = ""

class BlockchainUTXOManager:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._utxos: dict[str, UTXO] = {}
        self._spent: set[str] = set()
        self._persist_path = self.root / "blockchain_utxo.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._utxos = {k: UTXO(**v) for k, v in data.get("utxos", {}).items()}
            self._spent = set(data.get("spent", []))

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "utxos": {k: v.__dict__ for k, v in self._utxos.items()},
            "spent": list(self._spent)
        }, indent=2))

    def add(self, tx_id: str, output_index: int, address: str, amount: float, script: str = "") -> UTXO:
        utxo_id = tx_id + ":" + str(output_index)
        utxo = UTXO(utxo_id=utxo_id, tx_id=tx_id, output_index=output_index, address=address, amount=amount, script=script)
        self._utxos[utxo_id] = utxo
        self._save()
        return utxo

    def spend(self, utxo_id: str) -> bool:
        if utxo_id in self._utxos and utxo_id not in self._spent:
            self._utxos[utxo_id].spent = True
            self._spent.add(utxo_id)
            self._save()
            return True
        return False

    def get_unspent(self, address: str = "") -> list[UTXO]:
        unspent = [u for u in self._utxos.values() if not u.spent]
        if address:
            unspent = [u for u in unspent if u.address == address]
        return unspent

    def get_balance(self, address: str) -> float:
        return sum(u.amount for u in self._utxos.values() if u.address == address and not u.spent)

    def select_inputs(self, address: str, target_amount: float) -> list[UTXO]:
        unspent = self.get_unspent(address)
        unspent.sort(key=lambda u: u.amount)
        selected = []
        total = 0.0
        for u in unspent:
            if total >= target_amount:
                break
            selected.append(u)
            total += u.amount
        return selected if total >= target_amount else []

    def to_dict(self) -> dict:
        return {"utxo_count": len(self._utxos), "spent": len(self._spent)}

    def get_stats(self) -> dict:
        unspent = [u for u in self._utxos.values() if not u.spent]
        total_value = sum(u.amount for u in unspent)
        return {"total": len(self._utxos), "unspent": len(unspent), "spent": len(self._spent), "total_value": round(total_value, 8)}

__all__ = ["BlockchainUTXOManager", "UTXO"]
