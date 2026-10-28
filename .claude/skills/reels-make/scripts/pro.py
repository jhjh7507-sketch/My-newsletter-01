"""Graphic scenes for the "mixed" info layout: keyword, compare, chain, counter, clip, pelvis.

Each builder takes (i, sc, s, C) - scene index, scene dict, start second and the
style colours - and returns (html, js, pops): the scene's inner HTML, GSAP lines
on the shared `tl` timeline, and the seconds where a pop sound belongs.

They draw things, not sentences. The caption already carries the words; a scene
shows the idea those words are about: a highlighted keyword, a two-sided
comparison, a sequence lighting up, a diagram.
"""
import html
import math

TONE = {"red": "accent", "blue": "accent2"}


def esc(s):
    return html.escape(str(s))


def tone(C, name):
    return C.get(TONE.get(name, "accent"), C["accent"])


def keyword(i, sc, s, C):
    sub = f'<div class="pk-sub">{esc(sc["sub"])}</div>' if sc.get("sub") else ""
    kick = f'<div class="pk-kick">{esc(sc["kicker"])}</div>' if sc.get("kicker") else ""
    body = (f'<div class="pk">{kick}<div class="pk-word"><span class="pk-bar" '
            f'style="background:{tone(C, sc.get("tone", "red"))}"></span>'
            f'<span class="pk-txt">{esc(sc["text"])}</span></div>{sub}</div>')
    js = [f'tl.fromTo("#sc{i} .pk-kick",{{opacity:0,y:16}},{{opacity:1,y:0,duration:.3}},{s:.3f});',
          f'tl.fromTo("#sc{i} .pk-txt",{{opacity:0,y:36}},{{opacity:1,y:0,duration:.4,ease:"expo.out"}},{s:.3f});',
          f'tl.fromTo("#sc{i} .pk-bar",{{scaleX:0}},{{scaleX:1,duration:.45,ease:"power3.inOut"}},{s + .3:.3f});',
          f'tl.fromTo("#sc{i} .pk-sub",{{opacity:0,y:16}},{{opacity:1,y:0,duration:.3}},{s + .55:.3f});']
    return body, js, [s + .3]


def compare(i, sc, s, C):
    boxes, js, pops = [], [], []
    for k, side in enumerate((sc["left"], sc["right"])):
        col = tone(C, side.get("tone", "red" if k else "blue"))
        arrow = {"down": "↓", "up": "↑"}.get(side.get("dir", ""), "")
        boxes.append(f'<div class="pc-box" id="sc{i}b{k}" style="border-color:{col};'
                     f'box-shadow:0 0 60px {col}33 inset">'
                     f'<div class="pc-t">{esc(side["title"])}</div>'
                     f'<div class="pc-s" style="color:{col}">{esc(side["state"])} {arrow}</div>'
                     f'<div class="pc-meter"><i id="sc{i}m{k}" style="background:{col}"></i></div></div>')
        t = s + .15 + k * .5
        lo, hi = side.get("meter", (0.7, 0.15) if side.get("dir") == "down" else (0.3, 0.95))
        js += [f'tl.fromTo("#sc{i}b{k}",{{opacity:0,y:40}},{{opacity:1,y:0,duration:.4,ease:"expo.out"}},{t:.3f});',
               f'tl.fromTo("#sc{i}m{k}",{{width:"{lo * 100:.0f}%"}},{{width:"{hi * 100:.0f}%",duration:.9,'
               f'ease:"power2.inOut"}},{t + .35:.3f});']
        pops.append(t)
    mid = esc(sc.get("mid", "→"))
    head = f'<div class="pc-head">{esc(sc["title"])}</div>' if sc.get("title") else ""
    body = (f'<div class="pc">{head}<div class="pc-row">{boxes[0]}'
            f'<div class="pc-mid">{mid}</div>{boxes[1]}</div></div>')
    js.append(f'tl.fromTo("#sc{i} .pc-head",{{opacity:0}},{{opacity:1,duration:.3}},{s:.3f});')
    return body, js, pops


