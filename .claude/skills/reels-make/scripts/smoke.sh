#!/usr/bin/env bash
# Smoke test for a new setup: builds a 3-second reel from a generated test clip
# (no footage, no API calls) and renders it. Run from the repo root:
#   bash .claude/skills/reels-make/scripts/smoke.sh
# Prints "SMOKE OK <path>" when ffmpeg, Python (yaml, PIL), Node/npx, the
# render browser and the CDN (fonts, GSAP) all work.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../../../.." && pwd)"
out="$root/work/smoke"
rm -rf "$out" && mkdir -p "$out"
ffmpeg -v error -y -f lavfi -i "testsrc2=size=1080x1920:rate=30:duration=3" \
       -f lavfi -i "sine=frequency=440:duration=3" -shortest \
       -c:v libx264 -pix_fmt yuv420p -c:a aac "$out/clip.mp4"
cat > "$out/words.json" <<'EOF'
[{"text": "테스트", "start": 0.2, "end": 0.9}, {"text": "영상입니다.", "start": 1.0, "end": 2.2}]
EOF
cat > "$out/plan.json" <<'EOF'
{"mode": "face", "layout": "mixed", "video": "clip.mp4", "words": "words.json",
 "scenes": [{"start": 0, "layout": "face"},
            {"start": 1.0, "layout": "split", "type": "keyword", "kicker": "SMOKE TEST", "text": "설치 확인"}]}
EOF
style="$root/.claude/instagram/style.yaml"
[ -f "$style" ] || style="$here/../style.default.yaml"
python3 "$here/build.py" "$out/plan.json" --style "$style" --out "$out/project"
bash "$here/render.sh" "$out/project" "$out/reel.mp4"
test -s "$out/reel.mp4" && echo "SMOKE OK $out/reel.mp4"
