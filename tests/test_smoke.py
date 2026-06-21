from importlib.metadata import version


def test_package_imports():
    import job104_mcp
    # __version__ is single-sourced from package metadata, not hardcoded
    assert job104_mcp.__version__ == version("job104-mcp")