def chain(i, sc, s, C):
    col = tone(C, sc.get("tone", "red"))
    parts, js, pops = [], [], []
    items = sc["items"]
    for k, it in enumerate(items):
        if k:
            parts.append(f'<div class="ch-line"><i id="sc{i}l{k}" style="background:{col}"></i></div>')
        parts.append(f'<div class="ch-node" id="sc{i}n{k}"><div class="ch-dot" id="sc{i}d{k}"></div>'
                     f'<div class="ch-lbl">{esc(it["text"])}</div></div>')
        t = float(it.get("t", s + .3 + k * .6))
        if k:
            js.append(f'tl.fromTo("#sc{i}l{k}",{{scaleX:0}},{{scaleX:1,duration:.25,ease:"power2.out"}},{t - .25:.3f});')
        js += [f'tl.to("#sc{i}n{k}",{{opacity:1,duration:.15}},{t:.3f});',
               f'tl.fromTo("#sc{i}d{k}",{{scale:.6}},{{scale:1,background:"{col}",boxShadow:"0 0 40px {col}",'
               f'duration:.35,ease:"back.out(3)"}},{t:.3f});']
        pops.append(t)
    head = f'<div class="ch-head">{esc(sc["title"])}</div>' if sc.get("title") else ""
    js.append(f'tl.fromTo("#sc{i} .ch-head",{{opacity:0,y:16}},{{opacity:1,y:0,duration:.3}},{s:.3f});')
    return f'<div class="ch">{head}<div class="ch-row">{"".join(parts)}</div></div>', js, pops


def counter(i, sc, s, C):
    """A number that drops (or climbs) from `from` to `to` at second `t`, with a bar.

    The renderer seeks with events suppressed, so the digits are pre-rendered
    spans switched with tl.set, one per frame, instead of an onUpdate tween.
    """
    a, b, unit = float(sc["from"]), float(sc["to"]), sc.get("unit", "")
    t, n = float(sc.get("t", s + .6)), 24
    dec = max(len(str(sc[k]).split(".")[1]) if "." in str(sc[k]) else 0 for k in ("from", "to"))
    col = tone(C, sc.get("tone", "blue"))
    vals = [a + (b - a) * (1 - (1 - k / n) ** 2) for k in range(n + 1)]
    fmt = lambda k, v: str(sc["from"]) if k == 0 else f"{v:.{dec}f}"
    on = lambda k: ' class="on"' if k == 0 else ""
    spans = "".join(f'<span id="sc{i}v{k}"{on(k)}>{esc(fmt(k, v))}<small>{esc(unit)}</small></span>'
                    for k, v in enumerate(vals))
    js = [f'tl.fromTo("#sc{i} .pn-head",{{opacity:0,y:16}},{{opacity:1,y:0,duration:.3}},{s:.3f});',
          f'tl.fromTo("#sc{i} .pn-num",{{opacity:0,scale:.9}},{{opacity:1,scale:1,duration:.4,ease:"back.out(2)"}},{s + .1:.3f});',
          f'tl.fromTo("#sc{i} .pn-bar",{{opacity:0}},{{opacity:1,duration:.3}},{s + .25:.3f});']
    for k in range(1, n + 1):
        tk = t + k / 30
        js.append(f'tl.set("#sc{i}v{k}",{{opacity:1}},{tk:.3f});tl.set("#sc{i}v{k - 1}",{{opacity:0}},{tk:.3f});')
    js += [f'tl.fromTo("#sc{i}bar",{{width:"100%"}},{{width:"{b / a * 100:.1f}%",duration:{n / 30:.2f},ease:"power2.out",'
           f'immediateRender:false}},{t:.3f});',
           f'tl.fromTo("#sc{i} .pn-chip",{{opacity:0,scale:.6}},{{opacity:1,scale:1,duration:.35,ease:"back.out(3)",'
           f'immediateRender:false}},{t + n / 30:.3f});']
    chip = sc.get("chip") or f"{(b - a) / a * 100:+.0f}%".replace("-", "−")
    left = f'<span>{esc(sc["label"])}</span>' if sc.get("label") else "<span></span>"
    head = f'<div class="pn-head">{esc(sc["title"])}</div>' if sc.get("title") else ""
    body = (f'<div class="pn">{head}<div class="pn-num">{spans}</div>'
            f'<div class="pn-bar"><i id="sc{i}bar" style="background:{col}"></i></div>'
            f'<div class="pn-row">{left}<b class="pn-chip" style="background:{col}">{esc(chip)}</b></div></div>')
    return body, js, [t, t + n / 30]


