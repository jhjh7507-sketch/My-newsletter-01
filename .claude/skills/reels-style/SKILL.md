---
name: reels-style
description: >-
  Turn reference reels (screen recordings or downloaded videos the user
  uploads) into numeric edit rules - caption position and length, cut pace,
  card motion, colours, layout - saved as .claude/instagram/style.yaml for
  /reels-make. Use when the user sends reference reels, says "analyze this
  reel", "copy this editing style", "make my edits look like this", or before
  the first /reels-make in a new niche.
---

# reels-style

Reads how a reference reel is edited and writes it down as numbers. Copies the
edit grammar (where captions sit, how long a shot lasts, how cards move), never
the creator's script, footage or branding.

Read `.claude/instagram/strategy.md` first.

## Step 1: measure

Uploaded files land under `/root/.claude/uploads/...`. Measure every reference
in one call:

```bash
python3 .claude/skills/reels-style/measure.py REF1.mov REF2.mp4 --out work/style
```

Per video it writes `stats.json` (duration, cuts, shot median, speech ratio,
loudness, dominant colours) and `sheet_*.jpg` contact sheets with timestamps.
Screen recordings include Instagram's own UI and the recorder's screen size:
judge positions inside the reel frame only, then scale to 1080x1920.

## Step 2: look

Read every contact sheet. For each reference note:

| field | what to look for |
| --- | --- |
| layout | full-frame graphics, graphics top + face bottom (where is the seam), face full-frame |
| caption | y position (in 1080x1920), size, words per caption (1-3? 2-4?), box or outline, highlight colour |
| cards | what types appear (title, checklist, steps, big number, quote), how they enter (rise, pop, slide) |
| pace | stats.json shot median and cuts per 10s; how often the graphic changes |
| face | push-in on emphasis? how much, how many frames |
| colours | background, card, accent (cross-check stats.json colours) |
| sound | effects on card changes or items? voice loudness (LUFS) |

When several references disagree, take the median, and say which reference
each rule came from.

## Step 3: write the rules

Update `.claude/instagram/style.yaml`. Keep its keys; only change values. Add
a `source:` list naming the references and the date. Show the user the
before/after of the values that changed, then remind them to commit (the file
only survives the session once committed).

```yaml
caption: {y_split: 864, y_full: 1420, size: 62, min_words: 1, max_words: 3, box: true}
motion: {card_rise_px: 52, ease: expo.out, in_dur: 0.5, stagger: 0.12,
         face_push_frames: 37, face_push_scale: 1.06}
cut: {pad: 0.12, max_gap: 0.35}
```

Delete `work/style` afterwards; contact sheets are not worth keeping.
