"""URL Router — pattern matching, parameters, middleware, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import re

@dataclass
class Route:
    pattern: str
    handler: Callable
    methods: List[str]
    name: Optional[str] = None

class URLRouter:
    def __init__(self):
        self.routes: List[Route] = []
        self.middleware: List[Callable] = []
        self.not_found_handler: Callable = lambda **kwargs: {"status": 404, "message": "Not Found"}

    def add_route(self, pattern: str, handler: Callable, methods: List[str] = None, name: str = None):
        self.routes.append(Route(pattern, handler, methods or ["GET"], name))

    def add_middleware(self, mw: Callable):
        self.middleware.append(mw)

    def match(self, path: str, method: str = "GET") -> Optional[Tuple[Callable, Dict]]:
        for route in self.routes:
            if method not in route.methods:
                continue
            regex = route.pattern.replace("<str:", r"(?P<").replace("<int:", r"(?P<").replace(">", ">[^/]+)")
            regex = re.sub(r"<\w+:(\w+)>", r"(?P<>[^/]+)", route.pattern)
            regex = "^" + regex + "$"
            m = re.match(regex, path)
            if m:
                return route.handler, m.groupdict()
        return None

    def handle(self, path: str, method: str = "GET", context: Dict = None) -> Any:
        result = self.match(path, method)
        if not result:
            return self.not_found_handler()
        handler, params = result
        ctx = context or {}
        ctx.update(params)
        for mw in self.middleware:
            ctx = mw(ctx) or ctx
        return handler(**ctx)

    def reverse(self, name: str, **kwargs) -> Optional[str]:
        for route in self.routes:
            if route.name == name:
                path = route.pattern
                for k, v in kwargs.items():
                    path = re.sub(rf"<\w+:{k}>", str(v), path)
                return path
        return None

    def stats(self) -> Dict:
        return {"routes": len(self.routes), "middleware": len(self.middleware)}

def run():
    router = URLRouter()
    def user_handler(user_id):
        return {"user_id": user_id}
    def list_handler():
        return {"users": []}
    router.add_route("/users", list_handler, name="users")
    router.add_route("/users/<int:user_id>", user_handler, name="user")
    print(router.handle("/users"))
    print(router.handle("/users/123"))
    print(router.reverse("user", user_id=456))
    print(router.stats())

if __name__ == "__main__":
    run()