def clip(i, sc, s, C):
    """A screen recording (the anatomy app) cropped to fill the scene, with labels.

    build.py copies the file and sets _media, _size (source w, h), _box (scene
    w, h), _dur and _track. `crop` is [x, y, w, h] in source pixels (drop the
    app's menus); `from` is the source second to start at; `zoom` a slow push;
    `labels` are chips and `rings` glowing circles, both at x, y in 0-1 of the scene.
    """
    (sw, sh), (bw, bh) = sc["_size"], sc["_box"]
    cx, cy, cw, ch = sc.get("crop") or (0, 0, sw, sh)
    k = max(bw / cw, bh / ch)
    left, top = -cx * k + (bw - cw * k) / 2, -cy * k + (bh - ch * k) / 2
    vid = (f'<video class="clip" id="sc{i}vid" src="{sc["_media"]}" muted data-start="{s:.3f}" '
           f'data-duration="{sc["_dur"]:.3f}" data-media-start="{float(sc.get("from", 0)):.3f}" '
           f'data-track-index="{sc["_track"]}" style="left:{left:.0f}px;top:{top:.0f}px;right:auto;bottom:auto;'
           f'width:{sw * k:.0f}px;height:{sh * k:.0f}px;object-fit:fill"></video>')
    chips, js, pops = [], [], []
    for n, c in enumerate(sc.get("labels", [])):
        col = tone(C, c.get("tone", "red"))
        x = min(max(float(c.get("x", .5)) * bw, 40 + 17 * len(c["text"]) + 28), bw - 40 - 17 * len(c["text"]) - 28)
        chips.append(f'<div class="ac-chip" id="sc{i}c{n}" style="left:{x:.0f}px;top:{float(c.get("y", .5)) * bh:.0f}px;'
                     f'background:{col}">{esc(c["text"])}</div>')
        t = float(c.get("t", s + .4 + n * .5))
        js.append(f'tl.fromTo("#sc{i}c{n}",{{xPercent:-50,yPercent:-50,opacity:0,scale:.6}},{{xPercent:-50,yPercent:-50,'
                  f'opacity:1,scale:1,duration:.35,ease:"back.out(3)",immediateRender:false}},{t:.3f});')
        pops.append(t)
    for n, r in enumerate(sc.get("rings", [])):  # a glowing circle round a muscle the app does not colour
        col, rad = tone(C, r.get("tone", "blue")), float(r.get("r", 120))
        chips.append(f'<div class="ac-ring" id="sc{i}r{n}" style="left:{float(r["x"]) * bw:.0f}px;top:{float(r["y"]) * bh:.0f}px;'
                     f'width:{2 * rad:.0f}px;height:{2 * rad:.0f}px;border-color:{col};'
                     f'box-shadow:0 0 34px {col},inset 0 0 34px {col}"></div>')
        t = float(r.get("t", s + .3))
        js.append(f'tl.fromTo("#sc{i}r{n}",{{xPercent:-50,yPercent:-50,opacity:0,scale:1.5}},{{xPercent:-50,yPercent:-50,'
                  f'opacity:1,scale:1,duration:.45,ease:"back.out(2)",immediateRender:false}},{t:.3f});')
        pops.append(t)
    js.insert(0, f'tl.fromTo("#sc{i} .ac-in",{{scale:1}},{{scale:{float(sc.get("zoom", 1.06))},'
                 f'duration:{sc["_dur"]:.3f},ease:"none",immediateRender:false}},{s:.3f});')
    title = f'<div class="pv-head ac-head">{esc(sc["title"])}</div>' if sc.get("title") else ""
    return f'<div class="ac"><div class="ac-in">{vid}</div>{"".join(chips)}{title}</div>', js, pops


