from job104_mcp.codes import CodeTable, load_jobcat, load_area


def _table():
    # flat list of (code, name) the loader produces from the nested 104 tree
    return CodeTable([
        ("2007001004", "資訊軟體系統類 軟體工程師"),
        ("2007001001", "資訊軟體系統類 MIS／網管人員"),
        ("6001001000", "台北市"),
    ])


def test_exact_substring_match():
    results = _table().lookup("軟體工程師")
    assert results[0] == ("2007001004", "資訊軟體系統類 軟體工程師")


def test_returns_empty_when_no_match():
    assert _table().lookup("不存在的東西zzz") == []


def test_respects_limit():
    results = _table().lookup("資訊", limit=1)
    assert len(results) == 1


def test_load_jobcat_has_software_engineer():
    table = load_jobcat()
    results = table.lookup("軟體工程師")
    assert any(code == "2007001004" for code, _ in results)


def test_load_area_has_taipei():
    table = load_area()
    results = table.lookup("台北市大安")
    assert any("大安區" in name for _, name in results)
