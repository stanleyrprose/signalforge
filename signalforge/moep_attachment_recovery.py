"""Recover original S20 PDFs only after official availability is proven.

A recovered PDF is immutable issuer evidence and native text for review, not
authority to invent bid deadlines or silently create canonical signals.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import ssl
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from pypdf import PdfReader

from .config import evidence_root
from .db import connect
from .engine import _write_evidence
from .http import _SameOriginHttpsRedirectHandler

_ALLOWED = {"moep.gov.mm", "www.moep.gov.mm"}


def _approved_url(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme == "https" and parsed.hostname in _ALLOWED
        and parsed.username is None and parsed.password is None
        and parsed.port in (None, 443) and not parsed.query and not parsed.fragment
        and re.fullmatch(r"/mm/userfile/[^/]+\.pdf", parsed.path, re.I) is not None
    )


def recover_accessible_s20_pdfs(
    database: Path, health: dict[str, object], *, evidence: Path | None = None,
    timeout: int = 6, max_bytes: int = 2_000_000, opener=None,
) -> dict[str, object]:
    """Fetch at most five HEAD-confirmed PDF URLs, preserving SHA-256 evidence.

    Fail-closed status for missing, redirected-away, non-PDF or damaged files.
    OCR and deadline normalization require a separate verified evidence review.
    """
    if not 1 <= timeout <= 10 or not 1 <= max_bytes <= 3_000_000:
        raise ValueError("S20 recovery must remain bounded")
    reported = health.get("rows")
    if not isinstance(reported, list) or len(reported) > 5:
        raise ValueError("invalid S20 availability results")
    root = evidence or evidence_root()
    if opener is None:
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            _SameOriginHttpsRedirectHandler(_ALLOWED),
        ).open

    output: dict[str, object] = {
        "available_candidates": 0, "downloaded_count": 0,
        "native_text_count": 0, "scan_or_parse_review_count": 0,
        "failed_count": 0, "rows": [],
    }
    with connect(database) as conn:
        for item in reported:
            if not isinstance(item, dict) or item.get("status") != "PDF_ACCESSIBLE":
                continue
            output["available_candidates"] += 1
            key = str(item.get("canonical_key") or "")
            row = conn.execute(
                "SELECT payload_json FROM canonical_items WHERE canonical_key=? "
                "AND source_id='S20' AND item_kind='TENDER'",
                (key,),
            ).fetchone()
            if row is None:
                output["failed_count"] += 1
                continue
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
                url = str(payload.get("attachment_url") or "")
            except (TypeError, ValueError, AttributeError):
                url = ""
            if not _approved_url(url) or urlparse(url).path.rsplit("/", 1)[-1] != item.get("attachment_name"):
                output["failed_count"] += 1
                continue
            result: dict[str, object] = {"canonical_key": key, "attachment_name": item["attachment_name"]}
            try:
                request = urllib.request.Request(url, method="GET", headers={"Accept": "application/pdf"})
                with opener(request, timeout=timeout) as response:
                    media_type = str(response.headers.get("Content-Type", "")).lower()
                    if int(getattr(response, "status", 200)) != 200 or "pdf" not in media_type:
                        raise ValueError("GET did not return an official PDF")
                    data = response.read(max_bytes + 1)
                if len(data) > max_bytes or not data.startswith(b"%PDF-"):
                    raise ValueError("PDF body missing, invalid or exceeds size limit")
                digest = hashlib.sha256(data).hexdigest()
                path = _write_evidence("S20", data, digest, root, suffix=".pdf")
                result.update({
                    "status": "OFFICIAL_PDF_ARCHIVED_REVIEW_REQUIRED",
                    "source_sha256": digest, "bytes": len(data),
                    "evidence_path": str(path), "canonical_promotion_allowed": False,
                })
                output["downloaded_count"] += 1
                try:
                    reader = PdfReader(io.BytesIO(data), strict=False)
                    if len(reader.pages) > 12:
                        raise ValueError("PDF has too many pages for native text review")
                    text = "\n".join((page.extract_text() or "") for page in reader.pages)
                    if len(text.strip()) >= 80:
                        # Derived text retains the original PDF SHA alongside it.
                        native_path = path.with_suffix(".native.txt")
                        if not native_path.exists():
                            native_path.write_text(text[:120_000], encoding="utf-8")
                            native_path.chmod(0o640)
                        result["native_text_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
                        result["native_text_chars"] = len(text)
                        result["native_text_path"] = str(native_path)
                        result["status"] = "NATIVE_TEXT_RECOVERED_REVIEW_REQUIRED"
                        output["native_text_count"] += 1
                    else:
                        output["scan_or_parse_review_count"] += 1
                except Exception:
                    output["scan_or_parse_review_count"] += 1
            except Exception as exc:
                result["status"] = "GET_OR_PDF_REVIEW_FAILED"
                result["failure_class"] = type(exc).__name__
                output["failed_count"] += 1
            output["rows"].append(result)
    return output
