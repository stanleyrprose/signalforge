from __future__ import annotations

import html
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .translation_queue import request_translation_and_wait, translation_queue_status

_MYANMAR_RANGES = (
    (0x1000, 0x109F),
    (0xA9E0, 0xA9FF),
    (0xAA60, 0xAA7F),
)
_MICROSOFT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
_GOOGLE_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"
_DEFAULT_PRIORITY = ("mac_oauth_llm", "microsoft", "google")


def contains_myanmar(value: object) -> bool:
    text = str(value or "")
    return any(
        start <= ord(char) <= end
        for char in text
        for start, end in _MYANMAR_RANGES
    )


def _priority(value: str | None = None) -> tuple[str, ...]:
    raw = value if value is not None else os.environ.get("SIGNALFORGE_TRANSLATION_PROVIDER", "")
    if not raw.strip():
        return _DEFAULT_PRIORITY
    normalized = raw.replace(";", ",")
    providers = tuple(part.strip().lower() for part in normalized.split(",") if part.strip())
    allowed = {"mac_oauth_llm", "microsoft", "google", "original"}
    return tuple(provider for provider in providers if provider in allowed) or _DEFAULT_PRIORITY


def _microsoft_configured() -> bool:
    return bool(os.environ.get("SIGNALFORGE_MICROSOFT_TRANSLATOR_KEY", "").strip())


def _google_configured() -> bool:
    return bool(os.environ.get("SIGNALFORGE_GOOGLE_TRANSLATE_API_KEY", "").strip())


def translation_ready(*, database: Path | None = None) -> bool:
    for provider in _priority():
        if provider == "mac_oauth_llm" and database is not None:
            try:
                if translation_queue_status(database=database).get("ready") is True:
                    return True
            except Exception:
                pass
        elif provider == "microsoft" and _microsoft_configured():
            return True
        elif provider == "google" and _google_configured():
            return True
    return False


def translation_status(*, database: Path | None = None) -> dict[str, object]:
    mac: dict[str, object] = {"ready": False}
    if database is not None:
        try:
            mac = translation_queue_status(database=database)
        except Exception as exc:
            mac = {"ready": False, "error": exc.__class__.__name__}
    return {
        "priority": list(_priority()),
        "source_language": "my",
        "target_language": "zh-Hans",
        "presentation_only": True,
        "fail_open_to_original": True,
        "providers": {
            "mac_oauth_llm": mac,
            "microsoft": {"configured": _microsoft_configured()},
            "google": {"configured": _google_configured()},
        },
        "ready": translation_ready(database=database),
    }


def _translate_microsoft(
    values: list[str],
    *,
    timeout: float,
    key: str | None,
    region: str | None,
    endpoint: str | None,
) -> list[str] | None:
    secret = (key or os.environ.get("SIGNALFORGE_MICROSOFT_TRANSLATOR_KEY", "")).strip()
    if not secret:
        return None
    resource_region = (
        region
        if region is not None
        else os.environ.get("SIGNALFORGE_MICROSOFT_TRANSLATOR_REGION", "")
    ).strip()
    base = (
        endpoint
        or os.environ.get("SIGNALFORGE_MICROSOFT_TRANSLATOR_ENDPOINT", _MICROSOFT_ENDPOINT)
    ).rstrip("/")
    url = f"{base}/translate?" + urlencode(
        {"api-version": "3.0", "from": "my", "to": "zh-Hans"}
    )
    body = json.dumps([{"Text": value} for value in values], ensure_ascii=False).encode("utf-8")
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
        return None
    if not isinstance(payload, list) or len(payload) != len(values):
        return None
    translated: list[str] = []
    for row in payload:
        if not isinstance(row, dict):
            return None
        options = row.get("translations")
        if not isinstance(options, list) or not options or not isinstance(options[0], dict):
            return None
        text = str(options[0].get("text") or "").strip()
        if not text:
            return None
        translated.append(text)
    return translated


def _translate_google(
    values: list[str],
    *,
    timeout: float,
    key: str | None = None,
    endpoint: str | None = None,
) -> list[str] | None:
    secret = (key or os.environ.get("SIGNALFORGE_GOOGLE_TRANSLATE_API_KEY", "")).strip()
    if not secret:
        return None
    base = endpoint or os.environ.get("SIGNALFORGE_GOOGLE_TRANSLATE_ENDPOINT", _GOOGLE_ENDPOINT)
    url = f"{base}?" + urlencode({"key": secret})
    body = json.dumps(
        {"q": values, "source": "my", "target": "zh-CN", "format": "text"},
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(262144).decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError):
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    rows = data.get("translations") if isinstance(data, dict) else None
    if not isinstance(rows, list) or len(rows) != len(values):
        return None
    translated: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            return None
        text = html.unescape(str(row.get("translatedText") or "")).strip()
        if not text:
            return None
        translated.append(text)
    return translated


def translate_myanmar_to_zh_hans(
    values: list[str],
    *,
    timeout: float = 5.0,
    database: Path | None = None,
    mac_wait_seconds: float = 20.0,
    provider_priority: str | None = None,
    key: str | None = None,
    region: str | None = None,
    endpoint: str | None = None,
    google_key: str | None = None,
    google_endpoint: str | None = None,
) -> tuple[list[str], bool]:
    """Translate Myanmar-script values for Telegram presentation only.

    Provider order defaults to Mac ChatGPT OAuth LLM, Microsoft Translator,
    Google Cloud Translation, then original text. Any provider failure falls
    through; translation can never suppress a SignalForge alert.
    """
    originals = [str(value or "") for value in values]
    indices = [index for index, value in enumerate(originals) if contains_myanmar(value)]
    if not indices:
        return originals, False
    subset = [originals[index] for index in indices]

    for provider in _priority(provider_priority):
        translated: list[str] | None = None
        if provider == "mac_oauth_llm" and database is not None:
            try:
                candidate, ok = request_translation_and_wait(
                    subset,
                    database=database,
                    wait_seconds=mac_wait_seconds,
                )
                translated = candidate if ok else None
            except Exception:
                translated = None
        elif provider == "microsoft":
            translated = _translate_microsoft(
                subset,
                timeout=timeout,
                key=key,
                region=region,
                endpoint=endpoint,
            )
        elif provider == "google":
            translated = _translate_google(
                subset,
                timeout=timeout,
                key=google_key,
                endpoint=google_endpoint,
            )
        elif provider == "original":
            break

        if translated is not None and len(translated) == len(indices):
            result = list(originals)
            for index, text in zip(indices, translated, strict=True):
                result[index] = text
            return result, True

    return originals, False
