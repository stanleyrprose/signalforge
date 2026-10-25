#!/bin/zsh
# Mac launchd entrypoint. Never invoke Tender Core; Bangkok owns Telegram transport.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin"
REPO="/Users/xu/Library/Application Support/SignalForge/runtime"
ROOT="/Users/xu/Library/Application Support/SignalForge/S01Daily"
mkdir -p "$ROOT" "/Users/xu/Library/Logs/SignalForge"
cd "$REPO"
if ! command -v codex >/dev/null 2>&1; then
  print -u2 "S01 not published: Codex CLI unavailable for required Chinese review"
  exit 1
fi
if [[ ! -f "$REPO/signalforge/s01_daily_runner.py" ]]; then
  print -u2 "S01 not published: runner missing"
  exit 1
fi
# The schedule owns one completed issue per Yangon date and resumes immutable manifests.
exec /opt/anaconda3/bin/python3 -m signalforge.s01_daily_schedule --root "$ROOT"
