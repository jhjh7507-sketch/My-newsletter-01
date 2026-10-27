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
import os
import subprocess
import sys


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

    starts, t = [], 0.0
    for s, e in segs:
        starts.append(t)
        t += e - s
    remapped = []
    for w in kept:
        for (s, e), off in zip(segs, starts):
            if s <= w["start"] < e:
                remapped.append({"text": w["text"], "start": round(off + w["start"] - s, 3),
                                 "end": round(off + min(w["end"], e) - s, 3)})
                break

    parts, labels = [], []
    for k, (s, e) in enumerate(segs):
        parts.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{k}];"
                     f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS[a{k}]")
        labels.append(f"[v{k}][a{k}]")
    graph = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(segs)}:v=1:a=1[v][a]"
    os.makedirs(a.out, exist_ok=True)
    gf = os.path.join(a.out, "cut.filter")
    open(gf, "w").write(graph)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-filter_complex_script", gf,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "18", "-c:a", "aac", "-b:a", "192k", os.path.join(a.out, "cut.mp4")],
                   check=True)
    os.remove(gf)
    with open(os.path.join(a.out, "words_cut.json"), "w", encoding="utf-8") as f:
        json.dump(remapped, f, ensure_ascii=False, indent=1)
    src = words[-1]["end"]
    print(f"cut.mp4: {src:.1f}s -> {t:.1f}s, {len(segs)} segments, {len(drop)} words dropped",
          file=sys.stderr)


if __name__ == "__main__":
    main()
