from __future__ import annotations

import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from signalforge.acquisition_runtime import (
    ProviderDiagnosticCapture,
    acquire_provider_document_ocr,
)


URL = "https://myanmar.gov.mm/documents/20143/0/tender.pdf/abc"
SHA = "a" * 64
REQUEST_ID = str(uuid.uuid4())


def _payload(*, page_count: int = 1, processed_pages: int = 1, truncated: bool = False) -> dict:
    return {
        "fetch": {
            "url": URL,
            "status": 200,
            "content_type": "application/pdf",
            "body_bytes": 34575,
            "sha256": SHA,
        },
        "document_ocr": {
            "engine": "tesseract",
            "rasterizer": "macOS PDFKit",
            "model_profile": "tessdata_best",
            "languages": ["mya", "eng"],
            "psm": 6,
            "input_sha256": SHA,
            "input_bytes": 34575,
            "page_count": page_count,
            "processed_pages": processed_pages,
            "page_limit_truncated": truncated,
            "pages": [{"page": index + 1, "text": f"page {index + 1}"} for index in range(processed_pages)],
            "text": "official tender OCR evidence",
            "mean_confidence": 78.5,
            "network_access": False,
            "intermediate_images_retained": False,
        },
    }


def _capture(payload: dict) -> ProviderDiagnosticCapture:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return ProviderDiagnosticCapture(
        payload=raw,
        provider_request_id=REQUEST_ID,
        sha256="b" * 64,
        media_type="application/json",
        final_url=URL,
        http_status=200,
        artifact_path="/tmp/provider-result.json",
    )


class ProviderDocumentOCRTests(unittest.TestCase):
    def test_wrapper_freezes_s01_document_ocr_request_and_normalized_response(self) -> None:
        with patch(
            "signalforge.acquisition_runtime.acquire_provider_diagnostic_bytes",
            return_value=_capture(_payload()),
        ) as provider:
            result = acquire_provider_document_ocr(
                database=Path("/tmp/signalforge-test.db"),
                url=URL,
                timeout_seconds=60,
                max_bytes=8_000_000,
            )

        self.assertEqual(result.provider_request_id, REQUEST_ID)
        self.assertEqual(result.input_sha256, SHA)
        self.assertEqual(result.result["provider_contract_version"], 1)
        self.assertEqual(result.result["provider_request_id"], REQUEST_ID)
        self.assertEqual(result.result["provider_fetch_sha256"], SHA)
        self.assertEqual(result.result["input_sha256"], SHA)
        self.assertFalse(result.result["network_access"])
        self.assertFalse(result.result["intermediate_images_retained"])

        kwargs = provider.call_args.kwargs
        self.assertEqual(kwargs["source_id"], "S01")
        self.assertEqual(kwargs["source_policy_version"], 2)
        self.assertEqual(kwargs["target_role"], "OFFICIAL_DOCUMENT")
        self.assertEqual(kwargs["capability"], "DOCUMENT_OCR")
        self.assertEqual(kwargs["url"], URL)
        self.assertEqual(kwargs["expected_content_types"], ["application/json"])

    def test_wrapper_rejects_hosts_and_paths_outside_frozen_pic_scope(self) -> None:
        invalid = (
            "https://www.myanmar.gov.mm/documents/20143/0/tender.pdf/abc",
            "https://myanmar.gov.mm/tenders/abc",
            "https://example.com/documents/abc.pdf",
            "http://myanmar.gov.mm/documents/abc.pdf",
            "https://user:pass@myanmar.gov.mm/documents/abc.pdf",
            "https://myanmar.gov.mm/documents/../admin.pdf",
            "https://myanmar.gov.mm/documents/abc.pdf?x=1",
            "https://myanmar.gov.mm/documents/abc.pdf#frag",
        )
        for url in invalid:
            with self.assertRaises(ValueError, msg=url):
                acquire_provider_document_ocr(database=Path("/tmp/x.db"), url=url)

    def test_wrapper_rejects_fetch_ocr_sha_or_length_mismatch(self) -> None:
        payload = _payload()
        payload["document_ocr"]["input_sha256"] = "c" * 64
        with patch(
            "signalforge.acquisition_runtime.acquire_provider_diagnostic_bytes",
            return_value=_capture(payload),
        ):
            with self.assertRaisesRegex(RuntimeError, "fetch/OCR SHA mismatch"):
                acquire_provider_document_ocr(database=Path("/tmp/x.db"), url=URL)

        payload = _payload()
        payload["document_ocr"]["input_bytes"] = 123
        with patch(
            "signalforge.acquisition_runtime.acquire_provider_diagnostic_bytes",
            return_value=_capture(payload),
        ):
            with self.assertRaisesRegex(RuntimeError, "byte length mismatch"):
                acquire_provider_document_ocr(database=Path("/tmp/x.db"), url=URL)

    def test_wrapper_rejects_unsafe_or_incomplete_ocr_response(self) -> None:
        mutations = [
            ("network_access", True, "network_access=false"),
            ("intermediate_images_retained", True, "must not retain"),
            ("languages", ["eng"], "language profile"),
            ("psm", 3, "PSM invalid"),
        ]
        for key, value, pattern in mutations:
            payload = _payload()
            payload["document_ocr"][key] = value
            with patch(
                "signalforge.acquisition_runtime.acquire_provider_diagnostic_bytes",
                return_value=_capture(payload),
            ):
                with self.assertRaisesRegex(RuntimeError, pattern):
                    acquire_provider_document_ocr(database=Path("/tmp/x.db"), url=URL)

    def test_wrapper_accepts_explicit_truncation_but_rejects_inconsistent_page_metadata(self) -> None:
        with patch(
            "signalforge.acquisition_runtime.acquire_provider_diagnostic_bytes",
            return_value=_capture(_payload(page_count=20, processed_pages=12, truncated=True)),
        ):
            result = acquire_provider_document_ocr(database=Path("/tmp/x.db"), url=URL)
        self.assertTrue(result.result["page_limit_truncated"])
        self.assertEqual(result.result["page_count"], 20)
        self.assertEqual(result.result["processed_pages"], 12)

        payload = _payload(page_count=20, processed_pages=12, truncated=False)
        with patch(
            "signalforge.acquisition_runtime.acquire_provider_diagnostic_bytes",
            return_value=_capture(payload),
        ):
            with self.assertRaisesRegex(RuntimeError, "page completeness"):
                acquire_provider_document_ocr(database=Path("/tmp/x.db"), url=URL)


if __name__ == "__main__":
    unittest.main()