# --- pelvis as the coaches' water bowl, side view facing right ---
# Local units, hip joint at (0, 0); the group is placed and scaled into a
# 1080x960 box. Anterior tilt rotates the bowl forward (clockwise) and the
# water, which stays level, spills over the front rim.
GX, GY, GS, TILT = 540, 650, 1.15, 16
BOWL = ("M -150 -170 L 150 -170 Q 160 -170 156 -158 L 100 30 Q 96 42 84 42 L -84 42 "
        "Q -96 42 -100 30 L -156 -158 Q -160 -170 -150 -170 Z")
VERTS = [(-62, -222, 4), (-57, -284, 0), (-57, -346, -3), (-62, -408, -6)]


def rot(x, y, deg):
    r = math.radians(deg)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)


def _glute(deg):
    ox, oy = rot(-140, -110, deg)
    return f"M {ox:.1f} {oy:.1f} C {ox - 60:.1f} {oy + 120:.1f}, -70 170, 12 150"


def _flexor(deg):
    px, py = rot(120, -60, deg)
    return f"M -30 -330 C 30 -250, {px + 10:.1f} {py - 70:.1f}, {px:.1f} {py:.1f} S 45 95, 22 120"


def _chip(cx, cy, text, col):
    w = 32 * len(text) + 56
    cx = min(max(cx, 40 + w / 2), 1040 - w / 2)
    return (f'<g class="chip"><rect x="{cx - w / 2:.0f}" y="{cy - 34:.0f}" width="{w:.0f}" height="68" rx="34" '
            f'fill="{col}"/><text x="{cx:.0f}" y="{cy + 12:.0f}" text-anchor="middle" font-size="34" '
            f'font-weight="800" fill="#fff">{esc(text)}</text></g>')


