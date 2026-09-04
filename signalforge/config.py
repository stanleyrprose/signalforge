from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .acquisition_contract import AcquisitionContractError, validate_source_acquisition_policy
from .source_adapters import ADAPTERS


class ConfigError(RuntimeError):
    pass


SOURCE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{0,15}$")


def repo_root() -> Path:
    return Path(os.environ.get("SIGNALFORGE_REPO_ROOT", Path(__file__).resolve().parents[1]))


def state_root() -> Path:
    return Path(os.environ.get("SIGNALFORGE_STATE_ROOT", "/srv/signalforge/state"))


def evidence_root() -> Path:
    return Path(os.environ.get("SIGNALFORGE_EVIDENCE_ROOT", "/srv/signalforge/evidence"))


def db_path() -> Path:
    return Path(os.environ.get("SIGNALFORGE_DB", str(state_root() / "signalforge.db")))


@dataclass(frozen=True)
class Registry:
    raw: dict[str, Any]

    @classmethod
    def load(cls, root: Path | None = None) -> "Registry":
        path = (root or repo_root()) / "registry" / "Source-Registry-v1.yaml"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(f"cannot load source registry: {exc}") from exc
        if value.get("registry_version") != 1 or value.get("source_schema_version") != 1:
            raise ConfigError("unsupported source registry version")
        policy = value.get("production_policy") or {}
        if policy.get("canonical_node") != "bangkok":
            raise ConfigError("R5 SignalForge canonical node must be bangkok")
        if policy.get("default_engine") != "direct_http" or policy.get("tls_verification_required") is not True:
            raise ConfigError("R5 production must be Direct HTTP with TLS verification")
        if policy.get("browser_production_approved") is not False:
            raise ConfigError("R5 browser production must remain disabled")
        sources = value.get("sources")
        if not isinstance(sources, dict) or not sources:
            raise ConfigError("source registry must contain sources")
        for source_id, source in sources.items():
            if not isinstance(source, dict) or source.get("enabled") is not True:
                continue
            adapter = source.get("adapter")
            if not isinstance(adapter, str) or adapter not in ADAPTERS:
                raise ConfigError(f"unsupported source adapter: {source_id}")
            try:
                validate_source_acquisition_policy(source_id, source)
            except AcquisitionContractError as exc:
                raise ConfigError(str(exc)) from exc
            health = source.get("health_policy")
            if not isinstance(health, dict):
                raise ConfigError(f"active source health policy missing: {source_id}")
            int_fields = (
                "freshness_yellow_seconds", "freshness_red_seconds",
                "fetch_yellow_failures", "fetch_red_failures",
                "parse_window_runs", "parse_min_attempts", "parse_probe_interval_seconds",
            )
            for field in int_fields:
                if not isinstance(health.get(field), int) or int(health[field]) < 1:
                    raise ConfigError(f"invalid health policy {field}: {source_id}")
            if health["freshness_yellow_seconds"] >= health["freshness_red_seconds"]:
                raise ConfigError(f"freshness health thresholds out of order: {source_id}")
            if health["fetch_yellow_failures"] >= health["fetch_red_failures"]:
                raise ConfigError(f"fetch health thresholds out of order: {source_id}")
            yellow = health.get("parse_yellow_ratio")
            red = health.get("parse_red_ratio")
            if not isinstance(yellow, (int, float)) or not isinstance(red, (int, float)):
                raise ConfigError(f"parse health ratios missing: {source_id}")
            if not 0 <= float(red) < float(yellow) <= 1:
                raise ConfigError(f"parse health ratios out of order: {source_id}")
            parse_sample_source = health.get("parse_sample_source", "DETAIL_SCHEDULER")
            if parse_sample_source not in {"DETAIL_SCHEDULER", "BUSINESS_PROCESSING"}:
                raise ConfigError(f"invalid parse sample source: {source_id}")
        return cls(value)

    def enabled_sources(self) -> list[tuple[str, dict[str, Any]]]:
        result: list[tuple[str, dict[str, Any]]] = []
        for source_id, source in sorted((self.raw.get("sources") or {}).items()):
            if not isinstance(source, dict) or source.get("enabled") is not True:
                continue
            if source.get("engine") != "direct_http":
                raise ConfigError(f"active R5 source must use direct_http: {source_id}")
            if source.get("network_zone") != "myanmar-international":
                raise ConfigError(f"active R5 source must route to Bangkok zone: {source_id}")
            result.append((source_id, source))
        return result

    def source(self, source_id: str) -> dict[str, Any]:
        if not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise ConfigError(f"invalid source id: {source_id}")
        value = (self.raw.get("sources") or {}).get(source_id)
        if not isinstance(value, dict) or value.get("enabled") is not True:
            raise ConfigError(f"source is not active: {source_id}")
        return value
