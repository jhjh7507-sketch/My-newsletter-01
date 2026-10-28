#!/usr/bin/env python3
"""Turn a plan + style rules + media into a HyperFrames project ready to render.

  python3 build.py plan.json --style .claude/instagram/style.yaml --out work/project

plan.json is described in ../SKILL.md. The project is rendered with render.sh.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pro  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PUNCT = re.compile(r"[.,!?…~]$")

DEFAULT_STYLE = {
    "canvas": {"w": 1080, "h": 1920, "fps": 30},
    "font": "Pretendard",
    "colors": {"bg": "#efe7e4", "panel": "#ffffff", "ink": "#1d1d1f", "muted": "#8a8a8e",
               "accent": "#d65745", "caption_bg": "#2b2b2d", "caption_ink": "#ffffff",
               "caption_accent": "#ffc93c"},
    "layout": {"split_y": 860},
    "caption": {"y_split": 864, "y_full": 1420, "size": 62, "weight": 800,
                "min_words": 1, "max_words": 3, "box": True},
    "motion": {"card_rise_px": 52, "ease": "expo.out", "in_dur": 0.5, "stagger": 0.12,
               "face_push_frames": 37, "face_push_scale": 1.06},
    "sfx": {"scene": "whoosh", "item": "pop", "volume": 0.35},
}


def merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def probe_size(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:stream_side_data=rotation", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    v = json.loads(r.stdout)["streams"][0]
    rot = abs(int(float(next((d.get("rotation", 0) for d in v.get("side_data_list", [])), 0))))
    return (v["height"], v["width"]) if rot in (90, 270) else (v["width"], v["height"])


def chunk_captions(words, lo, hi):
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= hi or (len(cur) >= lo and PUNCT.search(w["text"])):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        end = c[-1]["end"]
        if i + 1 < len(chunks) and chunks[i + 1][0]["start"] - end < 0.3:
            end = chunks[i + 1][0]["start"]
        out.append({"words": [w["text"] for w in c], "start": c[0]["start"], "end": end})
    return out


def find_anchor(words, anchor):
    target = re.sub(r"\s+", "", anchor)
    flat = [re.sub(r"\s+", "", w["text"]) for w in words]
    for i in range(len(words)):
        acc = ""
        for j in range(i, len(words)):
            acc += flat[j]
            if acc.startswith(target) or target.startswith(acc) and len(acc) >= len(target):
                return words[i]["start"]
            if not target.startswith(acc):
                break
    sys.exit(f"scene anchor not found in transcript: {anchor!r}")


def esc(s):
    return html.escape(str(s))


def mark(text, terms):
    t = esc(text)
    for term in sorted(terms, key=len, reverse=True):
        if term:
            t = t.replace(esc(term), f"<b>{esc(term)}</b>")
    return t


def scene_html(i, sc, emph):
    kind = sc.get("type", "title" if "title" in sc else "none")
    kicker = f'<div class="kicker">{esc(sc["kicker"])}</div>' if sc.get("kicker") else ""
    terms = emph + ([sc["highlight"]] if sc.get("highlight") else [])
    if kind == "none":
        return ""
    if kind == "hook":
        return f'<div class="card hook"><div class="hooktxt rise">{mark(sc["text"], terms)}</div></div>'
    if kind == "title":
        sub = f'<p class="sub rise">{mark(sc["sub"], terms)}</p>' if sc.get("sub") else ""
        body = f'<h1 class="big rise">{mark(sc["title"], terms)}</h1>{sub}'
    elif kind in ("list", "steps"):
        items = []
        for n, it in enumerate(sc.get("items", []), 1):
            lead = f"STEP {n}" if kind == "steps" else "✓"
            on = " on" if kind == "list" or n == sc.get("active", n) else ""
            items.append(f'<li class="item rise{on}"><span class="lead">{lead}</span>'
                         f'<span>{mark(it, terms)}</span></li>')
        head = f'<h2 class="head rise">{mark(sc["title"], terms)}</h2>' if sc.get("title") else ""
        body = f'{head}<ul class="items">{"".join(items)}</ul>'
    elif kind == "stat":
        body = (f'<div class="label rise">{mark(sc.get("label", ""), terms)}</div>'
                f'<div class="stat rise"><span class="num" data-to="{esc(sc["value"])}">0</span>'
                f'<span class="unit">{esc(sc.get("unit", ""))}</span></div>')
    elif kind == "quote":
        body = f'<blockquote class="quote rise">{mark(sc["text"], terms)}</blockquote>'
    else:
        sys.exit(f"unknown scene type: {kind}")
    return f'<div class="card" id="card{i}">{kicker}{body}</div>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--style")
    ap.add_argument("--out", default="work/project")
    a = ap.parse_args()

    plan = json.load(open(a.plan, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.plan))
    st = merge(DEFAULT_STYLE, yaml.safe_load(open(a.style, encoding="utf-8")) if a.style else {})
    mode = plan.get("mode", "faceless")
    C, M, CAP, L = st["colors"], st["motion"], st["caption"], st["layout"]
    W, H, FPS = st["canvas"]["w"], st["canvas"]["h"], st["canvas"]["fps"]

    def src(key):
        p = plan.get(key)
        return os.path.join(base, p) if p and not os.path.isabs(p) else p

    os.makedirs(os.path.join(a.out, "media"), exist_ok=True)
    words = json.load(open(src("words"), encoding="utf-8"))
    media = {}
    for key in ("voice", "video", "image"):
        if plan.get(key):
            name = key + os.path.splitext(plan[key])[1]
            shutil.copy(src(key), os.path.join(a.out, "media", name))
            media[key] = "media/" + name
    audio_src = media.get("voice") or media.get("video")
    if not audio_src:
        sys.exit("plan needs voice (narration) or video (recorded footage with sound)")
    D = round(probe_duration(os.path.join(a.out, audio_src)) + 0.4, 3)
    subprocess.run([sys.executable, os.path.join(HERE, "sfx.py"), os.path.join(a.out, "media")],
                   check=True)

    scenes = plan.get("scenes", [])
    for i, sc in enumerate(scenes):
        if sc.get("type") == "clip":  # screen recordings (anatomy app) shown inside a graphic scene
            p = sc["src"] if os.path.isabs(sc["src"]) else os.path.join(base, sc["src"])
            name = f"clip{i}{os.path.splitext(p)[1]}"
            shutil.copy(p, os.path.join(a.out, "media", name))
            sc["_media"], sc["_size"] = "media/" + name, probe_size(p)
    starts = []
    for sc in scenes:
        starts.append(float(sc["start"]) if "start" in sc else find_anchor(words, sc["at"]))
    emph = plan.get("emphasis", [])
    # "full" puts footage on the whole canvas with captions and an optional hook
    # line on top: for skits and reactions, where a card would hide the joke.
    full = plan.get("layout") == "full" and mode in ("face", "character")
    # "mixed" switches per scene between "face" (footage fills the frame), "split"
    # (graphic on top, footage below) and "full" (graphic fills the frame), with the
    # caption fixed on the seam. Built from the reference reels of 2026-10-28.
    mixed = plan.get("layout") == "mixed" and mode in ("face", "character")
    split = mode in ("face", "character") and not full and not mixed
    cap_y = CAP.get("y_mixed", L["split_y"]) if mixed else (CAP["y_split"] if split else CAP["y_full"])
    sy = L["split_y"]
    caps = chunk_captions(words, CAP["min_words"], CAP["max_words"])

    clips, js = [], []
    vol = st["sfx"]["volume"]
    push = M["face_push_frames"] / FPS
    # mixed: layout changes move, they never cut. The footage slides between the
    # whole frame and the lower half while the graphic panel slides with it from
    # the top; full-frame graphics wipe down over the face and back up.
    T, LE = M.get("layout_dur", 0.45), M.get("layout_ease", "power2.inOut")
    lays = [sc.get("layout", "split") for sc in scenes] if mixed else []
    FT = {"face": (0, H), "split": (sy, H - sy)}
    inset = lambda b: f'"inset(0% 0% {b}% 0%)"'
    fstate = None
    for i, sc in enumerate(scenes):
        s = starts[i]
        e = starts[i + 1] if i + 1 < len(scenes) else D
        lay = lays[i] if mixed else None
        dur, attrs, tj = e - s, 'data-track-index="1"', []
        if mixed:
            prev = lays[i - 1] if i else None
            nxt = lays[i + 1] if i + 1 < len(lays) else None
            # under a full-frame graphic the footage moves unseen to where the next scene wants it
            want = lay if lay != "full" else next((x for x in lays[i + 1:] if x != "full"), fstate)
            if want and want != fstate:
                (a0, b0), (a1, b1) = FT[fstate or want], FT[want]
                if fstate is None or lay == "full":
                    t0 = s if fstate is None else min(s + T, e)
                    js.append(f'tl.set("#ftw",{{top:{a1},height:{b1}}},{t0:.3f});tl.set("#ft",{{scale:1}},{t0:.3f});')
                else:
                    js.append(f'tl.fromTo("#ftw",{{top:{a0},height:{b0}}},{{top:{a1},height:{b1},duration:{T},'
                              f'ease:"{LE}",immediateRender:false}},{s:.3f});')
                fstate = want
            if lay == "face":
                js.append(f'tl.fromTo("#ft",{{scale:1}},{{scale:{M["face_push_scale"]},'
                          f'duration:{T if prev == "split" else push:.3f},ease:"power2.out",immediateRender:false}},{s:.3f});')
            elif lay == "split" and prev == "face":
                js.append(f'tl.fromTo("#ft",{{scale:{M["face_push_scale"]}}},{{scale:1,duration:{T},ease:"{LE}",'
                          f'immediateRender:false}},{s:.3f});')
            elif lay == "split":
                js.append(f'tl.set("#ft",{{scale:1}},{s:.3f});')
            if st["sfx"].get("scene") and i > 0:
                clips.append(f'<audio src="media/{st["sfx"]["scene"]}.wav" data-start="{s:.3f}" '
                             f'data-duration="0.45" data-volume="{vol}" data-track-index="5"></audio>')
            # graphic panel: stays T past its end so the next change can move it out;
            # neighbours alternate tracks and the later one stacks on top
            dur = (min(e + T, D) if nxt else e) - s
            attrs = f'data-track-index="{1 + i % 2}"'
            el, IR = f'"#sc{i}"', "immediateRender:false"
            if i and lay == "split" and prev == "face":
                tj.append(f'tl.fromTo({el},{{yPercent:-100}},{{yPercent:0,duration:{T},ease:"{LE}",{IR}}},{s:.3f});')
            elif i and lay == "full" and prev in ("face", "split"):
                tj.append(f'tl.fromTo({el},{{clipPath:{inset(100 if prev == "face" else 50)}}},'
                          f'{{clipPath:{inset(0)},duration:{T},ease:"{LE}",{IR}}},{s:.3f});')
            if i and prev in ("split", "full"):
                tj.append(f'tl.fromTo({el},{{opacity:0}},{{opacity:1,duration:.3,ease:"power1.out",{IR}}},{s:.3f});')
            if nxt == "face" and lay == "split":
                tj.append(f'tl.fromTo({el},{{yPercent:0}},{{yPercent:-100,duration:{T},ease:"{LE}",{IR}}},{e:.3f});')
            elif lay == "full" and nxt in ("face", "split"):
                tj.append(f'tl.fromTo({el},{{clipPath:{inset(0)}}},{{clipPath:{inset(100 if nxt == "face" else 50)},'
                          f'duration:{T},ease:"{LE}",{IR}}},{e:.3f});')
        if sc.get("type") in pro.BUILDERS:
            sc["_box"], sc["_dur"], sc["_track"] = (W, H if lay == "full" else sy), dur, 8 + i % 2
            inner, pjs, pops = pro.BUILDERS[sc["type"]](i, sc, s, C)
            glow = pro.tone(C, sc.get("glow", "red"))
            bg = f'background:radial-gradient(110% 70% at 50% 38%,{glow}2e 0%,transparent 60%),{C["bg"]}'
            z = f"z-index:{10 + i};" if mixed else ""
            clips.append(f'<div class="clip scene lay-{lay or "split"}" id="sc{i}" style="{z}{bg}" data-start="{s:.3f}" '
                         f'data-duration="{dur:.3f}" {attrs}>{inner}</div>')
            js += tj + pjs
            for t in pops:
                clips.append(f'<audio src="media/{st["sfx"]["item"]}.wav" data-start="{t:.3f}" '
                             f'data-duration="0.09" data-volume="{vol}" data-track-index="6"></audio>')
            continue
        inner = scene_html(i, sc, emph)
        if not inner:
            continue
        cls = f" lay-{lay}" if mixed else ""
        z = f' style="z-index:{10 + i}"' if mixed else ""
        clips.append(f'<div class="clip scene{cls}" id="sc{i}"{z} data-start="{s:.3f}" '
                     f'data-duration="{dur:.3f}" {attrs}>{inner}</div>')
        js += tj
        if sc.get("type") == "hook":
            # readable from the first frame: a small settle, never a fade from nothing
            js.append(f'tl.fromTo("#sc{i} .hooktxt",{{scale:1.08}},'
                      f'{{scale:1,duration:0.3,ease:"power2.out"}},{s:.3f});')
        else:
            op0 = 1 if s < 0.05 else 0  # the opening card is on screen from frame one
            js.append(f'tl.fromTo("#sc{i} .card",{{opacity:{op0},y:{M["card_rise_px"]}}},'
                      f'{{opacity:1,y:0,duration:{M["in_dur"]},ease:"{M["ease"]}"}},{s:.3f});')
            js.append(f'tl.fromTo("#sc{i} .rise",{{opacity:{op0},y:{M["card_rise_px"]}}},'
                      f'{{opacity:1,y:0,duration:{M["in_dur"]},ease:"{M["ease"]}",'
                      f'stagger:{M["stagger"]}}},{s + 0.08:.3f});')
        if sc.get("type") == "stat":
            js.append(f'(()=>{{const el=document.querySelector("#sc{i} .num");'
                      f'const to=parseFloat(el.dataset.to);const dec=(el.dataset.to.split(".")[1]||"").length;'
                      f'const o={{v:0}};tl.to(o,{{v:to,duration:0.9,ease:"power2.out",'
                      f'onUpdate:()=>{{el.textContent=o.v.toFixed(dec)}}}},{s + 0.1:.3f});}})();')
        if st["sfx"].get("scene") and i > 0 and not mixed:
            clips.append(f'<audio src="media/{st["sfx"]["scene"]}.wav" data-start="{s:.3f}" '
                         f'data-duration="0.45" data-volume="{vol}" data-track-index="5"></audio>')
        n_items = len(sc.get("items", [])) if sc.get("type") in ("list", "steps") else 0
        for k in range(n_items):
            t = s + 0.08 + (k + (1 if sc.get("title") else 0)) * M["stagger"]
            clips.append(f'<audio src="media/{st["sfx"]["item"]}.wav" data-start="{t:.3f}" '
                         f'data-duration="0.09" data-volume="{vol}" data-track-index="6"></audio>')

    if (split or full or mixed) and media.get("video"):
        has_audio = 'data-has-audio="true"' if not media.get("voice") else "muted"
        clips.append(f'<div class="footage" id="ftw"><video id="ft" class="clip" src="{media["video"]}" '
                     f'data-start="0" data-duration="{D}" {has_audio} data-track-index="0"></video></div>')
    elif (split or full) and media.get("image"):
        clips.append(f'<div class="footage"><img id="ft" class="clip" src="{media["image"]}" '
                     f'data-start="0" data-duration="{D}" data-track-index="0" /></div>')
    if (split or full) and (media.get("video") or media.get("image")):
        for s in [0.0] + starts[1:]:
            js.append(f'tl.fromTo("#ft",{{scale:1}},{{scale:{M["face_push_scale"]},'
                      f'duration:{push:.3f},ease:"power2.out"}},{s:.3f});')
    if media.get("voice"):
        clips.append(f'<audio src="{media["voice"]}" data-start="0" data-duration="{D}" '
                     f'data-track-index="4"></audio>')

    span = lambda i: (starts[i], starts[i + 1] if i + 1 < len(scenes) else D)
    hot = [span(i) for i, sc in enumerate(scenes) if sc.get("hot")]
    # a full-frame graphic sits on the centre line, so its captions drop below it
    low = [span(i) for i, sc in enumerate(scenes) if mixed and sc.get("layout") == "full"]
    for k, c in enumerate(caps):
        toks = {t for term in emph for t in term.split()}
        mid = (c["start"] + c["end"]) / 2  # the scene a caption mostly sits in decides its look
        hc = (" hot" if any(a <= mid < b for a, b in hot) else "") + \
             (" low" if any(a <= mid < b for a, b in low) else "")
        txt = " ".join(f"<b>{esc(w)}</b>" if re.sub(r"[^\w]", "", w) in toks or any(
            t and t in w for t in toks if len(t) > 1) else esc(w) for w in c["words"])
        clips.append(f'<div class="clip cap{hc}" id="cap{k}" data-start="{c["start"]:.3f}" '
                     f'data-duration="{max(0.08, c["end"] - c["start"]):.3f}" data-track-index="3">'
                     f'<span>{txt}</span></div>')
        js.append(f'tl.fromTo("#cap{k} span",{{scale:0.92,opacity:0}},{{scale:1,opacity:1,'
                  f'duration:0.12,ease:"back.out(2)"}},{c["start"]:.3f});')

    top = L["split_y"] if split else H
    ftop = 0 if (full or mixed) else top
    fy = plan.get("focus_y")
    ft_pos = f"50% {float(fy) * 100:.0f}%" if fy is not None else "50% 50%"
    ft_origin = f"50% {float(fy) * 100:.0f}%" if fy is not None else "50% 40%"
    css = f"""*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{C['bg']}}}
