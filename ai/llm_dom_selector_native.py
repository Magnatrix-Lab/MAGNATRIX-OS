"""LLM DOM Selector — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class DOMElement:
    def __init__(self, tag: str = "", text: str = "", attributes: Dict[str, str] = None, parent: "DOMElement" = None) -> None:
        self.tag = tag
        self.text = text
        self.attributes = attributes or {}
        self.children: List[DOMElement] = []
        self.parent = parent

    def select(self, tag: str) -> List["DOMElement"]:
        results = []
        if self.tag == tag:
            results.append(self)
        for child in self.children:
            results.extend(child.select(tag))
        return results

    def select_by_attr(self, attr: str, value: str) -> List["DOMElement"]:
        results = []
        if self.attributes.get(attr) == value:
            results.append(self)
        for child in self.children:
            results.extend(child.select_by_attr(attr, value))
        return results

    def select_by_class(self, class_name: str) -> List["DOMElement"]:
        classes = self.attributes.get("class", "").split()
        results = []
        if class_name in classes:
            results.append(self)
        for child in self.children:
            results.extend(child.select_by_class(class_name))
        return results

    def select_by_id(self, id_name: str) -> List["DOMElement"]:
        results = []
        if self.attributes.get("id") == id_name:
            results.append(self)
        for child in self.children:
            results.extend(child.select_by_id(id_name))
        return results

    def get_text(self) -> str:
        parts = [self.text]
        for child in self.children:
            parts.append(child.get_text())
        return " ".join(p for p in parts if p)

class DOMSelector:
    def __init__(self) -> None:
        self._root: Optional[DOMElement] = None

    def parse_simple(self, html: str) -> DOMElement:
        root = DOMElement("root")
        stack = [root]
        tag_pattern = re.compile(r'<(\/?)(\w+)([^>]*)>')
        pos = 0
        while pos < len(html):
            match = tag_pattern.search(html, pos)
            if not match:
                break
            if match.start() > pos:
                text = html[pos:match.start()].strip()
                if text and stack:
                    stack[-1].text += " " + text if stack[-1].text else text
            closing, tag, attrs = match.groups()
            if not closing:
                node = DOMElement(tag, "", self._parse_attrs(attrs), stack[-1] if stack else None)
                if stack:
                    stack[-1].children.append(node)
                stack.append(node)
            else:
                if len(stack) > 1 and stack[-1].tag == tag:
                    stack.pop()
            pos = match.end()
        self._root = root
        return root

    def _parse_attrs(self, attr_str: str) -> Dict[str, str]:
        attrs = {}
        for match in re.finditer(r'(\w+)=\"([^\"]*)\"', attr_str):
            attrs[match.group(1)] = match.group(2)
        return attrs

    def query(self, selector: str, root: Optional[DOMElement] = None) -> List[DOMElement]:
        node = root or self._root
        if not node:
            return []
        if selector.startswith("#"):
            return node.select_by_id(selector[1:])
        elif selector.startswith("."):
            return node.select_by_class(selector[1:])
        elif selector.startswith("[") and selector.endswith("]"):
            attr_parts = selector[1:-1].split("=")
            if len(attr_parts) == 2:
                return node.select_by_attr(attr_parts[0], attr_parts[1].strip("'\""))
            return node.select_by_attr(attr_parts[0], "")
        return node.select(selector)

    def get_stats(self, root: DOMElement) -> Dict[str, Any]:
        return {"tag": root.tag, "children": len(root.children)}

def run() -> None:
    print("DOM Selector test")
    e = DOMSelector()
    html = "<div id='main' class='container'><h1>Title</h1><p class='text'>Hello</p><p class='text'>World</p></div>"
    root = e.parse_simple(html)
    print("  By tag h1: " + str([el.get_text() for el in e.query("h1", root)]))
    print("  By class text: " + str([el.get_text() for el in e.query(".text", root)]))
    print("  By id main: " + str([el.tag for el in e.query("#main", root)]))
    print("  Stats: " + str(e.get_stats(root)))
    print("DOM Selector test complete.")

if __name__ == "__main__":
    run()
