from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlparse, urlunparse

from pypdf import PdfReader

from .mpt import SitemapEntry, normalize_text

SELECTION_POLICY_VERSION = 1
MITV_BASE_URL = "https://www.myanmaritv.com"
MITV_LIST_URL = f"{MITV_BASE_URL}/news"
MDN_BASE_URL = "https://mdn.gov.mm"
MDN_LIST_URL = f"{MDN_BASE_URL}/my/latest-news"
GNLM_BASE_URL = "https://www.moi.gov.mm"
GNLM_LIST_URL = f"{GNLM_BASE_URL}/nlm/"
MYAWADY_LIST_URL = "https://myawady.net.mm/english_news"

_OPEN_PROCUREMENT_TOKENS = (
    "open tender", "invitation to tender", "invitation for bid", "invitation to bid",
    "request for proposal", "request for quotation", "အိတ်ဖွင့်တင်ဒါ",
    "အိတ်ဖွင့်တင်ဒါ", "တင်ဒါခေါ်ယူ",
)

_CATEGORY_TOKENS: dict[str, tuple[str, ...]] = {
    "DIGITAL_GOVERNMENT": (
        "e-government", "e government", "digital government", "digital governance",
        "single window", "one-stop digital", "one stop digital", "edms",
        "electronic document management", "open government data",
        "digital development strategy", "digital development law",
        "ဒီဂျစ်တယ်အစိုးရ", "ဒီဂျစ်တယ် အစိုးရ",
    ),
    "CYBERSECURITY": (
        "cybersecurity", "cyber security", "information security", "cyber-security",
        "ဆိုက်ဘာလုံခြုံ", "သတင်းအချက်အလက်လုံခြုံ",
    ),
    "ICT_INFRASTRUCTURE": (
        " ict ", "ict infrastructure", "digital infrastructure", "cloud platform",
        "cloud service", "data center", "data centre", "shared platform",
        "shared digital", "fiber", "fibre", "telecom", "telecommunication",
        "5g", "digital platform", "government network", "national network",
        "ကွန်ရက်", "ဆက်သွယ်ရေး", "ဒေတာစင်တာ", "ကွန်ပျူတာစနစ်",
    ),
}

_FORWARD_ACTION_TOKENS = (
    "implement", "implementation", "transition", "plan", "planning", "strategy",
    "law", "framework", "public-private partnership", "public private partnership",
    " ppp ", "establish", "development", "develop", "upgrade", "build", "approval",
    "approved", "budget", "fund", "procurement plan", "tender preparation",
    "rollout", "platform", "service", "system", "coordination", "roadmap",
    "အကောင်အထည်ဖော်", "မဟာဗျူဟာ", "ဥပဒေ", "အစီအစဉ်", "ဖွံ့ဖြိုး",
    "ညှိနှိုင်း", "စနစ်", "ဝန်ဆောင်မှု",
)

_POLICY_TOKENS = (
    "strategy", "law", "framework", "roadmap", "policy", "digital governance",
    "မဟာဗျူဟာ", "ဥပဒေ", "မူဝါဒ",
)
_PREPROCUREMENT_TOKENS = (
    "procurement plan", "tender preparation", "budget", "fund allocation",
    "funding approved", "ဘတ်ဂျက်", "တင်ဒါပြင်ဆင်",
)
_PPP_TOKENS = ("public-private partnership", "public private partnership", " ppp ")
_IMPLEMENTATION_TOKENS = (
    "implementation", "implement", "transition", "rollout", "platform", "service",
    "system", "coordination", "အကောင်အထည်ဖော်", "ညှိနှိုင်း", "စနစ်",
)


class OfficialMediaParseError(ValueError):
    pass


def _classes(attrs) -> set[str]:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == "class" and value:
            return set(str(value).split())
    return set()


def _attr(attrs, name: str) -> str | None:  # type: ignore[no-untyped-def]
    for key, value in attrs:
        if key == name and value is not None:
            return str(value)
    return None


def _attrs(attrs) -> dict[str, str]:  # type: ignore[no-untyped-def]
    return {str(key): str(value) for key, value in attrs if value is not None}


def _lower(value: str) -> str:
    return f" {normalize_text(unescape(value)).lower()} "


def _contains_any(value: str, tokens: tuple[str, ...]) -> bool:
    normalized = _lower(value)
    return any(token.lower() in normalized for token in tokens)


def relevance_categories(value: str) -> list[str]:
    normalized = _lower(value)
    return [
        category
        for category, tokens in _CATEGORY_TOKENS.items()
        if any(token.lower() in normalized for token in tokens)
    ]


