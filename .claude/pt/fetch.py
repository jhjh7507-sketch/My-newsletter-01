"""Download a class recording from Drive through the Apps Script web app.

python3 .claude/pt/fetch.py <script_url> <key> <file_id> <out.m4a>
The Drive connector cannot return files over about 7 MB, so the web app
sends the file in 8 MB base64 chunks (see "녹음 받기" in run.md).
"""
import base64, json, sys, time, urllib.parse, urllib.request


def get(url):
    for attempt in range(3):
        try:
            body = urllib.request.urlopen(url, timeout=300).read().decode("utf-8")
            return json.loads(body)
        except json.JSONDecodeError:
            sys.exit("Apps Script returned an error page instead of JSON:\n" + body[:500])
        except OSError:
            if attempt == 2:
                raise
            time.sleep(5)


def main():
    url, key, fid, out = sys.argv[1:5]
    start, size, buf = 0, None, bytearray()
    while size is None or start < size:
        r = get(f"{url}?{urllib.parse.urlencode({'key': key, 'id': fid, 'start': start})}")
        if "error" in r:
            sys.exit(f"error: {r['error']}")
        size = r["size"]
        chunk = base64.b64decode(r["data"])
        if not chunk:
            break
        buf += chunk
        start += len(chunk)
    if len(buf) != size:
        sys.exit(f"incomplete download: {len(buf)}/{size}")
    open(out, "wb").write(buf)
    print(out, size)


if __name__ == "__main__":
    main()
