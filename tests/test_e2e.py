import pytest
from job104_mcp import server


@pytest.mark.live
def test_search_then_detail_end_to_end():
    out = server.search_jobs(keyword="python", area=["台北市大安區"], page_size=3)
    assert "error" not in out, out
    assert out["total"] >= 0
    if out["jobs"]:
        detail_id = out["jobs"][0]["detail_id"]
        detail = server.get_job_detail(detail_id)
        assert "error" not in detail
        assert detail["job_name"]
