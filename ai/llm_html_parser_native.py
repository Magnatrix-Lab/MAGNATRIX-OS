"""LLM HTML Parser — Native Python (stdlib only)."""
from __future__ import annotations
import html
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
import re

class HTMLNode:
    def __init__(self, tag: str, attributes: Dict[str, str] = None, text: str = "") -> None:
        self.tag = tag
        self.attributes = attributes or {}
        self.text = text
        self.children: List[HTMLNode] = []
        self.parent: Optional[HTMLNode] = None

    def add_child(self, child: "HTMLNode") -> None:
        child.parent = self
        self.children.append(child)

    def get_text(self) -> str:
        parts = [self.text]
        for child in self.children:
            parts.append(child.get_text())
        return " ".join(p for p in parts if p)

    def find_by_tag(self, tag: str) -> List["HTMLNode"]:
        results = []
        if self.tag == tag:
            results.append(self)
        for child in self.children:
            results.extend(child.find_by_tag(tag))
        return results

    def find_by_attribute(self, attr: str, value: str) -> List["HTMLNode"]:
        results = []
        if self.attributes.get(attr) == value:
            results.append(self)
        for child in self.children:
            results.extend(child.find_by_attribute(attr, value))
        return results

class HTMLParser:
    def __init__(self) -> None:
        self._root: Optional[HTMLNode] = None

    def parse(self, html_text: str) -> HTMLNode:
        root = HTMLNode("root")
        stack = [root]
        tag_pattern = re.compile(r'<(\/?)(\w+)([^>]*)>')
        text_pattern = re.compile(r'>([^<]*)<')
        pos = 0
        while pos < len(html_text):
            match = tag_pattern.search(html_text, pos)
            if not match:
                break
            if match.start() > pos:
                text = html_text[pos:match.start()].strip()
                if text and stack:
                    stack[-1].text += " " + text
            closing, tag, attrs = match.groups()
            if not closing:
                node = HTMLNode(tag, self._parse_attrs(attrs))
                if stack:
                    stack[-1].add_child(node)
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

    def extract_text(self, html_text: str) -> str:
        text = re.sub(r'<[^>]+>', ' ', html_text)
        text = html.unescape(text)
        return re.sub(r'\s+', ' ', text).strip()

    def extract_links(self, html_text: str) -> List[tuple]:
        return re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)<\/a>', html_text)

    def extract_images(self, html_text: str) -> List[tuple]:
        return re.findall(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"]*)["\']', html_text)

    def get_stats(self, root: HTMLNode) -> Dict[str, Any]:
        return {"tag": root.tag, "children": len(root.children), "text_length": len(root.get_text())}

def run() -> None:
    print("HTML Parser test")
    e = HTMLParser()
    html = "<html><body><h1>Title</h1><p>Hello <a href='http://test.com'>link</a></p><img src='img.jpg' alt='pic'></body></html>"
    root = e.parse(html)
    print("  Text: " + e.extract_text(html))
    print("  Links: " + str(e.extract_links(html)))
    print("  Images: " + str(e.extract_images(html)))
    h1s = root.find_by_tag("h1")
    print("  H1 text: " + (h1s[0].get_text() if h1s else "None"))
    print("  Stats: " + str(e.get_stats(root)))
    print("HTML Parser test complete.")

if __name__ == "__main__":
    run()
