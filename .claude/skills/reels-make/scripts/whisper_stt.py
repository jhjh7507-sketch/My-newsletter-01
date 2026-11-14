#!/usr/bin/env python3
"""Word-timed transcript with the free local Whisper (faster-whisper), same output as stt.py.

  python3 whisper_stt.py audio_or_video --out work/dir [--prompt "승모근, 쇄골"]

Writes work/dir/words.json ([{text, start, end}], seconds). Costs nothing. The model
(Systran/faster-whisper-medium, 1.5 GB) is kept in work/whisper/medium; download it once with
  HF_HUB_DISABLE_XET=1 python3 -c "from huggingface_hub import snapshot_download as s; s('Systran/faster-whisper-medium', local_dir='work/whisper/medium')"
(needs huggingface.co and us.aws.cdn.hf.co allowed in the network settings, added 2026-11-14).
Use it when ElevenLabs credits run out; fix spelling against the script before building.
"""
import argparse, json, os, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = os.path.normpath(os.path.join(HERE, '../../../../work/whisper/medium'))

ap = argparse.ArgumentParser()
ap.add_argument('media'); ap.add_argument('--out', default='work')
ap.add_argument('--model', default=DEFAULT_MODEL); ap.add_argument('--prompt', default='')
a = ap.parse_args()
m = WhisperModel(a.model, device='cpu', compute_type='int8', cpu_threads=os.cpu_count() or 4)
# decode with ffmpeg ourselves: the bundled PyAV decoder breaks on newer PyAV releases
pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.media, '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                     capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.float32)
segs, info = m.transcribe(audio, language='ko', beam_size=5, word_timestamps=True, vad_filter=False,
                          initial_prompt=a.prompt or None, condition_on_previous_text=False)
words = []
for s in segs:
    for w in s.words or []:
        t = w.word.strip()
        if t:
            words.append({'text': t, 'start': round(w.start, 3), 'end': round(w.end, 3)})
os.makedirs(a.out, exist_ok=True)
json.dump(words, open(os.path.join(a.out, 'words.json'), 'w'), ensure_ascii=False, indent=0)
print(f'{len(words)} words, {info.duration:.1f}s', file=sys.stderr)