def _has_forward_action(value: str) -> bool:
    return _contains_any(value, _FORWARD_ACTION_TOKENS)


def _is_open_procurement(value: str) -> bool:
    return _contains_any(value, _OPEN_PROCUREMENT_TOKENS)


def _listing_candidate(title: str) -> bool:
    return bool(relevance_categories(title)) and not _is_open_procurement(title)


def _stage_hint(value: str) -> str:
    if _contains_any(value, _PREPROCUREMENT_TOKENS):
        return "PRE_PROCUREMENT"
    if _contains_any(value, _PPP_TOKENS):
        return "PPP_FORMATION"
    if _contains_any(value, _POLICY_TOKENS):
        return "POLICY_FORMATION"
    if _contains_any(value, _IMPLEMENTATION_TOKENS):
        return "IMPLEMENTATION_PREP"
    return "OFFICIAL_SIGNAL"


def _scope_summary(text: str, *, max_chars: int = 1800) -> str:
    normalized = normalize_text(text)
    lowered = normalized.lower()
    positions = [
        lowered.find(token.strip().lower())
        for tokens in _CATEGORY_TOKENS.values()
        for token in tokens
        if token.strip() and lowered.find(token.strip().lower()) >= 0
    ]
    if not positions:
        return normalized[:max_chars]
    center = min(positions)
    start = max(0, center - 450)
    end = min(len(normalized), start + max_chars)
    return normalized[start:end]


def _iso_date(value: str) -> str | None:
    text = normalize_text(value)
    patterns = (
        ("%Y-%m-%d", r"20\d{2}-\d{2}-\d{2}"),
        ("%d/%m/%y", r"\d{1,2}/\d{1,2}/\d{2}"),
        ("%d/%m/%Y", r"\d{1,2}/\d{1,2}/20\d{2}"),
        ("%d %B %Y", r"\d{1,2}\s+[A-Za-z]+\s+20\d{2}"),
        ("%b %d,%Y", r"[A-Za-z]{3}\s+\d{1,2},20\d{2}"),
        ("%B %d, %Y", r"[A-Za-z]+\s+\d{1,2},\s+20\d{2}"),
    )
    for fmt, pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(0), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _iso_listing_time(value: str) -> str | None:
    text = normalize_text(value)
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is not None:
            return dt.isoformat()
    except ValueError:
        pass
    date = _iso_date(text)
    return f"{date}T00:00:00+06:30" if date else None


def _canonical_https(base_url: str, href: str, *, hosts: set[str], path_prefix: str) -> str | None:
    absolute = urljoin(base_url, unescape(href))
    parsed = urlparse(absolute)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme not in {"http", "https"}
        or host not in hosts
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 80, 443)
        or not parsed.path.startswith(path_prefix)
    ):
        return None
    return urlunparse(("https", parsed.netloc, parsed.path, "", parsed.query, ""))


@dataclass(frozen=True)
class OfficialMediaSignal:
    source_tag: str
    record_id: str
    issuer: str
    title: str
    publication_date: str
    scope_summary: str
    relevance_categories: tuple[str, ...]
    precursor_stage_hint: str
    url: str

    item_kind = "REGULATORY_NOTICE"
    deadline = None
    location = "Myanmar"

    @property
    def canonical_key(self) -> str:
        return f"official-media:{self.source_tag}:{self.record_id}"

    @property
    def reference_no(self) -> str:
        return f"{self.source_tag.upper()}-{self.record_id}"

    @property
    def project_name(self) -> str:
        return self.title

    def payload(self) -> dict[str, object]:
        return {
            "item_kind": self.item_kind,
            "issuer": self.issuer,
            "title": self.title,
            "project_name": self.project_name,
            "reference_no": self.reference_no,
            "reference_no_kind": "official_media_record",
            "source_record_id": self.record_id,
            "publication_date": self.publication_date,
            "deadline": None,
            "location": self.location,
            "scope_summary": self.scope_summary,
            "selection_policy_version": SELECTION_POLICY_VERSION,
            "business_stage": "PROJECT_PRECURSOR_CANDIDATE",
            "precursor_stage_hint": self.precursor_stage_hint,
            "precursor_review_required": True,
            "precursor_selection_basis": (
                "OFFICIAL_MEDIA+DIGITAL_ICT_SCOPE+FORWARD_ACTION-NOT_OPEN_PROCUREMENT"
            ),
            "relevance_categories": list(self.relevance_categories),
            "detail_completeness": "OFFICIAL_MEDIA_TITLE_DATE_BODY",
            "url": self.url,
        }


