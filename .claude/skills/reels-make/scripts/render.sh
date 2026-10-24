#!/usr/bin/env bash
# Render a built project to MP4 with the pinned HyperFrames CLI.
#   bash render.sh work/project out.mp4
set -euo pipefail
proj="$1"; out="$(realpath -m "${2:-$1/out.mp4}")"
HF_VERSION=0.8.143
if [ -z "${HYPERFRAMES_BROWSER_PATH:-}" ]; then
  shell=$(ls /opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell 2>/dev/null | head -1 || true)
  [ -n "$shell" ] && export HYPERFRAMES_BROWSER_PATH="$shell"
fi
export HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_TELEMETRY=1
cd "$proj"
npx --yes "hyperframes@${HF_VERSION}" render -o "$out" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -vE "Framey|desktop app|pins hyperframes|Bump it" || true
test -s "$out" && ffprobe -v error -show_entries format=duration -of csv=p=0 "$out" | xargs -I{} echo "rendered $out ({}s)"
