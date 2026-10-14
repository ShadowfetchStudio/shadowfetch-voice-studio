#!/usr/bin/env bash
# Download VoiceStudio next to this app. The tree stays AGPL-3.0 and is not
# relicensed. Shadowfetch talks to it over HTTP; it does not import its code.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${SFVS_VOICESTUDIO_ROOT:-$ROOT/third_party/VoiceStudio}"
URL="https://github.com/debpalash/VoiceStudio.git"

if [[ -d "$DEST/.git" ]]; then
  git -C "$DEST" fetch --depth 1 origin main
  git -C "$DEST" checkout --detach FETCH_HEAD
else
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 "$URL" "$DEST"
fi

echo "VoiceStudio is at $DEST"
echo "Start its API with: scripts/run-voicestudio-api.sh"
