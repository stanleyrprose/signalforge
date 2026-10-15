from __future__ import annotations

import logging
import ssl
import urllib.error
import urllib.request
import re
from urllib.parse import urlencode, urlparse


USER_AGENT = "SignalForge/0.1 (+commercial-signal-monitor)"


class FetchError(RuntimeError):
    pass




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


def _fetch_bytes_with_headers(
    url: str, *, timeout: int, max_bytes: int, headers: dict[str, str],
    expired_cert_hosts: set[str] | None = None,
) -> bytes:
    try:
        return _fetch_bytes_with_context(
            url, timeout=timeout, max_bytes=max_bytes, headers=headers,
            context=ssl.create_default_context(),
            allowed_redirect_hosts=expired_cert_hosts,
        )
    except FetchError as exc:
        # Issuer-specific, explicitly approved exception: only expired certs;
        # host mismatches, unknown CAs and other TLS failures stay fail-closed.
        message = " ".join(str(item) for item in _walk_exception(exc)).lower()
        if expired_cert_hosts is None or not (
            "certificate has expired" in message or "certificate expired" in message
        ):
            raise
        parsed = urlparse(url)
        if (parsed.scheme != "https" or (parsed.hostname or "").lower() not in expired_cert_hosts
            or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443)):
            raise
        logging.getLogger(__name__).warning(
            "S41 issuer TLS expiry exception used for approved host: %s", parsed.hostname
        )
        return _fetch_bytes_with_context(
            url, timeout=timeout, max_bytes=max_bytes, headers=headers,
            context=ssl._create_unverified_context(),
            allowed_redirect_hosts=expired_cert_hosts,
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


def fetch_bytes_cloudrity_d1n(
    url: str, *, timeout: int = 30, max_bytes: int = 2_000_000,
    allow_expired_certificate: bool = False,
) -> bytes:
    parsed = urlparse(url)
    if (parsed.scheme != "https" or (parsed.hostname or "").lower() not in _CLOUDRITY_D1N_HOSTS
        or parsed.username is not None or parsed.password is not None or parsed.port not in (None, 443)
        or parsed.fragment):
        raise FetchError(f"Cloudrity D1N profile not authorized for host: {url}")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"}
    exception_hosts = _CLOUDRITY_D1N_HOSTS if allow_expired_certificate else None
    first = _fetch_bytes_with_headers(
        url, timeout=timeout, max_bytes=max_bytes, headers=headers,
        expired_cert_hosts=exception_hosts,
    )
    match = _D1N_CHALLENGE_RE.search(first)
    if match is None:
        return first
    headers["Cookie"] = f"D1N={match.group(1).decode('ascii')}"
    second = _fetch_bytes_with_headers(
        url, timeout=timeout, max_bytes=max_bytes, headers=headers,
        expired_cert_hosts=exception_hosts,
    )
    if _D1N_CHALLENGE_RE.search(second) is not None:
        raise FetchError(f"Cloudrity D1N challenge persisted after one retry: {url}")
    return second
