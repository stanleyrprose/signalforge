"""Bounded issuer-PDF availability check, not a PDF content parser."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from .db import connect


def probe_recent_s20_attachments(
    database: Path, *, now: datetime | None = None,
    max_checks: int = 5, timeout: int = 6, opener=None,
) -> dict[str, object]:
    """HEAD at most five issuer-linked PDFs. Never invent missing tender facts."""
    if not 1 <= max_checks <= 5 or not 1 <= timeout <= 10:
        raise ValueError("S20 attachment check must remain bounded")
    opener = opener or urllib.request.urlopen
    today = (now or datetime.now(UTC)).astimezone(UTC)
    cutoff = (today - timedelta(days=45)).date().isoformat()
    with connect(database) as conn:
        rows = conn.execute(
            "SELECT canonical_key,payload_json FROM canonical_items "
            "WHERE source_id='S20' AND item_kind='TENDER' AND publication_date>=? "
            "AND deadline IS NULL ORDER BY publication_date DESC LIMIT 25",
            (cutoff,),
        ).fetchall()
    urls = {}
    for row in rows:
        try:
            payload = json.loads(str(row["payload_json"] or "{}"))
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        url = str(payload.get("attachment_url") or "")
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower() not in {"moep.gov.mm", "www.moep.gov.mm"}
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443)
            or not re.fullmatch(r"/mm/userfile/[^/]+\.pdf", parsed.path, re.I)
            or parsed.query or parsed.fragment
        ):
            continue
        urls.setdefault(url, str(row["canonical_key"]))
        if len(urls) == max_checks:
            break

    results = []
    for url, key in urls.items():
        request = urllib.request.Request(url, method="HEAD")
        try:
            with opener(request, timeout=timeout) as response:
                code = int(getattr(response, "status", 200))
                content_type = str(response.headers.get("Content-Type", "")).lower()
                status = "PDF_ACCESSIBLE" if code == 200 and "pdf" in content_type else f"HTTP_{code}_NON_PDF"
        except urllib.error.HTTPError as exc:
            status = f"HTTP_{exc.code}"
        except Exception as exc:
            status = f"CHECK_FAILED_{type(exc).__name__}"
        results.append({"canonical_key": key, "attachment_name": urlparse(url).path.rsplit("/", 1)[-1], "status": status})

    missing = sum(row["status"] == "HTTP_404" for row in results)
    healthy = sum(row["status"] == "PDF_ACCESSIBLE" for row in results)
    return {
        "status": "DEGRADED_HTTP_404" if missing else "AVAILABLE" if results and healthy == len(results) else "UNPROVEN",
        "checked_count": len(results),
        "http_404_count": missing,
        "pdf_accessible_count": healthy,
        "rows": results,
        "meaning": "Availability only; HEAD responses do not authorize PDF-derived item, quantity, or deadline fields",
    }
