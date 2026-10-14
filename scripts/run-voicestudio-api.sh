#!/usr/bin/env bash
# Start the VoiceStudio API on loopback for Shadowfetch Voice Studio.
# Requires the checkout from scripts/fetch-voicestudio.sh, plus that project's
# own Python environment (see its README: bun run setup:api, or uv).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${SFVS_VOICESTUDIO_ROOT:-$ROOT/third_party/VoiceStudio}"
PORT="${OMNIVOICE_PORT:-3900}"

if [[ ! -f "$DEST/backend/main.py" ]]; then
  echo "VoiceStudio is not checked out. Run scripts/fetch-voicestudio.sh first." >&2
  exit 1
fi

cd "$DEST"
export OMNIVOICE_PORT="$PORT"
export OMNIVOICE_BIND_HOST="${OMNIVOICE_BIND_HOST:-127.0.0.1}"
if [[ -x "$DEST/.venv/bin/python" ]]; then
  exec "$DEST/.venv/bin/python" -m backend.main
fi
exec python3 -m backend.main
