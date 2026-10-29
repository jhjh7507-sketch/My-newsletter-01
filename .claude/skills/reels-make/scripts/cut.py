#!/usr/bin/env python3
"""Cut dead air and dropped takes out of a recorded video.

  python3 cut.py raw.mov work/words.json --out work/ [--drop 12-30,55-61] [--keep 31.5-34] [--pad 0.12]

Keeps only spoken words, closes every gap longer than --max-gap, and leaves
--pad seconds of breath around each kept run. --drop removes word index
ranges (inclusive), which is how bad takes and retakes are removed. --keep
adds source time ranges in seconds that stay even without speech: a silent
exercise demo, a held stretch, a reaction. Find them with /watch frames.
Writes work/cut.mp4 and work/words_cut.json with times remapped.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def probe_fps(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=avg_frame_rate,r_frame_rate", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    for rate in r.stdout.strip().split(","):
        num, _, den = rate.partition("/")
        if float(num or 0) > 0 and float(den or 1) > 0:
            return float(num) / float(den or 1)
    sys.exit(f"cannot read the frame rate of {path}")


# iPhone HDR (HLG) or HDR10 footage: tone-map to SDR BT.709. Left as HDR, the colours
# come out washed out and HyperFrames switches to a slow HDR render (about 1 s a frame).
TONEMAP = ("zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")


def is_hdr(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=color_transfer", "-of", "csv=p=0", path], capture_output=True, text=True)
    return r.stdout.strip() in ("arib-std-b67", "smpte2084")


def parse_drop(s):
    out = set()
    for part in filter(None, (s or "").split(",")):
        lo, _, hi = part.partition("-")
        out.update(range(int(lo), int(hi or lo) + 1))
    return out


def parse_keep(s):
    out = []
    for part in filter(None, (s or "").split(",")):
        lo, _, hi = part.partition("-")
        if float(hi) <= float(lo):
            sys.exit(f"--keep range {part} ends before it starts")
        out.append((float(lo), float(hi)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("words")
    ap.add_argument("--out", default="work")
    ap.add_argument("--drop", default="")
    ap.add_argument("--keep", default="")
    ap.add_argument("--pad", type=float, default=0.12)
    ap.add_argument("--max-gap", type=float, default=0.35)
    a = ap.parse_args()

    words = json.load(open(a.words, encoding="utf-8"))
    drop = parse_drop(a.drop)
    kept = [dict(w, i=i) for i, w in enumerate(words) if i not in drop]
    if not kept:
        sys.exit("nothing left to keep")

    runs = []
    for w in kept:
        if runs and w["i"] == runs[-1]["last"] + 1 and w["start"] - runs[-1]["end"] <= a.max_gap:
            runs[-1]["end"], runs[-1]["last"] = w["end"], w["i"]
            runs[-1]["words"].append(w)
        else:
            runs.append({"start": w["start"], "end": w["end"], "last": w["i"], "words": [w]})

    spans = sorted([(max(0.0, r["start"] - a.pad), r["end"] + a.pad) for r in runs]
                   + parse_keep(a.keep))
    segs = []
    for s, e in spans:
        if segs and s <= segs[-1][1]:
            segs[-1] = (segs[-1][0], max(segs[-1][1], e))
        else:
            segs.append((s, e))

    # Snap every segment to the video frame grid so each one carries exactly as much
    # sound as picture. Otherwise every join leaves a few ms of picture without
    # sound, and over dozens of segments the voice runs ahead of the lips.
    fps = probe_fps(a.video)
    hdr = is_hdr(a.video)
    if hdr:
        print("HDR footage: tone-mapping to SDR (turn off HDR video in the iPhone camera settings to skip this)",
              file=sys.stderr)
    snapped = []
    for s, e in segs:
        s, e = math.floor(s * fps + 1e-6) / fps, math.ceil(e * fps - 1e-6) / fps
        if snapped and s <= snapped[-1][1]:
            snapped[-1] = (snapped[-1][0], max(snapped[-1][1], e))
        else:
            snapped.append((s, e))
    segs = snapped

    # One ffmpeg run per segment, then a stream-copy concat. A single trim/concat
    # filter graph buffers every decoded frame and is killed for lack of memory on
    # phone footage longer than half a minute.
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="cut_", dir=a.out)
    parts, durs = [], []
    for k, (s, e) in enumerate(segs):
        n = round((e - s) * fps)
        d = n / fps
        p = os.path.join(tmp, f"{k:04d}.mkv")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s:.6f}", "-i", a.video,
                        "-map", "0:v:0", "-map", "0:a:0", "-t", f"{d:.6f}",
                        "-vf", (TONEMAP if hdr else "") + f"fps={fps}", "-frames:v", str(n),
                        "-af", f"apad=whole_dur={d:.6f},atrim=0:{d:.6f}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-g", str(round(fps)), "-keyint_min", str(round(fps)),  # renderer seeks; sparse keyframes freeze
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-c:a", "pcm_s16le", p], check=True)
        parts.append(p)
        durs.append(d)
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.basename(p)}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                    os.path.join(a.out, "cut.mp4")], check=True)
    shutil.rmtree(tmp)

    starts, t = [], 0.0
    for d in durs:
        starts.append(t)
        t += d
    remapped = []
    for w in kept:
        for (s, e), off, d in zip(segs, starts, durs):
            if s <= w["start"] < e:
                remapped.append({"text": w["text"], "start": round(off + w["start"] - s, 3),
                                 "end": round(off + min(w["end"] - s, d), 3)})
                break

    with open(os.path.join(a.out, "words_cut.json"), "w", encoding="utf-8") as f:
        json.dump(remapped, f, ensure_ascii=False, indent=1)
    # which source seconds were kept, for graphics that show the cut itself (a waveform losing its pauses)
    with open(os.path.join(a.out, "segments.json"), "w") as f:
        json.dump({"source": round(probe_duration(a.video), 3),
                   "kept": [[round(s, 3), round(e, 3)] for s, e in segs]}, f)
    src = words[-1]["end"]
    print(f"cut.mp4: {src:.1f}s -> {t:.1f}s, {len(segs)} segments, {len(drop)} words dropped",
          file=sys.stderr)


if __name__ == "__main__":
    main()
