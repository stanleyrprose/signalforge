from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from signalforge.business_profile import (
    BusinessProfile,
    BusinessProfileError,
    load_business_profile,
    match_tender,
)


class BusinessProfileTests(unittest.TestCase):
    def test_category_and_product_keyword_produce_high_match(self) -> None:
        profile = BusinessProfile.from_dict(
            {
                "profile_id": "telecom",
                "delivery_mode": "MATCHED_ONLY",
                "minimum_score": 45,
                "relevance_categories": ["ICT", "TELECOM"],
                "keywords": ["router", "fiber"],
            }
        )
        result = match_tender(
            {
                "relevance_categories": ["ICT"],
                "title": "Network equipment tender",
                "scope_excerpt": "Supply router and fiber equipment",
                "issuer": "Ministry of Transport",
            },
            profile,
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["score"], 80)
        self.assertEqual(result["category_hits"], ["ICT"])
        self.assertEqual(result["keyword_hits"], ["router", "fiber"])
        self.assertIn("ICT", str(result["summary"]))

    def test_matched_only_filters_irrelevant_tender(self) -> None:
        profile = BusinessProfile.from_dict(
            {
                "profile_id": "power",
                "delivery_mode": "MATCHED_ONLY",
                "relevance_categories": ["ENERGY"],
                "keywords": ["transformer"],
            }
        )
        result = match_tender(
            {
                "relevance_categories": ["MEDICAL"],
                "title": "Medical consumables",
                "issuer": "Hospital",
            },
            profile,
        )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["score"], 0)

    def test_all_tenders_never_filters_even_without_match(self) -> None:
        profile = BusinessProfile.from_dict(
            {
                "profile_id": "observer",
                "delivery_mode": "ALL_TENDERS",
                "relevance_categories": ["TELECOM"],
            }
        )
        result = match_tender({"title": "Office furniture", "relevance_categories": ["OTHER"]}, profile)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["score"], 0)

    def test_exclusion_rule_is_fail_closed(self) -> None:
        profile = BusinessProfile.from_dict(
            {
                "profile_id": "infra",
                "delivery_mode": "ALL_TENDERS",
                "exclude_keywords": ["medical consumables"],
            }
        )
        result = match_tender({"title": "Medical consumables tender"}, profile)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["excluded_hits"], ["medical consumables"])

    def test_load_profile_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            path.write_text(
                json.dumps(
                    {
                        "profile_id": "p1",
                        "name": "Pilot",
                        "delivery_mode": "MATCHED_ONLY",
                        "keywords": ["UPS"],
                    }
                ),
                encoding="utf-8",
            )
            profile = load_business_profile(path)
            assert profile is not None
            self.assertEqual(profile.profile_id, "p1")
            self.assertEqual(profile.keywords, ("ups",))

    def test_matched_only_requires_positive_rule(self) -> None:
        with self.assertRaises(BusinessProfileError):
            BusinessProfile.from_dict({"profile_id": "bad", "delivery_mode": "MATCHED_ONLY"})


if __name__ == "__main__":
    unittest.main()
