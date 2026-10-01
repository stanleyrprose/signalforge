from __future__ import annotations

import ssl
import urllib.error
import urllib.request
import re
from dataclasses import dataclass
from urllib.parse import urlencode, urlparse


USER_AGENT = "SignalForge/0.1 (+commercial-signal-monitor)"


class FetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResult:
    payload: bytes
    fetch_method: str
    strict_tls_failed: bool = False


_MYAWADY_HOSTS = {"myawady.net.mm", "www.myawady.net.mm"}


def _walk_exception(exc: BaseException):
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        cause = current.__cause__ or current.__context__
        current = cause if isinstance(cause, BaseException) else None


def _is_tls_certificate_failure(exc: BaseException) -> bool:
    text = " ".join(str(item) for item in _walk_exception(exc)).lower()
    return any(
        isinstance(item, ssl.SSLCertVerificationError)
        for item in _walk_exception(exc)
    ) or "certificate verify failed" in text or "unable to get local issuer certificate" in text


class _SameOriginHttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: set[str]) -> None:
        super().__init__()
        self.allowed_hosts = {value.lower() for value in allowed_hosts}

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        parsed = urlparse(newurl)
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower() not in self.allowed_hosts
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            raise FetchError(f"redirect outside authorized HTTPS origin: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch_bytes_with_context(
    url: str,
    *,
    timeout: int,
    max_bytes: int,
    headers: dict[str, str],
    context: ssl.SSLContext,
    allowed_redirect_hosts: set[str] | None = None,
) -> bytes:
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        if allowed_redirect_hosts is None:
            response = urllib.request.urlopen(request, timeout=timeout, context=context)
        else:
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=context),
                _SameOriginHttpsRedirectHandler(allowed_redirect_hosts),
            )
            response = opener.open(request, timeout=timeout)
        with response:
            if int(getattr(response, "status", 200)) != 200:
                raise FetchError(f"HTTP {getattr(response, 'status', 'unknown')} for {url}")
            data = response.read(max_bytes + 1)
    except (urllib.error.URLError, TimeoutError, OSError, FetchError) as exc:
        if isinstance(exc, FetchError):
            raise
        raise FetchError(f"fetch failed for {url}: {exc}") from exc
    if len(data) > max_bytes:
        raise FetchError(f"response exceeds {max_bytes} bytes: {url}")
    return data


def _fetch_bytes_with_headers(url: str, *, timeout: int, max_bytes: int, headers: dict[str, str]) -> bytes:
    return _fetch_bytes_with_context(
        url,
        timeout=timeout,
        max_bytes=max_bytes,
        headers=headers,
        context=ssl.create_default_context(),
    )


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

def fetch_bytes_myawady_insecure_readonly(
    url: str,
    *,
    timeout: int = 30,
    max_bytes: int = 2_000_000,
) -> FetchResult:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or host not in _MYAWADY_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise FetchError(f"Myawady insecure read-only profile not authorized for URL: {url}")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    insecure_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    insecure_context.check_hostname = False
    insecure_context.verify_mode = ssl.CERT_NONE
    payload = _fetch_bytes_with_context(
        url,
        timeout=timeout,
        max_bytes=max_bytes,
        headers=headers,
        context=insecure_context,
        allowed_redirect_hosts=_MYAWADY_HOSTS,
    )
    return FetchResult(
        payload=payload,
        fetch_method="DIRECT_HTTP_TLS_INSECURE_READONLY",
        strict_tls_failed=False,
    )
