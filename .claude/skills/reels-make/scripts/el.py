"""Shared ElevenLabs helpers: API calls and word grouping. Stdlib only."""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

API = "https://api.elevenlabs.io"


def key():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not k:
        sys.exit("ELEVENLABS_API_KEY is not set (add it in the environment settings)")
    return k


def call(method, path, body=None, headers=None, timeout=300):
    h = {"xi-api-key": key()}
    h.update(headers or {})
    req = urllib.request.Request(API + path, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        sys.exit(f"ElevenLabs {method} {path} -> HTTP {e.code}: {detail}")


def call_json(method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    raw = call(method, path, body, {"Content-Type": "application/json"} if body else None)
    return json.loads(raw)


def multipart(fields, files):
    """fields: {name: str}, files: {name: (filename, bytes, mime)} -> (body, content_type)"""
    b = uuid.uuid4().hex
    out = []
    for n, v in fields.items():
        out += [f"--{b}", f'Content-Disposition: form-data; name="{n}"', "", str(v)]
    parts = "\r\n".join(out).encode() + b"\r\n" if out else b""
    for n, (fn, data, mime) in files.items():
        parts += (f"--{b}\r\nContent-Disposition: form-data; name=\"{n}\"; filename=\"{fn}\"\r\n"
                  f"Content-Type: {mime}\r\n\r\n").encode() + data + b"\r\n"
    parts += f"--{b}--\r\n".encode()
    return parts, f"multipart/form-data; boundary={b}"


def chars_to_words(chars, starts, ends):
    """Group character-level alignment into space-separated words (Korean eojeol)."""
    words, cur, s, e = [], "", None, None
    for c, cs, ce in zip(chars, starts, ends):
        if c.isspace():
            if cur:
                words.append({"text": cur, "start": round(s, 3), "end": round(e, 3)})
            cur, s, e = "", None, None
            continue
        if s is None:
            s = cs
        cur += c
        e = ce
    if cur:
        words.append({"text": cur, "start": round(s, 3), "end": round(e, 3)})
    return words
