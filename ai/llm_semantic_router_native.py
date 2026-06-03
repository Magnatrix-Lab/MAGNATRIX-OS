"""LLM Semantic Router — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from enum import Enum, auto

class RouteType(Enum):
    EXACT = auto()
    KEYWORD = auto()
    FALLBACK = auto()

@dataclass
class Route:
    name: str
    keywords: List[str]
    handler: Callable[[str], Any]
    route_type: RouteType = RouteType.KEYWORD

class SemanticRouter:
    def __init__(self) -> None:
        self._routes: List[Route] = []
        self._fallback: Optional[Callable[[str], Any]] = None

    def add_route(self, name: str, keywords: List[str], handler: Callable[[str], Any]) -> None:
        self._routes.append(Route(name, keywords, handler, RouteType.KEYWORD))

    def set_fallback(self, handler: Callable[[str], Any]) -> None:
        self._fallback = handler

    def route(self, text: str) -> Any:
        text_lower = text.lower()
        for route in self._routes:
            if route.route_type == RouteType.EXACT:
                if text_lower == route.keywords[0].lower():
                    return route.handler(text)
            elif route.route_type == RouteType.KEYWORD:
                for kw in route.keywords:
                    if kw.lower() in text_lower:
                        return route.handler(text)
        if self._fallback:
            return self._fallback(text)
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {"routes": len(self._routes), "has_fallback": self._fallback is not None}

def run() -> None:
    print("Semantic Router test")
    e = SemanticRouter()
    e.add_route("weather", ["weather", "forecast", "temperature"], lambda t: "Weather result for: " + t)
    e.add_route("math", ["calculate", "sum", "multiply", "divide"], lambda t: "Math result for: " + t)
    e.set_fallback(lambda t: "General response for: " + t)
    queries = ["What is the weather today?", "Calculate 5 plus 3", "Tell me a joke"]
    for q in queries:
        print("  '" + q + "' -> " + str(e.route(q)))
    print("Semantic Router test complete.")

if __name__ == "__main__":
    run()
