---
name: reels-make
description: >-
  Make a finished Instagram Reel MP4 from one topic line (faceless), from the
  user's own recorded video plus script (face), or with an AI character
  (character): script, voice, motion graphics, word-timed captions, sound
  effects, cover and caption text, following .claude/instagram/style.yaml.
  Use when the user says "make a reel about X", "주제: ...", "릴스 만들어줘",
  "편집해줘" with a video, or wants the daily reel produced.
---

# reels-make

Topic in, MP4 out. Three modes share one pipeline:

| mode | input | voice | picture |
| --- | --- | --- | --- |
| `faceless` | topic line | ElevenLabs TTS | full-frame cards |
| `face` | user's raw video + script | the user's own audio | cards on top, footage below |
| `character` | topic line + AI character | ElevenLabs TTS | cards on top, character below |

**Reference video + one line** ("이 영상처럼, 주제: ..."): run `/reels-style` on
the attached video first, write its rules to `work/style.yaml` (a copy of
`.claude/instagram/style.yaml` with the measured values; keep the shared file
unless the user says to adopt the new look), match the reference's hook
formula and scene rhythm in the script, then build with `--style work/style.yaml`.
Tell the user which parts of the reference could not be matched (its own
footage, 3D, photos, unusual effects) and what was used instead.

Before anything, read `.claude/instagram/strategy.md`, `.claude/instagram/style.yaml`
and, if they exist, `voice.md` and `swipe.md` in the same folder. Work in
`work/` at the repo root (it is scratch; never commit it).

## 1. Script

- faceless / character: write the script with `/ig-reel` (hook from swipe.md
  formulas, then body, then one CTA). Spoken Korean, 25-45 seconds, short
  sentences. Run it through `/ig-human`. Save as `work/script.txt`.
- face: the user's script is the reference for what should be said; the
  recording is the source of truth.
- Show the script to the user before spending voice credits, unless they said
  to run straight through.

## 2. Voice and word timings

faceless / character:

```bash
python3 .claude/skills/reels-make/scripts/tts.py work/script.txt --voice VOICE_ID --speed 1.05 --out work
```

`--list-voices` prints the voices the key can use. VOICE_ID and speed come from
style.yaml `voice`. Output: `work/voice.mp3`, `work/words.json`.

face:

```bash
python3 .claude/skills/reels-make/scripts/stt.py RAW.mov --out work      # needs Speech to Text permission
```

Then pick takes. Read `work/words.json` against the user's script: where a
sentence was said more than once, keep the cleanest complete take (usually the
last), and list every other word index range to drop, plus filler-only runs
("음", "어", false starts). Then:

```bash
python3 .claude/skills/reels-make/scripts/cut.py RAW.mov work/words.json --out work --drop 0-14,37-41 --pad 0.12
```

`--pad` and `--max-gap` come from style.yaml `cut`. Output: `work/cut.mp4`,
`work/words_cut.json`. Tell the user how long the raw was, how long the cut
is, and what was dropped.

## 3. Plan the picture

Write `work/plan.json`. One scene per idea, 2-5 seconds each; a scene changes
when the spoken sentence changes. Anchor scenes with `at` (the first words of
the sentence that starts the scene, as spoken) rather than guessing seconds.

```json
{
  "mode": "faceless",
  "voice": "voice.mp3",
  "words": "words.json",
  "emphasis": ["혈당 스파이크", "30분"],
  "scenes": [
    {"start": 0, "type": "title", "kicker": "건강 상식", "title": "공복 커피, 혈당 스파이크 옵니다", "highlight": "혈당 스파이크"},
    {"at": "이유는", "type": "list", "title": "이유 3가지", "items": ["코르티솔 상승", "인슐린 저항", "위산 자극"]},
    {"at": "딱", "type": "stat", "label": "커피는 기상 후", "value": "30", "unit": "분 뒤"}
  ]
}
```

- Paths are relative to plan.json.
- face: `"video": "cut.mp4", "words": "words_cut.json"` and no `voice`.
- character: `"voice"` plus either `"image": "character.png"` (one still,
  slow push-ins, no extra credits) or `"video": "char_clip.mp4"` (muted
  character footage under the TTS voice).
- Scene types: `title` (title, sub), `list` (title, items), `steps` (title,
  items, active), `stat` (label, value, unit; counts up), `quote` (text),
  `none` (no card, footage only). `kicker` is the small pill label on any card.
- `emphasis` terms turn the accent colour in cards and captions. Two or three
  per reel, not more.

## 4. Build and render

```bash
python3 .claude/skills/reels-make/scripts/build.py work/plan.json --style .claude/instagram/style.yaml --out work/project
bash .claude/skills/reels-make/scripts/render.sh work/project work/reel.mp4
```

build.py chunks captions to style.yaml's `min_words`-`max_words`, places them,
adds whoosh/pop effects on scene and item changes, and writes
`work/project/captions.srt`. Rendering takes about 3 seconds per second of
video. HyperFrames is pinned in render.sh; do not bump it casually.

## 5. Check before handing over

Pull frames and look at them:

```bash
for t in 1 5 10 15 20; do ffmpeg -v error -y -ss $t -i work/reel.mp4 -frames:v 1 -vf scale=270:-1 work/f_$t.jpg; done
ffmpeg -v error -y -i work/f_1.jpg -i work/f_5.jpg -i work/f_10.jpg -i work/f_15.jpg -i work/f_20.jpg -filter_complex hstack=5 work/check.jpg
```

Fix and rebuild when: a caption covers a face or a card, text wraps badly,
a card is empty, or audio and captions drift. Then copy the result where the
user can open it (repo `output/YYYY-MM-DD-slug.mp4`, git-ignored) and send it.

## 6. Publish kit

Write the caption with `/ig-caption` and the cover line (the hook, 2 lines
max). If a scheduler is connected (Blotato), offer to schedule; never post
without an explicit yes. Character mode: remind the user to switch on
Instagram's AI label. Append the reel to `.claude/instagram/log.md` (date,
hook, topic, mode) and offer to commit it.

## Character setup (once per character)

With the Higgsfield connector: plan the character with the user (look, age,
style, personality; never a real person, never a fake doctor or pharmacist),
call `ai_influencer_prepare` for the design and its credit price, and only run
`ai_influencer_generate` after the user approves the cost. Save the chosen
image as `.claude/instagram/character.png` and describe it in
`.claude/instagram/character.md`. Character video clips (`generate_video`)
cost far more; quote first, every time.

## Rules

- No credits are spent (TTS, Higgsfield) without the user knowing the plan.
- Copy formulas from references, never their words or footage.
- Health topics: no diagnosis or treatment claims; general information,
  sources where a number is stated.
