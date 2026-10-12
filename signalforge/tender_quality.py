"""Read-only evidence-backed completeness audit for formal tender sources."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .config import Registry, db_path
from .db import connect


def tender_quality(*, database: Path | None = None, registry: Registry | None = None) -> dict[str, object]:
    """Require item, quantity and submission deadline in one canonical tender.

    No records is UNKNOWN, not an unhealthy source; no network requests are made.
    """
    registry = registry or Registry.load()
    sources = registry.raw["sources"]
    results = {sid: {"source_id": sid, "status": "NO_OBSERVED_TENDERS", "observed": 0,
                     "complete": 0, "examples": [], "missing": {"item": 0, "quantity": 0, "deadline": 0}}
               for sid, cfg in sources.items() if cfg.get("enabled") is True and cfg.get("item_kind") == "TENDER"}
    with connect(database or db_path()) as conn:
        for row in conn.execute("SELECT source_id,canonical_key,url,payload_json,deadline FROM canonical_items WHERE item_kind='TENDER'"):
            sid = str(row["source_id"])
            if sid not in results:
                continue
            result = results[sid]
            result["observed"] += 1
            try:
                payload = json.loads(row["payload_json"] or "{}")
            except (ValueError, TypeError):
                payload = {}
            item = any(str(payload.get(k) or "").strip() for k in ("scope_summary", "project_name", "required_items", "items"))
            quantity = any(str(payload.get(k) or "").strip() for k in ("required_quantity", "quantity", "quantities", "lots", "quantity_or_lot_summary"))
            deadline = bool(str(row["deadline"] or payload.get("deadline") or "").strip())
            missing = [name for name, present in (("item", item), ("quantity", quantity), ("deadline", deadline)) if not present]
            for name in missing:
                result["missing"][name] += 1
            if not missing:
                result["complete"] += 1
            if len(result["examples"]) < 3:
                result["examples"].append({"canonical_key": row["canonical_key"], "url": row["url"], "missing": missing})
    for result in results.values():
        if result["observed"]:
            result["status"] = "COMPLETE_OBSERVED" if result["complete"] else "INCOMPLETE_OBSERVED"
    return {"generated_at": datetime.now(UTC).isoformat(), "definition": "same canonical tender: item + quantity + deadline", "source_count": len(results), "sources": list(results.values()), "limitation": "Database-only completeness; network availability and original-document semantic correctness require independent live evidence review."}
