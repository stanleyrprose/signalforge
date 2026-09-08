from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from .config import db_path
from .provider_invocation import PIC_PROVIDER_ID
from .provider_result import ProviderResultError, accept_result_stream
from .provider_queue import (
    ProviderQueueError,
    claim_next_provider_request,
    complete_provider_claim,
    fail_provider_claim,
    provider_queue_status,
)


MAX_STDIN_BYTES = 64 * 1024
ALLOWED_COMMANDS = {
    "provider-claim-v1",
    "provider-status-v1",
    "provider-submit-v1",
    "provider-fail-v1",
}


class ProviderDispatcherError(RuntimeError):
    pass


def _strict_payload(payload: object, expected: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProviderDispatcherError("dispatcher payload must be a JSON object")
    if set(payload) != expected:
        raise ProviderDispatcherError("dispatcher payload fields do not match command contract")
    return payload


def dispatch(
    original_command: str,
    payload: object | None = None,
    *,
    database: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    command = original_command.strip()
    if command not in ALLOWED_COMMANDS or command != original_command:
        raise ProviderDispatcherError("DENY: unsupported provider command")
    target_db = database or db_path()
    observed_now = (now or datetime.now(UTC)).astimezone(UTC)

    if command == "provider-claim-v1":
        if payload is not None:
            raise ProviderDispatcherError("provider-claim-v1 accepts no payload")
        return claim_next_provider_request(
            provider_id=PIC_PROVIDER_ID,
            database=target_db,
            now=observed_now,
            lease_seconds=60,
        )

    if command == "provider-status-v1":
        if payload is not None:
            raise ProviderDispatcherError("provider-status-v1 accepts no payload")
        return provider_queue_status(provider_id=PIC_PROVIDER_ID, database=target_db, now=observed_now)

    if command == "provider-submit-v1":
        raise ProviderDispatcherError("provider-submit-v1 requires binary stream boundary")

    if command == "provider-fail-v1":
        body = _strict_payload(
            payload,
            {
                "provider_request_id",
                "provider_attempt_id",
                "claim_token",
                "failure_class",
            },
        )
        return fail_provider_claim(
            provider_request_id=str(body["provider_request_id"]),
            provider_attempt_id=str(body["provider_attempt_id"]),
            claim_token=str(body["claim_token"]),
            failure_class=str(body["failure_class"]),
            database=target_db,
            now=observed_now,
        )

    raise ProviderDispatcherError("DENY: unreachable provider command")


def _read_stdin_json(stream: TextIO) -> object:
    raw = stream.read(MAX_STDIN_BYTES + 1)
    if len(raw.encode("utf-8")) > MAX_STDIN_BYTES:
        raise ProviderDispatcherError("dispatcher payload exceeds 64KiB")
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderDispatcherError("dispatcher payload is not valid JSON") from exc


def main() -> int:
    original_command = os.environ.get("SSH_ORIGINAL_COMMAND")
    if original_command is None:
        print(json.dumps({"status": "DENY", "error": "SSH_ORIGINAL_COMMAND missing"}), flush=True)
        return 126
    try:
        payload = None
        if original_command == "provider-submit-v1":
            result = accept_result_stream(sys.stdin.buffer, database=db_path())
            print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
            return 0
        if original_command == "provider-fail-v1":
            payload = _read_stdin_json(sys.stdin)
        elif original_command in {"provider-claim-v1", "provider-status-v1"}:
            # Do not consume arbitrary client data for no-payload commands.
            payload = None
        result = dispatch(original_command, payload)
    except (ProviderDispatcherError, ProviderQueueError, ProviderResultError) as exc:
        print(json.dumps({"status": "DENY", "error": str(exc)}, sort_keys=True), flush=True)
        return 126
    except Exception as exc:
        # No traceback or environment disclosure across the SSH boundary.
        print(json.dumps({"status": "ERROR", "error": exc.__class__.__name__}, sort_keys=True), flush=True)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