def pelvis(i, sc, s, C):
    state = sc.get("state", "tilt")
    red, blue = C["accent"], C["accent2"]
    deg0 = 0 if state == "tilt" else TILT
    line = 'stroke="rgba(240,242,248,.9)" stroke-width="5" stroke-linejoin="round"'
    spine = "".join(f'<rect x="{x - 34}" y="{y - 25}" width="68" height="50" rx="14" transform="rotate({a} {x} {y})" '
                    f'fill="rgba(255,255,255,.06)" stroke="rgba(240,242,248,.65)" stroke-width="4"/>' for x, y, a in VERTS)
    femur = ('<line x1="0" y1="0" x2="26" y2="340" stroke="rgba(240,242,248,.5)" stroke-width="30" stroke-linecap="round"/>'
             '<circle r="26" fill="rgba(240,242,248,.8)"/>')
    water = (f'<clipPath id="cl{i}"><path id="sc{i}clp" d="{BOWL}" transform="rotate({deg0})"/></clipPath>'
             f'<rect x="-220" y="-150" width="440" height="220" fill="{blue}" fill-opacity=".35" clip-path="url(#cl{i})"/>'
             f'<line x1="-220" y1="-150" x2="220" y2="-150" stroke="{blue}" stroke-width="4" stroke-opacity=".8" clip-path="url(#cl{i})"/>')
    bowl = (f'<g id="sc{i}pel" transform="rotate({deg0})"><path d="{BOWL}" fill="rgba(255,255,255,.04)" {line}/>'
            f'<line x1="-150" y1="-170" x2="150" y2="-170" stroke="#fff" stroke-width="9" stroke-linecap="round"/></g>')
    ghost = f'<path d="{BOWL}" fill="none" stroke="rgba(255,255,255,.3)" stroke-width="3" stroke-dasharray="10 10"/>'
    drops = "".join(f'<circle class="drop" cx="{150 + 14 * k}" cy="{-128 + 22 * k}" r="{9 - k}" fill="{blue}"/>' for k in range(3))
    mus, chips, js = "", "", []
    if state == "tilt":
        mus = drops + (f'<path id="sc{i}arr" d="M 70 -230 Q 190 -235 205 -150" fill="none" stroke="{red}" stroke-width="9" '
                       f'stroke-linecap="round" marker-end="url(#ah{i})"/>')
        chips = _chip(820, 170, sc.get("label", "앞으로 기울어짐"), red)
        js += [f'tl.fromTo("#sc{i}pel, #sc{i}clp",{{rotation:0,svgOrigin:"0 0"}},{{rotation:{TILT},duration:1.1,ease:"power2.inOut"}},{s + .25:.3f});',
               f'tl.fromTo("#sc{i}arr",{{strokeDasharray:300,strokeDashoffset:300}},{{strokeDashoffset:0,duration:.5}},{s + .5:.3f});',
               f'tl.fromTo("#sc{i} .drop",{{opacity:0,y:-20}},{{opacity:1,y:40,duration:.7,stagger:.12,ease:"power1.in"}},{s + 1.1:.3f});',
               f'tl.fromTo("#sc{i} .chip",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.35}},{s + .9:.3f});']
    else:
        key = "glute" if state == "glute" else "flexor"
        col = blue if key == "glute" else red
        d = _glute(TILT) if key == "glute" else _flexor(TILT)
        other, ocol = (_flexor(TILT), red) if key == "glute" else (_glute(TILT), blue)
        mus = (f'<path d="{other}" fill="none" stroke="{ocol}" stroke-opacity=".18" stroke-width="24" stroke-linecap="round"/>'
               f'<path id="sc{i}mus" d="{d}" fill="none" stroke="{col}" stroke-width="32" stroke-linecap="round" '
               f'style="filter:drop-shadow(0 0 18px {col})"/>'
               f'<path d="{d}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="8" stroke-linecap="round"/>')
        text = sc.get("label") or ("엉덩이 근육 · 늘어남" if key == "glute" else "고관절 앞 근육 · 긴장")
        chips = _chip(260, 470, text, col) if key == "glute" else _chip(800, 250, text, col)
        js += [f'tl.fromTo("#sc{i}mus",{{strokeDasharray:900,strokeDashoffset:900}},{{strokeDashoffset:0,duration:.7,ease:"power2.out"}},{s + .15:.3f});',
               f'tl.fromTo("#sc{i}mus",{{opacity:1}},{{opacity:.55,duration:.45,repeat:5,yoyo:true}},{s + .9:.3f});',
               f'tl.fromTo("#sc{i} .chip",{{opacity:0,y:20}},{{opacity:1,y:0,duration:.35}},{s + .5:.3f});']
    title = f'<div class="pv-head">{esc(sc["title"])}</div>' if sc.get("title") else ""
    svg = (f'<svg class="pv" viewBox="0 0 1080 960"><defs><marker id="ah{i}" markerWidth="6" markerHeight="6" refX="3" '
           f'refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{red}"/></marker></defs>'
           f'<g transform="translate({GX} {GY}) scale({GS})">{spine}{femur}{ghost}{water}{bowl}{mus}</g>{chips}'
           f'<text x="1000" y="930" text-anchor="end" font-size="30" font-weight="700" fill="rgba(255,255,255,.45)">앞 →</text></svg>')
    js.insert(0, f'tl.fromTo("#sc{i} .pv-head",{{opacity:0,y:16}},{{opacity:1,y:0,duration:.3}},{s:.3f});')
    return f'<div class="pvw">{title}{svg}</div>', js, [s + .5]


BUILDERS = {"keyword": keyword, "compare": compare, "chain": chain, "counter": counter, "clip": clip,
            "pelvis": pelvis}


