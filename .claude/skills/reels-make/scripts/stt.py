#!/usr/bin/env python3
"""Word-timed transcript of a recorded video via ElevenLabs Speech-to-Text.

  python3 stt.py raw.mov --out work/

Writes work/words.json ([{text, start, end}]). The key needs the
Speech to Text permission.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import el  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--lang", default="kor")
    ap.add_argument("--out", default="work")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "a.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vn", "-ac", "1",
                        "-ar", "16000", "-b:a", "64k", wav], check=True)
        data = open(wav, "rb").read()
    body, ctype = el.multipart(
        {"model_id": "scribe_v1", "language_code": a.lang, "timestamps_granularity": "word",
         "tag_audio_events": "false"},
        {"file": ("audio.mp3", data, "audio/mpeg")})
    r = json.loads(el.call("POST", "/v1/speech-to-text", body, {"Content-Type": ctype}, timeout=900))
    words = [{"text": w["text"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)}
             for w in r.get("words", []) if w.get("type") == "word" and w["text"].strip()]
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "words.json"), "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=1)
    print(f"words.json: {len(words)} words", file=sys.stderr)


if __name__ == "__main__":
    main()
