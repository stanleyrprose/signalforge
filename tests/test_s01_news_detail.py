from pathlib import Path
from tempfile import TemporaryDirectory

from signalforge.s01_news_detail import acquire_detail, extract_article_text


def test_extract_detail_handles_malformed_br_and_excludes_navigation():
    html = b'<div>navigation</div><div class="journal-content-article"><h2>Title</h2><br><p>Body content</p></br><p>More body</p></div><div>footer</div>'
    text = extract_article_text(html)
    assert "Title" in text and "Body content" in text and "More body" in text
    assert "navigation" not in text and "footer" not in text


def test_acquire_detail_keeps_original_html_and_review_state():
    html = b'<div class="journal-content-article"><p>' + b"hello " * 40 + b'</p></div>'
    with TemporaryDirectory() as temp:
        result = acquire_detail("https://myanmar.gov.mm/en/news-media/news/latest-news/example", Path(temp), payload=html)
        assert result["status"] == "DETAIL_EXTRACTED_UNCORROBORATED"
        assert Path(result["detail_evidence_path"]).read_bytes() == html
        assert "hello" in result["body_text"]
