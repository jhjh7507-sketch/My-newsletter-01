#!/usr/bin/env python3
"""Narration with word timings from ElevenLabs.

  python3 tts.py script.txt --voice VOICE_ID --out work/
  python3 tts.py --list-voices

Writes work/voice.mp3 and work/words.json ([{text, start, end}], seconds).
"""
import argparse
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import el  # noqa: E402

DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script", nargs="?")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--model", default="eleven_multilingual_v2")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--stability", type=float, default=0.5)
    ap.add_argument("--out", default="work")
    ap.add_argument("--list-voices", action="store_true")
    a = ap.parse_args()

    if a.list_voices:
        for v in el.call_json("GET", "/v1/voices")["voices"]:
            labels = ", ".join(f"{k}={x}" for k, x in (v.get("labels") or {}).items())
            print(f"{v['voice_id']}  {v['name']}  {labels}")
        return

    text = open(a.script, encoding="utf-8").read().strip()
    payload = {
        "text": text,
        "model_id": a.model,
        "voice_settings": {"stability": a.stability, "similarity_boost": 0.75, "speed": a.speed},
    }
    r = el.call_json("POST", f"/v1/text-to-speech/{a.voice}/with-timestamps?output_format=mp3_44100_128", payload)
    al = r.get("normalized_alignment") or r["alignment"]
    words = el.chars_to_words(al["characters"], al["character_start_times_seconds"],
                              al["character_end_times_seconds"])
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "voice.mp3"), "wb") as f:
        f.write(base64.b64decode(r["audio_base64"]))
    with open(os.path.join(a.out, "words.json"), "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=1)
    dur = words[-1]["end"] if words else 0
    print(f"voice.mp3 + words.json: {len(words)} words, {dur:.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
