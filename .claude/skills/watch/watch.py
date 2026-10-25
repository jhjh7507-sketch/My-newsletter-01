#!/usr/bin/env python3
"""Turn a video into something Claude can read: timed frames + transcript.

  python3 watch.py reel.mov --out work/watch/reel

Writes into --out:
  frames/t012.40.jpg   one frame per scene change (and at least every --every s)
  sheet_01.jpg ...     the frames tiled 4x3 with their timestamps
  words.json           word-timed transcript (ElevenLabs STT, needs the
                       Speech to Text permission; skipped if it fails)
  timeline.md          each frame's timestamp with what was said until the next
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "reels-make", "scripts"))


def frames(video, out, scene, every, width):
    d = os.path.join(out, "frames")
    os.makedirs(d, exist_ok=True)
    sel = f"gt(scene,{scene})+isnan(prev_selected_t)+gte(t-prev_selected_t,{every})"
    p = subprocess.run(
        ["ffmpeg", "-v", "info", "-y", "-i", video, "-vf",
         f"select='{sel}',scale={width}:-2,showinfo", "-vsync", "vfr", os.path.join(d, "raw_%04d.jpg")],
        capture_output=True, text=True)
    if p.returncode:
        sys.exit(p.stderr[-800:])
    times = [float(t) for t in re.findall(r"pts_time:([\d.]+)", p.stderr)]
    raws = sorted(f for f in os.listdir(d) if f.startswith("raw_"))
    shots = []
    for f, t in zip(raws, times):
        name = f"t{t:06.2f}.jpg"
        os.replace(os.path.join(d, f), os.path.join(d, name))
        shots.append((t, os.path.join(d, name)))
    return shots


def sheets(shots, out, cols=4, rows=3):
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype(subprocess.run(["fc-match", "-f", "%{file}", "sans"],
                                                 capture_output=True, text=True).stdout, 28)
    except Exception:
        font = ImageFont.load_default()
    per = cols * rows
    paths = []
    for i in range(0, len(shots), per):
        batch = shots[i:i + per]
        ims = [Image.open(p).convert("RGB") for _, p in batch]
        w, h = ims[0].size
        sheet = Image.new("RGB", (w * cols, h * ((len(ims) + cols - 1) // cols)), "black")
        for j, ((t, _), im) in enumerate(zip(batch, ims)):
            x, y = (j % cols) * w, (j // cols) * h
            sheet.paste(im.resize((w, h)), (x, y))
            draw = ImageDraw.Draw(sheet)
            draw.rectangle([x, y, x + 120, y + 40], fill="black")
            draw.text((x + 8, y + 4), f"{t:.1f}s", fill="yellow", font=font)
        p = os.path.join(out, f"sheet_{i // per + 1:02d}.jpg")
        sheet.save(p, quality=85)
        paths.append(p)
    return paths


def transcript(video, out, lang):
    import tempfile
    import el
    with tempfile.TemporaryDirectory() as td:
        mp3 = os.path.join(td, "a.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1",
                        "-ar", "16000", "-b:a", "64k", mp3], check=True)
        data = open(mp3, "rb").read()
    body, ctype = el.multipart(
        {"model_id": "scribe_v1", "language_code": lang, "timestamps_granularity": "word",
         "tag_audio_events": "false"},
        {"file": ("audio.mp3", data, "audio/mpeg")})
    r = json.loads(el.call("POST", "/v1/speech-to-text", body, {"Content-Type": ctype}, timeout=900))
    words = [{"text": w["text"].strip(), "start": round(w["start"], 2), "end": round(w["end"], 2)}
             for w in r.get("words", []) if w.get("type") == "word" and w["text"].strip()]
    with open(os.path.join(out, "words.json"), "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=1)
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scene", type=float, default=0.3, help="scene-change threshold, lower = more frames")
    ap.add_argument("--every", type=float, default=1.0, help="max seconds between frames")
    ap.add_argument("--width", type=int, default=540)
    ap.add_argument("--lang", default="kor")
    ap.add_argument("--no-stt", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    shots = frames(a.video, a.out, a.scene, a.every, a.width)
    sh = sheets(shots, a.out)
    words = []
    if not a.no_stt:
        try:
            words = transcript(a.video, a.out, a.lang)
        except SystemExit as e:
            print(f"transcript skipped: {e}", file=sys.stderr)

    lines = [f"# {os.path.basename(a.video)}", ""]
    for i, (t, p) in enumerate(shots):
        end = shots[i + 1][0] if i + 1 < len(shots) else float("inf")
        said = " ".join(w["text"] for w in words if t <= w["start"] < end)
        lines.append(f"- **{t:.1f}s** `{os.path.relpath(p, a.out)}` {said}".rstrip())
    if not words:
        lines += ["", "(no transcript)"]
    with open(os.path.join(a.out, "timeline.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{len(shots)} frames, {len(sh)} sheets, {len(words)} words -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
