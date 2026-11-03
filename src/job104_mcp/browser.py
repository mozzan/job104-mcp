"""Headless-Chrome fallback for when Cloudflare blocks curl_cffi.

104 now challenges non-browser clients on its JSON endpoints. A cf_clearance
cookie solved by Chrome does not carry over to curl_cffi (it is bound to the
browser's fingerprint), so the request itself runs inside a real 104 page via
the Chrome DevTools Protocol.
"""
from __future__ import annotations

import atexit
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass

from websockets.sync.client import connect

START_URL = "https://www.104.com.tw/jobs/search/"

_FETCH_JS = """fetch(%s, {
  headers: {Accept: 'application/json, text/plain, */*'},
  referrer: %s, credentials: 'include',
}).then(async r => JSON.stringify({status: r.status, text: await r.text()}))"""


class BrowserUnavailable(Exception):
    """No usable Chrome/Edge/Chromium, or it failed to start."""


@dataclass
class BrowserResponse:
    status_code: int
    text: str

    def json(self):
        return json.loads(self.text)


def find_chrome() -> str | None:
    env = os.environ.get("JOB104_CHROME")
    if env:
        return env
    if sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        ]
    elif sys.platform == "win32":
        roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
        rels = [
            r"Google\Chrome\Application\chrome.exe",
            r"Microsoft\Edge\Application\msedge.exe",
            r"BraveSoftware\Brave-Browser\Application\brave.exe",
        ]
        candidates = [os.path.join(root, rel) for root in roots if root for rel in rels]
    else:
        candidates = []
    for path in candidates:
        if os.path.exists(path):
            return path
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "microsoft-edge", "chrome", "msedge"):
        path = shutil.which(name)
        if path:
            return path
    return None


class BrowserFetcher:
    """One lazily started headless browser, reused for the life of the process."""

    def __init__(self, start_timeout: float = 20.0, challenge_timeout: float = 20.0):
        self._start_timeout = start_timeout
        self._challenge_timeout = challenge_timeout
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._profile: str | None = None
        self._ws = None
        self._ws_stack = contextlib.ExitStack()
        self._msg_id = 0
        atexit.register(self.close)

    def get(self, url: str, referrer: str) -> BrowserResponse:
        with self._lock:
            try:
                return self._fetch_with_retry(url, referrer)
            except BrowserUnavailable:
                raise
            except Exception:
                # browser crashed or the socket dropped: restart once
                self.close()
                return self._fetch_with_retry(url, referrer)

    def _fetch_with_retry(self, url: str, referrer: str) -> BrowserResponse:
        if self._ws is None:
            self._start()
        # right after launch Cloudflare may still be solving its challenge
        deadline = time.monotonic() + self._challenge_timeout
        while True:
            resp = self._fetch(url, referrer)
            if resp.status_code != 403 or time.monotonic() > deadline:
                return resp
            time.sleep(1)

    def _fetch(self, url: str, referrer: str) -> BrowserResponse:
        expr = _FETCH_JS % (json.dumps(url), json.dumps(referrer))
        result = self._call("Runtime.evaluate", expression=expr,
                            awaitPromise=True, returnByValue=True)
        value = result.get("result", {}).get("value")
        if value is None:
            # page not ready yet (e.g. mid-navigation): treat like a block
            return BrowserResponse(403, json.dumps(result))
        data = json.loads(value)
        return BrowserResponse(data["status"], data["text"])

    def _call(self, method: str, **params) -> dict:
        self._msg_id += 1
        msg_id = self._msg_id
        self._ws.send(json.dumps({"id": msg_id, "method": method, "params": params}))
        while True:
            msg = json.loads(self._ws.recv(timeout=60))
            if msg.get("id") == msg_id:
                if "error" in msg:
                    raise RuntimeError(f"CDP {method} failed: {msg['error']}")
                return msg.get("result", {})

    def _start(self) -> None:
        chrome = find_chrome()
        if not chrome:
            raise BrowserUnavailable(
                "找不到 Chrome/Edge/Chromium；請安裝 Chrome，或用環境變數 JOB104_CHROME 指定路徑"
            )
        self._profile = tempfile.mkdtemp(prefix="job104-chrome-")
        try:
            self._proc = subprocess.Popen(
                [chrome, "--headless=new", f"--user-data-dir={self._profile}",
                 "--remote-debugging-port=0", "--no-first-run", "--no-default-browser-check",
                 "--disable-blink-features=AutomationControlled", "about:blank"],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise BrowserUnavailable(f"無法啟動瀏覽器 {chrome}: {exc}") from exc
        port = self._wait_for_port()
        page_ws = self._wait_for_page(port)
        # Chrome never answers the websocket close handshake, so don't wait long for it
        self._ws = self._ws_stack.enter_context(
            connect(page_ws, max_size=None, proxy=None, close_timeout=1)
        )
        # headless announces itself as "HeadlessChrome", which Cloudflare blocks outright
        ua = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version"))["User-Agent"]
        self._call("Emulation.setUserAgentOverride", userAgent=ua.replace("HeadlessChrome", "Chrome"))
        self._call("Page.enable")
        self._call("Page.navigate", url=START_URL)
        self._wait_for_104_origin()

    def _wait_for_port(self) -> int:
        port_file = os.path.join(self._profile, "DevToolsActivePort")
        deadline = time.monotonic() + self._start_timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                raise BrowserUnavailable(f"瀏覽器啟動後立即結束 (exit {self._proc.returncode})")
            try:
                with open(port_file) as f:
                    return int(f.readline().strip())
            except (OSError, ValueError):
                time.sleep(0.1)
        raise BrowserUnavailable("等待瀏覽器 DevTools 逾時")

    def _wait_for_page(self, port: int) -> str:
        deadline = time.monotonic() + self._start_timeout
        while time.monotonic() < deadline:
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list"))
                for t in targets:
                    if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                        return t["webSocketDebuggerUrl"]
            except OSError:
                pass
            time.sleep(0.1)
        raise BrowserUnavailable("等待瀏覽器分頁逾時")

    def _wait_for_104_origin(self) -> None:
        # fetch() needs the page to be on www.104.com.tw so cookies and CORS line up
        deadline = time.monotonic() + self._start_timeout
        while time.monotonic() < deadline:
            res = self._call("Runtime.evaluate", expression="location.origin", returnByValue=True)
            if res.get("result", {}).get("value") == "https://www.104.com.tw":
                return
            time.sleep(0.2)
        raise BrowserUnavailable("瀏覽器無法開啟 104 網站")

    def close(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        try:
            self._ws_stack.close()
        except Exception:
            pass
        self._ws = None
        if self._profile is not None:
            shutil.rmtree(self._profile, ignore_errors=True)
            self._profile = None
