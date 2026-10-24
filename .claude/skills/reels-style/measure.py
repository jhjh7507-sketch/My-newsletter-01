#!/usr/bin/env python3
"""Measure a reference reel so its edit can be turned into numeric rules.

  python3 measure.py ref1.mp4 [ref2.mov ...] --out work/style

Per video: duration, size, cut times (scene changes), shot lengths, speech vs
silence, loudness, dominant background colours, and contact sheets with
timestamps (sheet_*.jpg) for reading layout, captions and motion by eye.
Writes work/style/<name>/stats.json and a combined work/style/summary.json.
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys

from PIL import Image

FONT = next((f for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") if os.path.exists(f)), None)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate:format=duration", "-of", "json", path])
    j = json.loads(r.stdout)
    s, f = j["streams"][0], j["format"]
    num, den = s["r_frame_rate"].split("/")
    return float(f["duration"]), s["width"], s["height"], float(num) / float(den)


def cuts(path, thresh):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-vf",
             f"select='gt(scene,{thresh})',showinfo", "-an", "-f", "null", "-"])
    return [round(float(t), 3) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def silences(path):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-af", "silencedetect=n=-35dB:d=0.25",
             "-vn", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def loudness(path):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128", "-vn", "-f", "null", "-"])
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def sheets(path, out, dur, fps):
    every = 0.5 if dur <= 20 else 1.0
    label = (f",drawtext=fontfile={FONT}:text='%{{pts\\:hms}}':x=10:y=10:fontsize=36:"
             f"fontcolor=yellow:box=1:boxcolor=black@0.6") if FONT else ""
    run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf",
         f"fps={1 / every},scale=360:-1{label},tile=5x4:padding=4", os.path.join(out, "sheet_%02d.jpg")])
    return every


def colours(path, out, dur):
    frames = []
    for k in range(6):
        f = os.path.join(out, f"probe_{k}.png")
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur * (k + 0.5) / 6:.2f}", "-i", path,
             "-frames:v", "1", "-vf", "scale=96:-1", f])
        if os.path.exists(f):
            frames.append(f)
    counts = {}
    for f in frames:
        img = Image.open(f).convert("RGB").quantize(colors=6).convert("RGB")
        for n, c in img.getcolors(96 * 200) or []:
            key = "#%02x%02x%02x" % tuple((v // 8) * 8 for v in c)
            counts[key] = counts.get(key, 0) + n
        os.remove(f)
    total = sum(counts.values()) or 1
    return [{"hex": k, "share": round(v / total, 3)}
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:6]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", default="work/style")
    ap.add_argument("--scene", type=float, default=0.32, help="cut detection threshold")
    a = ap.parse_args()

    summary = []
    for v in a.videos:
        name = os.path.splitext(os.path.basename(v))[0][:40]
        out = os.path.join(a.out, name)
        os.makedirs(out, exist_ok=True)
        dur, w, h, fps = probe(v)
        c = cuts(v, a.scene)
        bounds = [0.0] + c + [dur]
        shots = [round(b - a_, 3) for a_, b in zip(bounds, bounds[1:]) if b - a_ > 0.05]
        sil = silences(v)
        silent = sum(e - s for s, e in sil)
        stats = {
            "file": v, "duration": round(dur, 2), "size": [w, h], "fps": round(fps, 2),
            "cuts": c, "cuts_per_10s": round(len(c) / dur * 10, 2) if dur else 0,
            "shot_median": round(statistics.median(shots), 2) if shots else None,
            "shot_min": min(shots) if shots else None,
            "speech_ratio": round(1 - silent / dur, 2) if dur else None,
            "silences": [[round(s, 2), round(e, 2)] for s, e in sil],
            "loudness_lufs": loudness(v), "colours": colours(v, out, dur),
            "sheet_every_s": sheets(v, out, dur, fps),
        }
        json.dump(stats, open(os.path.join(out, "stats.json"), "w"), indent=1)
        summary.append({k: stats[k] for k in ("file", "duration", "size", "cuts_per_10s",
                                               "shot_median", "speech_ratio", "loudness_lufs")})
        print(f"{name}: {dur:.1f}s, {len(c)} cuts, shot median {stats['shot_median']}s, "
              f"speech {stats['speech_ratio']}", file=sys.stderr)
    json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
