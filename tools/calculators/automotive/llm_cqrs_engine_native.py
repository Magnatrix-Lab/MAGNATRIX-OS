"""CQRS Engine — command/query separation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum, auto

class CommandType(Enum):
    CREATE = auto()
    UPDATE = auto()
    DELETE = auto()

class QueryType(Enum):
    GET = auto()
    LIST = auto()
    SEARCH = auto()

@dataclass
class Command:
    cmd_id: str
    cmd_type: CommandType
    target: str
    payload: Dict

@dataclass
class Query:
    query_id: str
    query_type: QueryType
    target: str
    filters: Dict

class CQRSEngine:
    def __init__(self):
        self.command_handlers: Dict[CommandType, Callable] = {}
        self.query_handlers: Dict[QueryType, Callable] = {}
        self.read_model: Dict[str, Any] = {}
        self.write_model: Dict[str, Any] = {}
        self.command_log: List[Command] = []
        self.query_log: List[Query] = []

    def register_command(self, cmd_type: CommandType, handler: Callable):
        self.command_handlers[cmd_type] = handler

    def register_query(self, query_type: QueryType, handler: Callable):
        self.query_handlers[query_type] = handler

    def execute(self, cmd: Command) -> Any:
        self.command_log.append(cmd)
        handler = self.command_handlers.get(cmd.cmd_type)
        if handler:
            return handler(cmd, self.write_model)
        return None

    def query(self, q: Query) -> Any:
        self.query_log.append(q)
        handler = self.query_handlers.get(q.query_type)
        if handler:
            return handler(q, self.read_model)
        return None

    def sync_read_model(self):
        self.read_model = dict(self.write_model)

    def stats(self) -> Dict:
        return {"commands": len(self.command_log), "queries": len(self.query_log), "write_keys": len(self.write_model), "read_keys": len(self.read_model)}

def run():
    engine = CQRSEngine()
    def create_handler(cmd, model):
        model[cmd.target] = cmd.payload
        return True
    def get_handler(query, model):
        return model.get(query.target)
    engine.register_command(CommandType.CREATE, create_handler)
    engine.register_query(QueryType.GET, get_handler)
    engine.execute(Command("c1", CommandType.CREATE, "user_1", {"name": "Alice"}))
    engine.sync_read_model()
    print(engine.query(Query("q1", QueryType.GET, "user_1", {})))
    print(engine.stats())

if __name__ == "__main__":
    run()
