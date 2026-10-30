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
test -s "$out"
# The renderer writes about 12 Mbps; a 76-second reel came out at 117 MB and the
# user could not save it on the phone (2026-10-31). Bring it to Instagram's own
# range (about 4-5 Mbps) with no visible loss.
if [ "$(ffprobe -v error -show_entries format=bit_rate -of csv=p=0 "$out")" -gt 6000000 ]; then
  tmp="${out%.mp4}.tmp.mp4"
  ffmpeg -v error -y -i "$out" -c:v libx264 -preset slow -crf 21 -maxrate 5M -bufsize 10M \
         -profile:v high -level 4.1 -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 \
         -colorspace bt709 -c:a aac -b:a 160k -movflags +faststart "$tmp" && mv "$tmp" "$out"
fi
ffprobe -v error -show_entries format=duration -of csv=p=0 "$out" | xargs -I{} echo "rendered $out ({}s, $(du -m "$out" | cut -f1) MB)"