def _build_signal(
    *,
    source_tag: str,
    record_id: str,
    issuer: str,
    title: str,
    publication_date: str | None,
    body: str,
    url: str,
) -> OfficialMediaSignal | None:
    title = normalize_text(title)
    body = normalize_text(body)
    combined = normalize_text(f"{title} {body}")
    categories = relevance_categories(combined)
    if (
        not title
        or not body
        or publication_date is None
        or not categories
        or not _has_forward_action(combined)
        or _is_open_procurement(combined)
    ):
        return None
    return OfficialMediaSignal(
        source_tag=source_tag,
        record_id=record_id,
        issuer=issuer,
        title=title,
        publication_date=publication_date,
        scope_summary=_scope_summary(body),
        relevance_categories=tuple(categories),
        precursor_stage_hint=_stage_hint(combined),
        url=url,
    )


class _MitvListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._row_depth = 0
        self._title_depth = 0
        self._href: str | None = None
        self._title: list[str] = []
        self._date: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        classes = _classes(attrs)
        if tag == "div":
            if self._row_depth:
                self._row_depth += 1
            elif "views-row" in classes:
                self._row_depth = 1
                self._href = None
                self._title = []
                self._date = None
                return
        if not self._row_depth:
            return
        if tag == "div" and "title" in classes:
            self._title_depth = 1
            return
        if tag == "span" and "date-display-single" in classes:
            self._date = _attr(attrs, "content") or self._date
        if self._title_depth:
            if tag == "a":
                href = _attr(attrs, "href")
                if href and href.startswith("/news/"):
                    self._href = href
            if tag not in {"br", "img", "meta", "link", "input", "hr"}:
                self._title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if not self._row_depth:
            return
        if self._title_depth and tag not in {"br", "img", "meta", "link", "input", "hr"}:
            self._title_depth -= 1
        if tag == "div":
            self._row_depth -= 1
            if self._row_depth == 0:
                title = normalize_text(" ".join(self._title))
                if self._href and self._date and _listing_candidate(title):
                    url = _canonical_https(
                        MITV_BASE_URL, self._href,
                        hosts={"myanmaritv.com", "www.myanmaritv.com"}, path_prefix="/news/",
                    )
                    lastmod = _iso_listing_time(self._date)
                    if url and lastmod:
                        self.entries.append(SitemapEntry(url, lastmod))

    def handle_data(self, data: str) -> None:
        if self._row_depth and self._title_depth:
            value = normalize_text(data)
            if value:
                self._title.append(value)


def parse_mitv_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = _MitvListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    dedup = {entry.url: entry for entry in parser.entries}
    return list(dedup.values())


class _MitvDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.date: str | None = None
        self._body_depth = 0
        self.body: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        values = _attrs(attrs)
        classes = _classes(attrs)
        if tag == "span" and values.get("property") == "dc:title":
            self.title = values.get("content") or self.title
        if tag == "span" and "date-display-single" in classes:
            self.date = values.get("content") or self.date
        if tag == "div" and "field-name-body" in classes:
            self._body_depth = 1
            return
        if self._body_depth and tag not in {"br", "img", "meta", "link", "input", "hr"}:
            self._body_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._body_depth and tag not in {"br", "img", "meta", "link", "input", "hr"}:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._body_depth:
            value = normalize_text(data)
            if value:
                self.body.append(value)


def parse_mitv_detail(html_bytes: bytes, page_url: str) -> OfficialMediaSignal | None:
    canonical = _canonical_https(
        MITV_BASE_URL, page_url,
        hosts={"myanmaritv.com", "www.myanmaritv.com"}, path_prefix="/news/",
    )
    if canonical is None:
        return None
    parser = _MitvDetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    record_id = urlparse(canonical).path.rstrip("/").split("/")[-1]
    return _build_signal(
        source_tag="mitv",
        record_id=record_id,
        issuer="Myanmar International TV (MITV)",
        title=parser.title or "",
        publication_date=_iso_date(parser.date or ""),
        body=" ".join(parser.body),
        url=canonical,
    )


