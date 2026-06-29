"""DB Query Planner -- Query optimization, plan selection, cost estimation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class QueryPlan:
    plan_id: str = ""
    table: str = ""
    scan_type: str = ""  # full_table | index | range
    index_used: str = ""
    estimated_rows: int = 0
    estimated_cost: float = 0.0
    steps: list[str] = None
    optimal: bool = False

    def __post_init__(self):
        if self.steps is None:
            self.steps = []

class DBQueryPlanner:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._plans: list[QueryPlan] = []
        self._table_stats: dict[str, dict] = {}
        self._persist_path = self.root / "db_query_planner.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._plans = [QueryPlan(**p) for p in data.get("plans", [])]
            self._table_stats = data.get("stats", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "plans": [p.__dict__ for p in self._plans],
            "stats": self._table_stats
        }, indent=2))

    def set_stats(self, table: str, row_count: int, index_count: int, avg_row_size: int) -> None:
        self._table_stats[table] = {"rows": row_count, "indexes": index_count, "avg_size": avg_row_size}
        self._save()

    def plan(self, query_ast: dict) -> QueryPlan:
        table = query_ast.get("table", "")
        stats = self._table_stats.get(table, {"rows": 1000, "indexes": 0, "avg_size": 100})
        rows = stats["rows"]

        plan = QueryPlan(plan_id=f"plan_{len(self._plans)}", table=table)

        # Simple heuristic planner
        if query_ast.get("query_type") == "SELECT":
            conditions = query_ast.get("conditions", [])
            if conditions and stats["indexes"] > 0:
                plan.scan_type = "index"
                plan.index_used = "idx_" + conditions[0].get("field", "")
                plan.estimated_rows = max(1, rows // 10)
                plan.estimated_cost = plan.estimated_rows * stats["avg_size"] * 0.5
                plan.steps = ["Index lookup on " + plan.index_used, "Filter rows", "Return results"]
            else:
                plan.scan_type = "full_table"
                plan.estimated_rows = rows
                plan.estimated_cost = rows * stats["avg_size"]
                plan.steps = ["Full table scan", "Return results"]
        else:
            plan.scan_type = "full_table"
            plan.estimated_rows = rows
            plan.estimated_cost = rows * stats["avg_size"] * 2
            plan.steps = ["Full table scan", "Apply changes"]

        plan.optimal = plan.scan_type == "index"
        self._plans.append(plan)
        self._save()
        return plan

    def compare_plans(self, plan_a: QueryPlan, plan_b: QueryPlan) -> QueryPlan:
        return plan_a if plan_a.estimated_cost <= plan_b.estimated_cost else plan_b

    def to_dict(self) -> dict:
        return {"plan_count": len(self._plans), "tables_with_stats": len(self._table_stats)}

    def get_stats(self) -> dict:
        by_scan = {}
        for p in self._plans:
            by_scan[p.scan_type] = by_scan.get(p.scan_type, 0) + 1
        avg_cost = sum(p.estimated_cost for p in self._plans) / len(self._plans) if self._plans else 0
        return {"plans": len(self._plans), "by_scan": by_scan, "avg_cost": round(avg_cost, 2)}

__all__ = ["DBQueryPlanner", "QueryPlan"]
