"""Conservative S01 image OCR triage. Never auto-promote OCR to a tender."""
from __future__ import annotations

import re
from datetime import date

_DIGITS = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
_DATE = re.compile(r"(?<!\d)(\d{1,2})[.\-/](\d{1,2})[.\-/](20\d{2})(?!\d)")
_NUMBER = re.compile(r"\(\s*([0-9][0-9,]*)\s*\)")
_ITEMS = {
    "diesel": ("ဒီဇယ်ဆီ",),
    "octane_92": ("Octane-92",),
    "premium_diesel": ("ပရီမီယမ်ဒီဇယ်",),
}


def _single_date(line: str) -> str | None:
    dates: set[str] = set()
    for day, month, year in _DATE.findall(line):
        try:
            dates.add(date(int(year), int(month), int(day)).isoformat())
        except ValueError:
            return None
    return next(iter(dates)) if len(dates) == 1 else None


def _quantity_candidates(text: str) -> dict[str, int | None]:
    """Only capture explicitly parenthesized numeric quantities adjacent to item names.

    Missing or ambiguous OCR digits remain unknown; do not infer by subtraction.
    """
    found: dict[str, int | None] = {}
    for key, aliases in _ITEMS.items():
        values: set[int] = set()
        for alias in aliases:
            pattern = re.compile(re.escape(alias) + r"\s*" + _NUMBER.pattern, re.I)
            for match in pattern.finditer(text):
                value = int(match.group(1).replace(",", ""))
                if 0 < value <= 10_000_000:
                    values.add(value)
        found[key] = next(iter(values)) if len(values) == 1 else None
    return found


def triage_s01_image_ocr(ocr_text: str) -> dict[str, object]:
    """Return review-only evidence candidates, not verified commercial facts."""
    text = ocr_text.translate(_DIGITS)
    lease = "ငှားရမ်း" in text and "Convention Centre" in text
    fuel = "Octane-92" in text and "ဒီဇယ်ဆီ" in text
    classification = ("GOVERNMENT_ASSET_LEASING" if lease else
                      "GOVERNMENT_FUEL_PROCUREMENT" if fuel else "UNKNOWN")
    dates: dict[str, set[str]] = {
        "document_sale_start": set(), "document_sale_end": set(),
        "bid_submission_deadline_date": set(), "bid_opening_date": set(),
    }
    for line in text.splitlines():
        value = _single_date(line)
        if value is None:
            continue
        if "တင်သွင်း" in line and "နောက်ဆုံး" in line:
            field = "bid_submission_deadline_date"
        elif "စတင်ရောင်းချ" in line:
            field = "document_sale_start"
        elif "ဝိတ်မည့်" in line or "ရောင်းချမည့်ရက်" in line:
            field = "document_sale_end"
        elif "ဆောင်ရွက်မည့်နေ့ရက်" in line or "ကျင်းပမည့်" in line:
            field = "bid_opening_date"
        else:
            continue
        dates[field].add(value)
    result: dict[str, object] = {
        "classification": classification,
        "formal_procurement_tender": True if fuel and not lease else False if lease else None,
        "item_quantity_candidates": _quantity_candidates(text) if fuel and not lease else {},
        "status": "OCR_REVIEW_REQUIRED",
        "canonical_promotion_allowed": False,
    }
    for field, values in dates.items():
        result[field] = next(iter(values)) if len(values) == 1 else None
    return result
