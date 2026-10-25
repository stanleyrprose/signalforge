"""Build a reproducible, not-yet-sent S01 edition manifest from AI coverage."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .s01_daily_ledger import S01Ledger, edition_identity
from .s01_daily_pdf import render_digest
from .s01_attachment import render_markdown


def prepare(audit_path: Path, ledger_path: Path, output_dir: Path,
            *, day: str, fontfile: Path) -> dict:
    report = json.loads(audit_path.read_text(encoding="utf-8"))
    pagination_path = audit_path.parent / "s01-news-coverage-audit.json"
    if not pagination_path.is_file():
        raise ValueError("pagination audit required before daily edition")
    pagination = json.loads(pagination_path.read_text(encoding="utf-8"))
    if pagination.get("pagination_incomplete") or any(
        page.get("status") == "FETCH_FAILED" for page in pagination.get("pages", [])):
        raise ValueError("pagination fetch incomplete")
    if report.get("excluded", 0):
        raise ValueError("news must not be excluded by importance")
    if report["included"] < 1 or report["included"] + report["unresolved"] != report["total_discovered"]:
        raise ValueError("S01 article accounting mismatch")
    # A successful article-level audit does not prove that all listing pages were fetched.
    if report.get("pagination_incomplete") or report.get("coverage_incomplete"):
        raise ValueError("source pagination/coverage incomplete")
    included = [x for x in report["items"] if x["disposition"] == "INCLUDED"]
    if len(included) != report["included"]:
        raise ValueError("included count mismatch")
    discovered_urls = [item["url"] for item in report["items"]]
    candidate_urls = pagination.get("candidate_urls")
    if not isinstance(candidate_urls, list) or not candidate_urls:
        raise ValueError("pagination audit must list candidate URLs")
    if len(discovered_urls) != len(set(discovered_urls)):
        raise ValueError("duplicate article URLs in AI audit")
    if set(discovered_urls) != set(candidate_urls) or len(candidate_urls) != len(set(candidate_urls)):
        raise ValueError("pagination/article audit URL mismatch; stale or missing news")
    from .s01_daily_ledger import article_identity
    by_identity = {}
    for item in included:
        identity = article_identity(item["url"])
        previous = by_identity.get(identity)
        current = (item["detail_sha256"], item.get("content_sha256"))
        if (previous is not None and previous[0] != current[0]
                and (previous[1] is None or previous[1] != current[1])):
            raise ValueError("same article identity has conflicting body hashes; review required")
        by_identity[identity] = current
    ledger = S01Ledger(ledger_path)
    try:
        for item in included:
            ai = item["ai_review"]
            if not ai or not item.get("detail_sha256"):
                raise ValueError("article has no validated translation/evidence")
        # Do not mutate the Mac delivery ledger until a Bangkok receipt is imported.
        # The sender maintains its own independent delivery state.
        pending = set()
        delivered = ledger.delivered_versions()
        for item in included:
            identity = article_identity(item["url"])
            versions = delivered.get(identity, {"raw": set(), "content": set()})
            if (item["detail_sha256"] not in versions["raw"]
                    and item.get("content_sha256") not in versions["content"]):
                pending.add((identity, item["detail_sha256"]))
        new_items = []
        seen_identities = set()
        for item in included:
            identity = article_identity(item["url"])
            if (identity, item["detail_sha256"]) in pending and identity not in seen_identities:
                new_items.append(item)
                seen_identities.add(identity)
        if not new_items:
            return {"status": "NO_NEW_ARTICLES", "date": day, "count": 0}
        subreport = {"items": new_items, "included": len(new_items),
                     "total_discovered": len(new_items), "excluded": 0, "unresolved": 0}
        output_dir.mkdir(parents=True, exist_ok=True)
        identities = sorted({(article_identity(x["url"]), x["detail_sha256"]) for x in new_items})
        edition = edition_identity(day, identities)
        pdf = output_dir / f"S01-Chinese-News-{day}-{edition[:12]}.md"
        if pdf.exists():
            raise ValueError("edition Markdown already exists; reuse immutable manifest or reconcile")
        pdf.write_text(render_markdown({**subreport, "pending_articles": [
            {"url": x["url"], "reason": x.get("exclusion_reason")} for x in report["items"]
            if x["disposition"] != "INCLUDED"]}, edition_date=day), encoding="utf-8")
        result = {"markdown": str(pdf), "articles": len(new_items), "bytes": pdf.stat().st_size}
        manifest = {
            "incomplete_count": report["unresolved"],
            "pending_articles": [{"url": x["url"], "reason": x.get("exclusion_reason")} for x in report["items"] if x["disposition"] != "INCLUDED"],
            "date": day, "edition_id": edition,
            "articles": [{"identity": identity, "detail_sha": sha,
                          "url": next(item["url"] for item in new_items
                                      if article_identity(item["url"]) == identity),
                          **next({k: item[k] for k in ("content_sha256", "ai_review") if k in item}
                                 for item in new_items if article_identity(item["url"]) == identity)}
                         for identity, sha in identities],
            "markdown": str(pdf), "markdown_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
            "digest": render_digest(subreport, edition_date=day) + (f"\n待补采/补译：{report['unresolved']} 条，详见审计记录。" if report["unresolved"] else ""),
            "caption": f"S01 缅甸政府门户中文新闻｜{day}｜{len(new_items)}条"
        }
        manifest_path = output_dir / f"S01-manifest-{day}-{edition[:12]}.json"
        encoded = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        if manifest_path.exists() and manifest_path.read_bytes() != encoded:
            raise ValueError("immutable edition manifest conflict")
        if not manifest_path.exists():
            manifest_path.write_bytes(encoded)
        return {"status": "READY_FOR_REVIEW", "manifest": str(manifest_path),
                "edition_id": edition, **result}
    finally:
        ledger.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--date", required=True)
    parser.add_argument("--font", type=Path, default=Path("/System/Library/Fonts/Hiragino Sans GB.ttc"))
    args = parser.parse_args()
    print(json.dumps(prepare(args.audit, args.ledger, args.output_dir,
                             day=args.date, fontfile=args.font), ensure_ascii=False))


if __name__ == "__main__":
    main()
