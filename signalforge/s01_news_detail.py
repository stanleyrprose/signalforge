"""Evidence-backed S01 news detail extraction (separate from tender signals)."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path

from .http import fetch_s01_news_unverified_tls


class _Article(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts = []
        self.skip = 0
        self.found = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if self.depth:
            if tag not in ("br", "img", "hr", "input", "meta", "link", "source", "wbr"):
                self.depth += 1
            if tag in ("script", "style"):
                self.skip += 1
        elif tag == "div" and "journal-content-article" in attributes.get("class", "").split():
            self.depth = 1
            self.found = True
        if self.depth and tag in ("p", "div", "br", "li", "h1", "h2", "h3"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("br", "img", "hr", "input", "meta", "link", "source", "wbr"):
            return
        if self.depth:
            if tag in ("script", "style") and self.skip:
                self.skip -= 1
            self.depth -= 1

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.parts.append(data)


def extract_article_text(payload: bytes) -> str:
    parser = _Article()
    parser.feed(payload.decode("utf-8", errors="replace"))
    if not parser.found:
        return ""
    return "\n".join(line.strip() for line in " ".join(parser.parts).splitlines() if line.strip())


def acquire_detail(url: str, evidence_dir: Path, *, payload: bytes | None = None) -> dict:
    if payload is None:
        payload = fetch_s01_news_unverified_tls(url)
    digest = hashlib.sha256(payload).hexdigest()
    text = extract_article_text(payload)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / f"s01-news-detail-{digest}.html"
    if not path.exists():
        path.write_bytes(payload)
    return {
        "url": url,
        "detail_sha256": digest,
        "detail_evidence_path": str(path),
        "body_text": text,
        "body_chars": len(text),
        "status": "DETAIL_EXTRACTED_UNCORROBORATED" if len(text) >= 100 else "DETAIL_REVIEW_REQUIRED",
    }
