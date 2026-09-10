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
STAGE="$ROOT/releases/.stage-$RELEASE"
VENV="$ROOT/venvs/$RELEASE"
VENV_STAGE="$ROOT/venvs/.stage-$RELEASE"
OLD=""
[ ! -L "$ROOT/active" ] || OLD="$(basename "$(readlink -f "$ROOT/active")")"
TIMER_WAS_ENABLED=0
DELIVERY_TIMER_WAS_ENABLED=0
DIGEST_TIMER_WAS_ENABLED=0
systemctl is-enabled signalforge-run-due.timer >/dev/null 2>&1 && TIMER_WAS_ENABLED=1 || true
systemctl is-enabled signalforge-telegram-deliver.timer >/dev/null 2>&1 && DELIVERY_TIMER_WAS_ENABLED=1 || true
systemctl is-enabled signalforge-telegram-digest.timer >/dev/null 2>&1 && DIGEST_TIMER_WAS_ENABLED=1 || true

install -d -m 0755 -o root -g root "$ROOT" "$ROOT/releases" "$ROOT/venvs"
install -d -m 0700 -o signalforge -g signalforge "$ROOT/state" "$ROOT/evidence" "$ROOT/artifacts" "$ROOT/tmp" "$ROOT/locks"
install -d -m 0750 -o root -g signalforge /etc/signalforge

cleanup() {
  rc=$?
  trap - EXIT
  rm -rf "$STAGE" "$VENV_STAGE"
  if [ "$rc" -ne 0 ]; then
    if [ -n "$OLD" ] && [ -d "$ROOT/releases/$OLD" ]; then
      ln -sfn "$ROOT/releases/$OLD" "$ROOT/active"
    fi
    if [ "$TIMER_WAS_ENABLED" -eq 1 ]; then
      systemctl enable --now signalforge-run-due.timer >/dev/null 2>&1 || true
    fi
    if [ "$DELIVERY_TIMER_WAS_ENABLED" -eq 1 ]; then
      systemctl enable --now signalforge-telegram-deliver.timer >/dev/null 2>&1 || true
    fi
    if [ "$DIGEST_TIMER_WAS_ENABLED" -eq 1 ]; then
      systemctl enable --now signalforge-telegram-digest.timer >/dev/null 2>&1 || true
    fi
  fi
  exit "$rc"
}
trap cleanup EXIT

systemctl disable --now signalforge-run-due.timer >/dev/null 2>&1 || true
systemctl disable --now signalforge-telegram-deliver.timer >/dev/null 2>&1 || true
systemctl disable --now signalforge-telegram-digest.timer >/dev/null 2>&1 || true
for _i in $(seq 1 30); do
  state="$(systemctl is-active signalforge-run-due.service 2>/dev/null || true)"
  delivery_state="$(systemctl is-active signalforge-telegram-deliver.service 2>/dev/null || true)"
  digest_state="$(systemctl is-active signalforge-telegram-digest.service 2>/dev/null || true)"
  refresh_busy="$(systemctl list-units --type=service --state=active,activating --no-legend --no-pager 'signalforge-refresh@*.service' 2>/dev/null | wc -l | tr -d ' ')"
  [ "$state" != active ] && [ "$state" != activating ] && [ "$delivery_state" != active ] && [ "$delivery_state" != activating ] && [ "$digest_state" != active ] && [ "$digest_state" != activating ] && [ "$refresh_busy" -eq 0 ] && break
  sleep 1
done
state="$(systemctl is-active signalforge-run-due.service 2>/dev/null || true)"
delivery_state="$(systemctl is-active signalforge-telegram-deliver.service 2>/dev/null || true)"
digest_state="$(systemctl is-active signalforge-telegram-digest.service 2>/dev/null || true)"
refresh_busy="$(systemctl list-units --type=service --state=active,activating --no-legend --no-pager 'signalforge-refresh@*.service' 2>/dev/null | wc -l | tr -d ' ')"
[ "$state" != active ] && [ "$state" != activating ] && [ "$delivery_state" != active ] && [ "$delivery_state" != activating ] && [ "$digest_state" != active ] && [ "$digest_state" != activating ] && [ "$refresh_busy" -eq 0 ] || { echo "SignalForge busy; deploy deferred" >&2; exit 75; }

