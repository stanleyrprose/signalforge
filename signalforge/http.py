from __future__ import annotations

import ssl
import urllib.error
import urllib.request


USER_AGENT = "SignalForge/0.1 (+commercial-signal-monitor)"


class FetchError(RuntimeError):
    pass


def fetch_bytes(url: str, *, timeout: int = 30, max_bytes: int = 2_000_000) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        method="GET",
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
