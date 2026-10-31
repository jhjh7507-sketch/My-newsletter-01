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

Fish Audio instead (free model `s2.1-pro-free`; added 2026-10-31 for the B
account): `fish.py work/script.txt --voice REFERENCE_ID --out work` writes the
same two files, the word times coming from ElevenLabs Speech to Text on the
generated audio. Compare both on the same script before picking a voice.

`--list-voices` prints the voices the key can use. VOICE_ID and speed come from
style.yaml `voice`. Output: `work/voice.mp3`, `work/words.json`.

face:

Raw footage arrives through Google Drive, because chat attachments and the
Drive connector (10 MB) are too small for video. The user uploads the original
to Drive and shares the file or its folder as "anyone with the link". Take the
file id from the link (`/file/d/FILE_ID/`), or list a folder with the Google
Drive connector (`search_files`, `parentId = 'FOLDER_ID'`) and order clips by
`createdTime`. Then:

```bash
curl -sSL -o work/raw.mov "https://drive.usercontent.google.com/download?id=FILE_ID&export=download&confirm=t"
ffprobe -v error -show_entries format=duration work/raw.mov   # an HTML page here means the file is not shared publicly
```

This needs `drive.google.com` and `drive.usercontent.google.com` allowed in the
environment's network settings. When the edit is done, remind the user to set
the sharing back to restricted. Several clips for one reel: join them in
recording order (ffmpeg concat filter, re-encoded) into one RAW before the next step.

```bash
python3 .claude/skills/reels-make/scripts/stt.py RAW.mov --out work      # needs Speech to Text permission
python3 .claude/skills/watch/watch.py RAW.mov --out work/watch --no-stt  # timed frames, to see demos and angles
```

Then pick takes. Read `work/words.json` against the user's script: where a
sentence was said more than once, keep the cleanest complete take (usually the
last), and list every other word index range to drop, plus filler-only runs
("음", "어", false starts). cut.py keeps only speech, so a silent exercise demo
or held stretch disappears unless you keep it: find it on the watch sheets and
pass its source seconds with `--keep`, usually 2-4 seconds of the best part.
Then:

```bash
python3 .claude/skills/reels-make/scripts/cut.py RAW.mov work/words.json --out work --drop 0-14,37-41 --keep 31.5-34 --pad 0.12
```

`--pad` and `--max-gap` come from style.yaml `cut`. HDR footage (iPhone HLG)
is tone-mapped to SDR BT.709 in the cut; left as HDR, HyperFrames promotes the
whole render to HDR and slows to about a second a frame. Output: `work/cut.mp4`,
`work/words_cut.json`. Tell the user how long the raw was, how long the cut
is, and what was dropped.

Then fix the transcript's mistakes in `words_cut.json` before captions are
built: names, places and numbers the recogniser got wrong ("선정점" →
"선정릉점", "사십삼초" → "43초"), and words it split ("힉스 필드" → one word).
Edit the text only and keep the times.

Optional AI voice (the user asked for it; it costs about 1,000 ElevenLabs
credits a minute, so a free month covers under ten minutes):

```bash
python3 .claude/skills/reels-make/scripts/sts.py work/cut.mp4 --voice VOICE_ID --out work/voice_ai.mp3
```

Speech to Speech keeps the user's words and timing, so lips and captions stay
in sync. Use their own cloned voice when it exists. To offer both voices from
one render, put a silent track of the cut's length in the plan as `voice`
(footage is then muted), render once, and mix each voice under the effects
with ffmpeg (`loudnorm=I=-16:TP=-1.5`, then `amix=normalize=0`).

