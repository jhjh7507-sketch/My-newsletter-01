#!/usr/bin/env python3
"""Build a quiet talk reel: one person talking to the camera, edited to the mood
of what they say rather than with info graphics.

  python3 talk.py plan.json --out work/project
  bash render.sh work/project work/reel.mp4

plan.json:
  {"video": "final.mp4", "words": "words_final.json",
   "stamp": "2026. 10. 31.  00:24",          # real recording time, from the file's creationdate
   "fade_out": 1.2,
   "beats": [{"start": 0, "end": 3.77, "zoom": 1.18,
              "quote": "리스크가 없는데\\n어떻게 리턴이 있습니까?"},
             {"start": 3.77, "zoom": 1.0}, ...]}

Each beat reframes the footage (zoom 1.0 wide, about 1.14 close) and drifts in
slowly, so the cuts between takes read as camera moves. A beat with "quote"
turns the footage black and white and darker and sets the line in serif on the
dark lower half, each line appearing as it is said; captions step aside there.
Elsewhere captions are serif, low, and fade in. No sound effects.
"""
import argparse
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import PUNCT, esc, probe_duration  # noqa: E402

W, H = 1080, 1920
SERIF = "https://cdn.jsdelivr.net/npm/@fontsource/noto-serif-kr@5.2.5/{}.css"
GRAY = "grayscale(1) brightness(0.5) contrast(1.05)"
COLOR = "grayscale(0) brightness(1) contrast(1)"
norm = lambda s: re.sub(r"[^\w]", "", s)


def captions(words, hi):
    """One sentence at a time, so a caption never runs across the end of a sentence
    ("많아요. 뭔가 내가..."). A sentence longer than `hi` words splits where the
    speaker paused longest, not at a fixed count ("생각한 / 대로")."""
    sents, cur = [], []
    for w in words:
        cur.append(w)
        if PUNCT.search(w["text"]):
            sents.append(cur)
            cur = []
    if cur:
        sents.append(cur)
    def split(ws):
        if len(ws) <= hi:
            return [ws]
        k = max(range(1, len(ws)), key=lambda i: ws[i]["start"] - ws[i - 1]["end"]
                - 0.04 * abs(len(ws) - 2 * i))  # a near tie goes to the more even split
        return split(ws[:k]) + split(ws[k:])

    chunks = [c for st in sents for c in split(st)]
    out = []
    for i, c in enumerate(chunks):
        end = c[-1]["end"]
        if i + 1 < len(chunks) and chunks[i + 1][0]["start"] - end < 0.3:
            end = chunks[i + 1][0]["start"]
        out.append({"words": [w["text"] for w in c], "start": c[0]["start"], "end": end})
    return out


