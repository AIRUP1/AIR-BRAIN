#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p dialer_inbox

: "${DIALER_BATCH:=150}"
: "${DIALER_GAP:=2}"
: "${MAX_FAILURES:=3}"

python -m webex_batch_dialer auto dialer_inbox \
  --once \
  --batch-size "$DIALER_BATCH" \
  --max-failures "$MAX_FAILURES" \
  --gap "$DIALER_GAP"
