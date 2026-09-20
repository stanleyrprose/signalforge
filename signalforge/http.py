from __future__ import annotations

import ssl
import urllib.error
import urllib.request
import re
from urllib.parse import urlencode, urlparse


USER_AGENT = "SignalForge/0.1 (+commercial-signal-monitor)"


class FetchError(RuntimeError):
    pass


def _fetch_bytes_with_headers(url: str, *, timeout: int, max_bytes: int, headers: dict[str, str]) -> bytes:
    request = urllib.request.Request(url, headers=headers, method="GET")
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            if int(getattr(response, "status", 200)) != 200:
                raise FetchError(f"HTTP {getattr(response, 'status', 'unknown')} for {url}")
            data = response.read(max_bytes + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FetchError(f"fetch failed for {url}: {exc}") from exc
    if len(data) > max_bytes:
        raise FetchError(f"response exceeds {max_bytes} bytes: {url}")
    return data


def fetch_bytes(url: str, *, timeout: int = 30, max_bytes: int = 2_000_000) -> bytes:
    return _fetch_bytes_with_headers(
        url,
        timeout=timeout,
        max_bytes=max_bytes,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
    )


def fetch_form_bytes(
    url: str,
    *,
    fields: dict[str, str],
    timeout: int = 30,
    max_bytes: int = 2_000_000,
) -> bytes:
    request = urllib.request.Request(
        url,
        data=urlencode(fields).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            if int(getattr(response, "status", 200)) != 200:
                raise FetchError(f"HTTP {getattr(response, 'status', 'unknown')} for {url}")
            data = response.read(max_bytes + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FetchError(f"fetch failed for {url}: {exc}") from exc
    if len(data) > max_bytes:
        raise FetchError(f"response exceeds {max_bytes} bytes: {url}")
    return data


_CLOUDRITY_D1N_HOSTS = {"viettelglobal.com.vn", "www.viettelglobal.com.vn"}
_D1N_CHALLENGE_RE = re.compile(rb'document\.cookie="D1N=([0-9a-f]{16,64})"[^<]{0,220}window\.location\.reload\(true\)')


def fetch_bytes_cloudrity_d1n(url: str, *, timeout: int = 30, max_bytes: int = 2_000_000) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in _CLOUDRITY_D1N_HOSTS:
        raise FetchError(f"Cloudrity D1N profile not authorized for host: {url}")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"}
    first = _fetch_bytes_with_headers(url, timeout=timeout, max_bytes=max_bytes, headers=headers)
    match = _D1N_CHALLENGE_RE.search(first)
    if match is None:
        return first
    headers["Cookie"] = f"D1N={match.group(1).decode('ascii')}"
    second = _fetch_bytes_with_headers(url, timeout=timeout, max_bytes=max_bytes, headers=headers)
    if _D1N_CHALLENGE_RE.search(second) is not None:
        raise FetchError(f"Cloudrity D1N challenge persisted after one retry: {url}")
    return second
