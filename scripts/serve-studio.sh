#!/usr/bin/env bash
# Open the Studio page at http://127.0.0.1:3900/
# VoiceStudio's speech API, when you start it, stays on 127.0.0.1:3901.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
export SFVS_STUDIO_PORT="${SFVS_STUDIO_PORT:-3900}"
exec python3 -m shadowfetch_worker.studio.serve
