"""Props for the "mixed" info layout: things that act out a sentence.

Where pro.py draws ideas (a keyword, a comparison, a diagram), these show the
object the speaker names, the way the reference reels do (얼굴반반3, 얼굴반반편집):
an ID card when they introduce themselves, a clock when they say what time it
is, a chat box typing when they say they asked an AI, the real waveform losing
its pauses when they say the silences get cut, a progress card when they hand
the video over. Same signature as pro.py builders: (i, sc, s, C) -> (html, js, pops).
Numbers and times on them are real values from the footage, never invented.
"""
from pro import esc, tone

ICON = {
    "spark": '<svg viewBox="0 0 24 24"><path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8z" fill="currentColor"/></svg>',
    "moon": '<svg viewBox="0 0 24 24"><path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5z" fill="currentColor"/></svg>',
    "film": '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3" fill="none" stroke="currentColor" stroke-width="2"/>'
            '<path d="M10 9.5v5l4.5-2.5z" fill="currentColor"/></svg>',
    "check": '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "clip": '<svg viewBox="0 0 24 24"><path d="M8 12.5l6.5-6.5a3 3 0 0 1 4.2 4.2l-8 8a5 5 0 0 1-7-7L11 4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    "up": '<svg viewBox="0 0 24 24"><path d="M12 19V5M6 11l6-6 6 6" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}


def _in(sel, t, y=24, d=.4, extra=""):
    return (f'tl.fromTo("{sel}",{{opacity:0,y:{y}}},{{opacity:1,y:0,duration:{d},ease:"expo.out",'
            f'immediateRender:false{extra}}},{t:.3f});')


def _ticker(i, name, vals, t, rate=30):
    """Pre-rendered numbers switched with tl.set (the renderer seeks with events off)."""
    spans = "".join(f'<span id="sc{i}{name}{k}"{" class=on" if k == 0 else ""}>{esc(v)}</span>' for k, v in enumerate(vals))
    js = [f'tl.set("#sc{i}{name}{k}",{{opacity:1}},{t + k / rate:.3f});tl.set("#sc{i}{name}{k - 1}",{{opacity:0}},{t + k / rate:.3f});'
          for k in range(1, len(vals))]
    return spans, js


def idcard(i, sc, s, C):
    """Staff card: photo, name, role, workplace, and a title badge that lands on its word."""
    t_name, t_place, t_badge = (float(sc.get(k, s + d)) for k, d in (("t_name", .4), ("t_place", 1.2), ("t_badge", 2.0)))
    photo = f'<div class="id-photo" style="background-image:url({sc["_image"]})"></div>' if sc.get("_image") else '<div class="id-photo"></div>'
    html = (f'<div class="id"><div class="id-card" id="sc{i}card"><div class="id-top"><span>{esc(sc.get("org", ""))}</span>'
            f'<b>STAFF</b></div><div class="id-body">{photo}<div class="id-info">'
            f'<div class="id-name" id="sc{i}nm">{esc(sc["name"])}</div>'
            f'<div class="id-role" id="sc{i}rl">{esc(sc.get("role", ""))}</div>'
            f'<div class="id-place" id="sc{i}pl"><span class="id-bar" id="sc{i}plb"></span><span>{esc(sc.get("place", ""))}</span></div>'
            f'<div class="id-badge" id="sc{i}bd">{esc(sc.get("badge", ""))}</div></div></div>'
            f'<div class="id-foot">{esc(sc.get("handle", ""))}</div></div></div>')
    js = [f'tl.fromTo("#sc{i}card",{{opacity:0,y:70,rotation:-5}},{{opacity:1,y:0,rotation:0,duration:.6,ease:"expo.out",immediateRender:false}},{s:.3f});',
          _in(f"#sc{i}nm", t_name), _in(f"#sc{i}rl", t_name + .15),
          _in(f"#sc{i}pl", t_place),
          f'tl.fromTo("#sc{i}plb",{{scaleX:0}},{{scaleX:1,duration:.5,ease:"power3.inOut",immediateRender:false}},{t_place + .15:.3f});',
          f'tl.fromTo("#sc{i}bd",{{opacity:0,scale:.5}},{{opacity:1,scale:1,duration:.45,ease:"back.out(3)",immediateRender:false}},{t_badge:.3f});']
    return html, js, [t_badge]


def clock(i, sc, s, C):
    """The real recording time (from the file), a blinking colon and a dot walking from A to B."""
    hh, mm = sc["time"].split(":")
    route = ""
    if sc.get("route"):
        a, b = sc["route"]
        route = (f'<div class="ck-route"><span>{esc(a)}</span><div class="ck-line"><i id="sc{i}dot"></i></div>'
                 f'<span>{esc(b)}</span></div>')
    html = (f'<div class="ck"><div class="ck-date" id="sc{i}dt">{esc(sc.get("date", ""))}</div>'
            f'<div class="ck-time" id="sc{i}tm">{hh}<span class="ck-colon" id="sc{i}cl">:</span>{mm}</div>'
            f'<div class="ck-state" id="sc{i}st"><span class="ck-ic">{ICON["moon"]}</span>{esc(sc.get("state", ""))}</div>{route}</div>')
    dur = float(sc.get("_dur", 2))
    js = [_in(f"#sc{i}dt", s), f'tl.fromTo("#sc{i}tm",{{opacity:0,scale:.92}},{{opacity:1,scale:1,duration:.5,ease:"expo.out",immediateRender:false}},{s + .05:.3f});',
          _in(f"#sc{i}st", s + .3),
          f'tl.fromTo("#sc{i}cl",{{opacity:1}},{{opacity:.15,duration:.5,repeat:{max(1, int(dur / .5))},yoyo:true,ease:"none",immediateRender:false}},{s + .5:.3f});']
    if route:
        js += [_in(f"#sc{i} .ck-route", s + .45),
               f'tl.fromTo("#sc{i}dot",{{left:"0%"}},{{left:"62%",duration:{max(.8, dur - .6):.2f},ease:"power1.inOut",immediateRender:false}},{s + .5:.3f});']
    return html, js, [s + .3]


def prompt(i, sc, s, C):
    """A chat box with an attached file; the request types itself in, then sends."""
    text, t0 = sc["text"], float(sc.get("t", s + .5))
    rate = float(sc.get("cps", 14))  # characters a second
    chars = "".join(f'<span class="pm-ch" id="sc{i}c{k}">{esc(c) if c != " " else "&nbsp;"}</span>' for k, c in enumerate(text))
    att = (f'<div class="pm-att" id="sc{i}att"><span class="pm-ic">{ICON["clip"]}</span>{esc(sc["attach"])}</div>'
           if sc.get("attach") else "")
    html = (f'<div class="pm"><div class="pm-win" id="sc{i}win"><div class="pm-head"><span class="pm-logo">{ICON["spark"]}</span>'
            f'{esc(sc.get("app", "AI"))}</div>{att}<div class="pm-input"><div class="pm-txt">{chars}'
            f'<i class="pm-caret" id="sc{i}cr"></i></div><b class="pm-send" id="sc{i}sd">{ICON["up"]}</b></div></div></div>')
    js = [f'tl.fromTo("#sc{i}win",{{opacity:0,y:50,scale:.96}},{{opacity:1,y:0,scale:1,duration:.5,ease:"expo.out",immediateRender:false}},{s:.3f});']
    if att:
        js.append(_in(f"#sc{i}att", s + .25, 14))
    js += [f'tl.set("#sc{i}c{k}",{{display:"inline"}},{t0 + k / rate:.3f});' for k in range(len(text))]
    t_send = t0 + len(text) / rate + .15
    js += [f'tl.fromTo("#sc{i}cr",{{opacity:1}},{{opacity:0,duration:.4,repeat:{max(1, int((t_send - s) / .4))},yoyo:true,ease:"none",immediateRender:false}},{s:.3f});',
           f'tl.fromTo("#sc{i}sd",{{background:"rgba(255,255,255,.12)",scale:1}},{{background:"{tone(C, sc.get("tone", "red"))}",scale:1.12,'
           f'duration:.2,yoyo:true,repeat:1,immediateRender:false}},{t_send:.3f});']
    return html, js, [t_send]


def wave(i, sc, s, C):
    """The speaker's own waveform; the pauses the cut removed turn red as a playhead passes, then close up."""
    bars, keep = sc["bars"], sc["keep"]
    red = tone(C, "red")
    t_scan, t_close = float(sc.get("t_scan", s + .4)), float(sc.get("t_close", s + 1.6))
    groups, cur, kind = [], [], None
    for h, k in zip(bars, keep):
        if kind is not None and k != kind:
            groups.append((kind, cur))
            cur = []
        cur.append(h)
        kind = k
    groups.append((kind, cur))
    parts, js, n, cuts = [], [], len(bars), 0
    pos = 0
    for g, (k, hs) in enumerate(groups):
        inner = "".join(f'<i style="height:{max(6, h * 300):.0f}px"></i>' for h in hs)
        if k:
            parts.append(f'<span class="wv-keep">{inner}</span>')
        else:
            parts.append(f'<span class="wv-cut" id="sc{i}g{g}">{inner}</span>')
            tg = t_scan + (pos + len(hs) / 2) / n * 1.0
            js.append(f'tl.to("#sc{i}g{g} i",{{background:"{red}",duration:.15,immediateRender:false}},{tg:.3f});')
            js.append(f'tl.to("#sc{i}g{g}",{{width:0,opacity:0,duration:.6,ease:"power3.inOut",immediateRender:false}},{t_close + cuts * .03:.3f});')
            cuts += 1
        pos += len(hs)
    html = (f'<div class="wv"><div class="wv-head" id="sc{i}hd">{esc(sc.get("title", ""))}</div>'
            f'<div class="wv-row" id="sc{i}row">{"".join(parts)}<b class="wv-head-line" id="sc{i}ph"></b></div>'
            f'<div class="wv-foot"><span id="sc{i}a">{esc(sc.get("from_label", ""))}</span>'
            f'<b class="wv-chip" id="sc{i}b" style="background:{red}">{esc(sc.get("to_label", ""))}</b></div></div>')
    js = [_in(f"#sc{i}hd", s), f'tl.fromTo("#sc{i}row",{{opacity:0}},{{opacity:1,duration:.35,immediateRender:false}},{s + .1:.3f});',
          _in(f"#sc{i}a", s + .2),
          f'tl.fromTo("#sc{i}ph",{{left:"0%",opacity:1}},{{left:"100%",opacity:1,duration:1.0,ease:"none",immediateRender:false}},{t_scan:.3f});',
          f'tl.to("#sc{i}ph",{{opacity:0,duration:.2,immediateRender:false}},{t_scan + 1.0:.3f});'] + js + [
          f'tl.fromTo("#sc{i}b",{{opacity:0,scale:.6}},{{opacity:1,scale:1,duration:.4,ease:"back.out(3)",immediateRender:false}},{t_close + .7:.3f});']
    return html, js, [t_scan, t_close + .7]


def progress(i, sc, s, C):
    """The file handed over: a bar fills with a live percentage, then a check and the result."""
    t0, dur = float(sc.get("t", s + .4)), float(sc.get("run", 1.2))
    n = 24
    vals = [f"{round(100 * (1 - (1 - k / n) ** 2))}%" for k in range(n + 1)]
    spans, tick = _ticker(i, "p", vals, t0, rate=n / dur)
    blue = tone(C, "blue")
    html = (f'<div class="pg"><div class="pg-card" id="sc{i}card"><div class="pg-file"><span class="pg-ic">{ICON["film"]}</span>'
            f'<div><b>{esc(sc.get("file", ""))}</b><small>{esc(sc.get("meta", ""))}</small></div></div>'
            f'<div class="pg-bar"><i id="sc{i}bar" style="background:{blue}"></i></div>'
            f'<div class="pg-row"><span class="pg-st"><span id="sc{i}s1">{esc(sc.get("working", "편집 중"))}</span>'
            f'<span id="sc{i}s2" class="pg-ok" style="color:{blue}"><span class="pg-ck">{ICON["check"]}</span>{esc(sc.get("done", "완료"))}</span></span>'
            f'<span class="pg-pct">{spans}</span></div></div></div>')
    t1 = t0 + dur
    js = [f'tl.fromTo("#sc{i}card",{{opacity:0,y:50}},{{opacity:1,y:0,duration:.5,ease:"expo.out",immediateRender:false}},{s:.3f});',
          f'tl.fromTo("#sc{i}bar",{{width:"0%"}},{{width:"100%",duration:{dur},ease:"power2.out",immediateRender:false}},{t0:.3f});',
          f'tl.set("#sc{i}s1",{{opacity:0}},{t1:.3f});',
          f'tl.fromTo("#sc{i}s2",{{opacity:0,scale:.7}},{{opacity:1,scale:1,duration:.35,ease:"back.out(3)",immediateRender:false}},{t1:.3f});'] + tick
    return html, js, [t1]


BUILDERS = {"idcard": idcard, "clock": clock, "prompt": prompt, "wave": wave, "progress": progress}


def css(C):
    return f"""
.id,.ck,.pm,.wv,.pg{{width:100%;display:flex;flex-direction:column;align-items:center}}
.id-card{{width:860px;border-radius:40px;padding:34px 40px 30px;background:linear-gradient(160deg,{C['panel']},#0b0e15);border:2px solid rgba(255,255,255,.09);box-shadow:0 30px 80px rgba(0,0,0,.55)}}
.id-top{{display:flex;justify-content:space-between;align-items:center;font-size:28px;font-weight:800;letter-spacing:.18em;color:{C['muted']}}}
.id-top b{{font-size:22px;letter-spacing:.2em;color:#fff;background:rgba(255,255,255,.1);padding:6px 16px;border-radius:999px}}
.id-body{{display:flex;gap:38px;align-items:center;margin-top:30px}}
.id-photo{{flex:none;width:210px;height:260px;border-radius:26px;background:#222 center/cover;box-shadow:0 0 0 3px rgba(255,255,255,.12)}}
.id-info{{display:flex;flex-direction:column;align-items:flex-start;gap:12px}}
.id-name{{font-size:84px;font-weight:900;color:#fff;letter-spacing:-.03em;line-height:1}}
.id-role{{font-size:34px;font-weight:700;color:{C['muted']}}}
.id-place{{position:relative;font-size:36px;font-weight:800;color:#fff;padding:2px 8px}}
.id-place span:last-child{{position:relative}}
.id-bar{{position:absolute;left:0;right:0;top:15%;bottom:5%;background:{C['accent']};opacity:.85;border-radius:8px;transform-origin:left center}}
.id-badge{{margin-top:6px;font-size:38px;font-weight:900;color:#fff;background:{C['accent']};padding:8px 26px;border-radius:999px;box-shadow:0 0 34px {C['accent']}88}}
.id-foot{{margin-top:24px;font-size:28px;font-weight:700;color:{C['muted']};letter-spacing:.04em}}
.ck-date{{font-size:40px;font-weight:700;color:{C['muted']}}}
.ck-time{{font-size:230px;font-weight:900;color:#fff;letter-spacing:-.04em;line-height:1;font-variant-numeric:tabular-nums}}
.ck-state{{display:flex;align-items:center;gap:14px;font-size:44px;font-weight:800;color:#fff;margin-top:8px}}
.ck-ic{{width:44px;height:44px;color:{C['caption_accent']}}}.ck-ic svg,.pm-logo svg,.pm-ic svg,.pm-send svg,.pg-ic svg,.pg-ck svg{{width:100%;height:100%}}
.ck-route{{display:flex;align-items:center;gap:18px;margin-top:30px;font-size:30px;font-weight:700;color:{C['muted']}}}
.ck-line{{position:relative;width:360px;height:6px;border-radius:3px;background:rgba(255,255,255,.15)}}
.ck-line i{{position:absolute;top:50%;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;background:{C['accent2']};box-shadow:0 0 24px {C['accent2']}}}
.pm-win{{width:900px;border-radius:36px;padding:30px 32px;background:{C['panel']};border:2px solid rgba(255,255,255,.08);box-shadow:0 30px 80px rgba(0,0,0,.55)}}
.pm-head{{display:flex;align-items:center;gap:14px;font-size:34px;font-weight:800;color:#fff}}
.pm-logo{{width:40px;height:40px;color:#d97757}}
.pm-att{{display:inline-flex;align-items:center;gap:12px;margin-top:24px;font-size:30px;font-weight:700;color:#fff;background:rgba(255,255,255,.08);padding:12px 22px;border-radius:18px}}
.pm-ic{{width:30px;height:30px;color:{C['muted']}}}
.pm-input{{display:flex;align-items:center;gap:20px;margin-top:22px;padding:22px 22px 22px 28px;border-radius:28px;background:#0b0e15;border:2px solid rgba(255,255,255,.1)}}
.pm-txt{{flex:1;font-size:46px;font-weight:700;color:#fff;min-height:58px;white-space:nowrap;overflow:hidden}}
.pm-ch{{display:none}}
.pm-caret{{display:inline-block;width:4px;height:48px;margin-left:4px;vertical-align:-8px;background:#fff}}
.pm-send{{flex:none;width:68px;height:68px;padding:16px;border-radius:50%;color:#fff;background:rgba(255,255,255,.12)}}
.wv-head{{font-size:40px;font-weight:800;color:{C['muted']};margin-bottom:46px;letter-spacing:.02em}}
.wv-row{{position:relative;display:flex;align-items:center;justify-content:center;height:320px;max-width:980px}}
.wv-keep,.wv-cut{{display:flex;align-items:center;overflow:hidden;flex:none}}
.wv-row i{{flex:none;width:7px;margin:0 1.5px;border-radius:4px;background:rgba(244,246,250,.85)}}
.wv-cut i{{background:rgba(244,246,250,.35)}}
.wv-head-line{{position:absolute;top:-20px;bottom:-20px;width:4px;margin-left:-2px;background:{C['caption_accent']};box-shadow:0 0 20px {C['caption_accent']};opacity:0}}
.wv-foot{{display:flex;align-items:center;gap:26px;margin-top:46px;font-size:40px;font-weight:800;color:{C['muted']}}}
.wv-chip{{color:#fff;font-size:46px;font-weight:900;padding:10px 30px;border-radius:999px}}
.pg-card{{width:880px;border-radius:36px;padding:36px 38px;background:{C['panel']};border:2px solid rgba(255,255,255,.08);box-shadow:0 30px 80px rgba(0,0,0,.55)}}
.pg-file{{display:flex;align-items:center;gap:22px}}
.pg-ic{{width:76px;height:76px;padding:14px;border-radius:20px;color:#fff;background:rgba(255,255,255,.08)}}
.pg-file b{{display:block;font-size:42px;font-weight:800;color:#fff}}
.pg-file small{{display:block;margin-top:6px;font-size:30px;font-weight:600;color:{C['muted']}}}
.pg-bar{{margin-top:34px;height:18px;border-radius:9px;background:rgba(255,255,255,.08);overflow:hidden}}
.pg-bar i{{display:block;height:100%;width:0;border-radius:9px}}
.pg-row{{display:flex;justify-content:space-between;align-items:center;margin-top:22px;font-size:38px;font-weight:800;color:{C['muted']}}}
.pg-st{{position:relative;height:50px;min-width:400px}}
.pg-st>span{{position:absolute;left:0;top:0;white-space:nowrap}}
.pg-ok{{display:flex;align-items:center;gap:10px;opacity:0}}.pg-ck{{width:42px;height:42px}}
.pg-pct{{position:relative;width:150px;height:50px;color:#fff;font-variant-numeric:tabular-nums}}
.pg-pct span{{position:absolute;right:0;top:0;opacity:0}}.pg-pct span.on{{opacity:1}}
"""