Footage sits below `layout.split_y` and is cropped to fill it, so roughly the
top and bottom fifth of a vertical frame is lost. Check the watch sheets for a
head or feet cut off and say so before rendering. `"focus_y"` in plan.json
moves the crop window: 0 shows the top of the frame, 1 the bottom, default 0.5.
Handheld selfie footage keeps the eyes high in the frame; 0.3 worked for it.

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
- `"layout": "mixed"` (face): the A account's info style, from the reference
  reels of 2026-10-28. Every scene sets `"layout"`: `face` (footage fills the
  frame, quick push-in), `split` (graphic on top, footage below) or `full`
  (graphic fills the frame, its captions drop below it). Captions sit on the
  centre line, white with a black outline; `"hot": true` turns a scene's
  captions yellow, for the one line that must land. Change the scene every
  2-5 seconds, on a sentence. Graphic types (pro.py) show the idea instead of
  repeating the words: `keyword` (text, kicker, sub, tone: one big term with a
  highlight sweep), `compare` (title, note, left and right: title, state, dir
  up/down, tone red/blue; `note` is a source line under the boxes), `chain` (title, items with text and absolute `t`
  seconds, lighting up in order), `counter` (title, from, to, unit, t, label, expr, chip:
  a big number that runs from `from` to `to` at second `t`, with a bar and a
  chip; for "43초가 20.9초가 됐어요", or from 0 with `expr` "68kg × 1.6g" for a
  calculation the user asks to show), `clip` (src, from,
  crop, title, labels, zoom: a screen recording such as the anatomy app,
  cropped to fill the scene; see below), `pelvis` (state tilt/glute/flexor,
  title: the tilting water bowl with the glute stretched in blue and the hip
  flexor tight in red). `glow` red/blue tints the background. Red means tight
  or painful, blue means stretched or weak. Never write a sentence into a
  graphic; the caption already says it.
