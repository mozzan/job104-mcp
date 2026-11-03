import pytest
from job104_mcp import client as client_mod
from job104_mcp.browser import BrowserResponse, BrowserUnavailable
from job104_mcp.client import Client, Client104Error


class FakeBrowser:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.calls = resp, exc, []

    def get(self, url, referrer):
        self.calls.append((url, referrer))
        if self.exc:
            raise self.exc
        return self.resp


class Resp403:
    status_code = 403


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

    monkeypatch.setattr(client, "_get", lambda url, params=None, **kw: FakeResp())
    with pytest.raises(Client104Error):
        client.search({"keyword": "python"})


def _curl_returns(monkeypatch, resp):
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return resp
    monkeypatch.setattr(client_mod.requests, "get", fake_get)
    return calls


def test_403_falls_back_to_browser_and_sticks(monkeypatch):
    curl_calls = _curl_returns(monkeypatch, Resp403())
    browser = FakeBrowser(BrowserResponse(200, '{"data": {"ok": true}}'))
    client = Client(min_interval=0.0, browser=browser)

    assert client.job_detail("abcde") == {"data": {"ok": True}}
    assert browser.calls == [("https://www.104.com.tw/job/ajax/content/abcde",
                              "https://www.104.com.tw/job/abcde")]

    n_curl = len(curl_calls)
    client.search({"keyword": "python"})
    assert len(curl_calls) == n_curl  # no more curl attempts once blocked
    url, referrer = browser.calls[-1]
    assert url.startswith(client_mod.SEARCH_URL + "?")
    assert "keyword=python" in url
    assert referrer == client_mod.SEARCH_REFERER


def test_non_403_does_not_use_browser(monkeypatch):
    class Resp500:
        status_code = 500
    _curl_returns(monkeypatch, Resp500())
    browser = FakeBrowser(BrowserResponse(200, "{}"))
    client = Client(min_interval=0.0, browser=browser)
    with pytest.raises(Client104Error, match="HTTP 500"):
        client.search({"keyword": "python"})
    assert browser.calls == []


def test_browser_unavailable_is_client_error(monkeypatch):
    _curl_returns(monkeypatch, Resp403())
    browser = FakeBrowser(exc=BrowserUnavailable("找不到 Chrome"))
    client = Client(min_interval=0.0, browser=browser)
    with pytest.raises(Client104Error, match="找不到 Chrome"):
        client.search({"keyword": "python"})