if [ ! -d "$FINAL" ]; then
  install -d -m 0755 -o root -g root "$STAGE"
  cp -a "$SOURCE"/. "$STAGE"/
  # cp -a SOURCE/. may preserve a restrictive SOURCE root mode onto STAGE
  # (for example mktemp -d creates 0700). Normalize the release root so the
  # dedicated signalforge user can traverse and execute the reviewed runtime.
  chmod 0755 "$STAGE"
  rm -rf "$STAGE/.git" "$STAGE/.ai-bridge" "$STAGE/__pycache__"
  chmod 0755 "$STAGE/bin/signalforge" "$STAGE/bin/signalforge-provider-dispatcher"
  python3 -m compileall -q "$STAGE/signalforge"
  chown -R root:root "$STAGE"
  chmod -R go-w "$STAGE"
  mv "$STAGE" "$FINAL"
fi

if [ ! -x "$VENV/bin/python" ]; then
  /usr/bin/python3 -m venv "$VENV_STAGE"
  "$VENV_STAGE/bin/python" -m pip install --disable-pip-version-check --no-input "$FINAL"
  chown -R root:root "$VENV_STAGE"
  chmod -R go-w "$VENV_STAGE"
  mv "$VENV_STAGE" "$VENV"
fi
ln -sfn "../../venvs/$RELEASE" "$FINAL/.venv"
"$VENV/bin/python" -c 'import pypdf; assert pypdf.__version__ == "6.16.2"'

ln -sfn "$FINAL" "$ROOT/active"
runuser -u signalforge -- env \
  SIGNALFORGE_STATE_ROOT="$ROOT/state" \
  SIGNALFORGE_EVIDENCE_ROOT="$ROOT/evidence" \
  SIGNALFORGE_DB="$ROOT/state/signalforge.db" \
  "$ROOT/active/bin/signalforge" migrate >/dev/null

install -m 0644 /srv/worker/current-release/generated/applications/signalforge/signalforge-run-due.service /etc/systemd/system/signalforge-run-due.service
install -m 0644 /srv/worker/current-release/generated/applications/signalforge/signalforge-refresh@.service /etc/systemd/system/signalforge-refresh@.service
install -m 0644 "$FINAL/systemd/signalforge-run-due.timer" /etc/systemd/system/signalforge-run-due.timer
install -m 0644 "$FINAL/systemd/signalforge-telegram-deliver.service" /etc/systemd/system/signalforge-telegram-deliver.service
install -m 0644 "$FINAL/systemd/signalforge-telegram-deliver.timer" /etc/systemd/system/signalforge-telegram-deliver.timer
install -m 0644 "$FINAL/systemd/signalforge-telegram-digest.service" /etc/systemd/system/signalforge-telegram-digest.service
install -m 0644 "$FINAL/systemd/signalforge-telegram-digest.timer" /etc/systemd/system/signalforge-telegram-digest.timer
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/signalforge-run-due.service /etc/systemd/system/signalforge-refresh@.service /etc/systemd/system/signalforge-run-due.timer /etc/systemd/system/signalforge-telegram-deliver.service /etc/systemd/system/signalforge-telegram-deliver.timer /etc/systemd/system/signalforge-telegram-digest.service /etc/systemd/system/signalforge-telegram-digest.timer >/dev/null

runuser -u signalforge -- env \
  SIGNALFORGE_STATE_ROOT="$ROOT/state" \
  SIGNALFORGE_EVIDENCE_ROOT="$ROOT/evidence" \
  SIGNALFORGE_DB="$ROOT/state/signalforge.db" \
  "$ROOT/active/bin/signalforge" status >/dev/null

# Gate O requires a manual real fixture/baseline run before 24x7 enable.
if [ "$TIMER_WAS_ENABLED" -eq 1 ]; then
  systemctl enable --now signalforge-run-due.timer >/dev/null
fi
if [ "$DELIVERY_TIMER_WAS_ENABLED" -eq 1 ]; then
  systemctl enable --now signalforge-telegram-deliver.timer >/dev/null
fi
if [ "$DIGEST_TIMER_WAS_ENABLED" -eq 1 ]; then
  systemctl enable --now signalforge-telegram-digest.timer >/dev/null
fi

trap - EXIT
rm -rf "$STAGE" "$VENV_STAGE"
echo "deployment=success application=signalforge release=$RELEASE previous=${OLD:-none} timer_preexisting=$TIMER_WAS_ENABLED"