def line_times(words, lines, s, e):
    """When each quote line starts being said: its first word inside the beat."""
    out, k = [], 0
    pool = [w for w in words if s - 0.25 <= w["start"] < e]
    for n, line in enumerate(lines):
        first = norm(line.split()[0])
        hit = next((w for w in pool[k:] if first and (first in norm(w["text"]) or norm(w["text"]) in first)), None)
        if hit:
            k = pool.index(hit) + 1
        out.append(max(s, hit["start"]) if hit else s + 0.5 * n)
    out[0] = s  # the first line is up with the cut
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", default="work/project")
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.plan))
    src = lambda k: os.path.join(base, plan[k])
    os.makedirs(os.path.join(a.out, "media"), exist_ok=True)
    shutil.copy(src("video"), os.path.join(a.out, "media", "video.mp4"))
    words = json.load(open(src("words"), encoding="utf-8"))
    D = round(probe_duration(src("video")), 3)
    beats = plan["beats"]
    origin = plan.get("origin", "50% 40%")

    clips, js, quiet = [], [], []
    for i, b in enumerate(beats):
        s = float(b["start"])
        e = float(b.get("end", beats[i + 1]["start"] if i + 1 < len(beats) else D))
        z = float(b.get("zoom", 1.0))
        js.append(f'tl.fromTo("#ft",{{scale:{z}}},{{scale:{z * 1.025:.4f},duration:{e - s:.3f},ease:"none",'
                  f'immediateRender:{"true" if i == 0 else "false"}}},{s:.3f});')
        q = b.get("quote")
        was_q = i and beats[i - 1].get("quote")
        if q and not was_q:  # into black and white; the cold open starts there
            if s < 0.05:
                js.append(f'tl.set("#ft",{{filter:"{GRAY}"}},0);')
            else:
                js.append(f'tl.fromTo("#ft",{{filter:"{COLOR}"}},{{filter:"{GRAY}",duration:.45,'
                          f'immediateRender:false}},{s:.3f});')
        if not q and was_q:
            js.append(f'tl.fromTo("#ft",{{filter:"{GRAY}"}},{{filter:"{COLOR}",duration:.45,'
                      f'immediateRender:false}},{s:.3f});')
        if q:
            quiet.append((s, e))
            lines = q.split("\n")
            ts = line_times(words, lines, s, e)
            spans = "".join(f'<span class="ql" id="q{i}l{n}">{esc(t)}</span>' for n, t in enumerate(lines))
            clips.append(f'<div class="clip qt" id="q{i}" data-start="{s:.3f}" data-duration="{e - s:.3f}" '
                         f'data-track-index="{2 + i % 2}"><div class="qbar"></div>{spans}</div>')
            for n, t in enumerate(ts):
                op0 = 1 if t < 0.05 else 0  # readable from the first frame
                js.append(f'tl.fromTo("#q{i}l{n}",{{opacity:{op0},y:{0 if op0 else 18}}},{{opacity:1,y:0,'
                          f'duration:.5,ease:"power2.out"}},{t:.3f});')
            js.append(f'tl.fromTo("#q{i} .qbar",{{scaleX:{1 if s < 0.05 else 0}}},{{scaleX:1,duration:.5,'
                      f'ease:"power2.out"}},{s:.3f});')
            if e < D - 0.05:
                js.append(f'tl.to("#q{i}",{{opacity:0,duration:.3,ease:"power1.in"}},{e - 0.3:.3f});')

    caps = captions(words, plan.get("max_words", 5))
    for k, c in enumerate(caps):
        mid = (c["start"] + c["end"]) / 2
        if any(a <= mid < b for a, b in quiet):
            continue
        clips.append(f'<div class="clip cap" id="cap{k}" data-start="{c["start"]:.3f}" '
                     f'data-duration="{max(0.08, c["end"] - c["start"]):.3f}" data-track-index="5">'
                     f'<span>{esc(" ".join(c["words"]))}</span></div>')
        js.append(f'tl.fromTo("#cap{k} span",{{opacity:0,y:10}},{{opacity:1,y:0,duration:.25,'
                  f'ease:"power2.out"}},{c["start"]:.3f});')

    if plan.get("stamp"):  # comes in after the cold open
        t0 = next((float(b["start"]) for b in beats if not b.get("quote")), 0)
        clips.append(f'<div class="clip stamp" id="stamp" data-start="{t0:.3f}" data-duration="{D - t0:.3f}" '
                     f'data-track-index="6">{esc(plan["stamp"])}</div>')
        js.append(f'tl.fromTo("#stamp",{{opacity:0}},{{opacity:1,duration:.8}},{t0 + .2:.3f});')
    fo = float(plan.get("fade_out", 0))
    if fo:
        clips.append(f'<div class="clip blk" id="blk" data-start="{D - fo:.3f}" data-duration="{fo:.3f}" '
                     f'data-track-index="7"></div>')
        js.append(f'tl.fromTo("#blk",{{opacity:0}},{{opacity:1,duration:{fo},ease:"power1.in"}},{D - fo:.3f});')
    clips.insert(0, f'<div class="footage"><video id="ft" class="clip" src="media/video.mp4" data-start="0" '
                    f'data-duration="{D}" data-has-audio="true" data-track-index="0"></video></div>'
                    f'<div class="vig"></div>')

    css = f"""*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#000}}
#root{{position:relative;word-break:keep-all;width:{W}px;height:{H}px;font-family:'Noto Serif KR',serif;color:#fff}}
.clip{{position:absolute;inset:0}}
.footage{{position:absolute;inset:0;overflow:hidden;z-index:1}}
.footage #ft{{width:100%;height:100%;object-fit:cover;transform-origin:{origin}}}
.vig{{position:absolute;inset:0;z-index:2;pointer-events:none;background:radial-gradient(ellipse 80% 70% at 50% 40%,rgba(0,0,0,0) 55%,rgba(0,0,0,.5) 100%)}}
.qt{{z-index:4;top:1420px;bottom:auto;display:flex;flex-direction:column;align-items:center;gap:18px;padding:0 70px;text-align:center}}
.qbar{{width:56px;height:3px;background:rgba(255,255,255,.75);margin-bottom:22px;transform-origin:50% 50%}}
.ql{{display:block;text-wrap:balance;font-size:70px;font-weight:600;line-height:1.32;letter-spacing:-.02em;text-shadow:0 4px 24px rgba(0,0,0,.6)}}
.cap{{z-index:5;top:1500px;bottom:auto;height:auto;display:flex;justify-content:center;padding:0 80px}}
.cap span{{font-size:52px;font-weight:600;line-height:1.4;text-align:center;text-wrap:balance;letter-spacing:-.01em;text-shadow:0 2px 6px rgba(0,0,0,.7),0 4px 22px rgba(0,0,0,.6)}}
.stamp{{z-index:6;top:230px;left:64px;right:auto;bottom:auto;font-family:Pretendard,sans-serif;font-size:28px;font-weight:600;letter-spacing:.14em;color:rgba(255,255,255,.78);text-shadow:0 2px 8px rgba(0,0,0,.6)}}
.blk{{z-index:9;background:#000}}
"""
    doc = f"""<!doctype html>
<html lang="ko" data-resolution="portrait">
<head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
<link rel="stylesheet" href="{SERIF.format(600)}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>{css}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{D}" data-width="{W}" data-height="{H}">
{chr(10).join(clips)}
</div>
<script>window.__timelines=window.__timelines||{{}};const tl=gsap.timeline({{paused:true}});
{chr(10).join(js)}
window.__timelines["main"]=tl;</script></body></html>
"""
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(doc)
    json.dump({"paths": {"assets": "media"}}, open(os.path.join(a.out, "hyperframes.json"), "w"))
    json.dump({"id": "reel", "name": "reel"}, open(os.path.join(a.out, "meta.json"), "w"))
    print(f"{a.out}: talk, {D:.1f}s, {len(beats)} beats, {len(quiet)} quotes", file=sys.stderr)


if __name__ == "__main__":
    main()
