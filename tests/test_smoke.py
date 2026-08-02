import tomllib
from importlib.metadata import version
from pathlib import Path

from packaging.requirements import Requirement


def test_package_imports():
    import job104_mcp
    # __version__ is single-sourced from package metadata, not hardcoded
    assert job104_mcp.__version__ == version("job104-mcp")


def test_mcp_requirement_excludes_versions_without_fastmcp():
    # server.py imports mcp.server.fastmcp, which mcp 2.0 removed. A fresh
    # `uvx job104-mcp` resolves deps from this spec (not uv.lock), so an
    # unbounded spec installs mcp 2.x and the server dies on import.
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    deps = tomllib.loads(pyproject.read_text())["project"]["dependencies"]
    mcp_req = next(r for r in map(Requirement, deps) if r.name == "mcp")
    assert not mcp_req.specifier.contains("2.0.0"), (
        f"mcp spec {mcp_req.specifier} allows 2.x, which has no mcp.server.fastmcp"
    )
