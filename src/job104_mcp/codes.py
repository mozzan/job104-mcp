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


def _flatten(nodes: list[dict]) -> list[tuple[str, str]]:
    """Walk the nested 104 tree; emit a (code, des) pair for EVERY node — both
    internal (e.g. city '台北市', category '資訊軟體系統類') and leaf (district,
    job title). 104's filter params accept a code at any level."""
    out: list[tuple[str, str]] = []
    for node in nodes:
        out.append((node["no"], node["des"]))
        children = node.get("n")
        if children:
            out.extend(_flatten(children))
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
