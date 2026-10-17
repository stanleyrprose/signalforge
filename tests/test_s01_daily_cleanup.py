"""S01 handoff failure matrix (authored only; not run without approval)."""
import hashlib
import json
from pathlib import Path

import pytest

from signalforge.s01_daily_cleanup import cleanup


def test_cleanup_rejects_missing_receipt(tmp_path, monkeypatch):
    edition = "a" * 64
    folder = tmp_path / edition
    folder.mkdir()
    (folder / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr("signalforge.s01_daily_cleanup.accept",
                        lambda _: {"edition_id": edition})
    with pytest.raises(ValueError, match="no Telegram receipt"):
        cleanup(tmp_path, edition)
    assert folder.exists()


def test_cleanup_rejects_wrong_manifest_hash(tmp_path, monkeypatch):
    edition = "a" * 64
    folder = tmp_path / edition
    folder.mkdir()
    (folder / "manifest.json").write_text('{"articles":[]}', encoding="utf-8")
    (folder / "manifest.receipt.json").write_text(json.dumps({
        "edition_id": edition, "manifest_sha256": "0" * 64,
        "telegram": {"digest": 100, "pdf": 101}, "articles": []
    }), encoding="utf-8")
    monkeypatch.setattr("signalforge.s01_daily_cleanup.accept",
                        lambda _: {"edition_id": edition})
    with pytest.raises(ValueError, match="mismatched"):
        cleanup(tmp_path, edition)
    assert folder.exists()


def test_cleanup_rejects_unexpected_files(tmp_path, monkeypatch):
    edition = "a" * 64
    folder = tmp_path / edition
    folder.mkdir()
    manifest = {"articles": [], "pdf": "daily.pdf"}
    raw = json.dumps(manifest).encode()
    (folder / "manifest.json").write_bytes(raw)
    (folder / "daily.pdf").write_bytes(b"PDF")
    (folder / "READY").write_text(edition)
    (folder / "extra.txt").write_text("do not delete")
    (folder / "manifest.receipt.json").write_text(json.dumps({
        "edition_id": edition, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "telegram": {"digest": 100, "pdf": 101}, "articles": []
    }), encoding="utf-8")
    monkeypatch.setattr("signalforge.s01_daily_cleanup.accept",
                        lambda _: {"edition_id": edition})
    with pytest.raises(ValueError, match="unexpected files"):
        cleanup(tmp_path, edition)
    assert (folder / "extra.txt").exists()
