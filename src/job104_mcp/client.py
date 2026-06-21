"""Only network layer. All 104 access goes through curl_cffi chrome impersonation."""
from __future__ import annotations

import time

from curl_cffi import requests

SEARCH_URL = "https://www.104.com.tw/jobs/search/api/jobs"
DETAIL_URL = "https://www.104.com.tw/job/ajax/content/{job_no}"

_SEARCH_DEFAULTS = {"jobsource": "joblist_search", "mode": "s"}


class Client104Error(Exception):
    """Raised when 104 returns an error, blocks us, or sends non-JSON."""


class Client:
    def __init__(self, min_interval: float = 1.0, timeout: int = 20):
        self._min_interval = min_interval
        self._timeout = timeout
        self._last_request = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    def _get(self, url: str, params: dict | None = None):
        self._throttle()
        headers = {
            "Referer": "https://www.104.com.tw/jobs/search/",
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
            last_err = Client104Error(
                f"104 returned HTTP {resp.status_code} (likely Cloudflare block)"
            )
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
        return self._parse_json(self._get(DETAIL_URL.format(job_no=job_no)))
