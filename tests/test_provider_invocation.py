from __future__ import annotations

import copy
import unittest
import uuid
from datetime import UTC, datetime, timedelta

from signalforge.provider_invocation import (
    CAPABILITY_TOOL_MAP,
    ProviderCapability,
    ProviderInvocationError,
    build_provider_request,
    request_sha256,
    validate_contract_projection,
    validate_final_url_policy,
    validate_provider_request,
)


NOW = datetime(2026, 9, 8, 4, 0, tzinfo=UTC)


def contract() -> dict:
    return {
        "schema_version": 1,
        "contract_name": "provider-invocation-v1",
        "provider_id": "mac-mm-01",
        "transport": "pull_ssh_v1",
        "enabled": False,
        "allowed_capabilities": ["C0_FETCH", "C1_RENDER", "C2_INSPECT", "C3_BROWSER_USE"],
        "tool_map": dict(CAPABILITY_TOOL_MAP),
        "limits": {
            "max_run_seconds": 180,
            "max_request_ttl_seconds": 180,
            "max_bytes": 16 * 1024 * 1024,
        },
        "security": {
            "https_only": True,
            "arbitrary_url_allowed": False,
            "arbitrary_shell_allowed": False,
            "public_mac_listener_allowed": False,
            "off_host_redirect_allowed": False,
            "personal_chrome_profile_allowed": False,
        },
        "source_policies": {
            "S38": {
                "enabled": True,
                "source_policy_version": 1,
                "allowed_capabilities": ["C0_FETCH", "C1_RENDER", "C2_INSPECT", "C3_BROWSER_USE"],
                "targets": {
                    "LISTING": {
                        "capabilities": ["C0_FETCH", "C1_RENDER", "C2_INSPECT", "C3_BROWSER_USE"],
                        "exact_urls": ["https://www.industrymsme.gov.mm/announcements"],
                        "max_bytes": 1_000_000,
                        "max_run_seconds": 45,
                    },
                    "DETAIL": {
                        "capabilities": ["C0_FETCH", "C1_RENDER", "C2_INSPECT", "C3_BROWSER_USE"],
                        "https_host": "www.industrymsme.gov.mm",
                        "path_prefix": "/announcements/",
                        "allow_query": False,
                        "allow_fragment": False,
                        "max_bytes": 1_000_000,
                        "max_run_seconds": 60,
                    },
                },
            }
        },
    }


def ids() -> dict[str, str]:
    return {
        "signalforge_job_id": str(uuid.uuid4()),
        "acquisition_request_id": str(uuid.uuid4()),
        "acquisition_attempt_id": str(uuid.uuid4()),
    }


def build(capability: str = "C0_FETCH", **kwargs):
    args = ids()
    args.update(
        contract=contract(),
        source_id="S38",
        source_policy_version=1,
        capability=capability,
        target_role="LISTING",
        requested_url="https://www.industrymsme.gov.mm/announcements",
        max_bytes=1_000_000,
        max_run_seconds=45,
        now=NOW,
        ttl_seconds=90,
    )
    args.update(kwargs)
    return build_provider_request(**args)