def css(C):
    return f"""
.lay-split,.lay-full{{background:{C['bg']}}}
.pk{{text-align:center}}
.pk-kick{{font-size:34px;font-weight:800;letter-spacing:.16em;color:{C['muted']};margin-bottom:26px}}
.pk-word{{position:relative;display:inline-block;padding:4px 26px}}
.pk-bar{{position:absolute;left:0;right:0;top:12%;bottom:8%;border-radius:10px;transform-origin:left center;opacity:.9}}
.pk-txt{{position:relative;font-size:124px;font-weight:900;letter-spacing:-.04em;color:#fff;white-space:nowrap}}
.pk-sub{{margin-top:30px;font-size:42px;font-weight:600;color:{C['muted']}}}
.pc{{width:100%}}
.pc-head{{text-align:center;font-size:40px;font-weight:800;color:{C['muted']};margin-bottom:40px;letter-spacing:.04em}}
.pc-row{{display:flex;align-items:center;gap:22px}}
.pc-box{{flex:1;border:3px solid;border-radius:34px;padding:40px 30px;background:{C['panel']};text-align:center}}
.pc-t{{font-size:44px;font-weight:800;color:{C['ink']}}}
.pc-s{{margin-top:14px;font-size:58px;font-weight:900}}
.pc-meter{{margin-top:28px;height:16px;border-radius:9px;background:rgba(255,255,255,.08);overflow:hidden}}
.pc-meter i{{display:block;height:100%;border-radius:9px}}
.pc-mid{{font-size:64px;font-weight:900;color:{C['muted']}}}
.ch{{width:100%;text-align:center}}
.ch-head{{font-size:46px;font-weight:800;color:{C['ink']};margin-bottom:70px}}
.ch-row{{display:flex;align-items:center;justify-content:center}}
.ch-node{{opacity:.35;display:flex;flex-direction:column;align-items:center;gap:26px}}
.ch-dot{{width:120px;height:120px;border-radius:50%;background:{C['panel']};border:4px solid rgba(255,255,255,.25)}}
.ch-lbl{{font-size:50px;font-weight:900;color:{C['ink']}}}
.ch-line{{width:110px;height:8px;margin:0 6px 82px;background:rgba(255,255,255,.12);border-radius:4px;overflow:hidden}}
.ch-line i{{display:block;width:100%;height:100%;transform-origin:left center}}
.pn{{width:100%;text-align:center}}
.pn-head{{font-size:44px;font-weight:800;color:{C['muted']};letter-spacing:.06em;margin-bottom:24px}}
.pn-num{{position:relative;height:290px}}
.pn-num span{{position:absolute;left:0;right:0;top:0;opacity:0;font-size:250px;font-weight:900;letter-spacing:-.04em;line-height:290px;color:#fff;font-variant-numeric:tabular-nums}}
.pn-num span.on{{opacity:1}}
.pn-num small{{font-size:100px;margin-left:10px;letter-spacing:0}}
.pn-bar{{position:relative;margin:50px auto 0;width:820px;height:28px;border-radius:14px;background:rgba(255,255,255,.08);overflow:hidden}}
.pn-bar i{{position:absolute;left:0;top:0;bottom:0;width:100%;border-radius:14px}}
.pn-row{{display:flex;justify-content:space-between;align-items:center;width:820px;margin:26px auto 0;font-size:38px;font-weight:700;color:{C['muted']}}}
.pn-chip{{opacity:0;color:#fff;border-radius:999px;padding:8px 28px;font-weight:900;font-size:42px}}
.ac,.ac-in{{position:absolute;inset:0;overflow:hidden}}
.ac-chip{{position:absolute;z-index:2;opacity:0;white-space:nowrap;font-size:36px;font-weight:800;color:#fff;border-radius:999px;padding:12px 28px;box-shadow:0 8px 30px rgba(0,0,0,.45)}}
.ac-ring{{position:absolute;z-index:2;opacity:0;border:7px solid;border-radius:50%}}
.ac-head{{z-index:2;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.8)}}
.pvw{{position:absolute;inset:0}}
.pv{{position:absolute;inset:0;width:100%;height:100%}}
.pv-head{{position:absolute;top:56px;left:0;right:0;text-align:center;font-size:40px;font-weight:800;color:{C['muted']};letter-spacing:.06em;z-index:1}}
"""
