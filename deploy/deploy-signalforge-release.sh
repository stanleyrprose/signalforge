#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "deploy must run as root" >&2
  exit 2
fi

RELEASE="${1:-}"
SOURCE="${2:-}"
case "$RELEASE" in *[!0-9a-f]*|'') echo "release must be lowercase hex" >&2; exit 2;; esac
[ ${#RELEASE} -ge 12 ] || { echo "release sha too short" >&2; exit 2; }
[ -d "$SOURCE" ] || { echo "source directory missing" >&2; exit 2; }

APP_DESC=/var/lib/worker/application-descriptors/active/signalforge.json
[ -f "$APP_DESC" ] || { echo "SignalForge Worker provider descriptor missing" >&2; exit 78; }
python3 - "$APP_DESC" <<'PY'
import json, pathlib, sys
value=json.loads(pathlib.Path(sys.argv[1]).read_text())
if value.get('application') != 'signalforge' or value.get('worker') != 'bangkok':
    raise SystemExit('SignalForge provider is not Bangkok canonical')
if value.get('process_user') != 'signalforge' or value.get('identity_class') != 'dedicated-user':
    raise SystemExit('SignalForge dedicated identity contract missing')
if value.get('runtime_sha') != pathlib.Path('/srv/worker/current-release').resolve().name:
    raise SystemExit('SignalForge provider runtime is not current Worker release')
PY

getent group signalforge >/dev/null 2>&1 || groupadd --system signalforge
id signalforge >/dev/null 2>&1 || useradd --system --gid signalforge --no-create-home --shell /usr/sbin/nologin signalforge

ROOT=/srv/signalforge
FINAL="$ROOT/releases/$RELEASE"
STAGE="$ROOT/releases/.stage-$RELEASE-$$"
OLD=""
[ ! -L "$ROOT/active" ] || OLD="$(basename "$(readlink -f "$ROOT/active")")"
TIMER_WAS_ENABLED=0
systemctl is-enabled signalforge-run-due.timer >/dev/null 2>&1 && TIMER_WAS_ENABLED=1 || true

install -d -m 0755 -o root -g root "$ROOT" "$ROOT/releases" "$ROOT/venvs"
install -d -m 0700 -o signalforge -g signalforge "$ROOT/state" "$ROOT/evidence" "$ROOT/artifacts" "$ROOT/tmp" "$ROOT/locks"

cleanup() {
  rc=$?
  trap - EXIT
  rm -rf "$STAGE"
  if [ "$rc" -ne 0 ]; then
    if [ -n "$OLD" ] && [ -d "$ROOT/releases/$OLD" ]; then
      ln -sfn "$ROOT/releases/$OLD" "$ROOT/active"
    fi
    if [ "$TIMER_WAS_ENABLED" -eq 1 ]; then
      systemctl enable --now signalforge-run-due.timer >/dev/null 2>&1 || true
    fi
  fi
  exit "$rc"
}
trap cleanup EXIT

systemctl disable --now signalforge-run-due.timer >/dev/null 2>&1 || true
for _i in $(seq 1 30); do
  state="$(systemctl is-active signalforge-run-due.service 2>/dev/null || true)"
  [ "$state" != active ] && [ "$state" != activating ] && break
  sleep 1
done
state="$(systemctl is-active signalforge-run-due.service 2>/dev/null || true)"
[ "$state" != active ] && [ "$state" != activating ] || { echo "SignalForge busy; deploy deferred" >&2; exit 75; }

if [ ! -d "$FINAL" ]; then
  install -d -m 0755 -o root -g root "$STAGE"
  cp -a "$SOURCE"/. "$STAGE"/
  rm -rf "$STAGE/.git" "$STAGE/.ai-bridge" "$STAGE/__pycache__"
  chmod 0755 "$STAGE/bin/signalforge"
  python3 -m compileall -q "$STAGE/signalforge"
  chown -R root:root "$STAGE"
  chmod -R go-w "$STAGE"
  mv "$STAGE" "$FINAL"
fi

ln -sfn "$FINAL" "$ROOT/active"
runuser -u signalforge -- env \
  SIGNALFORGE_STATE_ROOT="$ROOT/state" \
  SIGNALFORGE_EVIDENCE_ROOT="$ROOT/evidence" \
  SIGNALFORGE_DB="$ROOT/state/signalforge.db" \
  "$ROOT/active/bin/signalforge" migrate >/dev/null

install -m 0644 /srv/worker/current-release/generated/applications/signalforge/signalforge-run-due.service /etc/systemd/system/signalforge-run-due.service
install -m 0644 "$FINAL/systemd/signalforge-run-due.timer" /etc/systemd/system/signalforge-run-due.timer
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/signalforge-run-due.service /etc/systemd/system/signalforge-run-due.timer >/dev/null

runuser -u signalforge -- env \
  SIGNALFORGE_STATE_ROOT="$ROOT/state" \
  SIGNALFORGE_EVIDENCE_ROOT="$ROOT/evidence" \
  SIGNALFORGE_DB="$ROOT/state/signalforge.db" \
  "$ROOT/active/bin/signalforge" status >/dev/null

# Gate O requires a manual real fixture/baseline run before 24x7 enable.
if [ "$TIMER_WAS_ENABLED" -eq 1 ]; then
  systemctl enable --now signalforge-run-due.timer >/dev/null
fi

trap - EXIT
rm -rf "$STAGE"
echo "deployment=success application=signalforge release=$RELEASE previous=${OLD:-none} timer_preexisting=$TIMER_WAS_ENABLED"
