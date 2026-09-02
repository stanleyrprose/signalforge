from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalforge.config import Registry
from signalforge.worker_context import WorkerContextError, load_worker_context


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_r5_registry_is_bangkok_direct_http_only(self) -> None:
        registry = Registry.load(ROOT)
        self.assertEqual(registry.raw["production_policy"]["canonical_node"], "bangkok")
        self.assertFalse(registry.raw["production_policy"]["browser_production_approved"])
        source = registry.source("S13")
        self.assertEqual(source["engine"], "direct_http")
        self.assertEqual(source["network_zone"], "myanmar-international")
        self.assertFalse(source["first_baseline_customer_signal"])
        self.assertEqual(source["discovery_url"], "https://mpt.com.mm/page-sitemap.xml")
        self.assertEqual(source["delta_detail_limit"], 20)
        self.assertEqual(source["recovery_slo_seconds"], 1800)
        self.assertEqual(source["availability_policy"]["class"], "DELAY_TOLERANT_MONITORED")
        self.assertEqual(source["availability_policy"]["collection_rto_seconds"], 1800)
        self.assertEqual(source["availability_policy"]["business_data_rpo_target_seconds"], 900)
        self.assertTrue(all(url.startswith("https://mpt.com.mm/en/") for url in source["bootstrap_seed_urls"]))

    def test_worker_application_correlation_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invocation_id = "0123456789abcdef0123456789abcdef"
            app_dir = root / "signalforge"
            app_dir.mkdir()
            (app_dir / f"{invocation_id}.json").write_text(
                json.dumps(
                    {
                        "invocation_id": invocation_id,
                        "run_id": "worker-run-live-shape",
                        "application": "signalforge",
                        "worker": "bangkok",
                    }
                ),
                encoding="utf-8",
            )
            env = {
                "INVOCATION_ID": invocation_id,
                "WORKER_APPLICATION_INVOCATION_ROOT": str(root),
            }
            with patch.dict(os.environ, env, clear=False):
                value = load_worker_context()
            self.assertEqual(value["run_id"], "worker-run-live-shape")

            bad = json.loads((app_dir / f"{invocation_id}.json").read_text())
            bad["worker"] = "beijing"
            (app_dir / f"{invocation_id}.json").write_text(json.dumps(bad), encoding="utf-8")
            with patch.dict(os.environ, env, clear=False):
                with self.assertRaisesRegex(WorkerContextError, "Bangkok"):
                    load_worker_context()


if __name__ == "__main__":
    unittest.main()
