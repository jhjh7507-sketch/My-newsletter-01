#!/usr/bin/env python3
"""Synthesize the small sound-effect kit with FFmpeg (no downloads, no credits).

  python3 sfx.py out_dir/

Writes whoosh.wav (scene change), pop.wav (item appears), tick.wav (number).
"""
import os
import subprocess
import sys

KIT = {
    "whoosh": "anoisesrc=d=0.45:c=pink:a=0.6,highpass=f=400,lowpass=f=5000,"
              "afade=t=in:d=0.18,afade=t=out:st=0.2:d=0.25",
    "pop": "sine=f=880:d=0.09,afade=t=out:st=0.02:d=0.07,volume=0.8",
    "tick": "sine=f=1600:d=0.04,afade=t=out:st=0.01:d=0.03,volume=0.5",
}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "sfx"
    os.makedirs(out, exist_ok=True)
    for name, graph in KIT.items():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", graph, "-ar", "44100",
                        "-ac", "2", os.path.join(out, f"{name}.wav")], check=True)
    print(f"sfx kit in {out}: {', '.join(KIT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
