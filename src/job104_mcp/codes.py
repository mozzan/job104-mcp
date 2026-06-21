"""Load 104's nested code trees and provide fuzzy name->code lookup. No network."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"


class CodeTable:
    def __init__(self, entries: list[tuple[str, str]]):
        # entries: list of (code, full_name) leaves
        self._entries = entries

    def lookup(self, query: str, limit: int = 5) -> list[tuple[str, str]]:
        q = query.strip()
        if not q:
            return []
        matches = [(code, name) for code, name in self._entries if q in name]
        # shorter names rank higher (closer to an exact match)
        matches.sort(key=lambda cn: len(cn[1]))
        return matches[:limit]


def _flatten(nodes: list[dict], prefix: str = "") -> list[tuple[str, str]]:
    """Walk the nested 104 tree; emit a (code, joined-name) leaf for every node
    that has no children."""
    out: list[tuple[str, str]] = []
    for node in nodes:
        name = node["des"]
        full = f"{prefix} {name}" if prefix else name
        children = node.get("n")
        if children:
            out.extend(_flatten(children, full))
        else:
            out.append((node["no"], full))
    return out


def _load(filename: str) -> CodeTable:
    raw = json.loads((_DATA_DIR / filename).read_text(encoding="utf-8"))
    return CodeTable(_flatten(raw))


@lru_cache(maxsize=None)
def load_jobcat() -> CodeTable:
    return _load("jobcat.json")


@lru_cache(maxsize=None)
def load_area() -> CodeTable:
    return _load("area.json")
