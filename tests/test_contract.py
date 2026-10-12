from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from signalforge.cli import verb_manifest
from signalforge.config import ConfigError, Registry
from signalforge.worker_context import WorkerContextError, load_worker_context


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_signalforge_exposes_versioned_closed_verb_manifest_and_source_grammar(self) -> None:
        manifest = verb_manifest()
        self.assertEqual(manifest["verb_manifest_version"], 1)
        self.assertEqual(
            set(manifest["verbs"]),
            {"signalforge-status", "signalforge-opportunities", "signalforge-briefing", "signalforge-audit", "signalforge-source-scorecard", "signalforge-assurance-run", "signalforge-assurance-status", "signalforge-harness-verify", "signalforge-misses", "signalforge-run-due", "signalforge-refresh", "signalforge-pause", "signalforge-resume"},
        )
        self.assertEqual(manifest["verbs"]["signalforge-refresh"]["argument"], "source_id")
        self.assertEqual(manifest["grammar"]["source_id"], "^[A-Z][A-Z0-9]{0,15}$")
        self.assertEqual(manifest["active_source_ids"], ["S13", "S16", "S20", "S21", "S22", "S23", "S25", "S26", "S28", "S29", "S30", "S31", "S32", "S33", "S34", "S35", "S36", "S37", "S39", "S40", "S41", "S43", "S47", "S01", "S15A", "S27", "S38", "S51"])

        registry = Registry.load(ROOT)
        railways = registry.raw["sources"]["S21"]
        self.assertTrue(railways["enabled"])
        self.assertEqual(railways["role"], "ACTIVE_PRIMARY")
        self.assertEqual(railways["audit_status"], "GREEN_REACTIVATED_OFFICIAL_SITE_REDESIGN_2026_10_03")
        self.assertTrue(railways["acquisition_policy"]["enabled"])
        self.assertTrue(railways["reactivation"]["historical_data_retained"])
        self.assertEqual(railways["discovery_url"], "https://www.railways.gov.mm/posts?category=tender")
        with self.assertRaisesRegex(ConfigError, "invalid source id"):
            registry.source("../../etc/passwd")
        self.assertEqual(registry.source("S21")["adapter"], "railways")
        with self.assertRaisesRegex(ConfigError, "source is not active"):
            registry.source("S99")

    def test_r4_r5_registry_keeps_direct_http_default_and_bounded_tender_providers(self) -> None:
        registry = Registry.load(ROOT)
        self.assertEqual(registry.raw["production_policy"]["canonical_node"], "bangkok")
        self.assertTrue(registry.raw["production_policy"]["browser_production_approved"])

        removed = {
            "S05A", "S07", "S08A", "S10", "S12",
            "S44", "S45", "S46", "S48", "S49", "S50",
            "S52", "S53", "S54", "S55", "S56", "S57",
        }
        self.assertTrue(removed.isdisjoint(registry.raw["sources"]))

        enabled = registry.enabled_sources()
        self.assertTrue(enabled)
        self.assertTrue(all(source.get("item_kind") == "TENDER" for _sid, source in enabled))
        self.assertTrue(all(int(source["poll_interval_seconds"]) == 86400 for _sid, source in enabled))
        provider_sources = {sid for sid, source in enabled if source["engine"] == "provider"}
        self.assertEqual(provider_sources, {"S01", "S15A", "S27", "S38", "S51"})

        railways = registry.source("S21")
        self.assertEqual(railways["adapter"], "railways")
        self.assertEqual(railways["role"], "ACTIVE_PRIMARY")
        self.assertEqual(railways["discovery_url"], "https://www.railways.gov.mm/posts?category=tender")

        mpt = registry.source("S13")
        self.assertEqual(mpt["engine"], "direct_http")
        self.assertEqual(mpt["discovery_url"], "https://mpt.com.mm/page-sitemap.xml")

        moi = registry.source("S37")
        self.assertEqual(moi["adapter"], "moi_tender")
        self.assertEqual(moi["item_kind"], "TENDER")
        self.assertTrue(moi["discovery_is_tender_only"])

        construction = registry.source("S43")
        self.assertEqual(construction["adapter"], "yangon_construction_tender")
        self.assertEqual(construction["item_kind"], "TENDER")
        self.assertTrue(construction["discovery_is_tender_only"])

        ycdc = registry.source("S47")
        self.assertEqual(ycdc["adapter"], "yangon_ycdc_mission_tender")
        self.assertEqual(ycdc["item_kind"], "TENDER")
        self.assertTrue(ycdc["discovery_is_tender_only"])

        energy = registry.source("S39")
        self.assertEqual(energy["adapter"], "energy_tender")
        self.assertEqual(energy["attachment_policy"]["mode"], "SINGLE_TEXT_PDF_REQUIRED")

        ddd = registry.source("S51")
        self.assertEqual(ddd["adapter"], "digital_development_tender")
        self.assertEqual(ddd["detail_target_kind"], "PDF")

        provider_contract = json.loads((ROOT / "registry" / "Provider-Invocation-Contract-v1.json").read_text())
        self.assertNotIn("S56", provider_contract["source_policies"])
        self.assertEqual(provider_contract["source_policies"]["S27"]["allowed_capabilities"], ["PUBLIC_READ_ACQUIRE", "C0_FETCH"])
        self.assertEqual(provider_contract["source_policies"]["S15A"]["allowed_capabilities"], ["PUBLIC_READ_ACQUIRE", "C0_FETCH"])
        s23_ocr = provider_contract["source_policies"]["S23"]
        self.assertEqual(s23_ocr["allowed_capabilities"], ["DOCUMENT_OCR"])
        self.assertEqual(s23_ocr["targets"]["OFFICIAL_DOCUMENT"]["https_host"], "construction.gov.mm")
        self.assertEqual(provider_contract["limits"]["max_run_seconds"], 300)
        self.assertEqual(provider_contract["limits"]["max_request_ttl_seconds"], 360)

    def test_deploy_installs_reviewed_refresh_template_and_drains_instances(self) -> None:
        deploy = (ROOT / "deploy" / "deploy-signalforge-release.sh").read_text(encoding="utf-8")
        self.assertIn("generated/applications/signalforge/signalforge-refresh@.service", deploy)
        self.assertIn("/etc/systemd/system/signalforge-refresh@.service", deploy)
        self.assertIn("signalforge-refresh@*.service", deploy)
        self.assertIn('chmod 0755 "$STAGE"', deploy)
        self.assertIn("systemd-analyze verify", deploy)
        self.assertIn("signalforge-telegram-deliver.service", deploy)
        self.assertIn("signalforge-telegram-deliver.timer", deploy)
        self.assertIn("DELIVERY_TIMER_WAS_ENABLED", deploy)
        self.assertIn("disable --now signalforge-telegram-digest.timer", deploy)
        self.assertIn("disable --now signalforge-telegram-feedback.timer", deploy)
        self.assertIn("stop signalforge-telegram-digest.service", deploy)
        self.assertIn("stop signalforge-telegram-feedback.service", deploy)
        self.assertIn("/etc/systemd/system/signalforge-telegram-digest.service", deploy)
        self.assertIn("/etc/systemd/system/signalforge-telegram-feedback.service", deploy)
        self.assertNotIn('install -m 0644 "$FINAL/systemd/signalforge-telegram-digest', deploy)
        self.assertNotIn('install -m 0644 "$FINAL/systemd/signalforge-telegram-feedback', deploy)
        self.assertIn("signalforge-assurance.service", deploy)
        self.assertIn("signalforge-assurance.timer", deploy)
        self.assertIn("ASSURANCE_TIMER_WAS_ENABLED", deploy)
        self.assertIn("signalforge-public-read-telemetry.service", deploy)
        self.assertIn("signalforge-public-read-telemetry.timer", deploy)
        self.assertIn("PUBLIC_READ_TELEMETRY_TIMER_WAS_ENABLED", deploy)
        self.assertIn("/etc/signalforge", deploy)
        service = (ROOT / "systemd" / "signalforge-telegram-deliver.service").read_text(encoding="utf-8")
        run_due_timer = (ROOT / "systemd" / "signalforge-run-due.timer").read_text(encoding="utf-8")
        timer = (ROOT / "systemd" / "signalforge-telegram-deliver.timer").read_text(encoding="utf-8")
        assurance_service = (ROOT / "systemd" / "signalforge-assurance.service").read_text(encoding="utf-8")
        assurance_timer = (ROOT / "systemd" / "signalforge-assurance.timer").read_text(encoding="utf-8")
        telemetry_service = (ROOT / "systemd" / "signalforge-public-read-telemetry.service").read_text(encoding="utf-8")
        telemetry_timer = (ROOT / "systemd" / "signalforge-public-read-telemetry.timer").read_text(encoding="utf-8")
        self.assertIn("EnvironmentFile=/etc/signalforge/telegram.env", service)
        self.assertIn("ExecStart=/srv/signalforge/active/bin/signalforge telegram-deliver", service)
        self.assertIn("User=signalforge", service)
        self.assertIn("OnCalendar=*-*-* 00:00:00 UTC", run_due_timer)
        self.assertIn("OnCalendar=*-*-* 00:30:00 UTC", timer)
        self.assertIn("ExecStart=/srv/signalforge/active/bin/signalforge assurance-run", assurance_service)
        self.assertNotIn("telegram.env", assurance_service)
        self.assertIn("OnCalendar=Sun *-*-* 14:40:00 UTC", assurance_timer)
        self.assertIn("Persistent=true", assurance_timer)
        self.assertIn("EnvironmentFile=/etc/signalforge/telegram.env", telemetry_service)
        self.assertIn("ExecStart=/srv/signalforge/active/bin/signalforge public-read-telemetry-alert --window-hours 24", telemetry_service)
        self.assertIn("User=signalforge", telemetry_service)
        self.assertIn("OnCalendar=*-*-* *:17:00 UTC", telemetry_timer)
        self.assertIn("Persistent=true", telemetry_timer)

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
