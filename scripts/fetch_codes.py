"""Regenerate bundled 104 code tables. Run: uv run python scripts/fetch_codes.py"""
import json
from pathlib import Path

from curl_cffi import requests

SOURCES = {
    "jobcat": "https://static.104.com.tw/category-tool/json/JobCat.json",
    "area": "https://static.104.com.tw/category-tool/json/Area.json",
}
OUT_DIR = Path(__file__).resolve().parent.parent / "src" / "job104_mcp" / "data"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        resp = requests.get(url, impersonate="chrome", timeout=20)
        resp.raise_for_status()
        out = OUT_DIR / f"{name}.json"
        out.write_text(
            json.dumps(resp.json(), ensure_ascii=False, indent=0),
            encoding="utf-8",
        )
        print(f"wrote {out} ({len(resp.text)} bytes)")


if __name__ == "__main__":
    main()
