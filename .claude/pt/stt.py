"""Transcribe class recordings with ElevenLabs Scribe.

python3 .claude/pt/stt.py <out_prefix> <audio> [<audio> ...]
Writes <out_prefix>.txt: one line per ~20 s chunk, "[mm:ss] text", files in order.
"""
import json, os, subprocess, sys, tempfile, urllib.request, uuid


def scribe(path):
    with tempfile.TemporaryDirectory() as td:
        mp3 = os.path.join(td, "a.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", "16000",
                        "-b:a", "64k", mp3], check=True)
        audio = open(mp3, "rb").read()
    b = uuid.uuid4().hex
    body = b"".join(
        f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, v in [("model_id", "scribe_v1"), ("language_code", "kor"),
                     ("timestamps_granularity", "word"), ("tag_audio_events", "false")])
    body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\n'
             f'Content-Type: audio/mpeg\r\n\r\n').encode() + audio + f'\r\n--{b}--\r\n'.encode()
    req = urllib.request.Request(
        "https://api.elevenlabs.io/v1/speech-to-text", data=body,
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"],
                 "Content-Type": f"multipart/form-data; boundary={b}"})
    return json.load(urllib.request.urlopen(req, timeout=900))


def lines(r):
    out, cur, t0 = [], [], None
    for w in r.get("words", []):
        if w.get("type") == "spacing":
            continue
        if t0 is None:
            t0 = w["start"]
        cur.append(w["text"])
        if w["start"] - t0 >= 20 or (w["text"].endswith((".", "?", "!")) and w["start"] - t0 > 8):
            out.append(f"[{int(t0 // 60):02d}:{int(t0 % 60):02d}] " + " ".join(cur))
            cur, t0 = [], None
    if cur:
        out.append(f"[{int(t0 // 60):02d}:{int(t0 % 60):02d}] " + " ".join(cur))
    return out


def main():
    prefix, files = sys.argv[1], sys.argv[2:]
    text = []
    for i, f in enumerate(files, 1):
        text += [f"===== {i}: {os.path.basename(f)} =====", *lines(scribe(f)), ""]
    open(prefix + ".txt", "w", encoding="utf-8").write("\n".join(text))
    print(prefix + ".txt")


if __name__ == "__main__":
    main()
