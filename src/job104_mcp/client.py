"""Only network layer. 104 access goes through curl_cffi chrome impersonation,
falling back to a headless browser once Cloudflare starts blocking it."""
from __future__ import annotations

import time
from urllib.parse import urlencode

from curl_cffi import requests

from .browser import BrowserFetcher, BrowserUnavailable

SEARCH_URL = "https://www.104.com.tw/jobs/search/api/jobs"
DETAIL_URL = "https://www.104.com.tw/job/ajax/content/{job_no}"
SEARCH_REFERER = "https://www.104.com.tw/jobs/search/"
DETAIL_REFERER = "https://www.104.com.tw/job/{job_no}"

_SEARCH_DEFAULTS = {"jobsource": "joblist_search", "mode": "s"}


class Client104Error(Exception):
    """Raised when 104 returns an error, blocks us, or sends non-JSON."""


class _Blocked(Client104Error):
    """curl_cffi got a 403: Cloudflare is rejecting non-browser clients."""


class Client:
    def __init__(self, min_interval: float = 1.0, timeout: int = 20,
                 browser: BrowserFetcher | None = None):
        self._min_interval = min_interval
        self._timeout = timeout
        self._last_request = 0.0
        self._browser = browser or BrowserFetcher()
        # flips on the first Cloudflare 403 so later calls skip the doomed curl attempt
        self._use_browser = False

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    def _get(self, url: str, params: dict | None = None, referer: str = SEARCH_REFERER):
        self._throttle()
        if not self._use_browser:
            try:
                return self._get_curl(url, params, referer)
            except _Blocked:
                self._use_browser = True
        return self._get_browser(url, params, referer)

    def _get_browser(self, url: str, params: dict | None, referer: str):
        if params:
            url = f"{url}?{urlencode(params, doseq=True)}"
        try:
            resp = self._browser.get(url, referer)
        except BrowserUnavailable as exc:
            raise Client104Error(f"104 擋下了直接請求，瀏覽器備援也無法使用：{exc}") from exc
        except Exception as exc:
            raise Client104Error(f"104 request via browser failed: {exc}") from exc
        if resp.status_code != 200:
            raise Client104Error(f"104 returned HTTP {resp.status_code} via browser")
        return resp

    def _get_curl(self, url: str, params: dict | None, referer: str):
        headers = {
            "Referer": referer,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-TW,zh;q=0.9",
        }
        last_err: Exception | None = None
        for impersonate in ("chrome", "chrome124"):
            try:
                resp = requests.get(
                    url, params=params, headers=headers,
                    impersonate=impersonate, timeout=self._timeout,
                )
            except Exception as exc:  # network/timeout
                last_err = exc
                continue
            if resp.status_code == 200:
                return resp
            error_cls = _Blocked if resp.status_code == 403 else Client104Error
            last_err = error_cls(
                f"104 returned HTTP {resp.status_code} (likely Cloudflare block)"
            )
        if isinstance(last_err, Client104Error):
            raise last_err
        raise Client104Error(f"104 request failed: {last_err}")

    def _parse_json(self, resp) -> dict:
        try:
            return resp.json()
        except Exception as exc:
            raise Client104Error(f"104 returned non-JSON response: {exc}") from exc

    def search(self, params: dict) -> dict:
        merged = {**_SEARCH_DEFAULTS, **params}
        return self._parse_json(self._get(SEARCH_URL, params=merged))

    def job_detail(self, job_no: str) -> dict:
        return self._parse_json(self._get(
            DETAIL_URL.format(job_no=job_no), referer=DETAIL_REFERER.format(job_no=job_no),
        ))
