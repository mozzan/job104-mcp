from unittest.mock import MagicMock

from job104_mcp import server


def test_search_jobs_tool_returns_dict(monkeypatch):
    fake = MagicMock()
    fake.search.return_value = {
        "data": [{"jobNo": "123", "jobName": "Python 工程師", "custName": "ACME",
                  "salaryLow": 40000, "salaryHigh": 60000, "s5": 50,
                  "jobAddrNoDesc": "台北市", "link": {"job": "https://www.104.com.tw/job/abcde"}}],
        "metadata": {"pagination": {"total": 1, "currentPage": 1, "lastPage": 1}},
    }
    monkeypatch.setattr(server, "_client", fake)
    out = server.search_jobs(keyword="python")
    assert out["total"] == 1
    assert out["jobs"][0]["job_name"] == "Python 工程師"
    assert out["jobs"][0]["detail_id"] == "abcde"
    fake.search.assert_called_once()


def test_lookup_code_tool():
    out = server.lookup_code(kind="area", query="台北市大安")
    assert any("大安" in row["name"] for row in out)