#root{{position:relative;word-break:keep-all;width:{W}px;height:{H}px;font-family:{st['font']},'Pretendard',sans-serif;color:{C['ink']}}}
.clip{{position:absolute;inset:0}}
.scene{{height:{top}px;display:flex;align-items:center;justify-content:center;padding:0 64px;z-index:2}}
.card{{width:100%;background:{C['panel']};border-radius:40px;padding:64px 60px;box-shadow:0 24px 60px rgba(0,0,0,.10)}}
.kicker{{display:inline-block;font-size:30px;font-weight:800;letter-spacing:.12em;color:{C['accent']};border:3px solid {C['accent']};border-radius:999px;padding:8px 26px;margin-bottom:28px}}
.big{{font-size:96px;line-height:1.18;font-weight:900;letter-spacing:-.03em}}
.big b,.head b,.item b,.quote b,.label b,.sub b{{color:{C['accent']}}}
.sub{{margin-top:28px;font-size:44px;font-weight:600;color:{C['muted']};line-height:1.4}}
.head{{font-size:64px;font-weight:900;letter-spacing:-.02em;margin-bottom:32px}}
.items{{list-style:none;display:flex;flex-direction:column;gap:22px}}
.item{{display:flex;gap:26px;align-items:center;font-size:50px;font-weight:800;background:{C['bg']};border-radius:24px;padding:26px 30px;opacity:.45}}
.item.on{{opacity:1}}
.lead{{flex:none;font-size:30px;font-weight:900;color:#fff;background:{C['accent']};border-radius:14px;padding:8px 16px}}
.label{{font-size:46px;font-weight:700;color:{C['muted']}}}
.stat{{margin-top:12px;font-weight:900;letter-spacing:-.04em}}
.num{{font-size:220px;color:{C['accent']}}}.unit{{font-size:90px;margin-left:10px}}
.quote{{font-size:70px;font-weight:900;line-height:1.3}}
.footage{{position:absolute;left:0;top:{ftop}px;width:{W}px;height:{H - ftop}px;overflow:hidden;z-index:1}}
.card.hook{{position:absolute;top:260px;left:64px;right:64px;width:auto;background:none;box-shadow:none;padding:0;text-align:center}}
.hooktxt{{white-space:pre-line;font-size:84px;line-height:1.22;font-weight:900;letter-spacing:-.03em;color:#fff;-webkit-text-stroke:3px rgba(0,0,0,.55);paint-order:stroke fill;text-shadow:0 6px 24px rgba(0,0,0,.55)}}
.hooktxt b{{color:{C['caption_accent']}}}
.footage #ft{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:{ft_pos};transform-origin:{ft_origin}}}
.cap{{z-index:100;top:{cap_y}px;bottom:auto;height:auto;display:flex;justify-content:center;transform:translateY(-50%)}}
.cap span{{display:inline-block;font-size:{CAP['size']}px;font-weight:{CAP['weight']};color:{C['caption_ink']};{"background:" + C['caption_bg'] + ";padding:10px 24px;border-radius:12px;" if CAP['box'] else "text-shadow:0 4px 14px rgba(0,0,0,.6);"}letter-spacing:-.02em}}
.cap b,.cap.hot span{{color:{C['caption_accent']}}}
.lay-split{{height:{sy}px!important;padding:0 60px}}.lay-full{{height:{H}px!important;padding:0 60px}}
.lay-face{{height:{sy}px!important}}
.cap.low{{top:{CAP.get("y_low", 1560)}px}}
""" + (pro.css(C) if mixed else "") + (
        ".cap span{background:none!important;padding:0!important;-webkit-text-stroke:9px rgba(0,0,0,.9);"
        "paint-order:stroke fill;text-shadow:0 6px 20px rgba(0,0,0,.45)}" if CAP.get("stroke") else "")

    doc = f"""<!doctype html>
<html lang="ko" data-resolution="portrait">
<head><meta charset="UTF-8" /><meta name="viewport" content="width={W}, height={H}" />
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
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
    srt = []
    for k, c in enumerate(caps, 1):
        f = lambda t: f"{int(t // 3600):02}:{int(t % 3600 // 60):02}:{int(t % 60):02},{int(t % 1 * 1000):03}"
        srt.append(f"{k}\n{f(c['start'])} --> {f(c['end'])}\n{' '.join(c['words'])}\n")
    open(os.path.join(a.out, "captions.srt"), "w", encoding="utf-8").write("\n".join(srt))
    print(f"{a.out}: {mode}, {D:.1f}s, {len(scenes)} scenes, {len(caps)} captions", file=sys.stderr)


if __name__ == "__main__":
    main()
