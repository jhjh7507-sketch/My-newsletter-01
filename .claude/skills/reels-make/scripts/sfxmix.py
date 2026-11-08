"""Mix sound effects (and optional background music) under the voice of a rendered reel.
python3 sfxmix.py events.json voice_src video_in out.mp4 [--bgm bgm.mp3 --bgm-db -26]
events.json: [{"t": sec, "f": file, "peak_db": -18, "align": "peak"|"onset"}]"""
import json, subprocess, sys, argparse, numpy as np, os
ap = argparse.ArgumentParser()
ap.add_argument("events"); ap.add_argument("voice"); ap.add_argument("video"); ap.add_argument("out")
ap.add_argument("--dir", default="."); ap.add_argument("--bgm"); ap.add_argument("--bgm-db", type=float, default=-26)
a = ap.parse_args()
ev = json.load(open(a.events))
dur = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",a.video]))
def analyse(f):
    raw = subprocess.run(['ffmpeg','-v','error','-i',f,'-ac','1','-ar','44100','-f','f32le','-'],capture_output=True).stdout
    x = np.abs(np.frombuffer(raw, np.float32)); env = np.convolve(x, np.ones(441)/441, 'same')
    return 20*np.log10(x.max()+1e-9), np.argmax(env > env.max()*0.1)/44100, env.argmax()/44100
inputs = ["-i", a.video, "-i", a.voice]; labels = []
fc = ["[1:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v][key]"]
cache = {}
for k, e in enumerate(ev):
    f = os.path.join(a.dir, e["f"])
    if f not in cache: cache[f] = analyse(f)
    mx, on, pk = cache[f]
    off = pk if e.get("align", "peak") == "peak" else on
    start = e["t"] - off
    trim = max(0.0, -start); start = max(0.0, start)
    inputs += ["-i", f]; n = k + 2
    fc.append(f"[{n}:a]atrim=start={trim:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,"
              f"volume={e.get('peak_db',-18) - mx:.2f}dB,adelay={int(start*1000)}|{int(start*1000)}[s{n}]")
    labels.append(f"[s{n}]")
mix_in = "[v]" + "".join(labels)
fc.append(f"{mix_in}amix=inputs={1+len(labels)}:normalize=0:dropout_transition=0[fx]")
last = "[fx]"
if a.bgm:
    inputs += ["-i", a.bgm]; b = len(ev) + 2
    # music sits low and dips further while the voice talks
    fc.append(f"[{b}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur:.3f},volume={a.bgm_db}dB,"
              f"afade=t=in:d=1.2,afade=t=out:st={dur-2.0:.3f}:d=2.0[bg]")
    fc.append("[bg][key]sidechaincompress=threshold=0.03:ratio=2:attack=80:release=600[bgd]")
    fc.append("[fx][bgd]amix=inputs=2:normalize=0[mx]"); last = "[mx]"
if not a.bgm: fc.append("[key]anullsink")
fc.append(f"{last}alimiter=limit=0.95,apad[aout]")
open(a.out + ".fc", "w").write(";\n".join(fc))
subprocess.run(["ffmpeg","-v","error","-y",*inputs,"-filter_complex_script",a.out+".fc",
                "-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","160k","-shortest",
                "-movflags","+faststart",a.out], check=True)
os.remove(a.out + ".fc")
print("wrote", a.out, len(ev), "effects", "+ bgm" if a.bgm else "")
