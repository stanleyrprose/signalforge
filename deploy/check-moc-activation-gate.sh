#!/bin/sh
set -eu

URL='https://construction.gov.mm/tindar-show/f878a520-d396-11ec-957c-cb8c3b494625?state_name=all'

# Intentionally rely on curl's default strict certificate verification.
# Do not add -k/--insecure or a custom CA-ignore path here.
if status="$(curl --silent --show-error --location --max-time 20 \
  --output /dev/null --write-out '%{http_code}' "$URL")"; then
  :
else
  rc=$?
  echo "gate=FAIL source=S23 reason=STRICT_TLS_OR_TRANSPORT curl_rc=$rc" >&2
  exit "$rc"
fi

if [ "$status" != "200" ]; then
  echo "gate=FAIL source=S23 reason=HTTP_STATUS status=$status" >&2
  exit 1
fi

echo "gate=PASS source=S23 tls=strict http_status=200"
