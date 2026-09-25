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
            {"signalforge-status", "signalforge-opportunities", "signalforge-briefing", "signalforge-audit", "signalforge-source-scorecard", "signalforge-assurance-run", "signalforge-assurance-status", "signalforge-harness-verify", "signalforge-misses", "signalforge-manual-promotions", "signalforge-run-due", "signalforge-refresh", "signalforge-pause", "signalforge-resume"},
        )
        self.assertEqual(manifest["verbs"]["signalforge-refresh"]["argument"], "source_id")
        self.assertEqual(manifest["grammar"]["source_id"], "^[A-Z][A-Z0-9]{0,15}$")
        self.assertEqual(manifest["active_source_ids"], ["S05A", "S07", "S08A", "S10", "S12", "S13", "S16", "S20", "S21", "S22", "S25", "S26", "S28", "S29", "S30", "S31", "S32", "S33", "S34", "S35", "S36", "S37", "S39", "S40", "S41", "S43", "S44", "S45", "S46", "S47", "S48", "S27", "S38"])

        registry = Registry.load(ROOT)
        with self.assertRaisesRegex(ConfigError, "invalid source id"):
            registry.source("../../etc/passwd")
        with self.assertRaisesRegex(ConfigError, "source is not active"):
            registry.source("S99")

    def test_r4_r5_registry_keeps_direct_http_default_and_enables_bounded_mac_provider(self) -> None:
        registry = Registry.load(ROOT)
        self.assertEqual(registry.raw["production_policy"]["canonical_node"], "bangkok")
        self.assertTrue(registry.raw["production_policy"]["browser_production_approved"])
        mac_provider = registry.raw["providers"]["mac-mm-01"]
        self.assertEqual(mac_provider["provider_type"], "browser")
        self.assertEqual(mac_provider["runtime"], "mac-browser-plane-r1")
        self.assertTrue(mac_provider["production_enabled"])
        self.assertEqual(mac_provider["invocation_mode"], "pull_ssh_v1")
        self.assertTrue(mac_provider["network"]["direct"])
        self.assertFalse(mac_provider["network"]["southeast_asia"])
        self.assertFalse(mac_provider["network"]["china"])
        self.assertTrue(mac_provider["capabilities"]["c0_fetch"])
        self.assertTrue(mac_provider["capabilities"]["c1_render"])
        self.assertFalse(mac_provider["capabilities"]["c1_generic_interaction"])
        self.assertTrue(mac_provider["capabilities"]["c2_readonly_inspect"])
        self.assertFalse(mac_provider["capabilities"]["c3_browser_agent"])
        self.assertTrue(mac_provider["capabilities"]["remote_invocation"])
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

        moi = registry.source("S37")
        self.assertEqual(moi["adapter"], "moi_tender")
        self.assertEqual(moi["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(moi["item_kind"], "TENDER")
        self.assertEqual(moi["discovery_url"], "https://www.moi.gov.mm/department-announcement")
        self.assertEqual(moi["canonical_key"], "drupal_node_id")
        self.assertTrue(moi["discovery_is_tender_only"])
        self.assertEqual(moi["baseline_lookback_days"], 180)
        self.assertEqual(moi["health_policy"]["parse_sample_source"], "DETAIL_SCHEDULER")
        self.assertEqual(moi["attachment_policy"]["mode"], "HTML_ONLY_NO_ATTACHMENT_REQUIRED")

        industry = registry.source("S38")
        self.assertEqual(industry["engine"], "provider")
        self.assertEqual(industry["provider_id"], "mac-mm-01")
        self.assertEqual(industry["provider_capability"], "C0_FETCH")
        self.assertEqual(industry["provider_target_roles"], {"DISCOVERY": "LISTING", "HTML": "DETAIL"})
        self.assertEqual(industry["network_zone"], "mac-direct")
        self.assertEqual(industry["egress_profile"], "mac-direct")
        self.assertEqual(industry["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertFalse(industry["first_baseline_customer_signal"])
        self.assertEqual(
            industry["detail_parser_replay_migration"],
            {
                "from_version": "industry-announcement-detail-v1",
                "to_version": "industry-announcement-detail-v2",
                "zero_items_only": True,
                "suppress_signal_once": True,
            },
        )
        self.assertEqual(
            industry["actionable_baseline_signal_policy"],
            {"enabled": True, "min_remaining_seconds": 43200, "max_signals_per_run": 3},
        )
        moba = registry.source("S27")
        self.assertEqual(moba["adapter"], "moba_tender")
        self.assertEqual(moba["engine"], "provider")
        self.assertEqual(moba["provider_id"], "mac-mm-01")
        self.assertEqual(moba["provider_capability"], "C0_FETCH")
        self.assertEqual(moba["provider_target_roles"], {"DISCOVERY": "LISTING", "HTML": "DETAIL"})
        self.assertEqual(moba["discovery_url"], "https://moba.gov.mm/my/tender")
        self.assertEqual(moba["canonical_key"], "issuer_drupal_tender_node_id")
        self.assertEqual(moba["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(moba["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(moba["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertNotIn("S27", registry.raw["deferred_sources"])

        construction = registry.source("S43")
        self.assertEqual(construction["adapter"], "yangon_construction_tender")
        self.assertEqual(construction["engine"], "direct_http")
        self.assertEqual(construction["role"], "ACTIVE_PRIMARY")
        self.assertEqual(construction["discovery_url"], "https://www.yangon.gov.mm/category/ministry-of-construction/")
        self.assertTrue(construction["discovery_is_tender_only"])
        self.assertEqual(construction["item_kind"], "TENDER")

        atom_network = registry.source("S44")
        self.assertEqual(atom_network["adapter"], "atom_network_notice")
        self.assertEqual(atom_network["item_kind"], "REGULATORY_NOTICE")
        self.assertTrue(atom_network["listing_complete_business_records"])
        self.assertEqual(atom_network["discovery_url"], "https://www.atom.com.mm/api/v1/medias?locale=en&search=5G&page=1")

        mpt_network = registry.source("S45")
        self.assertEqual(mpt_network["adapter"], "mpt_network_notice")
        self.assertEqual(mpt_network["item_kind"], "REGULATORY_NOTICE")
        self.assertTrue(mpt_network["listing_complete_business_records"])
        self.assertEqual(mpt_network["discovery_url"], "https://mpt.com.mm/en/about-home/media-press-releases/latest-news/")

        ptd_policy = registry.source("S46")
        self.assertEqual(ptd_policy["adapter"], "ptd_policy_notice")
        self.assertEqual(ptd_policy["item_kind"], "REGULATORY_NOTICE")
        self.assertEqual(ptd_policy["role"], "ACTIVE_SELECTIVE")
        self.assertTrue(ptd_policy["listing_complete_business_records"])
        self.assertEqual(ptd_policy["discovery_url"], "https://www.ptd.gov.mm/LawsFP.aspx")
        self.assertEqual(ptd_policy["poll_interval_seconds"], 21600)

        ycdc_mission = registry.source("S47")
        self.assertEqual(ycdc_mission["adapter"], "yangon_ycdc_mission_tender")
        self.assertEqual(ycdc_mission["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(ycdc_mission["discovery_url"], "https://www.yangon.gov.mm/category/tenders/")
        self.assertTrue(ycdc_mission["discovery_is_tender_only"])
        self.assertEqual(ycdc_mission["item_kind"], "TENDER")
        self.assertEqual(ycdc_mission["actionable_baseline_signal_policy"]["min_remaining_seconds"], 43200)

        precursor = registry.source("S48")
        self.assertEqual(precursor["adapter"], "moi_project_precursor")
        self.assertEqual(precursor["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(precursor["item_kind"], "REGULATORY_NOTICE")
        self.assertEqual(precursor["discovery_url"], "https://www.moi.gov.mm/news")
        self.assertFalse(precursor["listing_complete_business_records"])
        self.assertEqual(precursor["baseline_lookback_days"], 0)
        self.assertEqual(precursor["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(precursor["attachment_policy"]["mode"], "HTML_ONLY_NO_ATTACHMENT_REQUIRED")

        energy = registry.source("S39")
        self.assertEqual(energy["adapter"], "energy_tender")
        self.assertEqual(energy["engine"], "direct_http")
        self.assertEqual(energy["discovery_url"], "https://energy.gov.mm/tenders")
        self.assertEqual(energy["canonical_key"], "issuer_tender_record_id")
        self.assertEqual(energy["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(energy["attachment_policy"]["mode"], "SINGLE_TEXT_PDF_REQUIRED")
        self.assertTrue(energy["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertEqual(energy["attachment_policy"]["required_primary_attachments"], 1)
        self.assertEqual(energy["attachment_policy"]["max_primary_attachments"], 1)
        self.assertEqual(
            energy["acquisition_policy"]["supplementary"],
            [{"method": "DIRECT_HTTP", "target_kind": "PDF", "required": True, "max_count": 1, "same_origin_only": True}],
        )
        self.assertEqual(
            energy["actionable_baseline_signal_policy"],
            {"enabled": True, "min_remaining_seconds": 43200, "max_signals_per_run": 3},
        )

        labour = registry.source("S40")
        self.assertEqual(labour["adapter"], "mol_tender")
        self.assertEqual(labour["engine"], "direct_http")
        self.assertEqual(labour["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(labour["discovery_url"], "https://www.mol.gov.mm/tender/")
        self.assertEqual(labour["canonical_key"], "wordpress_post_id")
        self.assertEqual(labour["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(labour["attachment_policy"]["mode"], "SINGLE_TEXT_PDF_REQUIRED")
        self.assertEqual(labour["bootstrap_seed_urls"], [])
        self.assertEqual(labour["acquisition_policy"]["supplementary"], energy["acquisition_policy"]["supplementary"])

        enabled = registry.enabled_sources()
        self.assertEqual([sid for sid, _source in enabled[-7:]], ["S44", "S45", "S46", "S47", "S48", "S27", "S38"])
        self.assertTrue(all(source["engine"] == "direct_http" for _sid, source in enabled[:-2]))
        self.assertTrue(all(source["engine"] == "provider" for _sid, source in enabled[-2:]))
        self.assertFalse(moi["attachment_policy"]["fetch_in_primary_pipeline"])

        provider_contract = json.loads((ROOT / "registry" / "Provider-Invocation-Contract-v1.json").read_text())
        self.assertEqual(provider_contract["source_policies"]["S27"]["allowed_capabilities"], ["C0_FETCH"])
        self.assertEqual(
            provider_contract["source_policies"]["S27"]["targets"]["LISTING"]["exact_urls"],
            ["https://moba.gov.mm/my/tender"],
        )
        detail_policy = provider_contract["source_policies"]["S27"]["targets"]["DETAIL"]
        self.assertEqual(detail_policy["https_host"], "moba.gov.mm")
        self.assertEqual(detail_policy["path_prefix"], "/my/tender/")
        self.assertEqual(detail_policy["capabilities"], ["C0_FETCH"])
        self.assertFalse(detail_policy["allow_query"])
        self.assertFalse(detail_policy["allow_fragment"])

        doa = registry.source("S36")
        self.assertEqual(doa["adapter"], "doa_tender")
        self.assertEqual(doa["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(doa["item_kind"], "TENDER")
        self.assertTrue(doa["listing_complete_business_records"])
        self.assertEqual(doa["discovery_url"], "https://www.doa.gov.mm/doa/index.php?route=cms/category&path=22")
        self.assertEqual(doa["canonical_key"], "issuer_article_id")
        self.assertEqual(doa["baseline_detail_limit"], 0)
        self.assertEqual(doa["delta_detail_limit"], 0)
        self.assertEqual(doa["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(doa["attachment_policy"]["mode"], "EMBEDDED_IMAGE_UNPARSED_NON_BLOCKING")
        self.assertFalse(doa["attachment_policy"]["fetch_in_primary_pipeline"])

        dast = registry.source("S35")
        self.assertEqual(dast["adapter"], "dast_tender")
        self.assertEqual(dast["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(dast["item_kind"], "TENDER")
        self.assertEqual(dast["discovery_url"], "https://www.dast.gov.mm/category/tender/")
        self.assertEqual(dast["canonical_key"], "wordpress_post_id")
        self.assertEqual(dast["baseline_lookback_days"], 180)
        self.assertEqual(dast["health_policy"]["parse_sample_source"], "DETAIL_SCHEDULER")
        self.assertEqual(dast["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(dast["attachment_policy"]["fetch_in_primary_pipeline"])

        ptd = registry.source("S34")
        self.assertEqual(ptd["adapter"], "ptd_tender")
        self.assertEqual(ptd["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(ptd["item_kind"], "TENDER")
        self.assertEqual(ptd["discovery_url"], "https://www.ptd.gov.mm/Announcement.aspx?id=jOhwNsVnnrHGITOdpDNvsw%3D%3D")
        self.assertEqual(ptd["canonical_key"], "issuer_business_event_fingerprint")
        self.assertEqual(ptd["baseline_lookback_days"], 150)
        self.assertEqual(ptd["health_policy"]["parse_sample_source"], "DETAIL_SCHEDULER")
        self.assertEqual(ptd["source_policy_version"], 2)
        self.assertEqual(ptd["attachment_policy"]["mode"], "SINGLE_TEXT_PDF_REQUIRED")
        self.assertTrue(ptd["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertEqual(ptd["attachment_policy"]["required_primary_attachments"], 1)
        self.assertEqual(ptd["attachment_policy"]["max_primary_attachments"], 1)
        self.assertTrue(ptd["attachment_policy"]["same_origin_only"])
        self.assertTrue(ptd["attachment_policy"]["suppress_signal_on_initial_attachment_enrichment"])
        self.assertEqual(ptd["acquisition_policy"]["supplementary"], energy["acquisition_policy"]["supplementary"])

        ycdc = registry.source("S16")
        self.assertEqual(ycdc["adapter"], "ycdc_building_tender")
        self.assertEqual(ycdc["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(ycdc["item_kind"], "TENDER")
        self.assertTrue(ycdc["listing_complete_business_records"])
        self.assertEqual(ycdc["canonical_key"], "issuer_archive_event_fingerprint")
        self.assertEqual(ycdc["discovery_url"], "https://www.ycdc.gov.mm/frontend_engineering_building_detail/1")
        self.assertEqual(ycdc["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(ycdc["acquisition_policy"]["primary"], {"method": "DIRECT_HTTP", "target_kind": "HTML"})
        self.assertEqual(ycdc["attachment_policy"]["mode"], "HTML_ONLY_NO_ATTACHMENT_REQUIRED")
        self.assertNotIn("S16", registry.raw["deferred_sources"])

        iwt = registry.source("S22")
        self.assertEqual(iwt["adapter"], "iwt")
        self.assertEqual(iwt["engine"], "direct_http")
        self.assertEqual(iwt["discovery_url"], "https://iwt.gov.mm/tenders")
        self.assertTrue(iwt["discovery_is_tender_only"])
        self.assertFalse(iwt["first_baseline_customer_signal"])
        self.assertEqual(iwt["canonical_key"], "issuer_record_id_publication_date")
        self.assertEqual(iwt["egress_profile"], "mm-intl-datacenter")

        moep = registry.source("S20")
        self.assertEqual(moep["adapter"], "moep")
        self.assertEqual(moep["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(moep["discovery_url"], "https://moep.gov.mm/mm/ignite/page/62")
        self.assertTrue(moep["discovery_is_tender_only"])
        self.assertEqual(moep["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(moep["attachment_policy"]["fetch_in_primary_pipeline"])

        commerce = registry.source("S05A")
        self.assertEqual(commerce["adapter"], "commerce_notice")
        self.assertEqual(commerce["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(commerce["item_kind"], "REGULATORY_NOTICE")
        self.assertEqual(commerce["discovery_url"], "https://commerce.gov.mm/my/node/32071")
        self.assertNotIn("discovery_is_tender_only", commerce)
        self.assertEqual(commerce["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(commerce["attachment_policy"]["fetch_in_primary_pipeline"])

        ird = registry.source("S12")
        self.assertEqual(ird["adapter"], "ird_notice")
        self.assertEqual(ird["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(ird["item_kind"], "REGULATORY_NOTICE")
        self.assertEqual(ird["discovery_url"], "https://www.ird.gov.mm/announcement-lists")
        self.assertEqual(ird["canonical_key"], "issuer_record_id_publication_date")
        self.assertEqual(ird["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(ird["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertIn("S04", registry.raw["deferred_sources"])
        self.assertIn("S15A", registry.raw["deferred_sources"])
        self.assertIn("S15B", registry.raw["deferred_sources"])

        dica = registry.source("S10")
        self.assertEqual(dica["adapter"], "dica_notice")
        self.assertEqual(dica["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(dica["item_kind"], "REGULATORY_NOTICE")
        self.assertEqual(dica["discovery_url"], "https://www.dica.gov.mm/category/announcements-and-information/")
        self.assertEqual(dica["canonical_key"], "issuer_record_id")
        self.assertEqual(dica["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(dica["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertEqual(dica["attachment_policy"]["pdf_value_gate"], "TRIGGERED")
        self.assertEqual(dica["attachment_policy"]["runtime_packaging_gate"], "DEFERRED_ZERO_DEPENDENCY")

        monpifer = registry.source("S25")
        self.assertEqual(monpifer["adapter"], "monpifer_tender")
        self.assertEqual(monpifer["role"], "ACTIVE_PRIMARY")
        self.assertEqual(monpifer["item_kind"], "TENDER")
        self.assertTrue(monpifer["listing_complete_business_records"])
        self.assertEqual(monpifer["canonical_key"], "issuer_article_alias")
        self.assertEqual(monpifer["discovery_url"], "https://www.monpifer.gov.mm/my/ministry-tenders")
        self.assertEqual(monpifer["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(monpifer["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(monpifer["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertNotIn("S25", registry.raw["deferred_sources"])

        mofa = registry.source("S30")
        self.assertEqual(mofa["adapter"], "mofa_tender")
        self.assertEqual(mofa["engine"], "direct_http")
        self.assertEqual(mofa["attachment_policy"]["mode"], "OPTIONAL_SINGLE_TEXT_PDF_ENRICHMENT")
        self.assertTrue(mofa["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertEqual(mofa["attachment_policy"]["required_primary_attachments"], 0)
        self.assertEqual(mofa["attachment_policy"]["max_primary_attachments"], 1)
        self.assertEqual(
            mofa["acquisition_policy"]["supplementary"],
            [{"method": "DIRECT_HTTP", "target_kind": "PDF", "required": False, "max_count": 1, "same_origin_only": True}],
        )

        doms = registry.source("S26")
        self.assertEqual(doms["adapter"], "doms_tender")
        self.assertEqual(doms["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(doms["item_kind"], "TENDER")
        self.assertTrue(doms["discovery_is_tender_only"])
        self.assertEqual(doms["canonical_key"], "wordpress_post_id")
        self.assertEqual(doms["acquisition_policy"]["primary"], {"method": "DIRECT_HTTP", "target_kind": "HTML"})
        self.assertEqual(doms["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(doms["attachment_policy"]["fetch_in_primary_pipeline"])

        dof = registry.source("S28")
        self.assertEqual(dof["adapter"], "dof_tender")
        self.assertEqual(dof["role"], "ACTIVE_PRIMARY")
        self.assertEqual(dof["item_kind"], "TENDER")
        self.assertTrue(dof["listing_complete_business_records"])
        self.assertEqual(dof["canonical_key"], "issuer_tender_alias")
        self.assertEqual(dof["discovery_url"], "https://www.dof.gov.mm/index.php/my/tender")
        self.assertEqual(dof["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(dof["acquisition_policy"]["primary"], {"method": "DIRECT_HTTP", "target_kind": "HTML"})
        self.assertEqual(dof["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(dof["attachment_policy"]["fetch_in_primary_pipeline"])

        moea = registry.source("S31")
        self.assertEqual(moea["adapter"], "moea_tender")
        self.assertEqual(moea["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(moea["item_kind"], "TENDER")
        self.assertTrue(moea["listing_complete_business_records"])
        self.assertEqual(moea["canonical_key"], "issuer_archive_event_fingerprint")
        self.assertEqual(moea["discovery_url"], "https://portal.moea.gov.mm/index.php?page=ORwuBwpT")
        self.assertEqual(moea["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(moea["acquisition_policy"]["primary"], {"method": "DIRECT_HTTP", "target_kind": "HTML"})
        self.assertEqual(moea["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(moea["attachment_policy"]["fetch_in_primary_pipeline"])
        self.assertEqual(
            moea["listing_semantic_migration"],
            {"from_version": 2, "to_version": 3, "suppress_signal": True},
        )

        mte = registry.source("S32")
        self.assertEqual(mte["adapter"], "mte_tender")
        self.assertEqual(mte["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(mte["item_kind"], "TENDER")
        self.assertTrue(mte["listing_complete_business_records"])
        self.assertEqual(mte["canonical_key"], "joomla_article_id")
        self.assertEqual(mte["discovery_url"], "https://mte.gov.mm/index.php/en/annoucements")
        self.assertEqual(mte["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(mte["acquisition_policy"]["primary"], {"method": "DIRECT_HTTP", "target_kind": "HTML"})
        self.assertEqual(mte["attachment_policy"]["mode"], "EMBEDDED_IMAGE_UNPARSED_NON_BLOCKING")
        self.assertFalse(mte["attachment_policy"]["fetch_in_primary_pipeline"])

        mcrd = registry.source("S33")
        self.assertEqual(mcrd["adapter"], "mcrd_tender")
        self.assertEqual(mcrd["role"], "ACTIVE_SELECTIVE")
        self.assertEqual(mcrd["item_kind"], "TENDER")
        self.assertTrue(mcrd["listing_complete_business_records"])
        self.assertEqual(mcrd["canonical_key"], "issuer_board_event_fingerprint")
        self.assertEqual(mcrd["discovery_url"], "https://www.mcrd.gov.mm/index.php?page=dGluZGEmbW8%3D")
        self.assertEqual(mcrd["health_policy"]["parse_sample_source"], "BUSINESS_PROCESSING")
        self.assertEqual(mcrd["acquisition_policy"]["primary"], {"method": "DIRECT_HTTP", "target_kind": "HTML"})
        self.assertEqual(mcrd["attachment_policy"]["mode"], "METADATA_ONLY_NON_BLOCKING")
        self.assertFalse(mcrd["attachment_policy"]["fetch_in_primary_pipeline"])

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
        self.assertIn("signalforge-telegram-digest.service", deploy)
        self.assertIn("signalforge-telegram-digest.timer", deploy)
        self.assertIn("DIGEST_TIMER_WAS_ENABLED", deploy)
        self.assertIn("signalforge-assurance.service", deploy)
        self.assertIn("signalforge-assurance.timer", deploy)
        self.assertIn("ASSURANCE_TIMER_WAS_ENABLED", deploy)
        self.assertIn("/etc/signalforge", deploy)
        service = (ROOT / "systemd" / "signalforge-telegram-deliver.service").read_text(encoding="utf-8")
        timer = (ROOT / "systemd" / "signalforge-telegram-deliver.timer").read_text(encoding="utf-8")
        digest_service = (ROOT / "systemd" / "signalforge-telegram-digest.service").read_text(encoding="utf-8")
        digest_timer = (ROOT / "systemd" / "signalforge-telegram-digest.timer").read_text(encoding="utf-8")
        assurance_service = (ROOT / "systemd" / "signalforge-assurance.service").read_text(encoding="utf-8")
        assurance_timer = (ROOT / "systemd" / "signalforge-assurance.timer").read_text(encoding="utf-8")
        self.assertIn("EnvironmentFile=/etc/signalforge/telegram.env", service)
        self.assertIn("ExecStart=/srv/signalforge/active/bin/signalforge telegram-deliver", service)
        self.assertIn("User=signalforge", service)
        self.assertIn("OnCalendar=*-*-* *:0/5:45 UTC", timer)
        self.assertIn("EnvironmentFile=/etc/signalforge/telegram.env", digest_service)
        self.assertIn("ExecStart=/srv/signalforge/active/bin/signalforge telegram-digest", digest_service)
        self.assertIn("User=signalforge", digest_service)
        self.assertIn("OnCalendar=*-*-* 02:00:00 UTC", digest_timer)
        self.assertIn("Persistent=true", digest_timer)
        self.assertIn("ExecStart=/srv/signalforge/active/bin/signalforge assurance-run", assurance_service)
        self.assertNotIn("telegram.env", assurance_service)
        self.assertIn("OnCalendar=Sun *-*-* 14:40:00 UTC", assurance_timer)
        self.assertIn("Persistent=true", assurance_timer)

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
