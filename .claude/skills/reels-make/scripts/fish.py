#!/usr/bin/env python3
"""Narration from Fish Audio, with word timings from ElevenLabs Speech to Text.

  python3 fish.py script.txt --voice REFERENCE_ID --out work/
  python3 fish.py script.txt --voice REFERENCE_ID --out work/ --no-timing

Writes work/voice.mp3 and work/words.json ([{text, start, end}], seconds), the
same files tts.py writes, so build.py takes either. The default model
`s2.1-pro-free` costs nothing on the Fish API (2026-10-31). Fish's plain TTS
call returns no word times, so the timings come from stt.py on the generated
audio (about 70 ElevenLabs credits a minute); fix its spelling against the
script before building. REFERENCE_ID is the voice's id from its fish.audio page
URL. Needs FISH_API_KEY and api.fish.audio allowed in the network settings.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--voice", help="reference_id of a Fish Audio voice")
    ap.add_argument("--model", default="s2.1-pro-free")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--out", default="work")
    ap.add_argument("--no-timing", action="store_true", help="skip the ElevenLabs word timings")
    a = ap.parse_args()

    key = os.environ.get("FISH_API_KEY", "").strip()
    if not key:
        sys.exit("FISH_API_KEY is not set (add it in the environment settings)")
    payload = {"text": open(a.script, encoding="utf-8").read().strip(), "format": "mp3",
               "mp3_bitrate": 128, "prosody": {"speed": a.speed}}
    if a.voice:
        payload["reference_id"] = a.voice
    req = urllib.request.Request("https://api.fish.audio/v1/tts", data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                          "model": a.model}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            audio = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"Fish Audio TTS -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    os.makedirs(a.out, exist_ok=True)
    mp3 = os.path.join(a.out, "voice.mp3")
    open(mp3, "wb").write(audio)
    print(f"voice.mp3: {len(audio) // 1024} KB from Fish Audio ({a.model})", file=sys.stderr)
    if not a.no_timing:
        subprocess.run([sys.executable, os.path.join(HERE, "stt.py"), mp3, "--out", a.out], check=True)


if __name__ == "__main__":
    main()
