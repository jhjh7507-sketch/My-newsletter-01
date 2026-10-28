#!/usr/bin/env python3
"""Re-voice a recording with ElevenLabs Speech-to-Speech, keeping its timing.

  python3 sts.py work/cut.mp4 --voice VOICE_ID --out work/voice_ai.mp3

The words, pauses and intonation stay the user's, so lip sync and the word
timings in words_cut.json still hold; only the voice changes. Needs the Speech
to Speech permission on the key. Use the user's own cloned voice when one
exists: a stranger's voice on a trainer's face reads as fake to people who
know them.
"""
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import el  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media")
    ap.add_argument("--voice", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="eleven_multilingual_sts_v2")
    ap.add_argument("--denoise", action="store_true", help="also strip background noise")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.media, "-vn", "-ac", "1",
                        "-ar", "44100", "-b:a", "128k", src], check=True)
        data = open(src, "rb").read()
    body, ctype = el.multipart(
        {"model_id": a.model, "remove_background_noise": "true" if a.denoise else "false"},
        {"audio": ("in.mp3", data, "audio/mpeg")})
    audio = el.call("POST", f"/v1/speech-to-speech/{a.voice}?output_format=mp3_44100_128", body,
                    {"Content-Type": ctype}, timeout=900)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(audio)
    print(f"{a.out}: {len(audio) // 1024} KB", file=sys.stderr)


if __name__ == "__main__":
    main()
