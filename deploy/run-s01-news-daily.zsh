#!/bin/zsh
# Mac launchd entrypoint. Never invoke Tender Core; Bangkok owns Telegram transport.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/opt/anaconda3/bin:/usr/bin:/bin:/usr/sbin:/sbin"
REPO="/Users/xu/Documents/mcpx-projects/signalforge"
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
# --publish is explicit: normal dry-run defaults must not suppress scheduled TG delivery.
exec /opt/anaconda3/bin/python3 -m signalforge.s01_daily_runner \
  --root "$ROOT" --publish --host vps-bangkok
