import pytest
from job104_mcp.client import Client, Client104Error


@pytest.mark.live
def test_search_returns_data_and_metadata():
    client = Client(min_interval=0.0)
    result = client.search({"keyword": "python", "pagesize": "5"})
    assert "data" in result
    assert "metadata" in result
    assert isinstance(result["data"], list)
    assert result["metadata"]["pagination"]["total"] >= 0


@pytest.mark.live
def test_job_detail_returns_data():
    client = Client(min_interval=0.0)
    # the detail endpoint keys on the SHORT code from link.job, not the numeric jobNo
    search = client.search({"keyword": "python", "pagesize": "1"})
    short_code = search["data"][0]["link"]["job"].rstrip("/").split("/")[-1]
    detail = client.job_detail(short_code)
    assert "data" in detail


def test_raises_on_bad_json(monkeypatch):
    client = Client(min_interval=0.0)

    class FakeResp:
        status_code = 200
        text = "<html>not json</html>"

        def json(self):
            raise ValueError("no json")

    monkeypatch.setattr(client, "_get", lambda url, params=None: FakeResp())
    with pytest.raises(Client104Error):
        client.search({"keyword": "python"})