- Props (props.py) show the thing a sentence names instead of its words:
  `idcard` (image, org, name, role, place, badge, handle, t_name, t_place,
  t_badge: a staff card with the speaker's photo cut from the footage),
  `clock` (date, time, state, route: the real recording time from the file's
  `creationdate` tag), `prompt` (app, attach, text, t, cps: a chat box that
  types the request and sends), `wave` (title, bars, keep, t_scan, t_close,
  from_label, to_label: the speaker's waveform; build bars from the raw audio
  and keep from cut.py's `segments.json`, so the pauses that turn red and close
  up are the ones really cut), `progress` (file, meta, working, done, t, run). For information reels:
  `label` (title, per, food, rows, highlight, t: a nutrition label with the
  row that matters highlighted on its word), `paper` (journal, title, authors,
  chips, finding, note, doi, t: the study a number comes from, finding
  highlighted; check every field against the abstract, keep `finding` to one
  line), `calc` (keys, result, t, gap, t_eq, chip, note: a calculator doing the
  sum the speaker does, use `full`), `amino` (mode split/join, title, label, t,
  t_label: a protein chain breaking into amino acids, or loose amino acids
  joining into a muscle fibre), `scale` (title, tag_a, tag_b, left, right,
  weight, chip, note, t_tip, t_drop, t_win: a balance that tips to the right
  pan, then a weight drops on the left and it tips back; use `full`).
  A face scene with `"card": {"label": "TEST"}` shrinks the footage into a
  framed card with REC and a running timecode. Pick a prop when the sentence
  names an object, a time, an app or an action on the video; keep `keyword` for
  a term to remember. Values on props are real, never invented.
- Layout changes in `mixed` move instead of cutting (style.yaml
  `motion.layout_dur`, 0.45 s): face to split slides the panel down from the
  top while the face slides into the lower half, split to face reverses it,
  a full graphic wipes down over the face and back up, and graphic to graphic
  crossfades. Nothing to set in the plan.
- Anatomy app recordings (`"type": "clip"`): the user records the app on the
  phone or iPad and uploads it to the same Drive folder. Download it next to
  plan.json, run `/watch` on it to find the seconds where the right muscle is
  on screen, and give each scene `"src"`, `"from"` (source second) and
  `"crop": [x, y, w, h]` in source pixels to cut away the app's menus and
  status bar (check the crop on a frame: `ffmpeg -ss FROM -i SRC -frames:v 1
  -vf crop=w:h:x:y f.jpg`). `labels` are chips on the picture: text, x and y
  (0-1 within the scene), tone red/blue, t (absolute seconds). `rings` (x, y,
  r in px, tone, t) circle a muscle the app does not colour, such as the
  glutes in blue. `"still": true` holds the frame at `from` when the app is
  spinning the body too fast for a label to stay on the muscle. Use `split` to
  keep the face below while the muscle is shown, `full` for the moment the
  muscle itself is the point. Keep one clip scene to 2-5 seconds like any other.
  Recordings already made, with their seconds and crops, are listed in
  `.claude/instagram/anatomy.md`; reuse them before asking for a new one.
- Show posture changes and muscle actions (a pelvis tilting, a muscle
  pulling) with the app recording, not AI video: hold a side-view frame
  (`still`), draw the bony line with `lines` and turn it with `rot` about the
  joint it turns on (ASIS-PSIS line about the hip joint; anterior tilt is
  negative when the body faces left), and show the pull with `arrows` along
  the muscle. Point at joints by ringing them on the bare-skeleton view
  (front skeleton held still; `"fit": "contain"` shows a tall crop whole on
  black instead of cropping into the app's menu). Compare two muscles side by
  side (one weak in blue, one tight in red) as one 1080x1920 still: pull each
  frame with ffmpeg (`-ss T -i rec.mp4 -frames:v 1 -vf crop,scale`), paste
  the two 535x1280 panels at y 200 with PIL (ffmpeg overlay of two seeks came
  out black), and use it as a `full` clip with `still`, rings and labels at
  y .145 above the panels (captions sit low at y 1560). Find the landmarks on
  a gridded crop and check them on a marked still before rendering. AI video got the direction wrong both times it was
  tried (2026-10-28) and the user rejected it.
- Moving anatomy with Higgsfield, only where direction does not matter: cut a still
  from the recording where the view holds (side view for posture, the
  muscle highlighted with "Fade others" when it must glow), crop the app's
  menus and pad it to 9:16 with black. Upload it (`media_upload`, then
  `curl -X PUT -H "Content-Type: image/png" -H "If-None-Match: *"
  --data-binary @f.png URL`, then `media_confirm`) and generate with
  `kling3_0`, mode std, sound off, 5 s, 9:16 (7.5 credits). Prompt a
  locked-off camera and a background that stays black. For a posture change
  give an end pose too: edit the still with `flux_kontext` (GPT Image refuses
  the anatomy figure as sensitive) and generate with `wan2_7` 720p, passing
  `start_image` and `end_image` (Kling refused that pair as sensitive; with a
  start image alone it bent the knees into a squat and once turned the
  background grey). Download the result from its `result_url`, look at six
  frames before using it, and use it as a `clip` scene (`src` the mp4).
  Needs `upload.higgsfield.ai` and `d8j0ntlcm91z4.cloudfront.net` allowed in
  the environment's network settings.
- `"layout": "full"` (face, character): footage fills the whole frame, captions
  sit low, and cards are not used. Use it for skits, reactions and anything
  where the face is the joke. Its scene type is `hook` (text; `\n` breaks the
  line): a white outlined line near the top, readable from the first frame.
  End it with a `none` scene. Info reels keep the default split layout.
- `emphasis` terms turn the accent colour in cards and captions. Two or three
  per reel, not more.

## Talk reels (mood edit)

When the footage is a person talking their thoughts (late at night in bed,
a quiet monologue, no demo), edit to the mood of what is said instead of with
info graphics: `scripts/talk.py` (2026-10-30, "세상"). Read the transcript and
pick the 3-4 lines the talk stands on. Open cold on the strongest one (cut it
from the source with `cut.py --drop` everything else and join it in front of the
body cut), then the talk in order. Cut with a gentler `--max-gap 0.9 --pad 0.2`
so the pauses breathe, drop restarts and fillers, and keep the last smile with
`--keep`. Beats alternate wide (`zoom` 1.0) and close (1.14, up to 1.28 for the
line that matters) at sentence starts, so jump cuts read as camera moves. A
`quote` beat stays wide, turns the footage black and white and darker, and sets
the line in serif on the shirt below the chin, each line as it is said;
captions are serif, low, phrase by phrase at the speaker's pauses. `stamp` is
the real recording time from the file's creationdate. No sound effects; the
user picks the music.

```bash
python3 .claude/skills/reels-make/scripts/talk.py work/plan.json --out work/project
```

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