class ProviderInvocationContractTests(unittest.TestCase):
    def test_contract_projects_c0_c1_c2_c3_exactly(self) -> None:
        value = validate_contract_projection(contract())
        self.assertEqual(set(value["allowed_capabilities"]), set(CAPABILITY_TOOL_MAP))
        self.assertEqual(value["tool_map"]["C0_FETCH"], "browser_fetch")
        self.assertEqual(value["tool_map"]["C1_RENDER"], "browser_render")
        self.assertEqual(value["tool_map"]["C2_INSPECT"], "browser_inspect")
        self.assertEqual(value["tool_map"]["C3_BROWSER_USE"], "browser_use")

    def test_builds_valid_readonly_requests_for_c0_c1_c2(self) -> None:
        for capability in (
            ProviderCapability.C0_FETCH.value,
            ProviderCapability.C1_RENDER.value,
            ProviderCapability.C2_INSPECT.value,
        ):
            request = build(capability)
            self.assertEqual(request["mcp_tool"], CAPABILITY_TOOL_MAP[capability])
            self.assertIsNone(request["interaction_plan"])
            self.assertEqual(request["request_sha256"], request_sha256(request))

    def test_builds_valid_c3_readonly_navigation_request(self) -> None:
        plan = {
            "side_effect_class": "READ_ONLY_NAVIGATION",
            "retry_safe": False,
            "steps": [
                {"action": "snapshot"},
                {"action": "click", "selector": "a.next"},
                {"action": "wait", "selector": "body"},
                {"action": "screenshot"},
            ],
        }
        request = build("C3_BROWSER_USE", interaction_plan=plan)
        self.assertEqual(request["mcp_tool"], "browser_use")
        self.assertEqual(request["interaction_plan"], plan)

    def test_c3_requires_explicit_readonly_plan(self) -> None:
        with self.assertRaisesRegex(ProviderInvocationError, "requires interaction_plan"):
            build("C3_BROWSER_USE")
        with self.assertRaisesRegex(ProviderInvocationError, "READ_ONLY_NAVIGATION"):
            build(
                "C3_BROWSER_USE",
                interaction_plan={"side_effect_class": "WRITE", "retry_safe": False, "steps": [{"action": "click"}]},
            )

    def test_c3_action_subset_matches_mac_mcp_pic_boundary(self) -> None:
        plan = {
            "side_effect_class": "READ_ONLY_NAVIGATION",
            "retry_safe": False,
            "steps": [{"action": "press", "key": "Escape"}],
        }
        request = build("C3_BROWSER_USE", interaction_plan=plan)
        self.assertEqual(request["interaction_plan"]["steps"][0]["action"], "press")
        with self.assertRaisesRegex(ProviderInvocationError, "not authorized"):
            build(
                "C3_BROWSER_USE",
                interaction_plan={
                    "side_effect_class": "READ_ONLY_NAVIGATION",
                    "retry_safe": False,
                    "steps": [{"action": "scroll"}],
                },
            )

    def test_final_url_policy_can_allow_bounded_same_issuer_navigation(self) -> None:
        value = contract()
        target = value["source_policies"]["S38"]["targets"]["LISTING"]
        target.pop("exact_urls")
        target.update({
            "https_host": "www.industrymsme.gov.mm",
            "path_prefix": "/",
            "allow_query": False,
            "allow_fragment": False,
            "final_url_policy": {
                "mode": "APPROVED_HOST_PATH",
                "https_host": "www.industrymsme.gov.mm",
                "path_prefix": "/",
            },
        })
        ids_value = ids()
        request = build_provider_request(
            contract=value, source_id="S38", source_policy_version=1, capability="C1_RENDER",
            target_role="LISTING", requested_url="https://www.industrymsme.gov.mm/announcements",
            max_bytes=1_000_000, max_run_seconds=45, now=NOW, ttl_seconds=90, **ids_value,
        )
        self.assertEqual(request["final_url_policy"]["mode"], "APPROVED_HOST_PATH")
        validate_final_url_policy(request["final_url_policy"], "https://www.industrymsme.gov.mm/announcements/123")
        with self.assertRaisesRegex(ProviderInvocationError, "host"):
            validate_final_url_policy(request["final_url_policy"], "https://example.com/announcements/123")

    def test_c3_rejects_arbitrary_execution_fields(self) -> None:
        with self.assertRaisesRegex(ProviderInvocationError, "arbitrary execution"):
            build(
                "C3_BROWSER_USE",
                interaction_plan={
                    "side_effect_class": "READ_ONLY_NAVIGATION",
                    "retry_safe": False,
                    "steps": [{"action": "click", "javascript": "alert(1)"}],
                },
            )

    def test_rejects_arbitrary_host_http_credentials_and_path_traversal(self) -> None:
        invalid = [
            "https://example.com/announcements/1",
            "http://www.industrymsme.gov.mm/announcements/1",
            "https://user:pass@www.industrymsme.gov.mm/announcements/1",
            "https://www.industrymsme.gov.mm/announcements/../admin",
        ]
        for url in invalid:
            with self.assertRaises(ProviderInvocationError, msg=url):
                build(target_role="DETAIL", requested_url=url)

    def test_rejects_query_and_fragment_when_target_does_not_allow_them(self) -> None:
        for url in (
            "https://www.industrymsme.gov.mm/announcements/1?x=1",
            "https://www.industrymsme.gov.mm/announcements/1#frag",
        ):
            with self.assertRaises(ProviderInvocationError, msg=url):
                build(target_role="DETAIL", requested_url=url)

    def test_rejects_unauthorized_capability(self) -> None:
        value = contract()
        value["source_policies"]["S38"]["allowed_capabilities"] = ["C0_FETCH"]
        args = ids()
        with self.assertRaisesRegex(ProviderInvocationError, "not source-authorized"):
            build_provider_request(
                contract=value,
                source_id="S38",
                source_policy_version=1,
                capability="C1_RENDER",
                target_role="LISTING",
                requested_url="https://www.industrymsme.gov.mm/announcements",
                max_bytes=1000,
                max_run_seconds=10,
                now=NOW,
                ttl_seconds=30,
                **args,
            )

    def test_rejects_expired_and_overlong_requests(self) -> None:
        request = build()
        with self.assertRaisesRegex(ProviderInvocationError, "expired"):
            validate_provider_request(request, contract=contract(), now=NOW + timedelta(minutes=3))
        with self.assertRaisesRegex(ProviderInvocationError, "TTL exceeds"):
            build(ttl_seconds=181)

    def test_rejects_tampered_request_hash(self) -> None:
        request = build()
        request["requested_url"] = "https://www.industrymsme.gov.mm/announcements/changed"
        with self.assertRaises(ProviderInvocationError):
            validate_provider_request(request, contract=contract(), now=NOW)

    def test_rejects_target_limit_escalation(self) -> None:
        with self.assertRaisesRegex(ProviderInvocationError, "max_bytes exceeds target"):
            build(max_bytes=1_000_001)
        with self.assertRaisesRegex(ProviderInvocationError, "max_run_seconds exceeds target"):
            build(max_run_seconds=46)

    def test_contract_rejects_capability_or_security_drift(self) -> None:
        missing_c3 = contract()
        missing_c3["allowed_capabilities"].remove("C3_BROWSER_USE")
        with self.assertRaisesRegex(ProviderInvocationError, r"C0\+C1\+C2\+C3"):
            validate_contract_projection(missing_c3)
        unsafe = copy.deepcopy(contract())
        unsafe["security"]["arbitrary_url_allowed"] = True
        with self.assertRaisesRegex(ProviderInvocationError, "security boundary"):
            validate_contract_projection(unsafe)


if __name__ == "__main__":
    unittest.main()