class _MdnListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._card_depth = 0
        self._title_depth = 0
        self._date_depth = 0
        self._href: str | None = None
        self._title: list[str] = []
        self._date: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        classes = _classes(attrs)
        if tag == "div":
            if self._card_depth:
                self._card_depth += 1
            elif {"card", "mb-3", "shadow"}.issubset(classes):
                self._card_depth = 1
                self._href = None
                self._title = []
                self._date = []
                return
        if not self._card_depth:
            return
        if tag == "h5" and "card-title" in classes:
            self._title_depth = 1
            return
        if tag == "p" and "card-text" in classes:
            self._date_depth = 1
            return
        if self._title_depth:
            if tag == "a":
                href = _attr(attrs, "href")
                if href:
                    self._href = href
            if tag not in {"br", "img", "meta", "link", "input", "hr"}:
                self._title_depth += 1
        if self._date_depth and tag not in {"br", "img", "meta", "link", "input", "hr", "i"}:
            self._date_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if not self._card_depth:
            return
        if self._title_depth and tag not in {"br", "img", "meta", "link", "input", "hr"}:
            self._title_depth -= 1
        if self._date_depth and tag not in {"br", "img", "meta", "link", "input", "hr", "i"}:
            self._date_depth -= 1
        if tag == "div":
            self._card_depth -= 1
            if self._card_depth == 0:
                title = normalize_text(" ".join(self._title))
                date = _iso_date(" ".join(self._date))
                if self._href and date and _listing_candidate(title):
                    url = _canonical_https(
                        MDN_BASE_URL, self._href,
                        hosts={"mdn.gov.mm", "www.mdn.gov.mm"}, path_prefix="/my/",
                    )
                    if url:
                        self.entries.append(SitemapEntry(url, f"{date}T00:00:00+06:30"))

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._title_depth:
            self._title.append(value)
        if self._date_depth:
            self._date.append(value)


def parse_mdn_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = _MdnListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    dedup = {entry.url: entry for entry in parser.entries}
    return list(dedup.values())


class _MdnDetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.canonical: str | None = None
        self._post_meta_depth = 0
        self._body_depth = 0
        self.meta_text: list[str] = []
        self.body: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        values = _attrs(attrs)
        classes = _classes(attrs)
        if tag == "meta" and values.get("property") == "og:title":
            self.title = values.get("content") or self.title
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href") or self.canonical
        if tag == "div" and "post-meta" in classes:
            self._post_meta_depth = 1
            return
        if tag == "div" and "field--name-body" in classes:
            self._body_depth = 1
            return
        if self._post_meta_depth and tag not in {"br", "img", "meta", "link", "input", "hr"}:
            self._post_meta_depth += 1
        if self._body_depth and tag not in {"br", "img", "meta", "link", "input", "hr"}:
            self._body_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._post_meta_depth and tag not in {"br", "img", "meta", "link", "input", "hr"}:
            self._post_meta_depth -= 1
        if self._body_depth and tag not in {"br", "img", "meta", "link", "input", "hr"}:
            self._body_depth -= 1

    def handle_data(self, data: str) -> None:
        value = normalize_text(data)
        if not value:
            return
        if self._post_meta_depth:
            self.meta_text.append(value)
        if self._body_depth:
            self.body.append(value)


def parse_mdn_detail(html_bytes: bytes, page_url: str) -> OfficialMediaSignal | None:
    parser = _MdnDetailParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    canonical = _canonical_https(
        MDN_BASE_URL, parser.canonical or page_url,
        hosts={"mdn.gov.mm", "www.mdn.gov.mm"}, path_prefix="/my/",
    )
    if canonical is None:
        return None
    record_id = unquote(urlparse(canonical).path.rstrip("/").split("/")[-1])
    return _build_signal(
        source_tag="mdn",
        record_id=record_id,
        issuer="Myanmar Digital News (MDN)",
        title=parser.title or "",
        publication_date=_iso_date(" ".join(parser.meta_text)),
        body=" ".join(parser.body),
        url=canonical,
    )


class _GnlmListingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[SitemapEntry] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        if tag != "a":
            return
        href = _attr(attrs, "href")
        if not href:
            return
        url = _canonical_https(
            GNLM_BASE_URL, href,
            hosts={"moi.gov.mm", "www.moi.gov.mm"}, path_prefix="/nlm/",
        )
        if url and re.fullmatch(r"/nlm/\d{1,2}-[a-z]+-20\d{2}", urlparse(url).path, re.I):
            self._href = url
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            date = _iso_date(" ".join(self._text))
            if date:
                self.entries.append(SitemapEntry(self._href, f"{date}T00:00:00+06:30"))
            self._href = None
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            value = normalize_text(data)
            if value:
                self._text.append(value)


def parse_gnlm_listing(html_bytes: bytes) -> list[SitemapEntry]:
    parser = _GnlmListingParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    dedup = {entry.url: entry for entry in parser.entries}
    return list(dedup.values())


