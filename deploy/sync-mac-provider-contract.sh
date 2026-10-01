#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE="$ROOT/registry/Provider-Invocation-Contract-v1.json"
TARGET="${SIGNALFORGE_MAC_PROVIDER_CONTRACT:-$HOME/agent-browser-runtime/config/provider-contract-v1.json}"
LABEL="${SIGNALFORGE_MAC_PROVIDER_LAUNCH_LABEL:-com.stanley.mac-browser-provider}"
MODE="${1:---check}"

[ -f "$SOURCE" ] || { echo "missing repo provider contract: $SOURCE" >&2; exit 2; }
[ -f "$TARGET" ] || { echo "missing Mac provider contract: $TARGET" >&2; exit 3; }

validate_contract() {
  python3 - "$1" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
value = json.loads(path.read_text(encoding="utf-8"))
policies = value.get("source_policies") or {}
required = {
    "S15A": 2,
    "S27": 2,
    "S38": 2,
}
for source_id, version in required.items():
    policy = policies.get(source_id)
    if not isinstance(policy, dict):
        raise SystemExit(f"missing provider source policy: {source_id}")
    if int(policy.get("source_policy_version") or 0) != version:
        raise SystemExit(
            f"unexpected provider source policy version: {source_id}="
            f"{policy.get('source_policy_version')!r}, expected {version}"
        )
print("provider_contract_validation=PASS")
PY
}

digest() {
  shasum -a 256 "$1" | awk '{print $1}'
}

validate_contract "$SOURCE"
SOURCE_SHA=$(digest "$SOURCE")
TARGET_SHA=$(digest "$TARGET")

if [ "$MODE" = "--check" ]; then
  printf 'repo_sha256=%s\nruntime_sha256=%s\n' "$SOURCE_SHA" "$TARGET_SHA"
  if [ "$SOURCE_SHA" != "$TARGET_SHA" ]; then
    echo "provider_contract_sync=DRIFT"
    exit 10
  fi
  validate_contract "$TARGET"
  echo "provider_contract_sync=PASS"
  exit 0
fi

[ "$MODE" = "--sync" ] || { echo "usage: $0 [--check|--sync]" >&2; exit 64; }

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP="$TARGET.bak-$STAMP"
cp -p "$TARGET" "$BACKUP"
cp -p "$SOURCE" "$TARGET"

TARGET_SHA=$(digest "$TARGET")
[ "$SOURCE_SHA" = "$TARGET_SHA" ] || {
  cp -p "$BACKUP" "$TARGET"
  echo "provider contract hash mismatch after sync; restored backup" >&2
  exit 11
}

validate_contract "$TARGET"
launchctl kickstart -k "gui/$(id -u)/$LABEL"
printf 'provider_contract_sync=PASS\nbackup=%s\nsha256=%s\nlaunch_label=%s\n' "$BACKUP" "$TARGET_SHA" "$LABEL"
