from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_MYANMAR_RANGES = (
    (0x1000, 0x109F),
    (0xA9E0, 0xA9FF),
    (0xAA60, 0xAA7F),
)
_DEFAULT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
_PROVIDER = "microsoft"


def contains_myanmar(value: object) -> bool:
    text = str(value or "")
    return any(
        start <= ord(char) <= end
        for char in text
        for start, end in _MYANMAR_RANGES
    )


def _microsoft_configured() -> bool:
    return bool(os.environ.get("SIGNALFORGE_MICROSOFT_TRANSLATOR_KEY", "").strip())


def translation_ready() -> bool:
    provider = os.environ.get("SIGNALFORGE_TRANSLATION_PROVIDER", "").strip().lower()
    return provider in {"", _PROVIDER} and _microsoft_configured()


def translate_myanmar_to_zh_hans(
    values: list[str],
    *,
    timeout: float = 5.0,
    key: str | None = None,
    region: str | None = None,
    endpoint: str | None = None,
) -> tuple[list[str], bool]:
    """Translate Myanmar-script values for Telegram display only.

    The function is intentionally fail-open: any missing configuration,
    transport error, provider error, or malformed response returns
    the original values so SignalForge never drops a business alert because
    translation is degraded.
    """
    originals = [str(value or "") for value in values]
    indices = [index for index, value in enumerate(originals) if contains_myanmar(value)]
    if not indices:
        return originals, False

    provider = os.environ.get("SIGNALFORGE_TRANSLATION_PROVIDER", "").strip().lower()
    if provider not in {"", _PROVIDER}:
        return originals, False

    secret = (key or os.environ.get("SIGNALFORGE_MICROSOFT_TRANSLATOR_KEY", "")).strip()
    if not secret:
        return originals, False

    resource_region = (
        region
        if region is not None
        else os.environ.get("SIGNALFORGE_MICROSOFT_TRANSLATOR_REGION", "")
    ).strip()
    base = (
        endpoint
        or os.environ.get("SIGNALFORGE_MICROSOFT_TRANSLATOR_ENDPOINT", _DEFAULT_ENDPOINT)
    ).rstrip("/")
    url = f"{base}/translate?" + urlencode(
        {"api-version": "3.0", "from": "my", "to": "zh-Hans"}
    )
    body = json.dumps(
        [{"Text": originals[index]} for index in indices],
        ensure_ascii=False,
    ).encode("utf-8")
    headers = {
        "Ocp-Apim-Subscription-Key": secret,
        "Content-Type": "application/json",
    }
    if resource_region:
        headers["Ocp-Apim-Subscription-Region"] = resource_region

    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(262144).decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError):
        return originals, False

    if not isinstance(payload, list) or len(payload) != len(indices):
        return originals, False

    translated: list[str] = []
    for row in payload:
        if not isinstance(row, dict):
            return originals, False
        options = row.get("translations")
        if not isinstance(options, list) or not options or not isinstance(options[0], dict):
            return originals, False
        text = str(options[0].get("text") or "").strip()
        if not text:
            return originals, False
        translated.append(text)

    result = list(originals)
    for index, text in zip(indices, translated, strict=True):
        result[index] = text
    return result, True