class _GnlmPdfParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[no-untyped-def]
        values = _attrs(attrs)
        candidates: list[str] = []
        if tag == "a" and values.get("href"):
            candidates.append(values["href"])
        if tag == "iframe" and values.get("src"):
            src = unescape(values["src"])
            match = re.search(r"(?:[?&]|&amp;)url=([^&]+)", src)
            if match:
                candidates.append(unquote(match.group(1)))
        for raw in candidates:
            url = _canonical_https(
                self.page_url, raw,
                hosts={"moi.gov.mm", "www.moi.gov.mm"}, path_prefix="/nlm/",
            )
            if url and (
                urlparse(url).path.lower().endswith(".pdf")
                or "/nlm/file-download/download/public/" in urlparse(url).path
            ):
                self.urls.append(url)


def extract_gnlm_pdf_urls(html_bytes: bytes, page_url: str) -> list[str]:
    parser = _GnlmPdfParser(page_url)
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    return list(dict.fromkeys(parser.urls))[:1]


def _gnlm_issue_date(page_url: str) -> str | None:
    slug = urlparse(page_url).path.rstrip("/").split("/")[-1].replace("-", " ")
    return _iso_date(slug)


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes.startswith(b"%PDF-"):
        raise OfficialMediaParseError("GNLM attachment is not a PDF")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages[:20])


def _gnlm_candidate_windows(text: str) -> list[str]:
    normalized = normalize_text(text)
    lowered = normalized.lower()
    exact = re.search(
        r"Push\s+to\s+Transition\s+from\s+E-Government\s+to\s+Digital\s+Governance",
        normalized,
        re.I,
    )
    if exact:
        center = exact.start()
        return [normalized[max(0, center - 2600): min(len(normalized), center + 1800)]]
    positions: list[int] = []
    for tokens in _CATEGORY_TOKENS.values():
        for token in tokens:
            needle = token.strip().lower()
            if not needle:
                continue
            offset = 0
            while True:
                pos = lowered.find(needle, offset)
                if pos < 0:
                    break
                positions.append(pos)
                offset = pos + len(needle)
    windows: list[str] = []
    for center in sorted(set(positions)):
        window = normalized[max(0, center - 1200): min(len(normalized), center + 1800)]
        if window not in windows:
            windows.append(window)
    return windows[:20]


def parse_gnlm_text_signal(
    text: str,
    *,
    page_url: str,
    publication_date: str | None = None,
) -> OfficialMediaSignal | None:
    normalized = normalize_text(text)
    date = publication_date or _gnlm_issue_date(page_url)
    if date is None:
        return None
    exact_title = re.search(
        r"Push\s+to\s+Transition\s+from\s+E-Government\s+to\s+Digital\s+Governance",
        normalized,
        re.I,
    )
    for window in _gnlm_candidate_windows(normalized):
        categories = relevance_categories(window)
        if not categories or not _has_forward_action(window) or _is_open_procurement(window):
            continue
        if exact_title and exact_title.group(0).lower() in window.lower():
            title = "Push to Transition from E-Government to Digital Governance"
        else:
            category_token = next(
                (
                    token.strip()
                    for tokens in _CATEGORY_TOKENS.values()
                    for token in tokens
                    if token.strip() and token.strip().lower() in window.lower()
                ),
                "Digital/ICT",
            )
            title = f"GNLM official {category_token} signal — {date}"
        record_id = urlparse(page_url).path.rstrip("/").split("/")[-1]
        return OfficialMediaSignal(
            source_tag="gnlm",
            record_id=record_id,
            issuer="The Global New Light of Myanmar (GNLM)",
            title=title,
            publication_date=date,
            scope_summary=_scope_summary(window),
            relevance_categories=tuple(categories),
            precursor_stage_hint=_stage_hint(window),
            url=page_url,
        )
    return None

def parse_gnlm_detail_with_attachments(
    html_bytes: bytes,
    page_url: str,
    attachments: list[tuple[str, bytes]],
) -> list[OfficialMediaSignal]:
    if len(attachments) != 1:
        raise OfficialMediaParseError("GNLM requires exactly one primary PDF attachment")
    attachment_url, pdf_bytes = attachments[0]
    allowed = extract_gnlm_pdf_urls(html_bytes, page_url)
    if attachment_url not in allowed:
        raise OfficialMediaParseError("GNLM PDF attachment does not match reviewed issue page")
    signal = parse_gnlm_text_signal(_extract_pdf_text(pdf_bytes), page_url=page_url)
    return [signal] if signal is not None else []
